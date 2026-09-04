from dataclasses import dataclass
from pathlib import Path
from typing import Any, LiteralString, cast

from psycopg import Connection, sql
from psycopg.types.json import Jsonb

from immo_pipelines.cadastre.contract import SchemaChangeError
from immo_pipelines.cadastre.geojson import iter_features
from immo_pipelines.cadastre.processor import (
    CadastreFeatureProcessor,
    NormalizedFeature,
)


@dataclass(frozen=True)
class ImportOutcome:
    import_run_id: str
    source_rows: int
    normalized_rows: int
    quarantined_rows: int
    deduplicated_rows: int
    skipped_as_idempotent: bool


class CadastreImporter:
    """Load one release x department x layer partition without exposing it as active."""

    def __init__(self, connection: Connection[Any], processor: CadastreFeatureProcessor) -> None:
        self.connection = connection
        self.processor = processor

    def import_file(
        self,
        *,
        import_run_id: str,
        release_id: str,
        department_code: str,
        layer: str,
        raw_asset_id: int,
        source_path: Path,
        idempotency_key: str,
    ) -> ImportOutcome:
        existing = self.connection.execute(
            """
            SELECT id, status, source_row_count, normalized_row_count, quarantined_row_count,
                   deduplicated_row_count
              FROM meta.import_run WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        ).fetchone()
        if existing is not None and existing[1] == "succeeded":
            return ImportOutcome(
                import_run_id=str(existing[0]),
                source_rows=int(existing[2]),
                normalized_rows=int(existing[3]),
                quarantined_rows=int(existing[4]),
                deduplicated_rows=int(existing[5]),
                skipped_as_idempotent=True,
            )
        if existing is not None:
            active = self.connection.execute(
                "SELECT 1 FROM meta.active_dataset_release WHERE release_id = %s", (release_id,)
            ).fetchone()
            if active is not None:
                raise RuntimeError("A published release cannot be destructively retried")
            self.connection.execute("DELETE FROM meta.import_run WHERE id = %s", (existing[0],))

        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'running',
                      jsonb_build_object('layer', %s::text, 'raw_asset_id', %s::bigint))
            """,
            (
                import_run_id,
                release_id,
                department_code,
                idempotency_key,
                layer,
                raw_asset_id,
            ),
        )
        self._create_staging_tables()

        source_count = 0
        quarantine_count = 0
        try:
            with self.connection.cursor().copy(
                """
                COPY cadastre_feature_stage (
                    is_quarantined, layer, source_feature_id, source_row_number,
                    properties, geometry_wkt, record_checksum, was_repaired,
                    repair_method, transformation_version, reason_code,
                    reason_detail, source_geometry, repair_attempted
                ) FROM STDIN
                """
            ) as feature_copy:
                for source_count, feature in enumerate(iter_features(source_path), start=1):
                    try:
                        result = self.processor.process(layer, source_count, feature)
                    except SchemaChangeError as exc:
                        feature_id = feature.get("id")
                        raise SchemaChangeError(
                            f"{layer} source row {source_count}, feature {feature_id}: {exc}"
                        ) from exc
                    if isinstance(result, NormalizedFeature):
                        feature_copy.write_row(
                            (
                                False,
                                result.layer,
                                result.source_feature_id,
                                result.source_row_number,
                                Jsonb(result.properties),
                                result.geometry_wkt,
                                result.record_checksum,
                                result.was_repaired,
                                result.repair_method,
                                result.transformation_version,
                                None,
                                None,
                                None,
                                False,
                            )
                        )
                    else:
                        feature_copy.write_row(
                            (
                                True,
                                result.layer,
                                result.source_feature_id,
                                result.source_row_number,
                                Jsonb(result.source_properties),
                                None,
                                None,
                                False,
                                None,
                                result.transformation_version,
                                result.reason_code,
                                result.reason_detail,
                                Jsonb(result.source_geometry),
                                result.repair_attempted,
                            )
                        )
                        quarantine_count += 1
            self._publish_staging(
                layer=layer,
                release_id=release_id,
                department_code=department_code,
                raw_asset_id=raw_asset_id,
                import_run_id=import_run_id,
            )
            normalized_count = self._inserted_count(layer, import_run_id)
            self.connection.execute(
                """
                INSERT INTO meta.transformation_run (
                    id, import_run_id, transformation_code, transformation_version,
                    parameters, input_row_count, output_row_count, repaired_row_count,
                    completed_at, status
                )
                SELECT %s, %s, 'normalize_geometry', %s,
                       jsonb_build_object('source_srid', 4326, 'canonical_srid', 2154),
                       %s, %s, count(*) FILTER (WHERE was_repaired),
                       clock_timestamp(), 'succeeded'
                  FROM cadastre_feature_stage
                 WHERE NOT is_quarantined
                """,
                (
                    f"{import_run_id}:normalize",
                    import_run_id,
                    self.processor.contract.normalization_version,
                    source_count,
                    normalized_count,
                ),
            )
            duplicate_count_row = self.connection.execute(
                """
                SELECT
                    coalesce(sum(occurrences - 1) FILTER (WHERE variants = 1), 0),
                    coalesce(sum(occurrences - 1) FILTER (WHERE variants > 1), 0)
                  FROM (
                    SELECT count(*) AS occurrences,
                           count(DISTINCT record_checksum) AS variants
                      FROM cadastre_feature_stage
                     WHERE NOT is_quarantined
                     GROUP BY source_feature_id HAVING count(*) > 1
                  ) duplicates
                """
            ).fetchone()
            exact_duplicate_count = int(duplicate_count_row[0]) if duplicate_count_row else 0
            conflicting_duplicate_count = int(duplicate_count_row[1]) if duplicate_count_row else 0
            explained_count = normalized_count + quarantine_count + exact_duplicate_count
            self.connection.execute(
                """
                INSERT INTO meta.data_quality_check (
                    release_id, import_run_id, check_code, check_version, scope_type,
                    scope_code, layer, status, severity, blocks_publication,
                    observed_value, expected_value, details
                ) VALUES
                    (%(release_id)s, %(import_run_id)s, 'source_vs_normalized_count', '2',
                     'department', %(department_code)s, %(layer)s,
                     CASE WHEN %(source_count)s = %(explained_count)s
                          THEN 'passed' ELSE 'failed' END,
                     CASE WHEN %(source_count)s = %(explained_count)s
                          THEN 'info' ELSE 'error' END,
                     true, %(explained_count)s, %(source_count)s,
                     jsonb_build_object(
                         'normalized', %(normalized_count)s::bigint,
                         'quarantined', %(quarantine_count)s::bigint,
                         'deduplicated', %(exact_duplicate_count)s::bigint
                     )),
                    (%(release_id)s, %(import_run_id)s, 'exact_duplicate_record', '1',
                     'department', %(department_code)s, %(layer)s,
                     CASE WHEN %(exact_duplicate_count)s = 0 THEN 'passed' ELSE 'warning' END,
                     CASE WHEN %(exact_duplicate_count)s = 0 THEN 'info' ELSE 'warning' END,
                     false, %(exact_duplicate_count)s, 0,
                     jsonb_build_object('strategy', 'identical_record_checksum')),
                    (%(release_id)s, %(import_run_id)s, 'conflicting_duplicate_source_id', '1',
                     'department', %(department_code)s, %(layer)s,
                     CASE WHEN %(conflicting_duplicate_count)s = 0
                          THEN 'passed' ELSE 'failed' END,
                     CASE WHEN %(conflicting_duplicate_count)s = 0
                          THEN 'info' ELSE 'error' END,
                     true, %(conflicting_duplicate_count)s, 0,
                     jsonb_build_object('strategy', 'distinct_record_checksum'))
                """,
                {
                    "release_id": release_id,
                    "import_run_id": import_run_id,
                    "department_code": department_code,
                    "layer": layer,
                    "source_count": source_count,
                    "explained_count": explained_count,
                    "normalized_count": normalized_count,
                    "quarantine_count": quarantine_count,
                    "exact_duplicate_count": exact_duplicate_count,
                    "conflicting_duplicate_count": conflicting_duplicate_count,
                },
            )
            self.connection.execute(
                """
                INSERT INTO meta.geometry_quarantine (
                    release_id, import_run_id, raw_asset_id, layer, source_feature_id,
                    source_row_number, reason_code, reason_detail, source_geometry,
                    source_properties, repair_attempted, transformation_version
                )
                SELECT %s, %s, %s, layer, source_feature_id, source_row_number,
                       reason_code, reason_detail, source_geometry, properties,
                       repair_attempted, transformation_version
                  FROM cadastre_feature_stage
                 WHERE is_quarantined
                """,
                (release_id, import_run_id, raw_asset_id),
            )
            self.connection.execute(
                """
                UPDATE meta.import_run SET
                    status = 'succeeded', completed_at = clock_timestamp(), source_row_count = %s,
                    normalized_row_count = %s, quarantined_row_count = %s,
                    deduplicated_row_count = %s
                 WHERE id = %s
                """,
                (
                    source_count,
                    normalized_count,
                    quarantine_count,
                    exact_duplicate_count,
                    import_run_id,
                ),
            )
            self.connection.execute("RESET ROLE")
            self.connection.commit()
        except (OSError, ValueError) as exc:
            self.connection.rollback()
            self._record_failure(
                import_run_id,
                release_id,
                department_code,
                idempotency_key,
                source_count,
                layer,
                raw_asset_id,
                exc,
            )
            raise

        return ImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_count,
            normalized_rows=normalized_count,
            quarantined_rows=quarantine_count,
            deduplicated_rows=exact_duplicate_count,
            skipped_as_idempotent=False,
        )

    def _inserted_count(self, layer: str, import_run_id: str) -> int:
        tables = {
            "parcelles": ("reference", "cadastral_parcel"),
            "batiments": ("reference", "cadastral_building"),
            "communes": ("reference", "administrative_area"),
        }
        try:
            schema_name, table_name = tables[layer]
        except KeyError as exc:
            raise ValueError(f"Unsupported cadastre layer {layer}") from exc
        query = sql.SQL("SELECT count(*) FROM {}.{} WHERE import_run_id = %s").format(
            sql.Identifier(schema_name), sql.Identifier(table_name)
        )
        row = self.connection.execute(query, (import_run_id,)).fetchone()
        return int(row[0]) if row else 0

    def _create_staging_tables(self) -> None:
        self.connection.execute(
            """
            CREATE TEMP TABLE cadastre_feature_stage (
                is_quarantined boolean NOT NULL,
                layer text NOT NULL,
                source_feature_id text,
                source_row_number bigint NOT NULL,
                properties jsonb NOT NULL,
                geometry_wkt text,
                record_checksum char(64),
                was_repaired boolean NOT NULL,
                repair_method text,
                transformation_version text NOT NULL,
                reason_code text,
                reason_detail text,
                source_geometry jsonb,
                repair_attempted boolean NOT NULL,
                CONSTRAINT feature_stage_shape CHECK (
                    (is_quarantined AND reason_code IS NOT NULL AND reason_detail IS NOT NULL)
                    OR (NOT is_quarantined AND source_feature_id IS NOT NULL
                        AND geometry_wkt IS NOT NULL AND record_checksum IS NOT NULL
                        AND reason_code IS NULL AND reason_detail IS NULL)
                )
            ) ON COMMIT DROP
            """
        )

    def _publish_staging(
        self,
        *,
        layer: str,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        import_run_id: str,
    ) -> None:
        statements = {
            "parcelles": """
                INSERT INTO reference.cadastral_parcel (
                    release_id, raw_asset_id, import_run_id, source_feature_id,
                    source_row_number, cadastral_id, department_code, commune_code,
                    prefix, section, number, stated_area_m2, surveyed,
                    source_created_on, source_updated_on, geom, was_repaired,
                    repair_method, transformation_version, record_checksum
                )
                SELECT %(release_id)s, %(raw_asset_id)s, %(import_run_id)s,
                       source_feature_id, source_row_number, properties->>'id',
                       %(department_code)s, properties->>'commune',
                       coalesce(properties->>'prefixe', '000'), properties->>'section',
                       properties->>'numero', (properties->>'contenance')::integer,
                       (properties->>'arpente')::boolean,
                       (properties->>'created')::date, (properties->>'updated')::date,
                       ST_GeomFromText(geometry_wkt, 2154)::geometry(MultiPolygon, 2154),
                       was_repaired, repair_method, transformation_version, record_checksum
                  FROM cadastre_feature_stage
                 WHERE layer = 'parcelles' AND NOT is_quarantined
                ON CONFLICT (release_id, cadastral_id) DO NOTHING
            """,
            "batiments": """
                INSERT INTO reference.cadastral_building (
                    release_id, raw_asset_id, import_run_id, source_feature_id,
                    source_row_number, department_code, commune_code, cadastral_type,
                    cadastral_name, source_created_on, source_updated_on, geom,
                    was_repaired, repair_method, transformation_version, record_checksum
                )
                SELECT %(release_id)s, %(raw_asset_id)s, %(import_run_id)s,
                       source_feature_id, source_row_number, %(department_code)s,
                       properties->>'commune', properties->>'type', properties->>'nom',
                       (properties->>'created')::date, (properties->>'updated')::date,
                       ST_GeomFromText(geometry_wkt, 2154)::geometry(MultiPolygon, 2154),
                       was_repaired, repair_method, transformation_version, record_checksum
                  FROM cadastre_feature_stage
                 WHERE layer = 'batiments' AND NOT is_quarantined
                ON CONFLICT (release_id, source_feature_id) DO NOTHING
            """,
            "communes": """
                INSERT INTO reference.administrative_area (
                    release_id, raw_asset_id, import_run_id, source_feature_id, source_row_number,
                    area_type, code, name, department_code, geom, record_checksum
                )
                SELECT %(release_id)s, %(raw_asset_id)s, %(import_run_id)s, source_feature_id,
                       source_row_number, 'commune', properties->>'id',
                       properties->>'nom', %(department_code)s,
                       ST_GeomFromText(geometry_wkt, 2154)::geometry(MultiPolygon, 2154),
                       record_checksum
                  FROM cadastre_feature_stage
                 WHERE layer = 'communes' AND NOT is_quarantined
                ON CONFLICT (release_id, area_type, code, source_feature_id) DO NOTHING
            """,
        }
        try:
            statement = statements[layer]
        except KeyError as exc:
            raise ValueError(f"Unsupported cadastre layer {layer}") from exc
        self.connection.execute(
            sql.SQL(cast(LiteralString, statement)),
            {
                "release_id": release_id,
                "raw_asset_id": raw_asset_id,
                "import_run_id": import_run_id,
                "department_code": department_code,
            },
        )

    def _record_failure(
        self,
        import_run_id: str,
        release_id: str,
        department_code: str,
        idempotency_key: str,
        source_count: int,
        layer: str,
        raw_asset_id: int,
        error: Exception,
    ) -> None:
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, completed_at, source_row_count, error_message, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'failed', clock_timestamp(), %s, %s,
                      jsonb_build_object('layer', %s::text, 'raw_asset_id', %s::bigint))
            ON CONFLICT (id) DO UPDATE SET
                status = 'failed', completed_at = clock_timestamp(),
                source_row_count = EXCLUDED.source_row_count,
                error_message = EXCLUDED.error_message
            """,
            (
                import_run_id,
                release_id,
                department_code,
                idempotency_key,
                source_count,
                str(error)[:4000],
                layer,
                raw_asset_id,
            ),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
