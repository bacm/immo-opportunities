"""Account for exact source duplicates without weakening conflict detection.

Revision ID: 20260804_0004
Revises: 20260804_0003
Create Date: 2026-08-04 18:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_0004"
down_revision: str | None = "20260804_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        ALTER TABLE meta.import_run
        ADD COLUMN deduplicated_row_count bigint NOT NULL DEFAULT 0
            CHECK (deduplicated_row_count >= 0)
        """
    )
    op.execute(
        """
        UPDATE meta.import_run
           SET deduplicated_row_count = greatest(
                   source_row_count - normalized_row_count - quarantined_row_count,
                   0
               )
         WHERE status = 'succeeded'
           AND runner_metadata->>'layer' = 'batiments'
        """
    )
    op.execute(
        """
        DELETE FROM meta.data_quality_check
         WHERE import_run_id IS NOT NULL
           AND check_code IN (
               'source_vs_normalized_count',
               'duplicate_source_id',
               'exact_duplicate_record',
               'conflicting_duplicate_source_id'
           )
        """
    )
    op.execute(
        """
        INSERT INTO meta.data_quality_check (
            release_id, import_run_id, check_code, check_version, scope_type,
            scope_code, layer, status, severity, blocks_publication,
            observed_value, expected_value, details
        )
        SELECT release_id, id, 'source_vs_normalized_count', '2', territory_type,
               territory_code, runner_metadata->>'layer',
               CASE WHEN source_row_count = normalized_row_count
                                             + quarantined_row_count
                                             + deduplicated_row_count
                    THEN 'passed' ELSE 'failed' END,
               CASE WHEN source_row_count = normalized_row_count
                                             + quarantined_row_count
                                             + deduplicated_row_count
                    THEN 'info' ELSE 'error' END,
               true,
               normalized_row_count + quarantined_row_count + deduplicated_row_count,
               source_row_count,
               jsonb_build_object(
                   'normalized', normalized_row_count,
                   'quarantined', quarantined_row_count,
                   'deduplicated', deduplicated_row_count
               )
          FROM meta.import_run
         WHERE status = 'succeeded'
        UNION ALL
        SELECT release_id, id, 'exact_duplicate_record', '1', territory_type,
               territory_code, runner_metadata->>'layer',
               CASE WHEN deduplicated_row_count = 0 THEN 'passed' ELSE 'warning' END,
               CASE WHEN deduplicated_row_count = 0 THEN 'info' ELSE 'warning' END,
               false, deduplicated_row_count, 0,
               jsonb_build_object('strategy', 'identical_record_checksum')
          FROM meta.import_run
         WHERE status = 'succeeded'
        UNION ALL
        SELECT release_id, id, 'conflicting_duplicate_source_id', '1', territory_type,
               territory_code, runner_metadata->>'layer',
               CASE WHEN source_row_count - normalized_row_count
                                                  - quarantined_row_count
                                                  - deduplicated_row_count = 0
                    THEN 'passed' ELSE 'failed' END,
               CASE WHEN source_row_count - normalized_row_count
                                                  - quarantined_row_count
                                                  - deduplicated_row_count = 0
                    THEN 'info' ELSE 'error' END,
               true,
               greatest(
                   source_row_count - normalized_row_count
                                    - quarantined_row_count
                                    - deduplicated_row_count,
                   0
               ),
               0, jsonb_build_object('strategy', 'distinct_record_checksum')
          FROM meta.import_run
         WHERE status = 'succeeded'
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        DELETE FROM meta.data_quality_check
         WHERE import_run_id IS NOT NULL
           AND check_code IN (
               'source_vs_normalized_count',
               'exact_duplicate_record',
               'conflicting_duplicate_source_id'
           )
        """
    )
    op.execute(
        """
        INSERT INTO meta.data_quality_check (
            release_id, import_run_id, check_code, check_version, scope_type,
            scope_code, layer, status, severity, blocks_publication,
            observed_value, expected_value, details
        )
        SELECT release_id, id, 'source_vs_normalized_count', '1', territory_type,
               territory_code, runner_metadata->>'layer',
               CASE WHEN source_row_count = normalized_row_count + quarantined_row_count
                    THEN 'passed' ELSE 'failed' END,
               CASE WHEN source_row_count = normalized_row_count + quarantined_row_count
                    THEN 'info' ELSE 'error' END,
               true, normalized_row_count + quarantined_row_count, source_row_count,
               jsonb_build_object(
                   'normalized', normalized_row_count,
                   'quarantined', quarantined_row_count
               )
          FROM meta.import_run
         WHERE status = 'succeeded'
        UNION ALL
        SELECT release_id, id, 'duplicate_source_id', '1', territory_type,
               territory_code, runner_metadata->>'layer',
               CASE WHEN deduplicated_row_count = 0 THEN 'passed' ELSE 'failed' END,
               CASE WHEN deduplicated_row_count = 0 THEN 'info' ELSE 'error' END,
               true, deduplicated_row_count, 0, '{}'::jsonb
          FROM meta.import_run
         WHERE status = 'succeeded'
        """
    )
    op.execute("ALTER TABLE meta.import_run DROP COLUMN deduplicated_row_count")
    op.execute("RESET ROLE")
