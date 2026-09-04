"""Introduce attribute-level quarantine and allow addresses without a position.

An import can only classify a source row as valid or quarantined. Many real anomalies
sit between the two: the record is sound while a single attribute is unusable. Without a
third state, an import has to choose between discarding certain information and
publishing doubtful information — both forbidden by the missing-value rule.

Revision ID: 20260904_0016
Revises: 20260810_0015
Create Date: 2026-09-04 10:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260904_0016"
down_revision: str | None = "20260810_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    op.execute(
        """
        CREATE TABLE meta.attribute_quarantine (
            id bigserial PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            import_run_id text NOT NULL REFERENCES meta.import_run(id) ON DELETE CASCADE,
            entity_type text NOT NULL,
            entity_id text NOT NULL,
            attribute text NOT NULL,
            reason_code text NOT NULL,
            reason_detail text NOT NULL DEFAULT '',
            evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT attribute_quarantine_identity
                UNIQUE (release_id, entity_type, entity_id, attribute),
            CONSTRAINT attribute_quarantine_attribute_not_blank CHECK (attribute <> ''),
            CONSTRAINT attribute_quarantine_reason_not_blank CHECK (reason_code <> '')
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE meta.attribute_quarantine IS "
        "'Attributes withheld from a canonical entity because their source values are "
        "contradictory or unusable. The entity itself stays valid; the attribute is "
        "missing with a motive and is never imputed, averaged or arbitrarily picked.'"
    )
    op.execute(
        "CREATE INDEX attribute_quarantine_entity_idx "
        "ON meta.attribute_quarantine (entity_type, entity_id)"
    )
    op.execute(
        "CREATE INDEX attribute_quarantine_release_idx "
        "ON meta.attribute_quarantine (release_id, attribute, reason_code)"
    )

    # A BAN identifier reused with divergent positions leaves the address certain and its
    # position unusable. The point becomes absent with a motive rather than arbitrary.
    op.execute("ALTER TABLE reference.address ALTER COLUMN geom DROP NOT NULL")

    # Les droits proviennent des ALTER DEFAULT PRIVILEGES du socle : api_rw obtient SELECT,
    # pipeline_rw les écritures, backup_ro la lecture. Aucun GRANT explicite n'est requis.
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DELETE FROM reference.address WHERE geom IS NULL")
    op.execute("ALTER TABLE reference.address ALTER COLUMN geom SET NOT NULL")
    op.execute("DROP TABLE meta.attribute_quarantine")
    op.execute("RESET ROLE")
