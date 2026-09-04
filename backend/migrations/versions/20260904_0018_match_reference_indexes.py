"""Index the foreign keys that point at meta.entity_match.

Three foreign keys reference meta.entity_match without an index:
`reference.property_unit_member.match_id`, `reference.building_parcel.match_id`, and
meta.entity_match's own `supersedes_match_id`. PostgreSQL checks a NO ACTION foreign key
by looking for referencing rows, so deleting matches costs one sequential scan of the
referencing table per deleted row. Retiring the 325 934 BAN address/parcel relations of
a single department did not finish in ten minutes — twice, the self-reference being the
decisive one since it scans the very table being emptied.

Any release rollback deletes matches, so an unindexed reference here makes rollback
impracticable at departmental scale — the operation v0.8 expects to demonstrate.

Revision ID: 20260904_0018
Revises: 20260904_0017
Create Date: 2026-09-04 14:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260904_0018"
down_revision: str | None = "20260904_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "CREATE INDEX property_unit_member_match_idx "
        "ON reference.property_unit_member (match_id) WHERE match_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX building_parcel_match_idx "
        "ON reference.building_parcel (match_id) WHERE match_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX entity_match_supersedes_idx "
        "ON meta.entity_match (supersedes_match_id) WHERE supersedes_match_id IS NOT NULL"
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP INDEX IF EXISTS meta.entity_match_supersedes_idx")
    op.execute("DROP INDEX IF EXISTS reference.building_parcel_match_idx")
    op.execute("DROP INDEX IF EXISTS reference.property_unit_member_match_idx")
    op.execute("RESET ROLE")
