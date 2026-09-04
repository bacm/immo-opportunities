"""Add versioned render geometries and least-privilege MVT functions.

Revision ID: 20260805_0008
Revises: 20260805_0007
Create Date: 2026-08-05 17:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260805_0008"
down_revision: str | None = "20260805_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    # Rendering geometries deliberately live outside the analytical reference model.
    # They can be rebuilt after a publication without mutating the source geometry.
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE tiles.parcel_render_v1 (
            id text PRIMARY KEY,
            cadastral_id text NOT NULL UNIQUE,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            geom geometry(MultiPolygon, 3857) NOT NULL,
            geom_generalized geometry(MultiPolygon, 3857) NOT NULL,
            rendered_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT parcel_render_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT parcel_render_generalized_valid CHECK (ST_IsValid(geom_generalized))
        )
        """
    )
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE tiles.building_render_v1 (
            id text PRIMARY KEY,
            source_feature_id text NOT NULL,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            geom geometry(MultiPolygon, 3857) NOT NULL,
            geom_generalized geometry(MultiPolygon, 3857) NOT NULL,
            rendered_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT building_render_geom_valid CHECK (ST_IsValid(geom)),
            CONSTRAINT building_render_generalized_valid CHECK (ST_IsValid(geom_generalized))
        )
        """
    )
    for table in ("parcel_render_v1", "building_render_v1"):
        op.execute(f"CREATE INDEX {table}_geom_gist ON tiles.{table} USING gist (geom)")
        op.execute(
            f"CREATE INDEX {table}_generalized_gist ON tiles.{table} USING gist (geom_generalized)"
        )
        op.execute(
            f"CREATE INDEX {table}_territory_idx ON tiles.{table} (department_code, commune_code)"
        )

    op.execute(
        """
        CREATE FUNCTION tiles.refresh_render_v1(p_department_code text)
        RETURNS TABLE(parcel_count bigint, building_count bigint)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, tiles, reference
        AS $function$
        BEGIN
            DELETE FROM tiles.parcel_render_v1
             WHERE department_code = p_department_code;

            INSERT INTO tiles.parcel_render_v1 (
                id, cadastral_id, commune_code, department_code,
                geom, geom_generalized
            )
            SELECT 'parcel:cadastre:' || source.cadastral_id,
                   source.cadastral_id,
                   source.commune_code,
                   source.department_code,
                   ST_Transform(ST_Force2D(source.geom), 3857)::geometry(MultiPolygon, 3857),
                   ST_SimplifyPreserveTopology(
                       ST_Transform(ST_Force2D(source.geom), 3857), 1.5
                   )::geometry(MultiPolygon, 3857)
              FROM reference.active_cadastral_parcel AS source
             WHERE source.department_code = p_department_code;

            DELETE FROM tiles.building_render_v1
             WHERE department_code = p_department_code;

            INSERT INTO tiles.building_render_v1 (
                id, source_feature_id, commune_code, department_code,
                geom, geom_generalized
            )
            SELECT 'building:cadastre:' || source.source_feature_id,
                   source.source_feature_id,
                   source.commune_code,
                   source.department_code,
                   ST_Transform(ST_Force2D(source.geom), 3857)::geometry(MultiPolygon, 3857),
                   ST_SimplifyPreserveTopology(
                       ST_Transform(ST_Force2D(source.geom), 3857), 0.75
                   )::geometry(MultiPolygon, 3857)
              FROM reference.active_cadastral_building AS source
             WHERE source.department_code = p_department_code;

            ANALYZE tiles.parcel_render_v1;
            ANALYZE tiles.building_render_v1;

            RETURN QUERY
            SELECT
                (SELECT count(*) FROM tiles.parcel_render_v1
                  WHERE department_code = p_department_code),
                (SELECT count(*) FROM tiles.building_render_v1
                  WHERE department_code = p_department_code);
        END
        $function$
        """
    )

    op.execute(
        """
        CREATE FUNCTION tiles.parcels(z integer, x integer, y integer)
        RETURNS bytea
        LANGUAGE sql
        STABLE
        PARALLEL SAFE
        SECURITY DEFINER
        SET search_path = pg_catalog, public, tiles
        AS $function$
            SELECT COALESCE(ST_AsMVT(tile, 'parcels', 4096, 'geom'), ''::bytea)
              FROM (
                    SELECT source.id,
                           source.cadastral_id,
                           source.commune_code,
                           ST_AsMVTGeom(
                               CASE WHEN z < 16 THEN source.geom_generalized ELSE source.geom END,
                               ST_TileEnvelope(z, x, y),
                               4096,
                               64,
                               true
                           ) AS geom
                      FROM tiles.parcel_render_v1 AS source
                     WHERE z BETWEEN 13 AND 22
                       AND (CASE WHEN z < 16 THEN source.geom_generalized ELSE source.geom END)
                           && ST_TileEnvelope(z, x, y)
                   ) AS tile
             WHERE tile.geom IS NOT NULL
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION tiles.buildings(z integer, x integer, y integer)
        RETURNS bytea
        LANGUAGE sql
        STABLE
        PARALLEL SAFE
        SECURITY DEFINER
        SET search_path = pg_catalog, public, tiles
        AS $function$
            SELECT COALESCE(ST_AsMVT(tile, 'buildings', 4096, 'geom'), ''::bytea)
              FROM (
                    SELECT source.id,
                           source.commune_code,
                           ST_AsMVTGeom(
                               CASE WHEN z < 17 THEN source.geom_generalized ELSE source.geom END,
                               ST_TileEnvelope(z, x, y),
                               4096,
                               64,
                               true
                           ) AS geom
                      FROM tiles.building_render_v1 AS source
                     WHERE z BETWEEN 15 AND 22
                       AND (CASE WHEN z < 17 THEN source.geom_generalized ELSE source.geom END)
                           && ST_TileEnvelope(z, x, y)
                   ) AS tile
             WHERE tile.geom IS NOT NULL
        $function$
        """
    )

    # Functions are executable by PUBLIC unless explicitly revoked.
    for function in ("parcels(integer, integer, integer)", "buildings(integer, integer, integer)"):
        op.execute(f"REVOKE ALL ON FUNCTION tiles.{function} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION tiles.{function} TO tiles_ro")
    op.execute("REVOKE ALL ON FUNCTION tiles.refresh_render_v1(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION tiles.refresh_render_v1(text) TO pipeline_rw")
    op.get_bind().exec_driver_sql(
        """
        COMMENT ON FUNCTION tiles.parcels(integer, integer, integer) IS
        '{"description":"Parcelles cadastrales actives v1",'
        '"minzoom":13,"maxzoom":22,"attribution":"Etalab · DGFiP"}'
        """
    )
    op.get_bind().exec_driver_sql(
        """
        COMMENT ON FUNCTION tiles.buildings(integer, integer, integer) IS
        '{"description":"Bâtiments cadastraux actifs v1",'
        '"minzoom":15,"maxzoom":22,"attribution":"Etalab · DGFiP"}'
        """
    )

    # Seed render storage for every accepted cadastral department already present.
    op.execute(
        """
        DO $block$
        DECLARE department text;
        BEGIN
            FOR department IN
                SELECT scope_code
                  FROM meta.active_dataset_release
                 WHERE data_source_id = 'DS-01' AND scope_type = 'department'
            LOOP
                PERFORM tiles.refresh_render_v1(department);
            END LOOP;
        END
        $block$
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP FUNCTION IF EXISTS tiles.buildings(integer, integer, integer)")
    op.execute("DROP FUNCTION IF EXISTS tiles.parcels(integer, integer, integer)")
    op.execute("DROP FUNCTION IF EXISTS tiles.refresh_render_v1(text)")
    op.execute("DROP TABLE IF EXISTS tiles.building_render_v1")
    op.execute("DROP TABLE IF EXISTS tiles.parcel_render_v1")
    op.execute("RESET ROLE")
