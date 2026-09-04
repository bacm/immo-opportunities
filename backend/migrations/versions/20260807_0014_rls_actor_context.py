"""Remove recursive identity RLS and snapshot private event author names.

Revision ID: 20260807_0014
Revises: 20260807_0013
Create Date: 2026-08-07 17:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_0014"
down_revision: str | None = "20260807_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP POLICY organization_membership_self ON app.organization_membership")
    op.execute("DROP POLICY app_user_same_organization ON app.app_user")
    op.execute(
        "CREATE POLICY organization_membership_current_user "
        "ON app.organization_membership USING (user_id = "
        "nullif(current_setting('app.current_user_id', true), ''))"
    )
    for table in ("candidate_status_history", "note", "candidate_review"):
        op.execute(
            f"ALTER TABLE app.{table} ADD COLUMN author_name text NOT NULL DEFAULT 'Utilisateur'"
        )
        op.execute(f"ALTER TABLE app.{table} ALTER COLUMN author_name DROP DEFAULT")
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    for table in ("candidate_review", "note", "candidate_status_history"):
        op.execute(f"ALTER TABLE app.{table} DROP COLUMN author_name")
    op.execute("DROP POLICY organization_membership_current_user ON app.organization_membership")
    op.execute(
        "CREATE POLICY organization_membership_self ON app.organization_membership "
        "USING (user_id IN (SELECT id FROM app.app_user WHERE external_subject = "
        "nullif(current_setting('app.current_subject', true), '')))"
    )
    op.execute(
        "CREATE POLICY app_user_same_organization ON app.app_user USING (EXISTS ("
        "SELECT 1 FROM app.organization_membership AS membership "
        "WHERE membership.user_id = app_user.id AND membership.organization_id = "
        "nullif(current_setting('app.current_organization_id', true), '')))"
    )
    op.execute("RESET ROLE")
