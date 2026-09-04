"""Give `display_only` a technical consequence instead of a documentary one.

`publication_mode` was persisted on meta.active_dataset_release without a single
consumer reading it: every join treated `display_only` exactly like `accepted`, so the
status was a label with no effect. A release accepted for display may feed address
search and the map, but must never found a feature entering a score.

This view names that boundary once, where all release filtering already happens.
Display consumers keep joining meta.active_dataset_release; anything computing a
feature joins meta.analysis_dataset_release instead.

Revision ID: 20260904_0017
Revises: 20260904_0016
Create Date: 2026-09-04 12:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260904_0017"
down_revision: str | None = "20260904_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE VIEW meta.analysis_dataset_release AS
        SELECT data_source_id, scope_type, scope_code, release_id,
               publication_mode, published_at, published_by
          FROM meta.active_dataset_release
         WHERE publication_mode = 'accepted'
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP VIEW meta.analysis_dataset_release")
    op.execute("RESET ROLE")
