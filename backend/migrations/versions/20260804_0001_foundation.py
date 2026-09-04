"""Create extensions, application schemas and least-privilege defaults.

Revision ID: 20260804_0001
Revises:
Create Date: 2026-08-04 10:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = (
    "meta",
    "reference",
    "observation",
    "feature",
    "scoring",
    "market",
    "app",
    "tiles",
    "audit",
)

READ_SCHEMAS = ("meta", "reference", "observation", "feature", "scoring", "market")
PIPELINE_SCHEMAS = ("meta", "reference", "observation", "feature", "scoring", "market", "tiles")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("SET LOCAL ROLE migration_owner")

    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}" AUTHORIZATION migration_owner')
        op.execute(f'REVOKE ALL ON SCHEMA "{schema}" FROM PUBLIC')

    for schema in READ_SCHEMAS:
        op.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO api_rw')
        op.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "{schema}" '
            "GRANT SELECT ON TABLES TO api_rw"
        )

    op.execute('GRANT USAGE ON SCHEMA "app" TO api_rw')
    op.execute(
        'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "app" '
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO api_rw"
    )
    op.execute(
        'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "app" '
        "GRANT USAGE, SELECT ON SEQUENCES TO api_rw"
    )
    op.execute('GRANT USAGE ON SCHEMA "audit" TO api_rw')
    op.execute(
        'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "audit" '
        "GRANT INSERT ON TABLES TO api_rw"
    )

    for schema in PIPELINE_SCHEMAS:
        op.execute(f'GRANT USAGE, CREATE ON SCHEMA "{schema}" TO pipeline_rw')
        op.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "{schema}" '
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pipeline_rw"
        )
        op.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "{schema}" '
            "GRANT USAGE, SELECT ON SEQUENCES TO pipeline_rw"
        )

    op.execute('GRANT USAGE ON SCHEMA "tiles" TO tiles_ro')
    op.execute(
        'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "tiles" '
        "GRANT SELECT ON TABLES TO tiles_ro"
    )

    for schema in SCHEMAS:
        op.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO backup_ro')
        op.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE migration_owner IN SCHEMA "{schema}" '
            "GRANT SELECT ON TABLES TO backup_ro"
        )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    op.execute("RESET ROLE")
