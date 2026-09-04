"""Enforce release completeness at the atomic publication boundary.

Revision ID: 20260804_0003
Revises: 20260804_0002
Create Date: 2026-08-04 17:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_0003"
down_revision: str | None = "20260804_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE FUNCTION meta.guard_active_dataset_release() RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            release_acceptance text;
            asset_layer_count integer;
            import_layer_count integer;
            commune_count integer;
            commune_metric_count integer;
        BEGIN
            SELECT acceptance_status INTO STRICT release_acceptance
              FROM meta.dataset_release
             WHERE id = NEW.release_id AND data_source_id = NEW.data_source_id;

            IF release_acceptance NOT IN ('accepted', 'display_only')
               OR NEW.publication_mode <> release_acceptance THEN
                RAISE EXCEPTION 'Release % acceptance does not permit publication', NEW.release_id;
            END IF;

            IF EXISTS (
                SELECT 1 FROM meta.data_quality_check
                 WHERE release_id = NEW.release_id
                   AND scope_type = NEW.scope_type
                   AND scope_code = NEW.scope_code
                   AND blocks_publication
                   AND status = 'failed'
            ) THEN
                RAISE EXCEPTION 'Release % has blocking quality failures', NEW.release_id;
            END IF;

            IF NEW.data_source_id = 'DS-01' AND NEW.scope_type = 'department' THEN
                SELECT count(DISTINCT layer) FILTER (
                           WHERE layer IN ('communes', 'parcelles', 'batiments')
                       )
                  INTO asset_layer_count
                  FROM meta.raw_asset
                 WHERE release_id = NEW.release_id
                   AND territory_type = NEW.scope_type
                   AND territory_code = NEW.scope_code;

                SELECT count(DISTINCT runner_metadata->>'layer') FILTER (
                           WHERE runner_metadata->>'layer'
                                 IN ('communes', 'parcelles', 'batiments')
                       )
                  INTO import_layer_count
                  FROM meta.import_run
                 WHERE release_id = NEW.release_id
                   AND territory_type = NEW.scope_type
                   AND territory_code = NEW.scope_code
                   AND status = 'succeeded';

                SELECT count(*) INTO commune_count
                  FROM reference.administrative_area
                 WHERE release_id = NEW.release_id
                   AND department_code = NEW.scope_code
                   AND area_type = 'commune';

                SELECT count(*) INTO commune_metric_count
                  FROM meta.data_quality_check
                 WHERE release_id = NEW.release_id
                   AND scope_type = 'commune'
                   AND check_code IN (
                       'parcel_count', 'building_count', 'quarantined_geometry_count'
                   );

                IF asset_layer_count <> 3 OR import_layer_count <> 3 THEN
                    RAISE EXCEPTION 'DS-01 release % is missing required layers', NEW.release_id;
                END IF;
                IF commune_count = 0 OR commune_metric_count <> commune_count * 3 THEN
                    RAISE EXCEPTION 'DS-01 release % lacks commune quality coverage', NEW.release_id;
                END IF;
            END IF;

            RETURN NEW;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER active_dataset_release_guard
        BEFORE INSERT OR UPDATE ON meta.active_dataset_release
        FOR EACH ROW EXECUTE FUNCTION meta.guard_active_dataset_release()
        """
    )
    op.execute("REVOKE ALL ON FUNCTION meta.guard_active_dataset_release() FROM PUBLIC")
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP TRIGGER IF EXISTS active_dataset_release_guard ON meta.active_dataset_release")
    op.execute("DROP FUNCTION IF EXISTS meta.guard_active_dataset_release()")
    op.execute("RESET ROLE")
