"""Add stable spatial entities, explainable matches and morphology features.

Revision ID: 20260805_0005
Revises: 20260804_0004
Create Date: 2026-08-05 10:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260805_0005"
down_revision: str | None = "20260804_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REFERENCE_TABLES = (
    "area",
    "address",
    "parcel",
    "building",
    "building_parcel",
    "property_unit",
    "property_unit_member",
)

MATCH_TABLES = (
    "entity_source_observation",
    "entity_source_identifier",
    "entity_match",
    "entity_match_review",
    "entity_match_metric",
)

FEATURE_TABLES = ("feature_definition", "feature_value")


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    op.execute(
        """
        CREATE TABLE reference.area (
            id text PRIMARY KEY,
            area_type text NOT NULL,
            code text NOT NULL,
            parent_area_id text REFERENCES reference.area(id),
            name text,
            department_code text NOT NULL,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT area_identity UNIQUE (area_type, code),
            CONSTRAINT area_id_format CHECK (id ~ '^area:[a-z_]+:[^:]+$'),
            CONSTRAINT area_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT area_geom_nonempty CHECK (NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.address (
            id text PRIMARY KEY,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            display_label text NOT NULL,
            normalized_label text NOT NULL,
            house_number text,
            repetition_index text,
            street_name text,
            postal_code text,
            position_type text,
            is_municipality_certified boolean,
            geom geometry(Point, 2154) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT address_id_format CHECK (id ~ '^address:[a-z0-9_-]+:.+$'),
            CONSTRAINT address_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT address_geom_nonempty CHECK (NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.parcel (
            id text PRIMARY KEY,
            cadastral_id text NOT NULL UNIQUE,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT parcel_id_format CHECK (id ~ '^parcel:cadastre:.+$'),
            CONSTRAINT parcel_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT parcel_geom_nonempty CHECK (NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.building (
            id text PRIMARY KEY,
            preferred_identity_source text NOT NULL,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            lifecycle_status text NOT NULL DEFAULT 'active',
            geom geometry(MultiPolygon, 2154) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT building_id_format CHECK (id ~ '^building:[a-z0-9_-]+:.+$'),
            CONSTRAINT building_identity_source CHECK (
                preferred_identity_source IN ('RNB', 'BDNB', 'BDTOPO', 'CADASTRE', 'RESOLVED')
            ),
            CONSTRAINT building_lifecycle CHECK (
                lifecycle_status IN ('active', 'demolished', 'superseded', 'unknown')
            ),
            CONSTRAINT building_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT building_geom_nonempty CHECK (NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.property_unit (
            id text PRIMARY KEY,
            stable_key text NOT NULL UNIQUE,
            unit_type text NOT NULL,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            publication_eligible boolean NOT NULL DEFAULT false,
            exclusion_reason text,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT property_unit_id_format CHECK (id ~ '^property-unit:.+$'),
            CONSTRAINT property_unit_type CHECK (
                unit_type IN ('single_parcel', 'multi_parcel', 'building_centric', 'manual')
            ),
            CONSTRAINT property_unit_publication_reason CHECK (
                publication_eligible OR exclusion_reason IS NOT NULL
            ),
            CONSTRAINT property_unit_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT property_unit_geom_nonempty CHECK (NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.building_parcel (
            building_id text NOT NULL REFERENCES reference.building(id) ON DELETE CASCADE,
            parcel_id text NOT NULL REFERENCES reference.parcel(id) ON DELETE CASCADE,
            relation_status text NOT NULL,
            match_id bigint,
            building_overlap_ratio numeric(8, 7),
            parcel_overlap_ratio numeric(8, 7),
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (building_id, parcel_id),
            CONSTRAINT building_parcel_status CHECK (
                relation_status IN ('certain', 'ambiguous', 'rejected')
            ),
            CONSTRAINT building_overlap_range CHECK (
                building_overlap_ratio IS NULL
                OR building_overlap_ratio BETWEEN 0 AND 1
            ),
            CONSTRAINT parcel_overlap_range CHECK (
                parcel_overlap_ratio IS NULL
                OR parcel_overlap_ratio BETWEEN 0 AND 1
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.property_unit_member (
            property_unit_id text NOT NULL
                REFERENCES reference.property_unit(id) ON DELETE CASCADE,
            entity_type text NOT NULL,
            entity_id text NOT NULL,
            member_role text NOT NULL,
            match_id bigint,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (property_unit_id, entity_type, entity_id),
            CONSTRAINT property_unit_member_type CHECK (
                entity_type IN ('address', 'parcel', 'building')
            ),
            CONSTRAINT property_unit_member_role CHECK (
                member_role IN ('primary', 'supporting', 'ambiguous')
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE meta.entity_source_observation (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            entity_type text NOT NULL,
            entity_id text,
            source_entity_type text NOT NULL,
            source_identifier text NOT NULL,
            source_row_number bigint,
            geometry geometry(Geometry, 2154),
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            record_checksum char(64) NOT NULL CHECK (record_checksum ~ '^[0-9a-f]{64}$'),
            observed_from date,
            observed_to date,
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT entity_source_observation_entity_type CHECK (
                entity_type IN ('area', 'address', 'parcel', 'building', 'property_unit')
            ),
            CONSTRAINT entity_source_observation_source UNIQUE (
                release_id, source_entity_type, source_identifier, record_checksum
            ),
            CONSTRAINT entity_source_observation_geom_valid CHECK (
                geometry IS NULL OR ST_IsValid(geometry)
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.entity_source_identifier (
            entity_type text NOT NULL,
            entity_id text NOT NULL,
            data_source_id text NOT NULL REFERENCES meta.data_source(id),
            source_entity_type text NOT NULL,
            source_identifier text NOT NULL,
            first_release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            last_release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            is_preferred boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (entity_type, entity_id, data_source_id, source_entity_type, source_identifier),
            CONSTRAINT entity_source_identifier_entity_type CHECK (
                entity_type IN ('area', 'address', 'parcel', 'building', 'property_unit')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.entity_match (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            candidate_group_key text NOT NULL,
            left_entity_type text NOT NULL,
            left_entity_id text NOT NULL,
            right_entity_type text NOT NULL,
            right_entity_id text NOT NULL,
            method text NOT NULL,
            algorithm_code text NOT NULL,
            algorithm_version text NOT NULL,
            confidence numeric(6, 5) NOT NULL,
            decision text NOT NULL,
            critical boolean NOT NULL DEFAULT false,
            blocks_publication boolean NOT NULL DEFAULT false,
            rationale text NOT NULL,
            evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
            release_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
            supersedes_match_id bigint REFERENCES meta.entity_match(id),
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT entity_match_entity_types CHECK (
                left_entity_type IN ('area', 'address', 'parcel', 'building', 'property_unit')
                AND right_entity_type IN ('area', 'address', 'parcel', 'building', 'property_unit')
                AND left_entity_type <> right_entity_type
            ),
            CONSTRAINT entity_match_method CHECK (
                method IN (
                    'official_identifier', 'source_relation', 'spatial_intersection',
                    'proximity', 'normalized_address', 'temporal_consistency', 'manual'
                )
            ),
            CONSTRAINT entity_match_confidence CHECK (confidence BETWEEN 0 AND 1),
            CONSTRAINT entity_match_decision CHECK (
                decision IN ('certain', 'ambiguous', 'rejected')
            ),
            CONSTRAINT entity_match_blocking_consistency CHECK (
                NOT blocks_publication OR (critical AND decision = 'ambiguous')
            ),
            CONSTRAINT entity_match_versioned UNIQUE (
                candidate_group_key, left_entity_type, left_entity_id,
                right_entity_type, right_entity_id, algorithm_code, algorithm_version
            )
        )
        """
    )
    op.execute(
        "ALTER TABLE reference.building_parcel ADD CONSTRAINT building_parcel_match_fk "
        "FOREIGN KEY (match_id) REFERENCES meta.entity_match(id)"
    )
    op.execute(
        "ALTER TABLE reference.property_unit_member ADD CONSTRAINT property_unit_member_match_fk "
        "FOREIGN KEY (match_id) REFERENCES meta.entity_match(id)"
    )
    op.execute(
        """
        CREATE TABLE meta.entity_match_review (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            match_id bigint NOT NULL REFERENCES meta.entity_match(id) ON DELETE CASCADE,
            previous_decision text NOT NULL,
            reviewed_decision text NOT NULL,
            reviewer text NOT NULL,
            rationale text NOT NULL,
            reviewed_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT entity_match_review_previous CHECK (
                previous_decision IN ('certain', 'ambiguous', 'rejected')
            ),
            CONSTRAINT entity_match_review_decision CHECK (
                reviewed_decision IN ('certain', 'ambiguous', 'rejected')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.entity_match_metric (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            commune_code text NOT NULL,
            relation_type text NOT NULL,
            algorithm_code text NOT NULL,
            algorithm_version text NOT NULL,
            certain_count bigint NOT NULL DEFAULT 0 CHECK (certain_count >= 0),
            ambiguous_count bigint NOT NULL DEFAULT 0 CHECK (ambiguous_count >= 0),
            rejected_count bigint NOT NULL DEFAULT 0 CHECK (rejected_count >= 0),
            unmatched_count bigint NOT NULL DEFAULT 0 CHECK (unmatched_count >= 0),
            measured_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT entity_match_metric_identity UNIQUE (
                release_id, commune_code, relation_type, algorithm_code, algorithm_version
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE feature.feature_definition (
            code text NOT NULL,
            version integer NOT NULL CHECK (version > 0),
            name text NOT NULL,
            strategy text NOT NULL,
            datasets jsonb NOT NULL,
            formula text NOT NULL,
            transformation_version text NOT NULL,
            value_type text NOT NULL,
            unit text,
            valid_min numeric,
            valid_max numeric,
            out_of_range_policy text NOT NULL,
            requirement text NOT NULL,
            missing_value_policy text NOT NULL,
            description text NOT NULL,
            PRIMARY KEY (code, version),
            CONSTRAINT feature_definition_code CHECK (code ~ '^(LAND|BLD)-[0-9]{3}$'),
            CONSTRAINT feature_definition_value_type CHECK (
                value_type IN ('number', 'integer', 'boolean', 'text', 'json')
            ),
            CONSTRAINT feature_definition_range CHECK (
                valid_min IS NULL OR valid_max IS NULL OR valid_min <= valid_max
            ),
            CONSTRAINT feature_definition_out_of_range CHECK (
                out_of_range_policy IN ('reject', 'flag', 'clip')
            ),
            CONSTRAINT feature_definition_requirement CHECK (
                requirement IN ('required', 'optional', 'confidence_only')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE feature.feature_value (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            property_unit_id text REFERENCES reference.property_unit(id) ON DELETE CASCADE,
            building_id text REFERENCES reference.building(id) ON DELETE CASCADE,
            feature_code text NOT NULL,
            feature_version integer NOT NULL,
            numeric_value numeric,
            text_value text,
            json_value jsonb,
            missing_reason text,
            source_observation_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
            source_release_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
            formula text NOT NULL,
            transformation_version text NOT NULL,
            confidence numeric(6, 5),
            computed_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (feature_code, feature_version)
                REFERENCES feature.feature_definition(code, version),
            CONSTRAINT feature_value_identity UNIQUE NULLS NOT DISTINCT (
                property_unit_id, building_id, feature_code, feature_version
            ),
            CONSTRAINT feature_value_subject CHECK (
                num_nonnulls(property_unit_id, building_id) = 1
            ),
            CONSTRAINT feature_value_single_value CHECK (
                num_nonnulls(numeric_value, text_value, json_value, missing_reason) = 1
            ),
            CONSTRAINT feature_value_confidence CHECK (
                confidence IS NULL OR confidence BETWEEN 0 AND 1
            ),
            CONSTRAINT feature_value_missing_reason CHECK (
                missing_reason IS NULL OR missing_reason IN (
                    'source_not_accepted', 'source_value_missing', 'not_applicable',
                    'ambiguous_match', 'invalid_geometry', 'calculation_error'
                )
            )
        )
        """
    )

    for table in ("area", "address", "parcel", "building", "property_unit"):
        op.execute(f"CREATE INDEX {table}_geom_gist ON reference.{table} USING gist (geom)")
        op.execute(
            f"CREATE INDEX {table}_territory_idx "
            f"ON reference.{table} (department_code, commune_code)"
            if table != "area"
            else "CREATE INDEX area_territory_idx "
            "ON reference.area (department_code, area_type, code)"
        )
    op.execute(
        "CREATE INDEX address_label_trgm "
        "ON reference.address USING gin (normalized_label gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX entity_source_observation_geom_gist "
        "ON meta.entity_source_observation USING gist (geometry)"
    )
    op.execute(
        "CREATE INDEX entity_source_identifier_lookup_idx "
        "ON meta.entity_source_identifier (data_source_id, source_entity_type, source_identifier)"
    )
    op.execute(
        "CREATE INDEX entity_match_left_idx "
        "ON meta.entity_match (left_entity_type, left_entity_id, decision)"
    )
    op.execute(
        "CREATE INDEX entity_match_right_idx "
        "ON meta.entity_match (right_entity_type, right_entity_id, decision)"
    )
    op.execute(
        "CREATE INDEX entity_match_blocking_idx ON meta.entity_match (blocks_publication) "
        "WHERE blocks_publication"
    )

    op.execute(
        """
        CREATE FUNCTION reference.refresh_cadastre_spatial_reference(p_department_code text)
        RETURNS TABLE(area_count bigint, parcel_count bigint, property_unit_count bigint)
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            INSERT INTO reference.area (
                id, area_type, code, name, department_code, geom
            )
            SELECT 'area:commune:' || source.code, 'commune', source.code,
                   source.name, source.department_code, source.geom
              FROM reference.administrative_area AS source
              JOIN meta.active_dataset_release AS active
                ON active.data_source_id = 'DS-01'
               AND active.scope_type = 'department'
               AND active.scope_code = source.department_code
               AND active.release_id = source.release_id
             WHERE source.department_code = p_department_code
               AND source.area_type = 'commune'
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                geom = EXCLUDED.geom,
                updated_at = clock_timestamp();

            INSERT INTO reference.parcel (
                id, cadastral_id, commune_code, department_code, geom
            )
            SELECT 'parcel:cadastre:' || cadastral_id, cadastral_id,
                   commune_code, department_code, geom
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT (id) DO UPDATE SET
                commune_code = EXCLUDED.commune_code,
                department_code = EXCLUDED.department_code,
                geom = EXCLUDED.geom,
                updated_at = clock_timestamp();

            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT 'parcel', 'parcel:cadastre:' || cadastral_id, 'DS-01', 'cadastral_parcel',
                   cadastral_id, release_id, release_id, true
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT (entity_type, entity_id, data_source_id, source_entity_type, source_identifier)
            DO UPDATE SET last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp();

            INSERT INTO reference.property_unit (
                id, stable_key, unit_type, commune_code, department_code,
                publication_eligible, exclusion_reason, geom
            )
            SELECT 'property-unit:parcel:' || cadastral_id,
                   'cadastre:' || cadastral_id, 'single_parcel',
                   commune_code, department_code, false,
                   'entity_resolution_incomplete', geom
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT (id) DO UPDATE SET
                commune_code = EXCLUDED.commune_code,
                department_code = EXCLUDED.department_code,
                geom = EXCLUDED.geom,
                updated_at = clock_timestamp();

            INSERT INTO reference.property_unit_member (
                property_unit_id, entity_type, entity_id, member_role
            )
            SELECT 'property-unit:parcel:' || cadastral_id, 'parcel',
                   'parcel:cadastre:' || cadastral_id, 'primary'
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT DO NOTHING;

            RETURN QUERY
            SELECT
                (SELECT count(*) FROM reference.area WHERE department_code = p_department_code),
                (SELECT count(*) FROM reference.parcel WHERE department_code = p_department_code),
                (SELECT count(*) FROM reference.property_unit
                  WHERE department_code = p_department_code);
        END
        $function$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION reference.refresh_cadastre_spatial_reference(text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION reference.refresh_cadastre_spatial_reference(text) TO pipeline_rw"
    )

    op.execute(
        """
        INSERT INTO meta.data_source (
            id, name, producer, homepage_url, licence_spdx,
            licence_name, attribution, usage_notes
        ) VALUES
            ('DS-02', 'Référentiel National des Bâtiments',
             'État / RNB', 'https://rnb.beta.gouv.fr/', 'etalab-2.0',
             'Licence Ouverte 2.0', 'Référentiel National des Bâtiments (RNB)',
             'Identifiant bâtiment pérenne privilégié; conserver tout historique d''identité.'),
            ('DS-03', 'Base de Données Nationale des Bâtiments Open',
             'CSTB', 'https://bdnb.io/', 'etalab-2.0',
             'Licence Ouverte 2.0', 'BDNB, millésime et sources originelles à citer',
             'Ne jamais assimiler automatiquement un groupe BDNB à un bâtiment physique; exclure les prédictions Expert.'),
            ('DS-04', 'BD TOPO thème Bâti et réseau routier',
             'IGN', 'https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-TOPO',
             'etalab-2.0', 'Licence Ouverte 2.0', 'IGN, BD TOPO',
             'Les géométries et attributs observés restent distincts des identités RNB et cadastrales.'),
            ('DS-05', 'Base Adresse Nationale',
             'DINUM / IGN / ANCT', 'https://adresse.data.gouv.fr/', 'etalab-2.0',
             'Licence Ouverte 2.0', 'Base Adresse Nationale',
             'Les liens cad_parcelles sont expérimentaux et doivent conserver leur confiance.')
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP FUNCTION IF EXISTS reference.refresh_cadastre_spatial_reference(text)")
    for table in reversed(FEATURE_TABLES):
        op.execute(f"DROP TABLE IF EXISTS feature.{table}")
    for table in reversed(MATCH_TABLES):
        op.execute(f"DROP TABLE IF EXISTS meta.{table}")
    for table in reversed(REFERENCE_TABLES):
        op.execute(f"DROP TABLE IF EXISTS reference.{table}")
    op.execute("DELETE FROM meta.data_source WHERE id IN ('DS-02', 'DS-03', 'DS-04', 'DS-05')")
    op.execute("RESET ROLE")
