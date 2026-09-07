from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg import Connection, sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from immo_pipelines.spatial.ban import (
    BAN_TRANSFORMATION_VERSION,
    BanQuarantine,
    iter_ban_records,
)
from immo_pipelines.spatial.bdnb import (
    BdnbQuarantine,
    iter_bdnb_group_rnb_links,
    iter_bdnb_groups,
    verify_field_policy,
)
from immo_pipelines.spatial.bdtopo import (
    BDTOPO_TRANSFORMATION_VERSION,
    BdtopoQuarantine,
    iter_bdtopo_buildings,
    iter_bdtopo_rnb_links,
    iter_bdtopo_roads,
)
from immo_pipelines.spatial.rnb import RnbQuarantine, iter_rnb_records

# Attributs non identitaires d'une adresse BAN. Lorsqu'un identifiant est réutilisé avec des
# valeurs contradictoires sur l'un d'eux, l'identité reste certaine et seul l'attribut devient
# inutilisable : il est retenu, motivé, et jamais moyenné ni choisi arbitrairement.
# (colonne de stage, attribut canonique, motif)
BAN_QUARANTINABLE_ATTRIBUTES: tuple[tuple[str, str, str], ...] = (
    ("geometry_wkt", "geom", "ambiguous_position"),
    ("cadastral_ids", "cadastral_ids", "ambiguous_attribute"),
    ("position_type", "position_type", "ambiguous_attribute"),
    ("source_position", "source_position", "ambiguous_attribute"),
    ("municipality_certified", "is_municipality_certified", "ambiguous_attribute"),
    ("fantoir_id", "fantoir_id", "ambiguous_attribute"),
)

