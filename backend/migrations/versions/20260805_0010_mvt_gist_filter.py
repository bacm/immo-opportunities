"""Make MVT functions use the render geometry GiST indexes.

Revision ID: 20260805_0010
Revises: 20260805_0009
Create Date: 2026-08-05 19:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260805_0010"
down_revision: str | None = "20260805_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PARCEL_FUNCTION = """
    CREATE OR REPLACE FUNCTION tiles.parcels(z integer, x integer, y integer)
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
                           ST_TileEnvelope(z, x, y), 4096, 64, true
                       ) AS geom
                  FROM tiles.parcel_render_v1 AS source
                 WHERE z BETWEEN 13 AND 22
                   AND source.geom && ST_TileEnvelope(z, x, y)
               ) AS tile
         WHERE tile.geom IS NOT NULL
    $function$
"""

BUILDING_FUNCTION = """
    CREATE OR REPLACE FUNCTION tiles.buildings(z integer, x integer, y integer)
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
                           ST_TileEnvelope(z, x, y), 4096, 64, true
                       ) AS geom
                  FROM tiles.building_render_v1 AS source
                 WHERE z BETWEEN 15 AND 22
                   AND source.geom && ST_TileEnvelope(z, x, y)
               ) AS tile
         WHERE tile.geom IS NOT NULL
    $function$
"""


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(PARCEL_FUNCTION)
    op.execute(BUILDING_FUNCTION)
    op.execute("RESET ROLE")


def downgrade() -> None:
    # Both render geometries have equivalent envelopes for supported data. The
    # indexed predicate is therefore also valid for the previous output contract.
    upgrade()
