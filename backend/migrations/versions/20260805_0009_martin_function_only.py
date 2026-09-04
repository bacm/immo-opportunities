"""Restrict Martin to explicit versioned MVT functions.

Revision ID: 20260805_0009
Revises: 20260805_0008
Create Date: 2026-08-05 18:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260805_0009"
down_revision: str | None = "20260805_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA tiles "
        "REVOKE SELECT ON TABLES FROM tiles_ro"
    )
    for relation in (
        "tiles.cadastral_parcels",
        "tiles.cadastral_buildings",
        "tiles.parcel_render_v1",
        "tiles.building_render_v1",
    ):
        op.execute(f"REVOKE ALL ON {relation} FROM tiles_ro")
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA tiles "
        "GRANT SELECT ON TABLES TO tiles_ro"
    )
    for relation in (
        "tiles.cadastral_parcels",
        "tiles.cadastral_buildings",
        "tiles.parcel_render_v1",
        "tiles.building_render_v1",
    ):
        op.execute(f"GRANT SELECT ON {relation} TO tiles_ro")
    op.execute("RESET ROLE")
