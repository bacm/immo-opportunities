"""Add organization-scoped workflow data with row-level security.

Revision ID: 20260807_0013
Revises: 20260807_0012
Create Date: 2026-08-07 15:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_0013"
down_revision: str | None = "20260807_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_TABLES = (
    "organization",
    "app_user",
    "organization_membership",
    "candidate_state",
    "candidate_status_history",
    "note",
    "candidate_review",
    "candidate_scenario",
    "saved_search",
)

TENANT_TABLES = (
    "organization_membership",
    "candidate_state",
    "candidate_status_history",
    "note",
    "candidate_review",
    "candidate_scenario",
    "saved_search",
)

STATUSES = (
    "new",
    "to_analyze",
    "retained",
    "contact_to_prepare",
    "contacted",
    "visit",
    "offer",
    "acquired",
    "lost",
    "rejected",
    "ignored",
)

REJECTION_REASONS = (
    "land_false_positive",
    "adverse_planning",
    "no_access",
    "risk_too_high",
    "estimate_too_optimistic",
    "works_too_large",
    "already_known",
    "outside_strategy",
    "other",
)


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE TABLE app.organization (
            id text PRIMARY KEY CHECK (id ~ '^org:[a-z0-9_-]+$'),
            name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.app_user (
            id text PRIMARY KEY CHECK (id ~ '^user:[0-9a-f-]{36}$'),
            external_subject text NOT NULL UNIQUE,
            email text,
            display_name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.organization_membership (
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            user_id text NOT NULL REFERENCES app.app_user(id) ON DELETE CASCADE,
            role text NOT NULL CHECK (
                role IN ('platform_admin', 'organization_admin', 'analyst', 'viewer')
            ),
            is_default boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (organization_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX membership_one_default_idx "
        "ON app.organization_membership (user_id) WHERE is_default"
    )
    op.execute(
        f"""
        CREATE TABLE app.candidate_state (
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            status text NOT NULL DEFAULT 'new' CHECK (status IN {STATUSES!r}),
            favorite boolean NOT NULL DEFAULT false,
            rejection_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
            rejection_comment text,
            updated_by text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (organization_id, opportunity_snapshot_id),
            CONSTRAINT candidate_state_reasons_array CHECK (
                jsonb_typeof(rejection_reasons) = 'array'
            ),
            CONSTRAINT candidate_state_rejection_required CHECK (
                status <> 'rejected' OR jsonb_array_length(rejection_reasons) > 0
            )
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE app.candidate_status_history (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            previous_status text CHECK (previous_status IS NULL OR previous_status IN {STATUSES!r}),
            status text NOT NULL CHECK (status IN {STATUSES!r}),
            rejection_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
            rejection_comment text,
            author_id text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            occurred_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.note (
            id text PRIMARY KEY CHECK (id ~ '^note:[0-9a-f-]{36}$'),
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            body text NOT NULL CHECK (length(btrim(body)) BETWEEN 1 AND 10000),
            author_id text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.candidate_review (
            id text PRIMARY KEY CHECK (id ~ '^review:[0-9a-f-]{36}$'),
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            decision text NOT NULL CHECK (
                decision IN ('worth_deeper_analysis', 'not_relevant', 'uncertain')
            ),
            rejection_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
            confidence smallint NOT NULL CHECK (confidence BETWEEN 1 AND 5),
            field_visit_performed boolean NOT NULL DEFAULT false,
            author_id text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            reviewed_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT candidate_review_reasons_array CHECK (
                jsonb_typeof(rejection_reasons) = 'array'
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.candidate_scenario (
            id text PRIMARY KEY CHECK (id ~ '^scenario:user:[0-9a-f-]{36}$'),
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            assumptions jsonb NOT NULL,
            results jsonb NOT NULL,
            author_id text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT candidate_scenario_objects CHECK (
                jsonb_typeof(assumptions) = 'object' AND jsonb_typeof(results) = 'object'
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.saved_search (
            id text PRIMARY KEY CHECK (id ~ '^search:[0-9a-f-]{36}$'),
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
            filters jsonb NOT NULL CHECK (jsonb_typeof(filters) = 'object'),
            owner_id text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, owner_id, name)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE audit.sensitive_access_event (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            organization_id text NOT NULL,
            actor_id text NOT NULL,
            action text NOT NULL,
            resource_type text NOT NULL,
            resource_id text,
            request_id text NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT now(),
            details jsonb NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.reject_immutable_private_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'private_history_is_immutable';
        END;
        $$
        """
    )
    for table in (
        "candidate_status_history",
        "note",
        "candidate_review",
        "candidate_scenario",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON app.{table} "
            "FOR EACH ROW EXECUTE FUNCTION app.reject_immutable_private_event()"
        )
    op.execute(
        "CREATE TRIGGER sensitive_access_event_immutable BEFORE UPDATE OR DELETE "
        "ON audit.sensitive_access_event FOR EACH ROW "
        "EXECUTE FUNCTION app.reject_immutable_private_event()"
    )

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON app.{table} "
            "USING (organization_id = nullif(current_setting('app.current_organization_id', true), '')) "
            "WITH CHECK (organization_id = nullif(current_setting('app.current_organization_id', true), ''))"
        )
    op.execute("ALTER TABLE app.organization ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.organization FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY organization_tenant_isolation ON app.organization "
        "USING (id = nullif(current_setting('app.current_organization_id', true), ''))"
    )
    op.execute("ALTER TABLE app.app_user ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.app_user FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY app_user_self ON app.app_user USING ("
        "external_subject = nullif(current_setting('app.current_subject', true), ''))"
    )
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

    for table in (
        "candidate_state",
        "candidate_status_history",
        "note",
        "candidate_review",
        "candidate_scenario",
    ):
        op.execute(
            f"CREATE INDEX {table}_opportunity_idx ON app.{table} "
            "(organization_id, opportunity_snapshot_id)"
        )
    op.execute("CREATE INDEX import_run_admin_idx ON meta.import_run (started_at DESC, id)")
    op.execute(
        "CREATE INDEX data_quality_admin_idx ON meta.data_quality_check "
        "(checked_at DESC, status, severity)"
    )
    op.execute("GRANT USAGE, SELECT ON SEQUENCE audit.sensitive_access_event_id_seq TO api_rw")
    op.execute(
        """
        CREATE FUNCTION tiles.opportunities(z integer, x integer, y integer)
        RETURNS bytea
        LANGUAGE sql
        STABLE
        PARALLEL SAFE
        SECURITY DEFINER
        SET search_path = pg_catalog, public, tiles, scoring, reference
        AS $function$
            SELECT COALESCE(ST_AsMVT(tile, 'opportunities', 4096, 'geom'), ''::bytea)
              FROM (
                    SELECT snapshot.id, snapshot.property_unit_id,
                           snapshot.strategy_code AS strategy,
                           snapshot.overall_score::double precision AS score,
                           snapshot.confidence_level,
                           ST_AsMVTGeom(
                               ST_Transform(unit.geom, 3857),
                               ST_TileEnvelope(z, x, y), 4096, 64, true
                           ) AS geom
                      FROM scoring.published_opportunity AS published
                      JOIN scoring.opportunity_snapshot AS snapshot
                        ON snapshot.id = published.opportunity_snapshot_id
                      JOIN reference.property_unit_geometry AS unit
                        ON unit.id = snapshot.property_unit_id
                     WHERE z BETWEEN 10 AND 22
                       AND ST_Transform(unit.geom, 3857) && ST_TileEnvelope(z, x, y)
                   ) AS tile
             WHERE tile.geom IS NOT NULL
        $function$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION tiles.opportunities(integer,integer,integer) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION tiles.opportunities(integer,integer,integer) TO tiles_ro")
    op.get_bind().exec_driver_sql(
        """
        COMMENT ON FUNCTION tiles.opportunities(integer,integer,integer) IS
        '{"description":"Opportunités publiées v1","minzoom":10,"maxzoom":22}'
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP FUNCTION tiles.opportunities(integer,integer,integer)")
    op.execute("DROP TABLE audit.sensitive_access_event")
    for table in reversed(APP_TABLES):
        op.execute(f"DROP TABLE app.{table}")
    op.execute("DROP FUNCTION app.reject_immutable_private_event()")
    op.execute("DROP INDEX meta.import_run_admin_idx")
    op.execute("DROP INDEX meta.data_quality_admin_idx")
    op.execute("RESET ROLE")
