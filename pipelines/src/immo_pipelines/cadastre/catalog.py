from dataclasses import dataclass
from datetime import date
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class RawAssetRegistration:
    release_id: str
    layer: str
    territory_code: str
    source_url: str
    object_key: str
    byte_size: int
    sha256: str
    etag: str | None
    media_type: str = "application/geo+json"
    content_encoding: str | None = "gzip"


@dataclass(frozen=True)
class RawAssetRecord:
    id: int
    object_key: str
    byte_size: int
    sha256: str


class DatasetCatalog:
    def __init__(self, connection: Connection[Any]) -> None:
        self.connection = connection

    def register_release(
        self,
        *,
        release_id: str,
        release_key: str,
        published_on: date,
        schema_fingerprint: str,
        department_code: str,
        previous_release_id: str | None = None,
        data_source_id: str = "DS-01",
        source_srid: int = 4326,
        contract_version: int = 1,
    ) -> None:
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.dataset_release (
                id, data_source_id, release_key, contract_version, source_published_on,
                source_srid, canonical_srid, coverage, schema_fingerprint,
                previous_release_id
            ) VALUES (%s, %s, %s, %s, %s, %s, 2154,
                      jsonb_build_object('departments', jsonb_build_array(%s::text)), %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                schema_fingerprint = EXCLUDED.schema_fingerprint,
                coverage = EXCLUDED.coverage,
                previous_release_id = coalesce(
                    meta.dataset_release.previous_release_id, EXCLUDED.previous_release_id
                )
            WHERE NOT EXISTS (
                SELECT 1 FROM meta.active_dataset_release active
                 WHERE active.release_id = EXCLUDED.id
            )
            """,
            (
                release_id,
                data_source_id,
                release_key,
                contract_version,
                published_on,
                source_srid,
                department_code,
                schema_fingerprint,
                previous_release_id,
            ),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def register_raw_asset(self, asset: RawAssetRegistration) -> int:
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        row = self.connection.execute(
            """
            INSERT INTO meta.raw_asset (
                release_id, layer, territory_type, territory_code, source_url,
                object_key, media_type, content_encoding, byte_size, sha256, etag
            ) VALUES (%s, %s, 'department', %s, %s, %s,
                      %s, %s, %s, %s, %s)
            ON CONFLICT (release_id, layer, territory_type, territory_code, sha256)
            DO UPDATE SET object_key = EXCLUDED.object_key
            RETURNING id
            """,
            (
                asset.release_id,
                asset.layer,
                asset.territory_code,
                asset.source_url,
                asset.object_key,
                asset.media_type,
                asset.content_encoding,
                asset.byte_size,
                asset.sha256,
                asset.etag,
            ),
        ).fetchone()
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        if row is None:
            raise RuntimeError("Raw asset registration returned no id")
        return int(row[0])

    def find_raw_asset(
        self,
        *,
        release_id: str,
        layer: str,
        territory_code: str,
        source_url: str,
    ) -> RawAssetRecord | None:
        """Return an already archived immutable source for a safe retry."""
        row = self.connection.execute(
            """
            SELECT id, object_key, byte_size, sha256
              FROM meta.raw_asset
             WHERE release_id = %s
               AND layer = %s
               AND territory_type = 'department'
               AND territory_code = %s
               AND source_url = %s
             ORDER BY downloaded_at DESC, id DESC
             LIMIT 1
            """,
            (release_id, layer, territory_code, source_url),
        ).fetchone()
        if row is None:
            return None
        return RawAssetRecord(
            id=int(row[0]),
            object_key=str(row[1]),
            byte_size=int(row[2]),
            sha256=str(row[3]),
        )

    def refresh_commune_quality(self, release_id: str, department_code: str) -> None:
        """Create comparable metrics for every source commune, including empty layers."""
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            DELETE FROM meta.data_quality_check
             WHERE release_id = %s AND scope_type = 'commune'
            """,
            (release_id,),
        )
        self.connection.execute(
            """
            WITH communes AS (
                SELECT code
                  FROM reference.administrative_area
                 WHERE release_id = %(release_id)s
                   AND department_code = %(department)s
                   AND area_type = 'commune'
            ), parcel_counts AS (
                SELECT commune_code,
                       count(*)::numeric AS count,
                       count(*) FILTER (WHERE stated_area_m2 IS NULL)::numeric
                           AS missing_stated_area_count
                  FROM reference.cadastral_parcel
                 WHERE release_id = %(release_id)s
                 GROUP BY commune_code
            ), building_counts AS (
                SELECT commune_code, count(*)::numeric AS count
                  FROM reference.cadastral_building
                 WHERE release_id = %(release_id)s
                 GROUP BY commune_code
            ), quarantine_counts AS (
                SELECT source_properties->>'commune' AS commune_code, count(*)::numeric AS count
                  FROM meta.geometry_quarantine
                 WHERE release_id = %(release_id)s
                 GROUP BY source_properties->>'commune'
            ), metrics AS (
                SELECT code, 'parcel_count'::text AS check_code,
                       coalesce(parcel_counts.count, 0) AS value,
                       jsonb_build_object(
                           'stated_area_missing_count',
                           coalesce(parcel_counts.missing_stated_area_count, 0)
                       ) AS details
                  FROM communes LEFT JOIN parcel_counts ON parcel_counts.commune_code = code
                UNION ALL
                SELECT code, 'building_count', coalesce(building_counts.count, 0),
                       '{}'::jsonb
                  FROM communes LEFT JOIN building_counts ON building_counts.commune_code = code
                UNION ALL
                SELECT code, 'quarantined_geometry_count', coalesce(quarantine_counts.count, 0),
                       '{}'::jsonb
                  FROM communes LEFT JOIN quarantine_counts ON quarantine_counts.commune_code = code
            )
            INSERT INTO meta.data_quality_check (
                release_id, check_code, check_version, scope_type, scope_code,
                status, severity, blocks_publication, observed_value, expected_value,
                details
            )
            SELECT %(release_id)s, check_code, '1', 'commune', code,
                   CASE
                     WHEN check_code = 'parcel_count' AND value = 0 THEN 'failed'
                     WHEN check_code = 'parcel_count'
                          AND (details->>'stated_area_missing_count')::numeric > 0 THEN 'warning'
                     WHEN check_code = 'quarantined_geometry_count' AND value > 0 THEN 'warning'
                     ELSE 'passed'
                   END,
                   CASE
                     WHEN check_code = 'parcel_count' AND value = 0 THEN 'error'
                     WHEN check_code = 'parcel_count'
                          AND (details->>'stated_area_missing_count')::numeric > 0 THEN 'warning'
                     WHEN check_code = 'quarantined_geometry_count' AND value > 0 THEN 'warning'
                     ELSE 'info'
                   END,
                   check_code = 'parcel_count', value,
                   CASE WHEN check_code = 'parcel_count' THEN 1 ELSE 0 END,
                   details
              FROM metrics
            """,
            {"release_id": release_id, "department": department_code},
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def record_asset_checks(
        self,
        *,
        release_id: str,
        department_code: str,
        layer: str,
        checksum_valid: bool,
        schema_valid: bool,
        schema_fingerprint: str,
    ) -> None:
        for check_code, valid in (("checksum", checksum_valid), ("schema", schema_valid)):
            self.record_asset_check(
                release_id=release_id,
                department_code=department_code,
                layer=layer,
                check_code=check_code,
                valid=valid,
                details={"schema_fingerprint": schema_fingerprint},
            )

    def record_asset_check(
        self,
        *,
        release_id: str,
        department_code: str,
        layer: str,
        check_code: str,
        valid: bool,
        details: dict[str, Any],
    ) -> None:
        if check_code not in {"checksum", "schema"}:
            raise ValueError(f"Unsupported asset check {check_code}")
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, check_code, check_version, scope_type, scope_code,
                layer, status, severity, blocks_publication, details
            ) VALUES (%s, %s, '1', 'department', %s, %s,
                      CASE WHEN %s::boolean THEN 'passed' ELSE 'failed' END,
                      CASE WHEN %s::boolean THEN 'info' ELSE 'error' END, true,
                      %s::jsonb)
            ON CONFLICT ON CONSTRAINT data_quality_result_identity DO UPDATE SET
                status = EXCLUDED.status, severity = EXCLUDED.severity,
                details = EXCLUDED.details, checked_at = now()
            """,
            (
                release_id,
                check_code,
                department_code,
                layer,
                valid,
                valid,
                Jsonb(details),
            ),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def _release_data_source(self, release_id: str) -> str:
        row = self.connection.execute(
            "SELECT data_source_id FROM meta.dataset_release WHERE id = %s",
            (release_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Unknown release {release_id}")
        return str(row[0])

    def _require_successful_import(self, release_id: str) -> None:
        """Toute source : rien n'est acceptable sans au moins un import reussi."""
        row = self.connection.execute(
            """
            SELECT 1 FROM meta.import_run
             WHERE release_id = %s AND status = 'succeeded' LIMIT 1
            """,
            (release_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Release requires at least one successful import run")

    def _require_complete_cadastre_release(self, release_id: str) -> None:
        """DS-01 seulement : trois couches archivees, importees, et metriques par commune."""
        gate = self.connection.execute(
            """
            WITH release_assets AS (
                SELECT count(DISTINCT layer) FILTER (
                           WHERE layer IN ('communes', 'parcelles', 'batiments')
                       ) AS layer_count
                  FROM meta.raw_asset WHERE release_id = %(release_id)s
            ), successful_imports AS (
                SELECT count(DISTINCT runner_metadata->>'layer') FILTER (
                           WHERE runner_metadata->>'layer'
                                 IN ('communes', 'parcelles', 'batiments')
                       ) AS layer_count
                  FROM meta.import_run
                 WHERE release_id = %(release_id)s AND status = 'succeeded'
            ), communes AS (
                SELECT count(*) AS count
                  FROM reference.administrative_area
                 WHERE release_id = %(release_id)s AND area_type = 'commune'
            ), commune_metrics AS (
                SELECT count(*) AS count
                  FROM meta.data_quality_check
                 WHERE release_id = %(release_id)s
                   AND scope_type = 'commune'
                   AND check_code IN (
                       'parcel_count', 'building_count', 'quarantined_geometry_count'
                   )
            )
            SELECT release_assets.layer_count,
                   successful_imports.layer_count,
                   communes.count,
                   commune_metrics.count
              FROM release_assets, successful_imports, communes, commune_metrics
            """,
            {"release_id": release_id},
        ).fetchone()
        if gate is None or int(gate[0]) != 3 or int(gate[1]) != 3:
            raise RuntimeError("Release requires all three archived and imported layers")
        commune_count = int(gate[2])
        if commune_count == 0 or int(gate[3]) != commune_count * 3:
            raise RuntimeError("Release requires complete quality metrics for every commune")

    def set_acceptance(self, release_id: str, mode: str) -> None:
        if mode not in {"accepted", "display_only", "rejected"}:
            raise ValueError(f"Unsupported acceptance mode {mode}")
        if mode in {"accepted", "display_only"}:
            # meta.guard_active_dataset_release fait autorite : il ne verifie la
            # completude par couches que pour DS-01. Appliquer cette regle a toute
            # source rendait inacceptable n'importe quelle release non cadastrale,
            # DS-05 comprise, qui ne publie qu'une seule couche.
            self._require_successful_import(release_id)
            if self._release_data_source(release_id) == "DS-01":
                self._require_complete_cadastre_release(release_id)

        blocking_failure = self.connection.execute(
            """
            SELECT 1 FROM meta.data_quality_check
             WHERE release_id = %s AND blocks_publication AND status = 'failed' LIMIT 1
            """,
            (release_id,),
        ).fetchone()
        if mode in {"accepted", "display_only"} and blocking_failure is not None:
            raise RuntimeError("Release has blocking quality failures")
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            UPDATE meta.dataset_release
               SET acceptance_status = %s, lifecycle_status = 'validated'
             WHERE id = %s
            """,
            (mode, release_id),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def publish(
        self,
        release_id: str,
        department_code: str,
        *,
        actor: str,
        reason: str,
        action: str = "publish",
    ) -> None:
        # La source vient de la release, jamais d'un litteral : `meta.publish_dataset_release`
        # cherche la release par (id, data_source_id) en SELECT STRICT, si bien qu'un
        # 'DS-01' code en dur rendait toute release non cadastrale impubliable.
        data_source_id = self._release_data_source(release_id)
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            "SELECT meta.publish_dataset_release(%s, %s, 'department', %s, %s, %s, %s)",
            (data_source_id, release_id, department_code, actor, reason, action),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def rollback_unpublished(self, release_id: str, *, actor: str, reason: str) -> None:
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            "SELECT meta.rollback_unpublished_dataset_release(%s, %s, %s)",
            (release_id, actor, reason),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def quality_report(self, release_id: str) -> dict[str, Any]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            release = cursor.execute(
                """
                SELECT id, release_key, lifecycle_status, acceptance_status,
                       source_published_on, coverage
                  FROM meta.dataset_release WHERE id = %s
                """,
                (release_id,),
            ).fetchone()
            checks = cursor.execute(
                """
                SELECT check_code, scope_type, scope_code, layer, status, severity,
                       blocks_publication, observed_value, expected_value, details
                  FROM meta.data_quality_check
                 WHERE release_id = %s
                 ORDER BY scope_type, scope_code, check_code
                """,
                (release_id,),
            ).fetchall()
        if release is None:
            raise KeyError(release_id)
        return {"release": dict(release), "checks": [dict(check) for check in checks]}

    def compare_releases(self, left_release_id: str, right_release_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT
              (SELECT count(*) FROM reference.cadastral_parcel WHERE release_id = %s),
              (SELECT count(*) FROM reference.cadastral_parcel WHERE release_id = %s),
              (SELECT count(*) FROM reference.cadastral_building WHERE release_id = %s),
              (SELECT count(*) FROM reference.cadastral_building WHERE release_id = %s),
              (SELECT count(*) FROM meta.geometry_quarantine WHERE release_id = %s),
              (SELECT count(*) FROM meta.geometry_quarantine WHERE release_id = %s)
            """,
            (
                left_release_id,
                right_release_id,
                left_release_id,
                right_release_id,
                left_release_id,
                right_release_id,
            ),
        ).fetchone()
        if row is None:
            raise RuntimeError("Release comparison failed")
        keys = ("parcels", "buildings", "quarantine")
        result: dict[str, Any] = {}
        for index, key in enumerate(keys):
            left = int(row[index * 2])
            right = int(row[index * 2 + 1])
            result[key] = {"left": left, "right": right, "delta": right - left}
        return result