# Sentinelle de comparaison : `count(DISTINCT colonne)` ignore les NULL, ce qui masquerait une
# divergence entre une valeur présente et une valeur absente. Aucune donnée BAN ne peut valoir
# cette chaîne.
_NULL_SENTINEL = "__null__"


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
        source_row_count = 0
        quarantined_row_count = 0
        with self.connection.cursor().copy(
            """
            COPY ban_stage (
                is_quarantined, source_row_number, ban_id, fantoir_id,
                house_number, repetition_index, street_name, postal_code,
                commune_code, commune_name, display_label, normalized_label,
                position_type, source_position, municipality_certified,
                geometry_wkt, cadastral_ids, properties, record_checksum,
                identity_checksum, reason_code, reason_detail
            ) FROM STDIN
            """
        ) as copy:
            for record in iter_ban_records(source_path):
                source_row_count += 1
                if isinstance(record, BanQuarantine):
                    quarantined_row_count += 1
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
                            record.identity_checksum,
                            None,
                            None,
                        )
                    )
        # La couche d'observation doit rester fidèle à ce que la source a dit, même lorsque
        # l'attribut canonique est retenu plus bas.
        self.connection.execute("UPDATE ban_stage SET source_geometry_wkt = geometry_wkt")

        # Un identifiant réutilisé avec des identités contradictoires est irréconciliable :
        # l'une des deux est fausse et rien ne permet de choisir. L'enregistrement entier part
        # en quarantaine et la release est bloquée.
        conflicting_identity_row = self.connection.execute(
            """
            WITH conflicting_ids AS (
                SELECT ban_id
                  FROM ban_stage
                 WHERE NOT is_quarantined
                 GROUP BY ban_id
                HAVING count(DISTINCT identity_checksum) > 1
            ), quarantined AS (
                UPDATE ban_stage AS stage
                   SET is_quarantined = true,
                       reason_code = 'conflicting_ban_identity',
                       reason_detail = 'BAN identifier occurs with contradictory address identities'
                  FROM conflicting_ids
                 WHERE stage.ban_id = conflicting_ids.ban_id
                   AND NOT stage.is_quarantined
                RETURNING stage.ban_id
            )
            SELECT count(*), count(DISTINCT ban_id) FROM quarantined
            """
        ).fetchone()
        conflicting_identity_row_count = (
            int(conflicting_identity_row[0]) if conflicting_identity_row else 0
        )
        conflicting_identity_identifier_count = (
            int(conflicting_identity_row[1]) if conflicting_identity_row else 0
        )
        quarantined_row_count += conflicting_identity_row_count

        # Doublons réellement présents dans la source, mesurés avant le retrait des attributs
        # contradictoires. Après ce retrait, les variantes d'un identifiant ambigu deviennent
        # identiques : les compter ici ferait passer pour des doublons de la source des lignes
        # que seule notre propre décision a rendues indiscernables.
        exact_duplicate_row = self.connection.execute(
            """
            SELECT count(*) - count(DISTINCT (ban_id, record_checksum))
              FROM ban_stage
             WHERE NOT is_quarantined
            """
        ).fetchone()
        exact_duplicate_excess_row_count = int(exact_duplicate_row[0]) if exact_duplicate_row else 0

        # Identité stable, attribut contradictoire : l'adresse est conservée et seul l'attribut
        # devient manquant avec un motif. Il est retiré de *toutes* les variantes de
        # l'identifiant, si bien que la déduplication qui suit ne choisit plus rien
        # arbitrairement — les variantes restantes sont identiques.
        ambiguous_attribute_counts: dict[str, int] = {}
        for column, attribute, reason_code in BAN_QUARANTINABLE_ATTRIBUTES:
            statement = sql.SQL(
                """
                WITH repeated AS (
                    SELECT ban_id
                      FROM ban_stage
                     WHERE NOT is_quarantined
                     GROUP BY ban_id
                    HAVING count(DISTINCT record_checksum) > 1
                ), divergent AS (
                    SELECT stage.ban_id
                      FROM ban_stage AS stage
                      JOIN repeated USING (ban_id)
                     WHERE NOT stage.is_quarantined
                     GROUP BY stage.ban_id
                    HAVING count(DISTINCT COALESCE(stage.{column}::text, %(sentinel)s)) > 1
                ), marked AS (
                    UPDATE ban_stage AS stage
                       SET {column} = NULL,
                           quarantined_attributes = stage.quarantined_attributes
                               || jsonb_build_array(jsonb_build_object(
                                      'attribute', %(attribute)s::text,
                                      'reason_code', %(reason_code)s::text
                                  ))
                      FROM divergent
                     WHERE stage.ban_id = divergent.ban_id
                    RETURNING stage.ban_id
                )
                SELECT count(DISTINCT ban_id) FROM marked
                """
            ).format(column=sql.Identifier(column))
            marked_row = self.connection.execute(
                statement,
                {
                    "sentinel": _NULL_SENTINEL,
                    "attribute": attribute,
                    "reason_code": reason_code,
                },
            ).fetchone()
            count = int(marked_row[0]) if marked_row else 0
            if count:
                ambiguous_attribute_counts[attribute] = count
        ambiguous_attribute_identifier_count = self._distinct_ambiguous_identifiers()
        (
            unresolved_reference_relation_count,
            unresolved_reference_address_count,
        ) = self._publish_stage_and_count_rejections(
            release_id=release_id,
            department_code=department_code,
            raw_asset_id=raw_asset_id,
            import_run_id=import_run_id,
        )
        normalized_row_count_row = self.connection.execute(
            "SELECT count(DISTINCT ban_id) FROM ban_stage WHERE NOT is_quarantined"
        ).fetchone()
        normalized_row_count = int(normalized_row_count_row[0]) if normalized_row_count_row else 0
        deduplicated_row = self.connection.execute(
            """
            SELECT count(*) - count(DISTINCT ban_id)
              FROM ban_stage
             WHERE NOT is_quarantined
            """
        ).fetchone()
        deduplicated_row_count = int(deduplicated_row[0]) if deduplicated_row else 0
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, import_run_id, check_code, check_version, scope_type,
                scope_code, layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            ) VALUES
                (%(release_id)s, %(import_run_id)s, 'source_vs_normalized_count', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(accounted_row_count)s = %(source_row_count)s
                      THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %(accounted_row_count)s = %(source_row_count)s
                      THEN 'info' ELSE 'error' END,
                 true, %(accounted_row_count)s, %(source_row_count)s,
                 jsonb_build_object(
                     'normalized', %(normalized_row_count)s::bigint,
                     'quarantined', %(quarantined_row_count)s::bigint,
                     'deduplicated', %(deduplicated_row_count)s::bigint
                 )),
                (%(release_id)s, %(import_run_id)s, 'exact_duplicate_ban_record', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(exact_duplicate_excess_row_count)s = 0
                      THEN 'passed' ELSE 'warning' END,
                 CASE WHEN %(exact_duplicate_excess_row_count)s = 0
                      THEN 'info' ELSE 'warning' END,
                 false, %(exact_duplicate_excess_row_count)s, 0,
                 jsonb_build_object(
                     'excess_rows_dropped_by_deduplication', %(deduplicated_row_count)s::bigint,
                     'policy', 'retain one canonical record; preserve raw asset'
                 )),
                (%(release_id)s, %(import_run_id)s, 'conflicting_ban_identity', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(conflicting_identity_identifier_count)s = 0
                      THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %(conflicting_identity_identifier_count)s = 0
                      THEN 'info' ELSE 'error' END,
                 true, %(conflicting_identity_identifier_count)s, 0,
                 jsonb_build_object(
                     'quarantined_rows', %(conflicting_identity_row_count)s::bigint,
                     'policy', 'contradictory address identities cannot be reconciled'
                 )),
                (%(release_id)s, %(import_run_id)s, 'ambiguous_ban_attribute', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(ambiguous_attribute_identifier_count)s = 0
                      THEN 'passed' ELSE 'warning' END,
                 CASE WHEN %(ambiguous_attribute_identifier_count)s = 0
                      THEN 'info' ELSE 'warning' END,
                 false, %(ambiguous_attribute_identifier_count)s, 0,
                 jsonb_build_object(
                     'by_attribute', %(ambiguous_attribute_counts)s::jsonb,
                     'excess_rows_collapsed_by_withholding',
                         %(deduplicated_row_count)s::bigint
                             - %(exact_duplicate_excess_row_count)s::bigint,
                     'policy', 'identity retained; contradictory attribute withheld with a motive'
                 )),
                (%(release_id)s, %(import_run_id)s, 'unresolved_cadastral_reference', '1',
                 'department', %(department_code)s, 'addresses',
                 CASE WHEN %(unresolved_reference_relation_count)s = 0
                      THEN 'passed' ELSE 'warning' END,
                 CASE WHEN %(unresolved_reference_relation_count)s = 0
                      THEN 'info' ELSE 'warning' END,
                 false, %(unresolved_reference_relation_count)s, 0,
                 jsonb_build_object(
                     'addresses_concerned', %(unresolved_reference_address_count)s::bigint,
                     'policy', 'relation rejected with a motive; never silently dropped'
                 ))
            """,
            {
                "release_id": release_id,
                "import_run_id": import_run_id,
                "department_code": department_code,
                "source_row_count": source_row_count,
                "accounted_row_count": (
                    normalized_row_count + quarantined_row_count + deduplicated_row_count
                ),
                "normalized_row_count": normalized_row_count,
                "quarantined_row_count": quarantined_row_count,
                "deduplicated_row_count": deduplicated_row_count,
                "conflicting_identity_identifier_count": conflicting_identity_identifier_count,
                "conflicting_identity_row_count": conflicting_identity_row_count,
                "exact_duplicate_excess_row_count": exact_duplicate_excess_row_count,
                "ambiguous_attribute_identifier_count": ambiguous_attribute_identifier_count,
                "ambiguous_attribute_counts": Jsonb(ambiguous_attribute_counts),
                "unresolved_reference_relation_count": unresolved_reference_relation_count,
                "unresolved_reference_address_count": unresolved_reference_address_count,
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
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                deduplicated_row_count,
                import_run_id,
            ),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        return SpatialImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_row_count,
            normalized_rows=normalized_row_count,
            quarantined_rows=quarantined_row_count,
            skipped_as_idempotent=False,
        )

    def _publish_stage_and_count_rejections(
        self,
        *,
        release_id: str,
        department_code: str,
        raw_asset_id: int,
        import_run_id: str,
    ) -> tuple[int, int]:
        """Publier le stage, puis compter les relations `cad_parcelles` rejetees.

        Une reference cadastrale absente du referentiel actif produit une relation
        `rejected` motivee plutot qu'aucune ligne. Sans ce comptage, la perte resterait
        invisible dans le rapport d'import : c'est le compteur qui rend le rejet opposable.
        Renvoie (relations rejetees, adresses concernees).
        """
        self._publish_stage(
            release_id=release_id,
            department_code=department_code,
            raw_asset_id=raw_asset_id,
            import_run_id=import_run_id,
        )
        row = self.connection.execute(
            """
            SELECT count(*), count(DISTINCT left_entity_id)
              FROM meta.entity_match
             WHERE algorithm_code = 'ban-cad-parcelles'
               AND algorithm_version = '1'
               AND decision = 'rejected'
               AND release_ids ? %s
            """,
            (release_id,),
        ).fetchone()
        return (int(row[0]), int(row[1])) if row else (0, 0)

    def _distinct_ambiguous_identifiers(self) -> int:
        row = self.connection.execute(
            """
            SELECT count(DISTINCT ban_id)
              FROM ban_stage
             WHERE NOT is_quarantined
               AND jsonb_array_length(quarantined_attributes) > 0
            """
        ).fetchone()
        return int(row[0]) if row else 0

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
                source_geometry_wkt text,
                cadastral_ids jsonb,
                properties jsonb NOT NULL,
                record_checksum char(64),
                identity_checksum char(64),
                quarantined_attributes jsonb NOT NULL DEFAULT '[]'::jsonb,
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
            "transformation_version": BAN_TRANSFORMATION_VERSION,
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
                   ST_GeomFromText(source_geometry_wkt, 2154), properties, record_checksum
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
            INSERT INTO meta.attribute_quarantine (
                release_id, import_run_id, entity_type, entity_id,
                attribute, reason_code, reason_detail, evidence
            )
            SELECT %(release_id)s, %(import_run_id)s, 'address',
                   'address:ban:' || stage.ban_id,
                   item->>'attribute', item->>'reason_code',
                   'BAN identifier reused with contradictory values for this attribute',
                   jsonb_build_object(
                       'variant_count', count(*),
                       'source_row_numbers',
                       jsonb_agg(stage.source_row_number ORDER BY stage.source_row_number)
                   )
              FROM ban_stage AS stage
              CROSS JOIN LATERAL jsonb_array_elements(stage.quarantined_attributes) AS item
             WHERE NOT stage.is_quarantined
             GROUP BY stage.ban_id, item->>'attribute', item->>'reason_code'
            ON CONFLICT ON CONSTRAINT attribute_quarantine_identity DO UPDATE SET
                import_run_id = EXCLUDED.import_run_id,
                reason_code = EXCLUDED.reason_code,
                evidence = EXCLUDED.evidence
            """,
            parameters,
        )
        self.connection.execute(
            """
            WITH candidates AS MATERIALIZED (
                SELECT stage.ban_id, cadastral_id.value AS cadastral_id,
                       coalesce(
                           parcel.id, 'parcel:cadastre:' || cadastral_id.value
                       ) AS parcel_id,
                       CASE WHEN parcel.id IS NULL THEN 'unresolved_cadastral_reference'
                            WHEN geometry.geom IS NULL THEN 'unpublished_parcel_geometry'
                            ELSE 'resolved' END AS resolution,
                       ST_Covers(geometry.geom, address.geom) AS point_covered,
                       ST_DWithin(geometry.geom, address.geom, 10) AS within_ten_meters
                  FROM ban_stage AS stage
                  CROSS JOIN LATERAL
                       jsonb_array_elements_text(stage.cadastral_ids) AS cadastral_id(value)
                  LEFT JOIN reference.parcel AS parcel
                         ON parcel.cadastral_id = cadastral_id.value
                  LEFT JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
                  CROSS JOIN LATERAL (
                      SELECT ST_GeomFromText(stage.geometry_wkt, 2154) AS geom
                  ) AS address
                 WHERE NOT stage.is_quarantined
                   AND stage.geometry_wkt IS NOT NULL
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
                   CASE WHEN candidate.resolution <> 'resolved' THEN 0
                        WHEN candidate.point_covered THEN 0.99
                        WHEN candidate.within_ten_meters THEN 0.95
                        ELSE 0.8 END,
                   CASE WHEN candidate.resolution <> 'resolved' THEN 'rejected'
                        WHEN candidate.within_ten_meters THEN 'certain'
                        ELSE 'ambiguous' END,
                   true,
                   candidate.resolution = 'resolved' AND NOT candidate.within_ten_meters,
                   CASE candidate.resolution
                        WHEN 'unresolved_cadastral_reference'
                             THEN 'BAN cad_parcelles names a cadastral parcel that the active'
                                  ' referential does not contain'
                        WHEN 'unpublished_parcel_geometry'
                             THEN 'BAN cad_parcelles names a parcel whose geometry belongs to no'
                                  ' published cadastral release'
                        ELSE 'BAN experimental cad_parcelles relation checked against active'
                             ' parcel geometry'
                        END,
                   jsonb_build_object(
                       'resolution', candidate.resolution,
                       'source_cadastral_id', candidate.cadastral_id,
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
                   properties, false, %(transformation_version)s::text
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
        source_row_count = 0
        quarantined_row_count = 0
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
                source_row_count += 1
                if isinstance(record, RnbQuarantine):
                    quarantined_row_count += 1
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
        normalized_row_count_row = self.connection.execute(
            "SELECT count(*) FROM rnb_stage WHERE NOT is_quarantined"
        ).fetchone()
        normalized_row_count = int(normalized_row_count_row[0]) if normalized_row_count_row else 0
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
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                normalized_row_count,
                quarantined_row_count,
                source_row_count,
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
            (source_row_count, normalized_row_count, quarantined_row_count, import_run_id),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        return SpatialImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_row_count,
            normalized_rows=normalized_row_count,
            quarantined_rows=quarantined_row_count,
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


class BdtopoImporter:
    """Import DS-04 : batiments comme observations du batiment canonique, voirie comme contexte.

    Deux principes gouvernent cet importeur, tous deux issus de l'audit DS-04.

    **Le RNB reste l'identite bativement preferee.** Une emprise BD TOPO ne remplace jamais une
    geometrie RNB, et un batiment RNB ponctuel n'herite d'aucune emprise : les geometries BD
    TOPO restent dans `meta.entity_source_observation`, et `reference.building.geom` n'est
    jamais ecrit ici.

    **L'appariement vient de la source.** `batiment.identifiants_rnb` couvre 96,5 % des
    batiments et `batiment_rnb_lien_bdtopo` publie 957 009 liens officiels. La proximite, seule
    methode qui exigerait un seuil, n'est donc pas executee : elle attend le profiling de B4.
    """

    ALGORITHM_CODE = "bdtopo-rnb-link"
    ALGORITHM_VERSION = "1"

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
                      jsonb_build_object('layer', 'bdtopo', 'raw_asset_id', %s::bigint))
            """,
            (import_run_id, release_id, department_code, idempotency_key, raw_asset_id),
        )
        self._create_stages()

        building_rows = 0
        road_rows = 0
        quarantined_rows = 0

        with self.connection.cursor().copy(
            """
            COPY bdtopo_building_stage (
                is_quarantined, source_row_number, cleabs, geometry_wkt, rnb_identifiers,
                nature, usage_1, usage_2, is_light_construction, lifecycle_state, height_m,
                dwelling_count, storey_count, properties, record_checksum,
                reason_code, reason_detail
            ) FROM STDIN
            """
        ) as copy:
            for record in iter_bdtopo_buildings(source_path):
                building_rows += 1
                if isinstance(record, BdtopoQuarantine):
                    quarantined_rows += 1
                    copy.write_row(
                        (
                            True,
                            record.source_row_number,
                            record.source_feature_id,
                            None,
                            Jsonb([]),
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
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
                            record.cleabs,
                            record.geometry_wkt,
                            Jsonb(list(record.rnb_identifiers)),
                            record.nature,
                            record.usage_1,
                            record.usage_2,
                            record.is_light_construction,
                            record.lifecycle_state,
                            record.height_m,
                            record.dwelling_count,
                            record.storey_count,
                            Jsonb(record.properties),
                            record.record_checksum,
                            None,
                            None,
                        )
                    )

        with self.connection.cursor().copy(
            """
            COPY bdtopo_road_stage (
                is_quarantined, source_row_number, cleabs, geometry_wkt, commune_code_left,
                commune_code_right, nature, importance, is_private, is_fictitious,
                properties, record_checksum, reason_code, reason_detail
            ) FROM STDIN
            """
        ) as copy:
            for record in iter_bdtopo_roads(source_path):
                road_rows += 1
                if isinstance(record, BdtopoQuarantine):
                    quarantined_rows += 1
                    copy.write_row(
                        (
                            True,
                            record.source_row_number,
                            record.source_feature_id,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
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
                            record.cleabs,
                            record.geometry_wkt,
                            record.commune_code_left,
                            record.commune_code_right,
                            record.nature,
                            record.importance,
                            record.is_private,
                            record.is_fictitious,
                            Jsonb(record.properties),
                            record.record_checksum,
                            None,
                            None,
                        )
                    )

        with self.connection.cursor().copy(
            "COPY bdtopo_rnb_link_stage (cleabs, rnb_identifier, building_cleabs) FROM STDIN"
        ) as copy:
            for link in iter_bdtopo_rnb_links(source_path):
                for building_cleabs in link.building_cleabs:
                    copy.write_row((link.cleabs, link.rnb_identifier, building_cleabs))

        self._publish_stage(
            release_id=release_id,
            department_code=department_code,
            raw_asset_id=raw_asset_id,
            import_run_id=import_run_id,
        )

        source_row_count = building_rows + road_rows
        normalized_row_count = source_row_count - quarantined_rows
        self._record_checks(
            release_id=release_id,
            import_run_id=import_run_id,
            department_code=department_code,
            source_row_count=source_row_count,
            normalized_row_count=normalized_row_count,
            quarantined_row_count=quarantined_rows,
        )
        self.connection.execute(
            """
            UPDATE meta.import_run SET
                status = 'succeeded', completed_at = clock_timestamp(),
                source_row_count = %s, normalized_row_count = %s, quarantined_row_count = %s
             WHERE id = %s
            """,
            (source_row_count, normalized_row_count, quarantined_rows, import_run_id),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        return SpatialImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_row_count,
            normalized_rows=normalized_row_count,
            quarantined_rows=quarantined_rows,
            skipped_as_idempotent=False,
        )

    def _create_stages(self) -> None:
        self.connection.execute(
            """
            CREATE TEMP TABLE bdtopo_building_stage (
                is_quarantined boolean NOT NULL,
                source_row_number bigint NOT NULL,
                cleabs text,
                geometry_wkt text,
                rnb_identifiers jsonb NOT NULL,
                nature text,
                usage_1 text,
                usage_2 text,
                is_light_construction boolean,
                lifecycle_state text,
                height_m double precision,
                dwelling_count integer,
                storey_count integer,
                properties jsonb NOT NULL,
                record_checksum char(64),
                reason_code text,
                reason_detail text
            ) ON COMMIT DROP
            """
        )
        self.connection.execute(
            """
            CREATE TEMP TABLE bdtopo_road_stage (
                is_quarantined boolean NOT NULL,
                source_row_number bigint NOT NULL,
                cleabs text,
                geometry_wkt text,
                commune_code_left text,
                commune_code_right text,
                nature text,
                importance text,
                is_private boolean,
                is_fictitious boolean,
                properties jsonb NOT NULL,
                record_checksum char(64),
                reason_code text,
                reason_detail text
            ) ON COMMIT DROP
            """
        )
        self.connection.execute(
            """
            CREATE TEMP TABLE bdtopo_rnb_link_stage (
                cleabs text NOT NULL,
                rnb_identifier text NOT NULL,
                building_cleabs text NOT NULL
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
            "CREATE INDEX ON bdtopo_building_stage (cleabs) WHERE NOT is_quarantined"
        )
        self.connection.execute("CREATE INDEX ON bdtopo_rnb_link_stage (building_cleabs)")

        # Les batiments BD TOPO sont des observations d'une entite canonique existante, pas
        # de nouvelles entites : `entity_id` reste NULL ici et n'est renseigne qu'une fois le
        # rattachement juge certain, plus bas.
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_observation (
                release_id, raw_asset_id, entity_type, entity_id, source_entity_type,
                source_identifier, source_row_number, geometry, properties, record_checksum
            )
            SELECT %(release_id)s, %(raw_asset_id)s, 'building', NULL,
                   'bdtopo_building', cleabs, source_row_number,
                   ST_GeomFromText(geometry_wkt, 2154), properties, record_checksum
              FROM bdtopo_building_stage WHERE NOT is_quarantined
            ON CONFLICT (release_id, source_entity_type, source_identifier, record_checksum)
            DO NOTHING
            """,
            parameters,
        )

        # Chaine de preference, methode par methode. Chaque candidat est conserve avec sa
        # methode et sa justification : un rattachement ecarte reste visible.
        #
        # 1. Identifiant officiel : `batiment.identifiants_rnb`. Un batiment BD TOPO portant
        #    plusieurs identifiants RNB est ambigu **par construction**, pas par erreur — la
        #    source declare elle-meme que l'emprise recouvre plusieurs batiments canoniques.
        self.connection.execute(
            """
            WITH candidate AS (
                SELECT observation.id AS observation_id,
                       'building:rnb:' || rnb.value AS entity_id,
                       jsonb_array_length(stage.rnb_identifiers) AS identifier_count
                  FROM bdtopo_building_stage AS stage
                  JOIN meta.entity_source_observation AS observation
                    ON observation.release_id = %(release_id)s
                   AND observation.source_entity_type = 'bdtopo_building'
                   AND observation.source_identifier = stage.cleabs
                  CROSS JOIN LATERAL jsonb_array_elements_text(stage.rnb_identifiers) AS rnb
                 WHERE NOT stage.is_quarantined
            )
            INSERT INTO meta.entity_observation_link (
                observation_id, entity_type, entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, rationale, evidence, release_ids
            )
            SELECT candidate.observation_id, 'building', candidate.entity_id,
                   'official_identifier', %(algorithm_code)s, %(algorithm_version)s,
                   CASE WHEN candidate.identifier_count = 1 THEN 1 ELSE 0.5 END,
                   CASE WHEN candidate.identifier_count = 1 THEN 'certain' ELSE 'ambiguous' END,
                   CASE WHEN candidate.identifier_count = 1
                        THEN 'BD TOPO carries the official RNB identifier for this footprint'
                        ELSE 'BD TOPO footprint declares several RNB buildings: the source'
                             ' itself states the footprint covers more than one canonical'
                             ' building, so no single attachment can be certain'
                        END,
                   jsonb_build_object('rnb_identifier_count', candidate.identifier_count),
                   jsonb_build_array(%(release_id)s::text)
              FROM candidate
              JOIN reference.building AS building ON building.id = candidate.entity_id
            ON CONFLICT ON CONSTRAINT entity_observation_link_identity DO NOTHING
            """,
            {
                **parameters,
                "algorithm_code": self.ALGORITHM_CODE,
                "algorithm_version": self.ALGORITHM_VERSION,
            },
        )

        # 2. Relation source explicite : la table `batiment_rnb_lien_bdtopo`. Elle ne sert que
        #    la ou l'identifiant direct est absent — sinon elle repeterait le meme couple.
        self.connection.execute(
            """
            WITH candidate AS (
                SELECT DISTINCT observation.id AS observation_id,
                       'building:rnb:' || link.rnb_identifier AS entity_id
                  FROM bdtopo_rnb_link_stage AS link
                  JOIN bdtopo_building_stage AS stage
                    ON stage.cleabs = link.building_cleabs AND NOT stage.is_quarantined
                  JOIN meta.entity_source_observation AS observation
                    ON observation.release_id = %(release_id)s
                   AND observation.source_entity_type = 'bdtopo_building'
                   AND observation.source_identifier = stage.cleabs
                 WHERE jsonb_array_length(stage.rnb_identifiers) = 0
            ), counted AS (
                SELECT observation_id, entity_id,
                       count(*) OVER (PARTITION BY observation_id) AS candidate_count
                  FROM candidate
            )
            INSERT INTO meta.entity_observation_link (
                observation_id, entity_type, entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, rationale, evidence, release_ids
            )
            SELECT counted.observation_id, 'building', counted.entity_id,
                   'source_relation', %(algorithm_code)s, %(algorithm_version)s,
                   CASE WHEN counted.candidate_count = 1 THEN 0.99 ELSE 0.5 END,
                   CASE WHEN counted.candidate_count = 1 THEN 'certain' ELSE 'ambiguous' END,
                   'BD TOPO publishes an explicit RNB link table for this footprint',
                   jsonb_build_object('candidate_count', counted.candidate_count),
                   jsonb_build_array(%(release_id)s::text)
              FROM counted
              JOIN reference.building AS building ON building.id = counted.entity_id
            ON CONFLICT ON CONSTRAINT entity_observation_link_identity DO NOTHING
            """,
            {
                **parameters,
                "algorithm_code": self.ALGORITHM_CODE,
                "algorithm_version": self.ALGORITHM_VERSION,
            },
        )

        # 3. Intersection spatiale, pour ce que la source n'a pas rattache. Elle **ne produit
        #    jamais de rattachement certain** : le taux de recouvrement au-dela duquel deux
        #    emprises decrivent le meme batiment ne vient d'aucune mesure. Le recouvrement est
        #    donc conserve comme preuve, la decision reste ambigue, et sa calibration releve de
        #    B4 — exactement le raisonnement qui a valu a DS-05 son verdict `display_only`.
        #
        #    La proximite, quatrieme methode de la chaine, n'est pas executee : contrairement a
        #    l'intersection elle exige un seuil de distance pour produire le moindre candidat,
        #    et aucun seuil observe n'existe. Un seuil invente est explicitement interdit.
        self.connection.execute(
            """
            WITH unattached AS (
                SELECT observation.id AS observation_id, observation.geometry
                  FROM meta.entity_source_observation AS observation
                 WHERE observation.release_id = %(release_id)s
                   AND observation.source_entity_type = 'bdtopo_building'
                   AND NOT EXISTS (
                       SELECT 1 FROM meta.entity_observation_link AS link
                        WHERE link.observation_id = observation.id
                   )
            ), candidate AS (
                SELECT unattached.observation_id, building.id AS entity_id,
                       ST_Area(ST_Intersection(unattached.geometry, building.geom))
                           / nullif(ST_Area(unattached.geometry), 0) AS overlap_ratio,
                       count(*) OVER (PARTITION BY unattached.observation_id) AS candidate_count
                  FROM unattached
                  JOIN reference.building AS building
                    ON building.geom IS NOT NULL
                   AND ST_Intersects(unattached.geometry, building.geom)
            )
            INSERT INTO meta.entity_observation_link (
                observation_id, entity_type, entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, rationale, evidence, release_ids
            )
            SELECT candidate.observation_id, 'building', candidate.entity_id,
                   'spatial_intersection', %(algorithm_code)s, %(algorithm_version)s,
                   0.5, 'ambiguous',
                   'Footprints intersect but no calibrated overlap threshold exists: the'
                   ' measured ratio is retained as evidence, the attachment is not asserted',
                   jsonb_build_object(
                       'overlap_ratio', round(coalesce(candidate.overlap_ratio, 0)::numeric, 6),
                       'candidate_count', candidate.candidate_count,
                       'threshold_calibrated', false
                   ),
                   jsonb_build_array(%(release_id)s::text)
              FROM candidate
            ON CONFLICT ON CONSTRAINT entity_observation_link_identity DO NOTHING
            """,
            {
                **parameters,
                "algorithm_code": self.ALGORITHM_CODE,
                "algorithm_version": self.ALGORITHM_VERSION,
            },
        )

        # `entity_source_observation.entity_id` reste NULL pour DS-04, et c'est deliberé.
        #
        # Pour le RNB, l'observation *definit* l'entite : y ecrire `entity_id` est une
        # tautologie utile. Pour BD TOPO, l'observation s'*attache* a une entite preexistante
        # au terme d'un jugement, avec une methode, une confiance et un motif — ce que seule
        # `meta.entity_observation_link` sait porter. Recopier le cas certain dans
        # `entity_id` dupliquerait cette decision sans sa justification.
        #
        # La dupliquer coutait par ailleurs tres cher : la table porte un index GiST sur la
        # geometrie, et mettre a jour 910 000 lignes d'emprises y provoquait autant
        # d'insertions GiST. Mesure : l'UPDATE seul depassait 20 minutes sans aboutir. Les
        # lecteurs passent donc par la table de liens, indexee sur
        # `(entity_type, entity_id, decision)`.
        #
        # DS-04 devient un identifiant externe observe du batiment canonique. `is_preferred`
        # reste faux : le RNB garde l'identite batiment preferee.
        self.connection.execute(
            """
            WITH attached AS (
                SELECT link.observation_id, min(link.entity_id) AS entity_id
                  FROM meta.entity_observation_link AS link
                 WHERE link.algorithm_code = %(algorithm_code)s
                   AND link.algorithm_version = %(algorithm_version)s
                   AND link.decision = 'certain'
                 GROUP BY link.observation_id
                HAVING count(*) = 1
            )
            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT 'building', attached.entity_id, 'DS-04', 'bdtopo_building',
                   observation.source_identifier, %(release_id)s, %(release_id)s, false
              FROM attached
              JOIN meta.entity_source_observation AS observation
                ON observation.id = attached.observation_id
            ON CONFLICT ON CONSTRAINT entity_source_identifier_pkey
            DO UPDATE SET last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp()
            """,
            {
                **parameters,
                "algorithm_code": self.ALGORITHM_CODE,
                "algorithm_version": self.ALGORITHM_VERSION,
            },
        )

        # La voirie ne cree aucune entite canonique : c'est une couche de contexte, qui servira
        # a calculer une distance ou un acces (LAND-008). Le departement est resolu depuis les
        # codes INSEE portes par la source, jamais depuis le nom de l'export.
        self.connection.execute(
            """
            INSERT INTO observation.road_segment (
                release_id, raw_asset_id, source_identifier, source_row_number,
                department_code, commune_code_left, commune_code_right, nature, importance,
                is_private, is_fictitious, geom, properties, record_checksum
            )
            SELECT %(release_id)s, %(raw_asset_id)s, cleabs, source_row_number,
                   left(coalesce(commune_code_left, commune_code_right), 2),
                   commune_code_left, commune_code_right, nature, importance,
                   is_private, is_fictitious,
                   ST_Multi(ST_GeomFromText(geometry_wkt, 2154))::geometry(MultiLineString, 2154),
                   properties, record_checksum
              FROM bdtopo_road_stage WHERE NOT is_quarantined
            ON CONFLICT ON CONSTRAINT road_segment_source DO NOTHING
            """,
            parameters,
        )

        for layer, stage in (
            ("batiment", "bdtopo_building_stage"),
            ("troncon_de_route", "bdtopo_road_stage"),
        ):
            self.connection.execute(
                sql.SQL(
                    """
                    INSERT INTO meta.geometry_quarantine (
                        release_id, import_run_id, raw_asset_id, layer, source_feature_id,
                        source_row_number, reason_code, reason_detail, source_properties,
                        repair_attempted, transformation_version
                    )
                    SELECT %(release_id)s, %(import_run_id)s, %(raw_asset_id)s, {layer},
                           cleabs, source_row_number, reason_code, reason_detail,
                           properties, true, {version}
                      FROM {stage} WHERE is_quarantined
                    ON CONFLICT ON CONSTRAINT geometry_quarantine_source DO NOTHING
                    """
                ).format(
                    layer=sql.Literal(layer),
                    version=sql.Literal(BDTOPO_TRANSFORMATION_VERSION),
                    stage=sql.Identifier(stage),
                ),
                parameters,
            )

    def _record_checks(
        self,
        *,
        release_id: str,
        import_run_id: str,
        department_code: str,
        source_row_count: int,
        normalized_row_count: int,
        quarantined_row_count: int,
    ) -> None:
        duplicate_row = self.connection.execute(
            """
            SELECT
              (SELECT count(*) FROM (
                  SELECT cleabs FROM bdtopo_building_stage WHERE NOT is_quarantined
                   GROUP BY cleabs HAVING count(*) > 1) AS d),
              (SELECT count(*) FROM (
                  SELECT cleabs FROM bdtopo_road_stage WHERE NOT is_quarantined
                   GROUP BY cleabs HAVING count(*) > 1) AS d)
            """
        ).fetchone()
        duplicate_count = (
            int(duplicate_row[0]) + int(duplicate_row[1]) if duplicate_row is not None else 0
        )
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, import_run_id, check_code, check_version, scope_type,
                scope_code, layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            ) VALUES
                (%s, %s, 'source_vs_normalized_count', '1', 'department', %s, 'bdtopo',
                 CASE WHEN %s = %s + %s THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %s = %s + %s THEN 'info' ELSE 'error' END,
                 true, %s + %s, %s, '{}'::jsonb),
                (%s, %s, 'identifier_uniqueness', '1', 'department', %s, 'bdtopo',
                 CASE WHEN %s = 0 THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %s = 0 THEN 'info' ELSE 'error' END,
                 true, %s, 0, '{}'::jsonb)
            ON CONFLICT ON CONSTRAINT data_quality_result_identity DO UPDATE SET
                status = EXCLUDED.status, severity = EXCLUDED.severity,
                observed_value = EXCLUDED.observed_value, checked_at = clock_timestamp()
            """,
            (
                release_id,
                import_run_id,
                department_code,
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                normalized_row_count,
                quarantined_row_count,
                source_row_count,
                release_id,
                import_run_id,
                department_code,
                duplicate_count,
                duplicate_count,
                duplicate_count,
            ),
        )

    def refresh_match_metrics(self, release_id: str, department_code: str) -> None:
        """Distribution en quatre classes par commune, jamais trois.

        La commune d'une observation rattachee vient du batiment canonique. Celle d'une
        observation non rattachee est resolue spatialement contre le referentiel communal
        actif : comme il ne couvre que le departement, une observation qui ne tombe dans
        aucune commune est **hors departement**, ce qui est compte a part et non ecarte.
        """
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        parameters = {
            "release_id": release_id,
            "department_code": department_code,
            "algorithm_code": self.ALGORITHM_CODE,
            "algorithm_version": self.ALGORITHM_VERSION,
        }
        self.connection.execute(
            """
            WITH observation AS (
                SELECT o.id, o.entity_id, o.geometry
                  FROM meta.entity_source_observation AS o
                 WHERE o.release_id = %(release_id)s
                   AND o.source_entity_type = 'bdtopo_building'
            ), decided AS (
                SELECT observation.id, observation.geometry,
                       coalesce(bool_or(link.decision = 'certain'), false) AS certain,
                       coalesce(bool_or(link.decision = 'ambiguous'), false) AS ambiguous,
                       coalesce(bool_or(link.decision = 'rejected'), false) AS rejected,
                       min(attached.commune_code) FILTER (
                           WHERE link.decision = 'certain'
                       ) AS attached_commune_code
                  FROM observation
                  LEFT JOIN meta.entity_observation_link AS link
                         ON link.observation_id = observation.id
                        AND link.algorithm_code = %(algorithm_code)s
                        AND link.algorithm_version = %(algorithm_version)s
                  LEFT JOIN reference.building AS attached
                         ON attached.id = link.entity_id
                 GROUP BY observation.id, observation.geometry
            ), classified AS (
                -- La commune d'une observation rattachee vient du batiment canonique. Sinon
                -- elle est resolue spatialement : le referentiel communal actif ne couvre que
                -- le departement, donc une observation qui ne tombe dans aucune commune est
                -- hors departement — comptee a part, jamais ecartee.
                SELECT decided.id, decided.certain, decided.ambiguous, decided.rejected,
                       coalesce(
                           decided.attached_commune_code,
                           (SELECT commune.code
                              FROM reference.area AS commune
                             WHERE commune.area_type = 'commune'
                               AND commune.department_code = %(department_code)s
                               AND ST_Covers(
                                   commune.geom, ST_PointOnSurface(decided.geometry)
                               )
                             LIMIT 1)
                       ) AS commune_code
                  FROM decided
            ), aggregate AS (
                SELECT commune.code,
                       count(*) FILTER (WHERE classified.certain) AS certain_count,
                       count(*) FILTER (
                           WHERE NOT classified.certain AND classified.ambiguous
                       ) AS ambiguous_count,
                       count(*) FILTER (
                           WHERE NOT classified.certain AND NOT classified.ambiguous
                             AND classified.rejected
                       ) AS rejected_count,
                       count(classified.id) FILTER (
                           WHERE NOT classified.certain AND NOT classified.ambiguous
                             AND NOT classified.rejected
                       ) AS unmatched_count
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
            SELECT %(release_id)s, code, 'bdtopo_building_rnb', %(algorithm_code)s,
                   %(algorithm_version)s, certain_count, ambiguous_count,
                   rejected_count, unmatched_count
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
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, check_code, check_version, scope_type, scope_code,
                layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            )
            SELECT metric.release_id, 'match_rate', '1', 'commune', metric.commune_code,
                   'bdtopo_building_rnb', 'passed', 'info', false,
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
             WHERE metric.release_id = %s AND metric.relation_type = 'bdtopo_building_rnb'
            ON CONFLICT ON CONSTRAINT data_quality_result_identity DO UPDATE SET
                observed_value = EXCLUDED.observed_value,
                details = EXCLUDED.details,
                checked_at = clock_timestamp()
            """,
            (release_id,),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def method_rates(self, release_id: str) -> dict[str, Any]:
        """Taux d'appariement par methode et hors departement, pour le rapport d'audit."""
        with self.connection.cursor(row_factory=dict_row) as cursor:
            by_method = cursor.execute(
                """
                SELECT link.method, link.decision, count(*) AS count
                  FROM meta.entity_observation_link AS link
                  JOIN meta.entity_source_observation AS observation
                    ON observation.id = link.observation_id
                 WHERE observation.release_id = %s
                   AND observation.source_entity_type = 'bdtopo_building'
                 GROUP BY link.method, link.decision
                 ORDER BY link.method, link.decision
                """,
                (release_id,),
            ).fetchall()
            totals = cursor.execute(
                """
                SELECT count(*) AS observations,
                       count(*) FILTER (
                           WHERE EXISTS (
                               SELECT 1 FROM meta.entity_observation_link AS link
                                WHERE link.observation_id = observation.id
                                  AND link.decision = 'certain'
                           )
                       ) AS attached_certain,
                       count(*) FILTER (
                           WHERE NOT EXISTS (
                               SELECT 1 FROM meta.entity_observation_link AS link
                                WHERE link.observation_id = observation.id
                           )
                       ) AS unmatched
                  FROM meta.entity_source_observation AS observation
                 WHERE observation.release_id = %s
                   AND observation.source_entity_type = 'bdtopo_building'
                """,
                (release_id,),
            ).fetchone()
            roads = cursor.execute(
                """
                SELECT count(*) AS segments,
                       count(*) FILTER (WHERE department_code = %s) AS in_department,
                       count(*) FILTER (
                           WHERE department_code IS DISTINCT FROM %s
                       ) AS outside_department
                  FROM observation.road_segment WHERE release_id = %s
                """,
                ("35", "35", release_id),
            ).fetchone()
        return {
            "buildings": dict(totals) if totals else {},
            "by_method": [dict(row) for row in by_method],
            "roads": dict(roads) if roads else {},
        }


class BdnbImporter:
    """Import DS-03 : le groupe BDNB comme observation, rattache au batiment canonique RNB.

    **Le groupe n'est jamais reduit a un batiment.** Un groupe couvrant plusieurs batiments RNB
    produit un lien par batiment, tous ambigus : ses attributs sont publies au niveau groupe et
    ne sont donc attribuables a aucun d'entre eux en particulier. Seul un groupe se resolvant en
    un **unique** batiment, par des relations toutes qualifiees « Alignement 1 BC = 1 RNB,
    recouvrement >= 95 % », porte un rattachement certain.

    Le seuil de 95 % est celui du producteur, qui l'enonce dans `type_appariement` : ce n'est pas
    une confiance opaque mais la description de la relation observee. Aucun seuil n'est invente
    ici — c'est ce qui distingue DS-03 de DS-04, dont l'intersection geometrique reste ambigue
    faute de critere declare.

    `entity_source_observation.entity_id` reste NULL, comme pour DS-04 : la decision de
    rattachement vit dans `meta.entity_observation_link` avec sa methode et son motif, et
    mettre a jour 546 301 lignes portant une geometrie indexee en GiST coutait vingt minutes
    pour une information dupliquee.
    """

    ALGORITHM_CODE = "bdnb-group-rnb-link"
    ALGORITHM_VERSION = "1"

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

        # Controle bloquant du contrat, avant tout import : aucune colonne reservee a des
        # ayants droit ne doit figurer dans un export declare Open. Verifie contre le
        # dictionnaire du producteur livre dans l'archive.
        policy = verify_field_policy(source_path)

        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        self.connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'running',
                      jsonb_build_object('layer', 'bdnb', 'raw_asset_id', %s::bigint,
                                         'field_policy', %s::jsonb))
            """,
            (
                import_run_id,
                release_id,
                department_code,
                idempotency_key,
                raw_asset_id,
                Jsonb(policy),
            ),
        )
        self._create_stages()

        source_rows = 0
        quarantined_rows = 0
        with self.connection.cursor().copy(
            """
            COPY bdnb_group_stage (
                is_quarantined, source_row_number, group_id, geometry_wkt, commune_code,
                department_code, iris_code, epci_code, ground_area_m2,
                has_fictitious_geometry, construction_year, storey_count, dwelling_count,
                usage_label, wall_material, roof_material, properties, record_checksum,
                reason_code, reason_detail
            ) FROM STDIN
            """
        ) as copy:
            for record in iter_bdnb_groups(source_path):
                source_rows += 1
                if isinstance(record, BdnbQuarantine):
                    quarantined_rows += 1
                    copy.write_row(
                        (
                            True,
                            record.source_row_number,
                            record.source_feature_id,
                            *([None] * 13),
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
                            record.group_id,
                            record.geometry_wkt,
                            record.commune_code,
                            record.department_code,
                            record.iris_code,
                            record.epci_code,
                            record.ground_area_m2,
                            record.has_fictitious_geometry,
                            record.construction_year,
                            record.storey_count,
                            record.dwelling_count,
                            record.usage_label,
                            record.wall_material,
                            record.roof_material,
                            Jsonb(record.properties),
                            record.record_checksum,
                            None,
                            None,
                        )
                    )

        link_rows = 0
        with self.connection.cursor().copy(
            """
            COPY bdnb_link_stage (
                group_id, rnb_id, rnb_count_for_group, relation_count,
                aligned_relation_count, match_types
            ) FROM STDIN
            """
        ) as copy:
            for link in iter_bdnb_group_rnb_links(source_path):
                link_rows += 1
                copy.write_row(
                    (
                        link.group_id,
                        link.rnb_id,
                        link.rnb_count_for_group,
                        link.relation_count,
                        link.aligned_relation_count,
                        Jsonb(list(link.match_types)),
                    )
                )

        self._publish_stage(
            release_id=release_id,
            department_code=department_code,
            raw_asset_id=raw_asset_id,
            import_run_id=import_run_id,
        )
        normalized_rows = source_rows - quarantined_rows
        self._record_checks(
            release_id=release_id,
            import_run_id=import_run_id,
            department_code=department_code,
            source_row_count=source_rows,
            normalized_row_count=normalized_rows,
            quarantined_row_count=quarantined_rows,
            policy=policy,
        )
        self.connection.execute(
            """
            UPDATE meta.import_run SET
                status = 'succeeded', completed_at = clock_timestamp(),
                source_row_count = %s, normalized_row_count = %s, quarantined_row_count = %s
             WHERE id = %s
            """,
            (source_rows, normalized_rows, quarantined_rows, import_run_id),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()
        return SpatialImportOutcome(
            import_run_id=import_run_id,
            source_rows=source_rows,
            normalized_rows=normalized_rows,
            quarantined_rows=quarantined_rows,
            skipped_as_idempotent=False,
        )

    def _create_stages(self) -> None:
        self.connection.execute(
            """
            CREATE TEMP TABLE bdnb_group_stage (
                is_quarantined boolean NOT NULL,
                source_row_number bigint NOT NULL,
                group_id text,
                geometry_wkt text,
                commune_code text,
                department_code text,
                iris_code text,
                epci_code text,
                ground_area_m2 double precision,
                has_fictitious_geometry boolean,
                construction_year integer,
                storey_count integer,
                dwelling_count integer,
                usage_label text,
                wall_material text,
                roof_material text,
                properties jsonb NOT NULL,
                record_checksum char(64),
                reason_code text,
                reason_detail text
            ) ON COMMIT DROP
            """
        )
        self.connection.execute(
            """
            CREATE TEMP TABLE bdnb_link_stage (
                group_id text NOT NULL,
                rnb_id text NOT NULL,
                rnb_count_for_group integer NOT NULL,
                relation_count integer NOT NULL,
                aligned_relation_count integer NOT NULL,
                match_types jsonb NOT NULL
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
            "algorithm_code": self.ALGORITHM_CODE,
            "algorithm_version": self.ALGORITHM_VERSION,
        }
        self.connection.execute(
            "CREATE INDEX ON bdnb_group_stage (group_id) WHERE NOT is_quarantined"
        )
        self.connection.execute("CREATE INDEX ON bdnb_link_stage (group_id)")

        # Le groupe est une observation d'un batiment canonique, pas une entite nouvelle :
        # `entity_id` reste NULL et la decision de rattachement vit dans la table de liens.
        # Les six champs Fichiers Fonciers sont persistes explicitement, aux cotes des
        # attributs source intacts.
        self.connection.execute(
            """
            INSERT INTO meta.entity_source_observation (
                release_id, raw_asset_id, entity_type, entity_id, source_entity_type,
                source_identifier, source_row_number, geometry, properties, record_checksum
            )
            SELECT %(release_id)s, %(raw_asset_id)s, 'building', NULL,
                   'bdnb_building_group', group_id, source_row_number,
                   ST_GeomFromText(geometry_wkt, 2154),
                   properties || jsonb_build_object(
                       'entity_level', 'building_group_not_physical_building',
                       'commune_code', commune_code,
                       'ground_area_m2', ground_area_m2,
                       'has_fictitious_geometry', has_fictitious_geometry,
                       'ffo_observed', jsonb_build_object(
                           'construction_year', construction_year,
                           'storey_count', storey_count,
                           'dwelling_count', dwelling_count,
                           'usage_label', usage_label,
                           'wall_material', wall_material,
                           'roof_material', roof_material
                       )
                   ),
                   record_checksum
              FROM bdnb_group_stage WHERE NOT is_quarantined
            ON CONFLICT (release_id, source_entity_type, source_identifier, record_checksum)
            DO NOTHING
            """,
            parameters,
        )

        # La decision, couple par couple.
        #
        # `certain` exige deux conditions cumulees : le groupe se resout en un unique batiment
        # RNB, et **toutes** les relations construction <-> RNB qui y contribuent portent le
        # type aligne. Un groupe couvrant plusieurs batiments produit autant de liens ambigus :
        # ses attributs restent au niveau groupe, ce qui est la seule reponse juste puisque
        # les attribuer a l'un d'eux serait arbitraire et les attribuer a tous les compterait
        # plusieurs fois.
        self.connection.execute(
            """
            WITH candidate AS (
                SELECT observation.id AS observation_id, link.*
                  FROM bdnb_link_stage AS link
                  JOIN meta.entity_source_observation AS observation
                    ON observation.release_id = %(release_id)s
                   AND observation.source_entity_type = 'bdnb_building_group'
                   AND observation.source_identifier = link.group_id
                  JOIN reference.building AS building
                    ON building.id = 'building:rnb:' || link.rnb_id
            )
            INSERT INTO meta.entity_observation_link (
                observation_id, entity_type, entity_id, method, algorithm_code,
                algorithm_version, confidence, decision, rationale, evidence, release_ids
            )
            SELECT candidate.observation_id, 'building',
                   'building:rnb:' || candidate.rnb_id,
                   'source_relation', %(algorithm_code)s, %(algorithm_version)s,
                   CASE WHEN candidate.rnb_count_for_group = 1
                             AND candidate.aligned_relation_count = candidate.relation_count
                        THEN 0.99 ELSE 0.5 END,
                   CASE WHEN candidate.rnb_count_for_group = 1
                             AND candidate.aligned_relation_count = candidate.relation_count
                        THEN 'certain' ELSE 'ambiguous' END,
                   CASE
                     WHEN candidate.rnb_count_for_group > 1
                       THEN 'BDNB group spans several canonical buildings: its group-level'
                            ' attributes belong to none of them in particular'
                     WHEN candidate.aligned_relation_count < candidate.relation_count
                       THEN 'Producer qualifies at least one contributing relation as diverging,'
                            ' split, merged, partial or fictitious'
                     ELSE 'Producer states a 1:1 construction to RNB alignment with at least'
                          ' 95 percent geometric overlap'
                     END,
                   jsonb_build_object(
                       'rnb_buildings_for_group', candidate.rnb_count_for_group,
                       'contributing_relations', candidate.relation_count,
                       'aligned_relations', candidate.aligned_relation_count,
                       'producer_match_types', candidate.match_types,
                       'threshold_declared_by_producer', true
                   ),
                   jsonb_build_array(%(release_id)s::text)
              FROM candidate
            ON CONFLICT ON CONSTRAINT entity_observation_link_identity DO NOTHING
            """,
            parameters,
        )

        # Mesurer ce que le producteur affirme, plutot que le croire.
        #
        # `type_appariement` enonce un recouvrement >= 95 % **au niveau construction**. Nous ne
        # detenons pas la geometrie des constructions — volontairement, elle est documentee
        # `(ign)` et DS-04 la fournit — donc nous mesurons au niveau groupe, ce qui est un
        # majorant plus lache. Sur echantillon, la mediane est a 1,0000 et 96,9 % des
        # rattachements certains depassent 95 % ; l'ecart residuel s'explique entierement par
        # un groupe plus vaste que le batiment, pas par un rattachement faux.
        #
        # La consequence importe a B5 : meme certain, un attribut publie au niveau groupe peut
        # decrire plus que le batiment auquel il est rattache. Le rapport de surface est donc
        # persiste comme preuve, pour que le calcul des features puisse ecarter les cas ou le
        # groupe deborde — sans quoi un `nb_log` de groupe surcompterait en silence.
        self.connection.execute(
            """
            UPDATE meta.entity_observation_link AS link
               SET evidence = link.evidence || jsonb_build_object(
                       'group_building_overlap_ratio',
                       round(measured.overlap_ratio::numeric, 6),
                       'group_area_over_building_area',
                       round(measured.area_ratio::numeric, 6)
                   )
              FROM (
                  SELECT link.id,
                         ST_Area(ST_Intersection(observation.geometry, building.geom))
                             / nullif(ST_Area(observation.geometry), 0) AS overlap_ratio,
                         ST_Area(observation.geometry)
                             / nullif(ST_Area(building.geom), 0) AS area_ratio
                    FROM meta.entity_observation_link AS link
                    JOIN meta.entity_source_observation AS observation
                      ON observation.id = link.observation_id
                     AND observation.release_id = %(release_id)s
                     AND observation.source_entity_type = 'bdnb_building_group'
                    JOIN reference.building AS building
                      ON building.id = link.entity_id
                     AND building.geom IS NOT NULL
                   WHERE link.algorithm_code = %(algorithm_code)s
                     AND link.algorithm_version = %(algorithm_version)s
                     AND link.decision = 'certain'
              ) AS measured
             WHERE link.id = measured.id
            """,
            parameters,
        )

        # DS-03 devient un identifiant externe observe du batiment canonique, seulement pour
        # un rattachement certain et unique. Le RNB garde l'identite preferee.
        self.connection.execute(
            """
            WITH attached AS (
                SELECT link.observation_id, min(link.entity_id) AS entity_id
                  FROM meta.entity_observation_link AS link
                 WHERE link.algorithm_code = %(algorithm_code)s
                   AND link.algorithm_version = %(algorithm_version)s
                   AND link.decision = 'certain'
                 GROUP BY link.observation_id
                HAVING count(*) = 1
            )
            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT 'building', attached.entity_id, 'DS-03', 'bdnb_building_group',
                   observation.source_identifier, %(release_id)s, %(release_id)s, false
              FROM attached
              JOIN meta.entity_source_observation AS observation
                ON observation.id = attached.observation_id
            ON CONFLICT ON CONSTRAINT entity_source_identifier_pkey
            DO UPDATE SET last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp()
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
            SELECT %(release_id)s, %(import_run_id)s, %(raw_asset_id)s, 'batiment_groupe',
                   group_id, source_row_number, reason_code, reason_detail,
                   properties, true, 'bdnb-open-normalize@1'
              FROM bdnb_group_stage WHERE is_quarantined
            ON CONFLICT ON CONSTRAINT geometry_quarantine_source DO NOTHING
            """,
            parameters,
        )

    def _record_checks(
        self,
        *,
        release_id: str,
        import_run_id: str,
        department_code: str,
        source_row_count: int,
        normalized_row_count: int,
        quarantined_row_count: int,
        policy: dict[str, Any],
    ) -> None:
        duplicate_row = self.connection.execute(
            """
            SELECT count(*) FROM (
                SELECT group_id FROM bdnb_group_stage WHERE NOT is_quarantined
                 GROUP BY group_id HAVING count(*) > 1) AS duplicates
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
                (%s, %s, 'source_vs_normalized_count', '1', 'department', %s, 'bdnb',
                 CASE WHEN %s = %s + %s THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %s = %s + %s THEN 'info' ELSE 'error' END,
                 true, %s + %s, %s, '{}'::jsonb),
                (%s, %s, 'identifier_uniqueness', '1', 'department', %s, 'bdnb',
                 CASE WHEN %s = 0 THEN 'passed' ELSE 'failed' END,
                 CASE WHEN %s = 0 THEN 'info' ELSE 'error' END,
                 true, %s, 0, '{}'::jsonb),
                (%s, %s, 'expert_fields_excluded', '1', 'department', %s, 'bdnb',
                 'passed', 'info', true, 0, 0, %s::jsonb)
            ON CONFLICT ON CONSTRAINT data_quality_result_identity DO UPDATE SET
                status = EXCLUDED.status, severity = EXCLUDED.severity,
                observed_value = EXCLUDED.observed_value, details = EXCLUDED.details,
                checked_at = clock_timestamp()
            """,
            (
                release_id,
                import_run_id,
                department_code,
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                source_row_count,
                normalized_row_count,
                quarantined_row_count,
                normalized_row_count,
                quarantined_row_count,
                source_row_count,
                release_id,
                import_run_id,
                department_code,
                duplicate_count,
                duplicate_count,
                duplicate_count,
                release_id,
                import_run_id,
                department_code,
                Jsonb(policy),
            ),
        )

    def refresh_match_metrics(self, release_id: str, department_code: str) -> None:
        """Distribution en quatre classes par commune.

        La commune est portee par le groupe lui-meme (`code_commune_insee`), donc aucune
        resolution spatiale n'est necessaire ici — contrairement a DS-04, dont l'export
        deborde du departement sans le dire.
        """
        self.connection.execute("SET LOCAL ROLE pipeline_rw")
        parameters = {
            "release_id": release_id,
            "department_code": department_code,
            "algorithm_code": self.ALGORITHM_CODE,
            "algorithm_version": self.ALGORITHM_VERSION,
        }
        self.connection.execute(
            """
            WITH decided AS (
                SELECT observation.id,
                       observation.properties->>'commune_code' AS commune_code,
                       coalesce(bool_or(link.decision = 'certain'), false) AS certain,
                       coalesce(bool_or(link.decision = 'ambiguous'), false) AS ambiguous,
                       coalesce(bool_or(link.decision = 'rejected'), false) AS rejected
                  FROM meta.entity_source_observation AS observation
                  LEFT JOIN meta.entity_observation_link AS link
                         ON link.observation_id = observation.id
                        AND link.algorithm_code = %(algorithm_code)s
                        AND link.algorithm_version = %(algorithm_version)s
                 WHERE observation.release_id = %(release_id)s
                   AND observation.source_entity_type = 'bdnb_building_group'
                 GROUP BY observation.id, observation.properties->>'commune_code'
            ), aggregate AS (
                SELECT commune.code,
                       count(*) FILTER (WHERE decided.certain) AS certain_count,
                       count(*) FILTER (
                           WHERE NOT decided.certain AND decided.ambiguous
                       ) AS ambiguous_count,
                       count(*) FILTER (
                           WHERE NOT decided.certain AND NOT decided.ambiguous
                             AND decided.rejected
                       ) AS rejected_count,
                       count(decided.id) FILTER (
                           WHERE NOT decided.certain AND NOT decided.ambiguous
                             AND NOT decided.rejected
                       ) AS unmatched_count
                  FROM reference.area AS commune
                  LEFT JOIN decided ON decided.commune_code = commune.code
                 WHERE commune.area_type = 'commune'
                   AND commune.department_code = %(department_code)s
                 GROUP BY commune.code
            )
            INSERT INTO meta.entity_match_metric (
                release_id, commune_code, relation_type, algorithm_code,
                algorithm_version, certain_count, ambiguous_count,
                rejected_count, unmatched_count
            )
            SELECT %(release_id)s, code, 'bdnb_group_rnb', %(algorithm_code)s,
                   %(algorithm_version)s, certain_count, ambiguous_count,
                   rejected_count, unmatched_count
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
            parameters,
        )
        self.connection.execute(
            """
            INSERT INTO meta.data_quality_check (
                release_id, check_code, check_version, scope_type, scope_code,
                layer, status, severity, blocks_publication,
                observed_value, expected_value, details
            )
            SELECT metric.release_id, 'match_rate', '1', 'commune', metric.commune_code,
                   'bdnb_group_rnb', 'passed', 'info', false,
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
             WHERE metric.release_id = %s AND metric.relation_type = 'bdnb_group_rnb'
            ON CONFLICT ON CONSTRAINT data_quality_result_identity DO UPDATE SET
                observed_value = EXCLUDED.observed_value,
                details = EXCLUDED.details,
                checked_at = clock_timestamp()
            """,
            (release_id,),
        )
        self.connection.execute("RESET ROLE")
        self.connection.commit()

    def report(self, release_id: str) -> dict[str, Any]:
        """Volumetries et taux, pour le rapport d'acceptation."""
        with self.connection.cursor(row_factory=dict_row) as cursor:
            groups = cursor.execute(
                """
                SELECT count(*) AS groups,
                       count(*) FILTER (
                           WHERE properties->>'has_fictitious_geometry' = 'true'
                       ) AS fictitious_geometry,
                       count(*) FILTER (
                           WHERE properties->'ffo_observed'->>'construction_year' IS NOT NULL
                       ) AS with_construction_year,
                       count(*) FILTER (
                           WHERE properties->'ffo_observed'->>'storey_count' IS NOT NULL
                       ) AS with_storey_count,
                       count(*) FILTER (
                           WHERE properties->'ffo_observed'->>'dwelling_count' IS NOT NULL
                       ) AS with_dwelling_count
                  FROM meta.entity_source_observation
                 WHERE release_id = %s AND source_entity_type = 'bdnb_building_group'
                """,
                (release_id,),
            ).fetchone()
            decisions = cursor.execute(
                """
                SELECT link.decision, count(*) AS links,
                       count(DISTINCT link.observation_id) AS groups,
                       count(DISTINCT link.entity_id) AS buildings
                  FROM meta.entity_observation_link AS link
                  JOIN meta.entity_source_observation AS observation
                    ON observation.id = link.observation_id
                 WHERE observation.release_id = %s
                   AND observation.source_entity_type = 'bdnb_building_group'
                 GROUP BY link.decision ORDER BY link.decision
                """,
                (release_id,),
            ).fetchall()
            unmatched = cursor.execute(
                """
                SELECT count(*) AS unmatched
                  FROM meta.entity_source_observation AS observation
                 WHERE observation.release_id = %s
                   AND observation.source_entity_type = 'bdnb_building_group'
                   AND NOT EXISTS (
                       SELECT 1 FROM meta.entity_observation_link AS link
                        WHERE link.observation_id = observation.id
                   )
                """,
                (release_id,),
            ).fetchone()
        return {
            "groups": dict(groups) if groups else {},
            "decisions": [dict(row) for row in decisions],
            "unmatched_groups": dict(unmatched) if unmatched else {},
        }
