"""Add the extensible dataset catalog and versioned cadastral reference data.

Revision ID: 20260804_0002
Revises: 20260804_0001
Create Date: 2026-08-04 14:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_0002"
down_revision: str | None = "20260804_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATASET_TABLES = (
    "data_source",
    "dataset_release",
    "raw_asset",
    "import_run",
    "transformation_run",
    "data_quality_check",
    "geometry_quarantine",
    "active_dataset_release",
    "publication_event",
)

REFERENCE_TABLES = (
    "administrative_area",
    "cadastral_parcel",
    "cadastral_building",
)


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    op.execute(
        """
        CREATE TABLE meta.data_source (
            id text PRIMARY KEY,
            name text NOT NULL,
            producer text NOT NULL,
            homepage_url text NOT NULL,
            licence_spdx text,
            licence_name text NOT NULL,
            attribution text NOT NULL,
            usage_notes text NOT NULL DEFAULT '',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT data_source_id_format CHECK (id ~ '^DS-[0-9]{2}$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.dataset_release (
            id text PRIMARY KEY,
            data_source_id text NOT NULL REFERENCES meta.data_source(id),
            release_key text NOT NULL,
            contract_version integer NOT NULL CHECK (contract_version > 0),
            source_published_on date,
            discovered_at timestamptz NOT NULL DEFAULT now(),
            lifecycle_status text NOT NULL DEFAULT 'discovered',
            acceptance_status text NOT NULL DEFAULT 'pending',
            source_srid integer NOT NULL,
            canonical_srid integer NOT NULL DEFAULT 2154,
            coverage jsonb NOT NULL DEFAULT '{}'::jsonb,
            schema_fingerprint text,
            previous_release_id text REFERENCES meta.dataset_release(id),
            notes text NOT NULL DEFAULT '',
            CONSTRAINT dataset_release_identity UNIQUE (data_source_id, release_key),
            CONSTRAINT dataset_release_source_identity UNIQUE (data_source_id, id),
            CONSTRAINT dataset_release_lifecycle CHECK (
                lifecycle_status IN ('discovered', 'downloading', 'staged', 'validated', 'retired')
            ),
            CONSTRAINT dataset_release_acceptance CHECK (
                acceptance_status IN ('pending', 'accepted', 'display_only', 'rejected')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.raw_asset (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            layer text NOT NULL,
            territory_type text NOT NULL,
            territory_code text NOT NULL,
            source_url text NOT NULL,
            object_key text NOT NULL UNIQUE,
            media_type text NOT NULL,
            content_encoding text,
            byte_size bigint NOT NULL CHECK (byte_size >= 0),
            sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            etag text,
            downloaded_at timestamptz NOT NULL DEFAULT now(),
            source_last_modified timestamptz,
            immutable boolean NOT NULL DEFAULT true CHECK (immutable),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT raw_asset_natural_key UNIQUE (
                release_id, layer, territory_type, territory_code, sha256
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.import_run (
            id text PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            territory_type text NOT NULL,
            territory_code text NOT NULL,
            idempotency_key text NOT NULL UNIQUE,
            status text NOT NULL DEFAULT 'running',
            started_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz,
            source_row_count bigint NOT NULL DEFAULT 0,
            normalized_row_count bigint NOT NULL DEFAULT 0,
            quarantined_row_count bigint NOT NULL DEFAULT 0,
            error_message text,
            runner_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT import_run_status CHECK (
                status IN ('running', 'succeeded', 'failed', 'rolled_back')
            ),
            CONSTRAINT import_run_counts CHECK (
                source_row_count >= 0 AND normalized_row_count >= 0
                AND quarantined_row_count >= 0
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.transformation_run (
            id text PRIMARY KEY,
            import_run_id text NOT NULL REFERENCES meta.import_run(id) ON DELETE CASCADE,
            transformation_code text NOT NULL,
            transformation_version text NOT NULL,
            parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
            input_row_count bigint NOT NULL DEFAULT 0 CHECK (input_row_count >= 0),
            output_row_count bigint NOT NULL DEFAULT 0 CHECK (output_row_count >= 0),
            repaired_row_count bigint NOT NULL DEFAULT 0 CHECK (repaired_row_count >= 0),
            started_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz,
            status text NOT NULL DEFAULT 'running',
            CONSTRAINT transformation_run_status CHECK (
                status IN ('running', 'succeeded', 'failed')
            ),
            CONSTRAINT transformation_run_identity UNIQUE (
                import_run_id, transformation_code, transformation_version
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.data_quality_check (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            import_run_id text REFERENCES meta.import_run(id) ON DELETE CASCADE,
            check_code text NOT NULL,
            check_version text NOT NULL,
            scope_type text NOT NULL,
            scope_code text NOT NULL,
            layer text,
            status text NOT NULL,
            severity text NOT NULL,
            blocks_publication boolean NOT NULL DEFAULT false,
            observed_value numeric,
            expected_value numeric,
            details jsonb NOT NULL DEFAULT '{}'::jsonb,
            checked_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT data_quality_status CHECK (status IN ('passed', 'warning', 'failed')),
            CONSTRAINT data_quality_severity CHECK (severity IN ('info', 'warning', 'error')),
            CONSTRAINT data_quality_result_identity UNIQUE NULLS NOT DISTINCT (
                release_id, import_run_id, check_code, check_version,
                scope_type, scope_code, layer
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.geometry_quarantine (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            import_run_id text NOT NULL REFERENCES meta.import_run(id) ON DELETE CASCADE,
            raw_asset_id bigint NOT NULL REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            layer text NOT NULL,
            source_feature_id text,
            source_row_number bigint NOT NULL CHECK (source_row_number > 0),
            reason_code text NOT NULL,
            reason_detail text NOT NULL,
            source_geometry jsonb,
            source_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            repair_attempted boolean NOT NULL DEFAULT false,
            transformation_version text NOT NULL,
            quarantined_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT geometry_quarantine_source UNIQUE (
                release_id, raw_asset_id, layer, source_row_number
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.active_dataset_release (
            data_source_id text NOT NULL REFERENCES meta.data_source(id),
            scope_type text NOT NULL,
            scope_code text NOT NULL,
            release_id text NOT NULL,
            publication_mode text NOT NULL,
            published_at timestamptz NOT NULL DEFAULT now(),
            published_by text NOT NULL,
            PRIMARY KEY (data_source_id, scope_type, scope_code),
            CONSTRAINT active_release_matches_source FOREIGN KEY (data_source_id, release_id)
                REFERENCES meta.dataset_release(data_source_id, id),
            CONSTRAINT active_release_mode CHECK (
                publication_mode IN ('accepted', 'display_only')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.publication_event (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            data_source_id text NOT NULL REFERENCES meta.data_source(id),
            scope_type text NOT NULL,
            scope_code text NOT NULL,
            release_id text NOT NULL REFERENCES meta.dataset_release(id),
            replaced_release_id text REFERENCES meta.dataset_release(id),
            action text NOT NULL,
            publication_mode text NOT NULL,
            actor text NOT NULL,
            reason text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT publication_event_action CHECK (action IN ('publish', 'rollback')),
            CONSTRAINT publication_event_mode CHECK (
                publication_mode IN ('accepted', 'display_only')
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE reference.administrative_area (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            raw_asset_id bigint NOT NULL REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            import_run_id text NOT NULL REFERENCES meta.import_run(id) ON DELETE CASCADE,
            source_feature_id text NOT NULL,
            source_row_number bigint NOT NULL CHECK (source_row_number > 0),
            area_type text NOT NULL,
            code text NOT NULL,
            name text,
            department_code text NOT NULL,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            record_checksum char(64) NOT NULL CHECK (record_checksum ~ '^[0-9a-f]{64}$'),
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT administrative_area_source UNIQUE (
                release_id, area_type, code, source_feature_id
            ),
            CONSTRAINT administrative_area_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT administrative_area_geom_nonempty CHECK (NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.cadastral_parcel (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            raw_asset_id bigint NOT NULL REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            import_run_id text NOT NULL REFERENCES meta.import_run(id) ON DELETE CASCADE,
            source_feature_id text NOT NULL,
            source_row_number bigint NOT NULL CHECK (source_row_number > 0),
            cadastral_id text NOT NULL,
            department_code text NOT NULL,
            commune_code text NOT NULL,
            prefix text NOT NULL DEFAULT '000',
            section text NOT NULL,
            number text NOT NULL,
            stated_area_m2 integer CHECK (stated_area_m2 IS NULL OR stated_area_m2 >= 0),
            surveyed boolean,
            source_created_on date,
            source_updated_on date,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            was_repaired boolean NOT NULL DEFAULT false,
            repair_method text,
            transformation_version text NOT NULL,
            record_checksum char(64) NOT NULL CHECK (record_checksum ~ '^[0-9a-f]{64}$'),
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT cadastral_parcel_identity UNIQUE (release_id, cadastral_id),
            CONSTRAINT cadastral_parcel_source UNIQUE (
                release_id, raw_asset_id, source_row_number
            ),
            CONSTRAINT cadastral_parcel_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT cadastral_parcel_geom_nonempty CHECK (NOT ST_IsEmpty(geom)),
            CONSTRAINT cadastral_parcel_repair_trace CHECK (
                (was_repaired AND repair_method IS NOT NULL)
                OR (NOT was_repaired AND repair_method IS NULL)
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.cadastral_building (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            raw_asset_id bigint NOT NULL REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            import_run_id text NOT NULL REFERENCES meta.import_run(id) ON DELETE CASCADE,
            source_feature_id text NOT NULL,
            source_row_number bigint NOT NULL CHECK (source_row_number > 0),
            department_code text NOT NULL,
            commune_code text NOT NULL,
            cadastral_type text,
            cadastral_name text,
            source_created_on date,
            source_updated_on date,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            was_repaired boolean NOT NULL DEFAULT false,
            repair_method text,
            transformation_version text NOT NULL,
            record_checksum char(64) NOT NULL CHECK (record_checksum ~ '^[0-9a-f]{64}$'),
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT cadastral_building_identity UNIQUE (release_id, source_feature_id),
            CONSTRAINT cadastral_building_source UNIQUE (
                release_id, raw_asset_id, source_row_number
            ),
            CONSTRAINT cadastral_building_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT cadastral_building_geom_nonempty CHECK (NOT ST_IsEmpty(geom)),
            CONSTRAINT cadastral_building_repair_trace CHECK (
                (was_repaired AND repair_method IS NOT NULL)
                OR (NOT was_repaired AND repair_method IS NULL)
            )
        )
        """
    )

    for table in REFERENCE_TABLES:
        op.execute(f"CREATE INDEX {table}_geom_gist ON reference.{table} USING gist (geom)")
        op.execute(
            f"CREATE INDEX {table}_release_department_idx "
            f"ON reference.{table} (release_id, department_code)"
        )
    op.execute(
        "CREATE INDEX cadastral_parcel_commune_idx "
        "ON reference.cadastral_parcel (release_id, commune_code, section, number)"
    )
    op.execute(
        "CREATE INDEX cadastral_building_commune_idx "
        "ON reference.cadastral_building (release_id, commune_code)"
    )
    op.execute(
        "CREATE INDEX data_quality_scope_idx "
        "ON meta.data_quality_check (release_id, scope_type, scope_code, check_code)"
    )
    op.execute("CREATE INDEX raw_asset_release_idx ON meta.raw_asset (release_id, layer)")

    op.execute(
        """
        CREATE VIEW reference.active_cadastral_parcel AS
        SELECT parcel.*
        FROM reference.cadastral_parcel AS parcel
        JOIN meta.active_dataset_release AS active
          ON active.data_source_id = 'DS-01'
         AND active.scope_type = 'department'
         AND active.scope_code = parcel.department_code
         AND active.release_id = parcel.release_id
        """
    )
    op.execute(
        """
        CREATE VIEW reference.active_cadastral_building AS
        SELECT building.*
        FROM reference.cadastral_building AS building
        JOIN meta.active_dataset_release AS active
          ON active.data_source_id = 'DS-01'
         AND active.scope_type = 'department'
         AND active.scope_code = building.department_code
         AND active.release_id = building.release_id
        """
    )
    op.execute(
        """
        CREATE VIEW tiles.cadastral_parcels AS
        SELECT id, cadastral_id, commune_code, section, number,
               ST_Transform(geom, 3857)::geometry(MultiPolygon, 3857) AS geom
        FROM reference.active_cadastral_parcel
        """
    )
    op.execute(
        """
        CREATE VIEW tiles.cadastral_buildings AS
        SELECT id, source_feature_id, commune_code, cadastral_type,
               ST_Transform(geom, 3857)::geometry(MultiPolygon, 3857) AS geom
        FROM reference.active_cadastral_building
        """
    )

    op.execute(
        """
        CREATE FUNCTION meta.publish_dataset_release(
            p_data_source_id text,
            p_release_id text,
            p_scope_type text,
            p_scope_code text,
            p_actor text,
            p_reason text,
            p_action text DEFAULT 'publish'
        ) RETURNS void
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            release_acceptance text;
            replaced_release text;
        BEGIN
            IF p_action NOT IN ('publish', 'rollback') THEN
                RAISE EXCEPTION 'Unsupported publication action: %', p_action;
            END IF;

            SELECT acceptance_status INTO STRICT release_acceptance
              FROM meta.dataset_release
             WHERE id = p_release_id AND data_source_id = p_data_source_id
             FOR UPDATE;

            IF release_acceptance NOT IN ('accepted', 'display_only') THEN
                RAISE EXCEPTION 'Release % is not publishable: %', p_release_id, release_acceptance;
            END IF;

            IF EXISTS (
                SELECT 1 FROM meta.data_quality_check
                 WHERE release_id = p_release_id
                   AND scope_type = p_scope_type
                   AND scope_code = p_scope_code
                   AND blocks_publication
                   AND status = 'failed'
            ) THEN
                RAISE EXCEPTION 'Release % has blocking quality failures', p_release_id;
            END IF;

            SELECT release_id INTO replaced_release
              FROM meta.active_dataset_release
             WHERE data_source_id = p_data_source_id
               AND scope_type = p_scope_type
               AND scope_code = p_scope_code
             FOR UPDATE;

            INSERT INTO meta.active_dataset_release (
                data_source_id, scope_type, scope_code, release_id,
                publication_mode, published_at, published_by
            ) VALUES (
                p_data_source_id, p_scope_type, p_scope_code, p_release_id,
                release_acceptance, now(), p_actor
            )
            ON CONFLICT (data_source_id, scope_type, scope_code) DO UPDATE SET
                release_id = EXCLUDED.release_id,
                publication_mode = EXCLUDED.publication_mode,
                published_at = EXCLUDED.published_at,
                published_by = EXCLUDED.published_by;

            INSERT INTO meta.publication_event (
                data_source_id, scope_type, scope_code, release_id,
                replaced_release_id, action, publication_mode, actor, reason
            ) VALUES (
                p_data_source_id, p_scope_type, p_scope_code, p_release_id,
                replaced_release, p_action, release_acceptance, p_actor, p_reason
            );
        END
        $function$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION meta.publish_dataset_release(text,text,text,text,text,text,text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION meta.publish_dataset_release(text,text,text,text,text,text,text) TO pipeline_rw"
    )

    op.execute(
        """
        CREATE FUNCTION meta.rollback_unpublished_dataset_release(
            p_release_id text,
            p_actor text,
            p_reason text
        ) RETURNS void
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF EXISTS (SELECT 1 FROM meta.active_dataset_release WHERE release_id = p_release_id)
               OR EXISTS (SELECT 1 FROM meta.publication_event WHERE release_id = p_release_id) THEN
                RAISE EXCEPTION 'Release % has publication history and cannot be purged', p_release_id;
            END IF;

            DELETE FROM reference.cadastral_parcel WHERE release_id = p_release_id;
            DELETE FROM reference.cadastral_building WHERE release_id = p_release_id;
            DELETE FROM reference.administrative_area WHERE release_id = p_release_id;
            DELETE FROM meta.data_quality_check WHERE release_id = p_release_id;
            DELETE FROM meta.import_run WHERE release_id = p_release_id;
            UPDATE meta.dataset_release
               SET lifecycle_status = 'retired', acceptance_status = 'pending',
                   notes = concat_ws(E'\n', nullif(notes, ''),
                       format('Rolled back by %s: %s', p_actor, p_reason))
             WHERE id = p_release_id;
        END
        $function$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION meta.rollback_unpublished_dataset_release(text,text,text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION meta.rollback_unpublished_dataset_release(text,text,text) TO pipeline_rw"
    )

    op.execute(
        """
        INSERT INTO meta.data_source (
            id, name, producer, homepage_url, licence_spdx,
            licence_name, attribution, usage_notes
        ) VALUES (
            'DS-01',
            'Cadastre Etalab consolidé issu du PCI Vecteur',
            'DGFiP / Etalab (DINUM)',
            'https://cadastre.data.gouv.fr/datasets/cadastre-etalab',
            'etalab-2.0',
            'Licence Ouverte 2.0',
            'Données cadastrales Etalab, issues du PCI Vecteur DGFiP',
            'Plan fiscal : les emprises bâties ne constituent pas un référentiel de bâtiments physiques.'
        )
        """
    )

    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP FUNCTION IF EXISTS meta.rollback_unpublished_dataset_release(text,text,text)")
    op.execute(
        "DROP FUNCTION IF EXISTS meta.publish_dataset_release(text,text,text,text,text,text,text)"
    )
    op.execute("DROP VIEW IF EXISTS tiles.cadastral_buildings")
    op.execute("DROP VIEW IF EXISTS tiles.cadastral_parcels")
    op.execute("DROP VIEW IF EXISTS reference.active_cadastral_building")
    op.execute("DROP VIEW IF EXISTS reference.active_cadastral_parcel")
    for table in reversed(REFERENCE_TABLES):
        op.execute(f"DROP TABLE IF EXISTS reference.{table}")
    for table in reversed(DATASET_TABLES):
        op.execute(f"DROP TABLE IF EXISTS meta.{table}")
    op.execute("RESET ROLE")
