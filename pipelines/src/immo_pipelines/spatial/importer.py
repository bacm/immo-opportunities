from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from immo_pipelines.spatial.ban import BanQuarantine, iter_ban_records
from immo_pipelines.spatial.rnb import RnbQuarantine, iter_rnb_records


@dataclass(frozen=True, slots=True)
class SpatialImportOutcome:
    import_run_id: str
    source_rows: int
    normalized_rows: int
    quarantined_rows: int
    skipped_as_idempotent: bool


class BanImporter:
    def __init__(self, connection: Connection[Any]) -> None:
        self.connection = connection

    def import_archive(
        self,
        *,
        import_run_id: str,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        source_path: Path,
        idempotency_key: str,
    ) -> SpatialImportOutcome:
        existing = self.connection.execute(
            """
            SELECT id, status, source_row_count, normalized_row_count, quarantined_row_count
              FROM meta.import_run WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        ).fetchone()
        if existing is not None and existing[1] == "succeeded":
            return SpatialImportOutcome(
                import_run_id=str(existing[0]),
                source_rows=int(existing[2]),
                normalized_rows=int(existing[3]),
                quarantined_rows=int(existing[4]),
                skipped_as_idempotent=True,
            )
        if existing is not None:
            self.connection.execute("DELETE FROM meta.import_run WHERE id = %s", (existing[0],))

        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'running',
                      jsonb_build_object('layer', 'addresses', 'raw_asset_id', %s::bigint))
            """,
            (import_run_id, release_id, department_code, idempotency_key, raw_asset_id),
        )
        self._create_stage()
        source_count = 0
        quarantine_count = 0
        with self.connection.cursor().copy(
            """
            COPY ban_stage (
                is_quarantined, source_row_number, ban_id, fantoir_id,
                house_number, repetition_index, street_name, postal_code,
                commune_code, commune_name, display_label, normalized_label,
                position_type, source_position, municipality_certified,
                geometry_wkt, cadastral_ids, properties, record_checksum,
                reason_code, reason_detail
            ) FROM STDIN
            """
        ) as copy:
            for record in iter_ban_records(source_path):
                source_count += 1
                if isinstance(record, BanQuarantine):
                    quarantine_count += 1
                    copy.write_row(
                        (
                            True,
                            record.source_row_number,
                            record.ban_id,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            Jsonb([]),
                            Jsonb(record.source_properties),
                            None,
                            record.reason_code,
                            record.reason_detail,
                        )
                    )
                else:
                    copy.write_row(
                        (
                            False,
                            record.source_row_number,
                            record.ban_id,
                            record.fantoir_id,
                            record.house_number,
                            record.repetition_index,
                            record.street_name,
                            record.postal_code,
                            record.commune_code,
                            record.commune_name,
                            record.display_label,
                            record.normalized_label,
                            record.position_type,
                            record.source_position,
                            record.municipality_certified,
                            record.geometry_wkt,
                            Jsonb(record.cadastral_ids),
                            Jsonb(record.properties),
                            record.record_checksum,
                            None,
                            None,
                        )
                    )
        conflicting_row = self.connection.execute(
            """
            WITH conflicting_ids AS (
                SELECT ban_id
                  FROM ban_stage
                 WHERE NOT is_quarantined
                 GROUP BY ban_id
                HAVING count(DISTINCT record_checksum) > 1
            ), quarantined AS (
                UPDATE ban_stage AS stage
                   SET is_quarantined = true,
                       reason_code = 'conflicting_ban_identifier',
                       reason_detail = 'BAN identifier occurs with contradictory source records'
                  FROM conflicting_ids
                 WHERE stage.ban_id = conflicting_ids.ban_id
                   AND NOT stage.is_quarantined
                RETURNING stage.ban_id
            )
            SELECT count(*), count(DISTINCT ban_id) FROM quarantined
            """
        ).fetchone()
        conflicting_row_count = int(conflicting_row[0]) if conflicting_row else 0
        conflicting_identifier_count = int(conflicting_row[1]) if conflicting_row else 0
        quarantine_count += conflicting_row_count
        self._publish_stage(
            release_id=release_id,
            department_code=department_code,
            raw_asset_id=raw_asset_id,
            import_run_id=import_run_id,
        )
        normalized_count_row = self.connection.execute(
            "SELECT count(DISTINCT ban_id) FROM ban_stage WHERE NOT is_quarantined"
        ).fetchone()
        normalized_count = int(normalized_count_row[0]) if normalized_count_row else 0
        deduplicated_row = self.connection.execute(
            """
            SELECT count(*) - count(DISTINCT ban_id)
              FROM ban_stage
             WHERE NOT is_quarantined
            """
        ).fetchone()
        deduplicated_count = int(deduplicated_row[0]) if deduplicated_row else 0
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, import_run_id, check_code, check_version, scope_type,
                scope_code, layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            ) VALUES
                (%(release_id)s, %(import_run_id)s, 'source_vs_normalized_count', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(source_count)s = %(normalized_count)s + %(quarantine_count)s
                                                + %(deduplicated_count)s
                      THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %(source_count)s = %(normalized_count)s + %(quarantine_count)s
                                                + %(deduplicated_count)s
                      THEN 'info' ELSE 'error' END,
                 true, %(normalized_count)s + %(quarantine_count)s + %(deduplicated_count)s,
                 %(source_count)s,
                 jsonb_build_object(
                     'normalized', %(normalized_count)s::bigint,
                     'quarantined', %(quarantine_count)s::bigint,
                     'deduplicated', %(deduplicated_count)s::bigint
                 )),
                (%(release_id)s, %(import_run_id)s, 'exact_duplicate_ban_record', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(deduplicated_count)s = 0 THEN 'passed' ELSE 'warning' END,
                 CASE WHEN %(deduplicated_count)s = 0 THEN 'info' ELSE 'warning' END,
                 false, %(deduplicated_count)s, 0,
                 jsonb_build_object('policy', 'retain one canonical record; preserve raw asset')),
                (%(release_id)s, %(import_run_id)s, 'conflicting_ban_identifier', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(conflicting_identifier_count)s = 0 THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %(conflicting_identifier_count)s = 0 THEN 'info' ELSE 'error' END,
                 true, %(conflicting_identifier_count)s, 0,
                 jsonb_build_object('quarantined_rows', %(conflicting_row_count)s::bigint))
            """,
            {
                "release_id": release_id,
                "import_run_id": import_run_id,
                "department_code": department_code,
                "source_count": source_count,
                "normalized_count": normalized_count,
                "quarantine_count": quarantine_count,
                "deduplicated_count": deduplicated_count,
                "conflicting_identifier_count": conflicting_identifier_count,
                "conflicting_row_count": conflicting_row_count,
            },
        )
        self.connection.execute(
            """
            UPDATE meta.import_run SET
                status = 'succeeded', completed_at = clock_timestamp(),
                source_row_count = %s, normalized_row_count = %s,
                quarantined_row_count = %s, deduplicated_row_count = %s
             WHERE id = %s
            """,
            (
                source_count,
                normalized_count,
                quarantine_count,
                deduplicated_count,
                import_run_id,
            ),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        return SpatialImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_count,
            normalized_rows=normalized_count,
            quarantined_rows=quarantine_count,
            skipped_as_idempotent=False,
        )

    def _create_stage(self) -> None:
        self.connection.execute(
            """
            CREATE TEMP TABLE ban_stage (
                is_quarantined boolean NOT NULL,
                source_row_number bigint NOT NULL,
                ban_id text,
                fantoir_id text,
                house_number text,
                repetition_index text,
                street_name text,
                postal_code text,
                commune_code text,
                commune_name text,
                display_label text,
                normalized_label text,
                position_type text,
                source_position text,
                municipality_certified boolean,
                geometry_wkt text,
                cadastral_ids jsonb NOT NULL,
                properties jsonb NOT NULL,
                record_checksum char(64),
                reason_code text,
                reason_detail text
            ) ON COMMIT DROP
            """
        )

    def _publish_stage(
        self,
        *,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        import_run_id: str,
    ) -> None:
        parameters = {
            "release_id": release_id,
            "department_code": department_code,
            "raw_asset_id": raw_asset_id,
            "import_run_id": import_run_id,
        }
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_observation (
                release_id, raw_asset_id, entity_type, entity_id, source_entity_type,
                source_identifier, source_row_number, geometry, properties,
                record_checksum
            )
            SELECT %(release_id)s, %(raw_asset_id)s, 'address', 'address:ban:' || ban_id,
                   'ban_address', ban_id, source_row_number,
                   ST_GeomFromText(geometry_wkt, 2154), properties, record_checksum
              FROM ban_stage WHERE NOT is_quarantined
            ON CONFLICT (release_id, source_entity_type, source_identifier, record_checksum)
            DO NOTHING
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO reference.address (
                id, commune_code, department_code, display_label, normalized_label,
                house_number, repetition_index, street_name, postal_code,
                position_type, is_municipality_certified, geom
            )
            SELECT DISTINCT ON (ban_id)
                   'address:ban:' || ban_id, commune_code, %(department_code)s,
                   display_label, normalized_label, house_number, repetition_index,
                   street_name, postal_code, position_type, municipality_certified,
                   ST_GeomFromText(geometry_wkt, 2154)::geometry(Point, 2154)
              FROM ban_stage WHERE NOT is_quarantined
             ORDER BY ban_id, source_row_number
            ON CONFLICT (id) DO UPDATE SET
                commune_code = EXCLUDED.commune_code,
                department_code = EXCLUDED.department_code,
                display_label = EXCLUDED.display_label,
                normalized_label = EXCLUDED.normalized_label,
                house_number = EXCLUDED.house_number,
                repetition_index = EXCLUDED.repetition_index,
                street_name = EXCLUDED.street_name,
                postal_code = EXCLUDED.postal_code,
                position_type = EXCLUDED.position_type,
                is_municipality_certified = EXCLUDED.is_municipality_certified,
                geom = EXCLUDED.geom,
                updated_at = clock_timestamp()
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT DISTINCT ON (ban_id)
                   'address', 'address:ban:' || ban_id, 'DS-05', 'ban_address',
                   ban_id, %(release_id)s, %(release_id)s, true
              FROM ban_stage WHERE NOT is_quarantined
             ORDER BY ban_id, source_row_number
            ON CONFLICT ON CONSTRAINT entity_source_identifier_pkey DO UPDATE SET
                last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp()
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT DISTINCT ON (ban_id, fantoir_id)
                   'address', 'address:ban:' || ban_id, 'DS-05', 'fantoir_address',
                   fantoir_id, %(release_id)s, %(release_id)s, false
              FROM ban_stage WHERE NOT is_quarantined AND fantoir_id IS NOT NULL
             ORDER BY ban_id, fantoir_id, source_row_number
            ON CONFLICT ON CONSTRAINT entity_source_identifier_pkey DO UPDATE SET
                last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp()
            """,
            parameters,
        )
        self.connection.execute(
            """
            WITH candidates AS MATERIALIZED (
                SELECT stage.ban_id, parcel.id AS parcel_id,
                       ST_Covers(geometry.geom, address.geom) AS point_covered,
                       ST_DWithin(geometry.geom, address.geom, 10) AS within_ten_meters
                  FROM ban_stage AS stage
                  CROSS JOIN LATERAL
                       jsonb_array_elements_text(stage.cadastral_ids) AS cadastral_id
                  JOIN reference.parcel AS parcel ON parcel.cadastral_id = cadastral_id
                  JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
                  CROSS JOIN LATERAL (
                      SELECT ST_GeomFromText(stage.geometry_wkt, 2154) AS geom
                  ) AS address
                 WHERE NOT stage.is_quarantined
            )
            INSERT INTO meta.entity_match (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, critical,
                blocks_publication, rationale, evidence, release_ids
            )
            SELECT 'ban-parcel:' || candidate.ban_id || ':' || candidate.parcel_id,
                   'address', 'address:ban:' || candidate.ban_id,
                   'parcel', candidate.parcel_id,
                   'source_relation', 'ban-cad-parcelles', '1',
                   CASE WHEN candidate.point_covered THEN 0.99
                        WHEN candidate.within_ten_meters THEN 0.95
                        ELSE 0.8 END,
                   CASE WHEN candidate.within_ten_meters
                        THEN 'certain' ELSE 'ambiguous' END,
                   true,
                   NOT candidate.within_ten_meters,
                   'BAN experimental cad_parcelles relation checked against active parcel geometry',
                   jsonb_build_object(
                       'point_covered', candidate.point_covered,
                       'within_ten_meters', candidate.within_ten_meters,
                       'source_relation_experimental', true
                   ), jsonb_build_array(%(release_id)s::text)
              FROM candidates AS candidate
            ON CONFLICT (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, algorithm_code, algorithm_version
            ) DO NOTHING
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.entity_match (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, critical,
                blocks_publication, rationale, evidence, release_ids
            )
            SELECT 'rnb-ban:' || observation.entity_id || ':' || stage.ban_id,
                   'building', observation.entity_id,
                   'address', 'address:ban:' || stage.ban_id,
                   'source_relation', 'rnb-ban-identifier', '1', 1,
                   'certain', true, false,
                   'RNB address relation uses the exact BAN interoperability key',
                   jsonb_build_object('cle_interop_ban', stage.ban_id),
                   jsonb_build_array(observation.release_id, %(release_id)s::text)
              FROM ban_stage AS stage
              JOIN meta.entity_source_observation AS observation
                ON observation.entity_type = 'building'
               AND observation.source_entity_type = 'rnb_building'
              CROSS JOIN LATERAL jsonb_array_elements(
                  observation.properties->'addresses'
              ) AS rnb_address
             WHERE NOT stage.is_quarantined
               AND rnb_address->>'cle_interop_ban' = stage.ban_id
            ON CONFLICT (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, algorithm_code, algorithm_version
            ) DO NOTHING
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO reference.property_unit_member (
                property_unit_id, entity_type, entity_id, member_role, match_id
            )
            SELECT 'property-unit:parcel:' || parcel.cadastral_id,
                   'address', matched.left_entity_id, 'supporting', matched.id
              FROM meta.entity_match AS matched
              JOIN reference.parcel AS parcel ON parcel.id = matched.right_entity_id
             WHERE matched.algorithm_code = 'ban-cad-parcelles'
               AND matched.algorithm_version = '1'
               AND matched.decision = 'certain'
               AND matched.release_ids ? %(release_id)s
            ON CONFLICT (property_unit_id, entity_type, entity_id) DO UPDATE SET
                member_role = EXCLUDED.member_role, match_id = EXCLUDED.match_id
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.geometry_quarantine (
                release_id, import_run_id, raw_asset_id, layer, source_feature_id,
                source_row_number, reason_code, reason_detail, source_properties,
                repair_attempted, transformation_version
            )
            SELECT %(release_id)s, %(import_run_id)s, %(raw_asset_id)s, 'addresses',
                   ban_id, source_row_number, reason_code, reason_detail,
                   properties, false, 'ban-csv-normalize@1'
              FROM ban_stage WHERE is_quarantined
            """,
            parameters,
        )

    def refresh_match_metrics(self, release_id: str, department_code: str) -> None:
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            WITH addresses AS (
                SELECT address.id, address.commune_code
                  FROM reference.address AS address
                  JOIN meta.entity_source_identifier AS identifier
                    ON identifier.entity_type = 'address'
                   AND identifier.entity_id = address.id
                   AND identifier.data_source_id = 'DS-05'
                   AND identifier.last_release_id = %(release_id)s
                 WHERE address.department_code = %(department_code)s
            ), classified AS (
                SELECT address.id, address.commune_code,
                       coalesce(bool_or(matched.decision = 'certain'), false) AS certain,
                       coalesce(bool_or(matched.decision = 'ambiguous'), false) AS ambiguous,
                       coalesce(bool_or(matched.decision = 'rejected'), false) AS rejected
                  FROM addresses AS address
                  LEFT JOIN meta.entity_match AS matched
                    ON matched.left_entity_type = 'address'
                   AND matched.left_entity_id = address.id
                   AND matched.right_entity_type = 'parcel'
                 GROUP BY address.id, address.commune_code
            )
            INSERT INTO meta.entity_match_metric (
                release_id, commune_code, relation_type, algorithm_code,
                algorithm_version, certain_count, ambiguous_count,
                rejected_count, unmatched_count
            )
            SELECT %(release_id)s, commune.code, 'address_parcel',
                   'ban-cad-parcelles', '1',
                   count(*) FILTER (WHERE classified.certain),
                   count(*) FILTER (WHERE NOT classified.certain AND classified.ambiguous),
                   count(*) FILTER (
                       WHERE NOT classified.certain AND NOT classified.ambiguous
                         AND classified.rejected
                   ),
                   count(*) FILTER (
                       WHERE classified.id IS NOT NULL
                         AND NOT classified.certain AND NOT classified.ambiguous
                         AND NOT classified.rejected
                   )
              FROM reference.area AS commune
              LEFT JOIN classified ON classified.commune_code = commune.code
             WHERE commune.area_type = 'commune'
               AND commune.department_code = %(department_code)s
             GROUP BY commune.code
            ON CONFLICT (
                release_id, commune_code, relation_type, algorithm_code, algorithm_version
            ) DO UPDATE SET
                certain_count = EXCLUDED.certain_count,
                ambiguous_count = EXCLUDED.ambiguous_count,
                rejected_count = EXCLUDED.rejected_count,
                unmatched_count = EXCLUDED.unmatched_count,
                measured_at = clock_timestamp()
            """,
            {"release_id": release_id, "department_code": department_code},
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()


class RnbImporter:
    def __init__(self, connection: Connection[Any]) -> None:
        self.connection = connection

    def import_archive(
        self,
        *,
        import_run_id: str,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        source_path: Path,
        idempotency_key: str,
    ) -> SpatialImportOutcome:
        existing = self.connection.execute(
            """
            SELECT id, status, source_row_count, normalized_row_count, quarantined_row_count
              FROM meta.import_run WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        ).fetchone()
        if existing is not None and existing[1] == "succeeded":
            return SpatialImportOutcome(
                import_run_id=str(existing[0]),
                source_rows=int(existing[2]),
                normalized_rows=int(existing[3]),
                quarantined_rows=int(existing[4]),
                skipped_as_idempotent=True,
            )
        if existing is not None:
            self.connection.execute("DELETE FROM meta.import_run WHERE id = %s", (existing[0],))

        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'running',
                      jsonb_build_object('layer', 'buildings', 'raw_asset_id', %s::bigint))
            """,
            (import_run_id, release_id, department_code, idempotency_key, raw_asset_id),
        )
        self._create_stage()
        source_count = 0
        quarantine_count = 0
        with self.connection.cursor().copy(
            """
            COPY rnb_stage (
                is_quarantined, source_row_number, rnb_id, status, commune_code,
                geometry_wkt, geometry_type, external_ids, addresses, plots,
                validated_by, record_checksum, reason_code, reason_detail, source_properties
            ) FROM STDIN
            """
        ) as copy:
            for record in iter_rnb_records(source_path):
                source_count += 1
                if isinstance(record, RnbQuarantine):
                    quarantine_count += 1
                    copy.write_row(
                        (
                            True,
                            record.source_row_number,
                            record.rnb_id,
                            None,
                            None,
                            None,
                            None,
                            Jsonb([]),
                            Jsonb([]),
                            Jsonb([]),
                            Jsonb([]),
                            None,
                            record.reason_code,
                            record.reason_detail,
                            Jsonb(record.source_properties),
                        )
                    )
                else:
                    copy.write_row(
                        (
                            False,
                            record.source_row_number,
                            record.rnb_id,
                            record.status,
                            record.commune_code,
                            record.geometry_wkt,
                            record.geometry_type,
                            Jsonb(record.external_ids),
                            Jsonb(record.addresses),
                            Jsonb(record.plots),
                            Jsonb(record.validated_by),
                            record.record_checksum,
                            None,
                            None,
                            Jsonb({}),
                        )
                    )
        self._publish_stage(
            release_id=release_id,
            department_code=department_code,
            raw_asset_id=raw_asset_id,
            import_run_id=import_run_id,
        )
        normalized_count_row = self.connection.execute(
            "SELECT count(*) FROM rnb_stage WHERE NOT is_quarantined"
        ).fetchone()
        normalized_count = int(normalized_count_row[0]) if normalized_count_row else 0
        duplicate_row = self.connection.execute(
            """
            SELECT count(*) FROM (
                SELECT rnb_id FROM rnb_stage WHERE NOT is_quarantined
                 GROUP BY rnb_id HAVING count(*) > 1
            ) duplicates
            """
        ).fetchone()
        duplicate_count = int(duplicate_row[0]) if duplicate_row else 0
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, import_run_id, check_code, check_version, scope_type,
                scope_code, layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            ) VALUES
                (%s, %s, 'source_vs_normalized_count', '1', 'department', %s, 'buildings',
                 CASE WHEN %s = %s + %s THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %s = %s + %s THEN 'info' ELSE 'error' END,
                 true, %s + %s, %s, '{}'::jsonb),
                (%s, %s, 'duplicate_rnb_id', '1', 'department', %s, 'buildings',
                 CASE WHEN %s = 0 THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %s = 0 THEN 'info' ELSE 'error' END,
                 true, %s, 0, '{}'::jsonb)
            """,
            (
                release_id,
                import_run_id,
                department_code,
                source_count,
                normalized_count,
                quarantine_count,
                source_count,
                normalized_count,
                quarantine_count,
                normalized_count,
                quarantine_count,
                source_count,
                release_id,
                import_run_id,
                department_code,
                duplicate_count,
                duplicate_count,
                duplicate_count,
            ),
        )
        self.connection.execute(
            """
            UPDATE meta.import_run SET
                status = 'succeeded', completed_at = clock_timestamp(),
                source_row_count = %s, normalized_row_count = %s,
                quarantined_row_count = %s
             WHERE id = %s
            """,
            (source_count, normalized_count, quarantine_count, import_run_id),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        return SpatialImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_count,
            normalized_rows=normalized_count,
            quarantined_rows=quarantine_count,
            skipped_as_idempotent=False,
        )

    def refresh_match_metrics(self, release_id: str, department_code: str) -> None:
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self._resolve_missing_communes(release_id, department_code)
        self.connection.execute(
            """
            WITH buildings AS (
                SELECT building.id, building.commune_code
                  FROM reference.building AS building
                  JOIN meta.entity_source_identifier AS identifier
                    ON identifier.entity_type = 'building'
                   AND identifier.entity_id = building.id
                   AND identifier.data_source_id = 'DS-02'
                   AND identifier.last_release_id = %(release_id)s
                 WHERE building.department_code = %(department_code)s
            ), classified AS (
                SELECT building.id, building.commune_code,
                       coalesce(bool_or(link.relation_status = 'certain'), false) AS certain,
                       coalesce(bool_or(link.relation_status = 'ambiguous'), false) AS ambiguous,
                       coalesce(bool_or(link.relation_status = 'rejected'), false) AS rejected
                  FROM buildings AS building
                  LEFT JOIN reference.building_parcel AS link ON link.building_id = building.id
                 GROUP BY building.id, building.commune_code
            ), aggregate AS (
                SELECT commune.code,
                       count(*) FILTER (WHERE classified.certain) AS certain_count,
                       count(*) FILTER (WHERE NOT classified.certain AND classified.ambiguous)
                           AS ambiguous_count,
                       count(*) FILTER (
                           WHERE NOT classified.certain AND NOT classified.ambiguous
                             AND classified.rejected
                       ) AS rejected_count,
                       count(*) FILTER (
                           WHERE classified.id IS NOT NULL
                             AND NOT classified.certain
                             AND NOT classified.ambiguous
                             AND NOT classified.rejected
                       ) AS unmatched_count,
                       count(classified.id) AS building_count
                  FROM reference.area AS commune
                  LEFT JOIN classified ON classified.commune_code = commune.code
                 WHERE commune.area_type = 'commune'
                   AND commune.department_code = %(department_code)s
                 GROUP BY commune.code
            )
            INSERT INTO meta.entity_match_metric (
                release_id, commune_code, relation_type, algorithm_code,
                algorithm_version, certain_count, ambiguous_count,
                rejected_count, unmatched_count
            )
            SELECT %(release_id)s, code, 'building_parcel', 'rnb-plot-relation', '1',
                   certain_count, ambiguous_count, rejected_count, unmatched_count
              FROM aggregate
            ON CONFLICT (
                release_id, commune_code, relation_type, algorithm_code, algorithm_version
            ) DO UPDATE SET
                certain_count = EXCLUDED.certain_count,
                ambiguous_count = EXCLUDED.ambiguous_count,
                rejected_count = EXCLUDED.rejected_count,
                unmatched_count = EXCLUDED.unmatched_count,
                measured_at = clock_timestamp()
            """,
            {"release_id": release_id, "department_code": department_code},
        )
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, check_code, check_version, scope_type, scope_code,
                layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            )
            SELECT metric.release_id, 'match_rate', '1', 'commune', metric.commune_code,
                   'building_parcel', 'passed', 'info', false,
                   CASE WHEN total.total_count = 0 THEN NULL
                        ELSE metric.certain_count::numeric / total.total_count END,
                   NULL,
                   jsonb_build_object(
                       'certain', metric.certain_count,
                       'ambiguous', metric.ambiguous_count,
                       'rejected', metric.rejected_count,
                       'unmatched', metric.unmatched_count,
                       'denominator', total.total_count
                   )
              FROM meta.entity_match_metric AS metric
              CROSS JOIN LATERAL (
                  SELECT metric.certain_count + metric.ambiguous_count
                       + metric.rejected_count + metric.unmatched_count AS total_count
              ) AS total
             WHERE metric.release_id = %s AND metric.relation_type = 'building_parcel'
            ON CONFLICT (
                release_id, import_run_id, check_code, check_version,
                scope_type, scope_code, layer
            ) DO UPDATE SET
                observed_value = EXCLUDED.observed_value,
                details = EXCLUDED.details,
                checked_at = clock_timestamp()
            """,
            (release_id,),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def _resolve_missing_communes(self, release_id: str, department_code: str) -> None:
        parameters = {"release_id": release_id, "department_code": department_code}
        self.connection.execute(
            """
            WITH unresolved AS (
                SELECT building.id, observation.geometry
                  FROM reference.building AS building
                  JOIN meta.entity_source_identifier AS identifier
                    ON identifier.entity_type = 'building'
                   AND identifier.entity_id = building.id
                   AND identifier.data_source_id = 'DS-02'
                   AND identifier.last_release_id = %(release_id)s
                  JOIN meta.entity_source_observation AS observation
                    ON observation.entity_type = 'building'
                   AND observation.entity_id = building.id
                   AND observation.release_id = %(release_id)s
                 WHERE building.department_code = %(department_code)s
                   AND (
                       building.commune_code IS NULL
                       OR NOT EXISTS (
                           SELECT 1 FROM reference.area AS current_commune
                            WHERE current_commune.area_type = 'commune'
                              AND current_commune.code = building.commune_code
                       )
                   )
            ), candidates AS MATERIALIZED (
                SELECT unresolved.id AS building_id, commune.id AS area_id,
                       count(*) OVER (PARTITION BY unresolved.id) AS candidate_count,
                       active.release_id AS area_release_id
                  FROM unresolved
                  JOIN reference.area AS commune
                    ON commune.area_type = 'commune'
                   AND commune.department_code = %(department_code)s
                   AND ST_Covers(commune.geom, ST_PointOnSurface(unresolved.geometry))
                  JOIN meta.active_dataset_release AS active
                    ON active.data_source_id = 'DS-01'
                   AND active.scope_type = 'department'
                   AND active.scope_code = %(department_code)s
            )
            INSERT INTO meta.entity_match (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, critical,
                blocks_publication, rationale, evidence, release_ids
            )
            SELECT 'rnb-commune:' || candidate.building_id,
                   'building', candidate.building_id, 'area', candidate.area_id,
                   'spatial_intersection', 'rnb-commune-spatial', '1',
                   CASE WHEN candidate.candidate_count = 1 THEN 0.99 ELSE 0.5 END,
                   CASE WHEN candidate.candidate_count = 1 THEN 'certain' ELSE 'ambiguous' END,
                   true, candidate.candidate_count <> 1,
                   'RNB building commune resolved from active commune geometry',
                   jsonb_build_object('candidate_count', candidate.candidate_count),
                   jsonb_build_array(%(release_id)s::text, candidate.area_release_id)
              FROM candidates AS candidate
            ON CONFLICT (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, algorithm_code, algorithm_version
            ) DO UPDATE SET
                confidence = EXCLUDED.confidence,
                decision = EXCLUDED.decision,
                blocks_publication = EXCLUDED.blocks_publication,
                evidence = EXCLUDED.evidence,
                release_ids = EXCLUDED.release_ids
            """,
            parameters,
        )
        self.connection.execute(
            """
            UPDATE reference.building AS building
               SET commune_code = commune.code, updated_at = clock_timestamp()
              FROM meta.entity_match AS matched
              JOIN reference.area AS commune ON commune.id = matched.right_entity_id
             WHERE matched.left_entity_type = 'building'
               AND matched.left_entity_id = building.id
               AND matched.right_entity_type = 'area'
               AND matched.algorithm_code = 'rnb-commune-spatial'
               AND matched.algorithm_version = '1'
               AND matched.decision = 'certain'
               AND matched.release_ids ? %(release_id)s
            """,
            parameters,
        )

    def _create_stage(self) -> None:
        self.connection.execute(
            """
            CREATE TEMP TABLE rnb_stage (
                is_quarantined boolean NOT NULL,
                source_row_number bigint NOT NULL,
                rnb_id text,
                status text,
                commune_code text,
                geometry_wkt text,
                geometry_type text,
                external_ids jsonb NOT NULL,
                addresses jsonb NOT NULL,
                plots jsonb NOT NULL,
                validated_by jsonb NOT NULL,
                record_checksum char(64),
                reason_code text,
                reason_detail text,
                source_properties jsonb NOT NULL
            ) ON COMMIT DROP
            """
        )

    def _publish_stage(
        self,
        *,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        import_run_id: str,
    ) -> None:
        parameters = {
            "release_id": release_id,
            "department_code": department_code,
            "raw_asset_id": raw_asset_id,
            "import_run_id": import_run_id,
        }
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_observation (
                release_id, raw_asset_id, entity_type, entity_id, source_entity_type,
                source_identifier, source_row_number, geometry, properties,
                record_checksum
            )
            SELECT %(release_id)s, %(raw_asset_id)s, 'building', 'building:rnb:' || rnb_id,
                   'rnb_building', rnb_id, source_row_number,
                   ST_GeomFromText(geometry_wkt, 2154),
                   jsonb_build_object(
                       'status', status, 'ext_ids', external_ids, 'addresses', addresses,
                       'plots', plots, 'validated_by', validated_by
                   ), record_checksum
              FROM rnb_stage WHERE NOT is_quarantined
            ON CONFLICT (release_id, source_entity_type, source_identifier, record_checksum)
            DO NOTHING
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO reference.building (
                id, preferred_identity_source, commune_code, department_code,
                lifecycle_status, geom
            )
            SELECT 'building:rnb:' || rnb_id, 'RNB', commune_code,
                   %(department_code)s,
                   CASE WHEN status IN ('constructed', 'underConstruction')
                        THEN 'active'
                        WHEN status = 'demolished' THEN 'demolished'
                        ELSE 'unknown' END,
                   CASE WHEN geometry_type = 'MultiPolygon'
                        THEN ST_GeomFromText(geometry_wkt, 2154)::geometry(MultiPolygon, 2154)
                        ELSE NULL END
              FROM rnb_stage WHERE NOT is_quarantined
            ON CONFLICT (id) DO UPDATE SET
                commune_code = coalesce(EXCLUDED.commune_code, reference.building.commune_code),
                lifecycle_status = EXCLUDED.lifecycle_status,
                geom = coalesce(EXCLUDED.geom, reference.building.geom),
                updated_at = clock_timestamp()
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT 'building', 'building:rnb:' || rnb_id, 'DS-02', 'rnb_building',
                   rnb_id, %(release_id)s, %(release_id)s, true
              FROM rnb_stage WHERE NOT is_quarantined
            ON CONFLICT ON CONSTRAINT entity_source_identifier_pkey
            DO UPDATE SET last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp()
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT 'building', 'building:rnb:' || stage.rnb_id,
                   CASE external->>'source' WHEN 'bdnb' THEN 'DS-03' ELSE 'DS-04' END,
                   CASE external->>'source'
                       WHEN 'bdnb' THEN 'bdnb_building_group' ELSE 'bdtopo_building' END,
                   external->>'id', %(release_id)s, %(release_id)s, false
              FROM rnb_stage AS stage
              CROSS JOIN LATERAL jsonb_array_elements(stage.external_ids) AS external
             WHERE NOT stage.is_quarantined
               AND external->>'source' IN ('bdnb', 'bdtopo')
               AND nullif(external->>'id', '') IS NOT NULL
            ON CONFLICT ON CONSTRAINT entity_source_identifier_pkey
            DO UPDATE SET last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp()
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.entity_match (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, critical,
                blocks_publication, rationale, evidence, release_ids
            )
            SELECT 'rnb-plot:' || stage.rnb_id || ':' || parcel.id,
                   'building', 'building:rnb:' || stage.rnb_id,
                   'parcel', parcel.id, 'source_relation', 'rnb-plot-relation', '1',
                   greatest(0.9, least(1, coalesce((plot->>'bdg_cover_ratio')::numeric, 0.9))),
                   'certain', true, false,
                   'RNB explicit plot relation retained with its building coverage ratio',
                   jsonb_build_object('bdg_cover_ratio', plot->'bdg_cover_ratio'),
                   jsonb_build_array(%(release_id)s::text)
              FROM rnb_stage AS stage
              CROSS JOIN LATERAL jsonb_array_elements(stage.plots) AS plot
              JOIN reference.parcel AS parcel ON parcel.cadastral_id = plot->>'id'
             WHERE NOT stage.is_quarantined
            ON CONFLICT (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, algorithm_code, algorithm_version
            ) DO NOTHING
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO reference.building_parcel (
                building_id, parcel_id, relation_status, match_id,
                building_overlap_ratio
            )
            SELECT matched.left_entity_id, matched.right_entity_id,
                   matched.decision, matched.id,
                   (matched.evidence->>'bdg_cover_ratio')::numeric
              FROM meta.entity_match AS matched
             WHERE matched.algorithm_code = 'rnb-plot-relation'
               AND matched.algorithm_version = '1'
               AND matched.release_ids ? %(release_id)s
            ON CONFLICT (building_id, parcel_id) DO UPDATE SET
                relation_status = EXCLUDED.relation_status,
                match_id = EXCLUDED.match_id,
                building_overlap_ratio = EXCLUDED.building_overlap_ratio
            """,
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.geometry_quarantine (
                release_id, import_run_id, raw_asset_id, layer, source_feature_id,
                source_row_number, reason_code, reason_detail, source_properties,
                repair_attempted, transformation_version
            )
            SELECT %(release_id)s, %(import_run_id)s, %(raw_asset_id)s, 'buildings',
                   rnb_id, source_row_number, reason_code, reason_detail,
                   source_properties, false, 'rnb-normalize@1'
              FROM rnb_stage WHERE is_quarantined
            """,
            parameters,
        )
