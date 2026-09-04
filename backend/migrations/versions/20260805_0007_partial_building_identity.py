"""Allow a stable building identity before a polygon and expose match review.

Revision ID: 20260805_0007
Revises: 20260805_0006
Create Date: 2026-08-05 14:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260805_0007"
down_revision: str | None = "20260805_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("ALTER TABLE reference.building ALTER COLUMN commune_code DROP NOT NULL")
    op.execute("ALTER TABLE reference.building ALTER COLUMN geom DROP NOT NULL")
    op.execute("ALTER TABLE reference.building DROP CONSTRAINT building_geom_valid")
    op.execute("ALTER TABLE reference.building DROP CONSTRAINT building_geom_nonempty")
    op.execute(
        "ALTER TABLE reference.building ADD CONSTRAINT building_geom_valid "
        "CHECK (geom IS NULL OR ST_IsValid(geom))"
    )
    op.execute(
        "ALTER TABLE reference.building ADD CONSTRAINT building_geom_nonempty "
        "CHECK (geom IS NULL OR NOT ST_IsEmpty(geom))"
    )

    op.execute(
        """
        CREATE FUNCTION meta.review_entity_match(
            p_match_id bigint,
            p_decision text,
            p_reviewer text,
            p_rationale text
        ) RETURNS void
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            previous_decision text;
            is_critical boolean;
        BEGIN
            IF p_decision NOT IN ('certain', 'ambiguous', 'rejected') THEN
                RAISE EXCEPTION 'Unsupported match decision: %', p_decision;
            END IF;
            IF length(trim(p_reviewer)) = 0 OR length(trim(p_rationale)) = 0 THEN
                RAISE EXCEPTION 'Reviewer and rationale are required';
            END IF;

            SELECT decision, critical INTO STRICT previous_decision, is_critical
              FROM meta.entity_match WHERE id = p_match_id FOR UPDATE;

            INSERT INTO meta.entity_match_review (
                match_id, previous_decision, reviewed_decision, reviewer, rationale
            ) VALUES (p_match_id, previous_decision, p_decision, p_reviewer, p_rationale);

            UPDATE meta.entity_match SET
                decision = p_decision,
                blocks_publication = is_critical AND p_decision = 'ambiguous',
                method = 'manual',
                rationale = p_rationale
             WHERE id = p_match_id;

            UPDATE reference.building_parcel SET relation_status = p_decision
             WHERE match_id = p_match_id;
            UPDATE reference.property_unit_member SET
                member_role = CASE
                    WHEN p_decision = 'certain' THEN 'supporting'
                    WHEN p_decision = 'ambiguous' THEN 'ambiguous'
                    ELSE member_role
                END
             WHERE match_id = p_match_id;
        END
        $function$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION meta.review_entity_match(bigint,text,text,text) FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION meta.review_entity_match(bigint,text,text,text) TO api_rw"
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP FUNCTION IF EXISTS meta.review_entity_match(bigint,text,text,text)")
    op.execute("DELETE FROM reference.building WHERE geom IS NULL OR commune_code IS NULL")
    op.execute("ALTER TABLE reference.building ALTER COLUMN geom SET NOT NULL")
    op.execute("ALTER TABLE reference.building ALTER COLUMN commune_code SET NOT NULL")
    op.execute("RESET ROLE")
