"""Add auditable Brittany pilot protocol and atomic regional publication.

Revision ID: 20260810_0015
Revises: 20260807_0014
Create Date: 2026-08-10 12:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260810_0015"
down_revision: str | None = "20260807_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BRITTANY_DEPARTMENTS = ("22", "29", "35", "56")
BRITTANY_DATASETS = tuple(f"DS-{number:02d}" for number in range(1, 10))
PILOT_SEGMENTS = ("metropolitan", "medium_city", "periurban", "coastal", "rural")


def _opportunity_tiles_sql(*, regional_gate: bool) -> str:
    gate = "CROSS JOIN meta.active_regional_release AS regional" if regional_gate else ""
    search_path = "pg_catalog, public, tiles, scoring, reference, meta"
    return f"""
        CREATE OR REPLACE FUNCTION tiles.opportunities(z integer, x integer, y integer)
        RETURNS bytea
        LANGUAGE sql
        STABLE
        PARALLEL SAFE
        SECURITY DEFINER
        SET search_path = {search_path}
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
                      {gate}
                     WHERE z BETWEEN 10 AND 22
                       AND ST_Transform(unit.geom, 3857) && ST_TileEnvelope(z, x, y)
                   ) AS tile
             WHERE tile.geom IS NOT NULL
        $function$
    """


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE TABLE scoring.segment_definition (
            id text NOT NULL,
            version integer NOT NULL CHECK (version > 0),
            status text NOT NULL CHECK (status IN ('draft', 'active', 'retired')),
            departments jsonb NOT NULL CHECK (jsonb_typeof(departments) = 'array'),
            segments jsonb NOT NULL CHECK (jsonb_typeof(segments) = 'object'),
            thresholds jsonb NOT NULL CHECK (jsonb_typeof(thresholds) = 'object'),
            rationale text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, version)
        )
        """
    )
    op.execute(
        """
        INSERT INTO scoring.segment_definition (
            id, version, status, departments, segments, thresholds, rationale
        ) VALUES (
            'brittany-market-segments', 1, 'draft',
            '["22", "29", "35", "56"]'::jsonb,
            '{
              "metropolitan": {"label": "Pôles urbains et métropolitains"},
              "medium_city": {"label": "Villes moyennes"},
              "periurban": {"label": "Couronnes périurbaines"},
              "coastal": {"label": "Marchés littoraux et touristiques"},
              "rural": {"label": "Territoires ruraux"}
            }'::jsonb,
            '{"status": "profiling_required"}'::jsonb,
            'Version initiale non publiable avant profilage et validation régionale.'
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE meta.territory_coverage_snapshot (
            id text PRIMARY KEY CHECK (id ~ '^coverage:[a-zA-Z0-9:_-]+$'),
            snapshot_at timestamptz NOT NULL,
            release_bundle_id text NOT NULL,
            department_code text NOT NULL CHECK (department_code IN {BRITTANY_DEPARTMENTS!r}),
            scope_type text NOT NULL CHECK (scope_type IN ('department', 'epci', 'commune')),
            scope_code text NOT NULL,
            segment_code text NOT NULL CHECK (segment_code IN {PILOT_SEGMENTS!r}),
            expected_count integer NOT NULL CHECK (expected_count >= 0),
            observed_count integer NOT NULL CHECK (observed_count >= 0),
            coverage_ratio numeric GENERATED ALWAYS AS (
                CASE WHEN expected_count = 0 THEN NULL
                     ELSE observed_count::numeric / expected_count END
            ) STORED,
            dataset_status jsonb NOT NULL CHECK (jsonb_typeof(dataset_status) = 'object'),
            limits jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(limits) = 'array'),
            UNIQUE (release_bundle_id, scope_type, scope_code, segment_code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.regional_release_bundle (
            id text PRIMARY KEY CHECK (id ~ '^brittany:[0-9a-f-]{36}$'),
            status text NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'published', 'withdrawn')),
            segment_definition_id text NOT NULL,
            segment_definition_version integer NOT NULL,
            created_by text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            published_at timestamptz,
            withdrawn_at timestamptz,
            reason text NOT NULL,
            FOREIGN KEY (segment_definition_id, segment_definition_version)
                REFERENCES scoring.segment_definition(id, version) ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE meta.regional_release_member (
            bundle_id text NOT NULL REFERENCES meta.regional_release_bundle(id) ON DELETE RESTRICT,
            data_source_id text NOT NULL REFERENCES meta.data_source(id),
            department_code text NOT NULL CHECK (department_code IN {BRITTANY_DEPARTMENTS!r}),
            release_id text NOT NULL REFERENCES meta.dataset_release(id),
            PRIMARY KEY (bundle_id, data_source_id, department_code),
            CONSTRAINT regional_member_source_release FOREIGN KEY (data_source_id, release_id)
                REFERENCES meta.dataset_release(data_source_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.active_regional_release (
            singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
            bundle_id text NOT NULL REFERENCES meta.regional_release_bundle(id),
            published_at timestamptz NOT NULL DEFAULT now(),
            published_by text NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.regional_release_event (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            bundle_id text NOT NULL REFERENCES meta.regional_release_bundle(id),
            replaced_bundle_id text REFERENCES meta.regional_release_bundle(id),
            action text NOT NULL CHECK (action IN ('publish', 'rollback', 'withdraw')),
            actor text NOT NULL,
            reason text NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        f"""
        CREATE VIEW meta.brittany_release_readiness AS
        WITH departments(department_code) AS (VALUES {",".join(f"('{code}')" for code in BRITTANY_DEPARTMENTS)}),
             datasets(data_source_id) AS (VALUES {",".join(f"('{code}')" for code in BRITTANY_DATASETS)})
        SELECT departments.department_code,
               datasets.data_source_id,
               active.release_id,
               release.acceptance_status,
               COALESCE(active.publication_mode = 'accepted'
                        AND release.acceptance_status = 'accepted', false) AS ready,
               COALESCE((
                   SELECT count(*)
                     FROM meta.data_quality_check AS quality
                    WHERE quality.release_id = active.release_id
                      AND quality.scope_type = 'department'
                      AND quality.scope_code = departments.department_code
                      AND quality.blocks_publication
                      AND quality.status = 'failed'
               ), 0) AS blocking_quality_count
          FROM departments CROSS JOIN datasets
          LEFT JOIN meta.active_dataset_release AS active
            ON active.data_source_id = datasets.data_source_id
           AND active.scope_type = 'department'
           AND active.scope_code = departments.department_code
          LEFT JOIN meta.dataset_release AS release ON release.id = active.release_id
        """
    )
    op.execute(
        """
        CREATE FUNCTION meta.stage_brittany_release(
            p_bundle_id text, p_actor text, p_reason text
        ) RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, meta, scoring
        AS $function$
        BEGIN
            INSERT INTO meta.regional_release_bundle (
                id, segment_definition_id, segment_definition_version, created_by, reason
            ) VALUES (
                p_bundle_id, 'brittany-market-segments', 1, p_actor, p_reason
            );
            INSERT INTO meta.regional_release_member (
                bundle_id, data_source_id, department_code, release_id
            )
            SELECT p_bundle_id, data_source_id, department_code, release_id
              FROM meta.brittany_release_readiness
             WHERE release_id IS NOT NULL;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION meta.publish_brittany_release(
            p_bundle_id text, p_actor text, p_reason text, p_action text DEFAULT 'publish'
        ) RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, meta, scoring
        AS $function$
        DECLARE
            selected meta.regional_release_bundle%ROWTYPE;
            replaced text;
        BEGIN
            IF p_action NOT IN ('publish', 'rollback') THEN
                RAISE EXCEPTION 'Unsupported regional publication action: %', p_action;
            END IF;
            SELECT * INTO STRICT selected FROM meta.regional_release_bundle
             WHERE id = p_bundle_id FOR UPDATE;
            IF (SELECT count(*) FROM meta.regional_release_member WHERE bundle_id = p_bundle_id) <> 36 THEN
                RAISE EXCEPTION 'Regional bundle must contain DS-01 to DS-09 for four departments';
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM meta.regional_release_member AS member
                  JOIN meta.dataset_release AS release ON release.id = member.release_id
                  LEFT JOIN meta.data_quality_check AS quality
                    ON quality.release_id = member.release_id
                   AND quality.scope_type = 'department'
                   AND quality.scope_code = member.department_code
                   AND quality.blocks_publication AND quality.status = 'failed'
                 WHERE member.bundle_id = p_bundle_id
                   AND (release.acceptance_status <> 'accepted' OR quality.id IS NOT NULL)
            ) THEN
                RAISE EXCEPTION 'Regional bundle contains a rejected or defective source';
            END IF;
            IF (SELECT count(*) FROM scoring.active_score_definition AS active
                JOIN scoring.score_definition AS definition
                  ON definition.id = active.definition_id
                 AND definition.version = active.definition_version
                WHERE definition.publication_eligible) <> 2 THEN
                RAISE EXCEPTION 'Both score strategies must be profiled and active';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM scoring.segment_definition
                 WHERE id = selected.segment_definition_id
                   AND version = selected.segment_definition_version
                   AND status = 'active'
            ) THEN
                RAISE EXCEPTION 'Regional segmentation must be active';
            END IF;
            IF (
                SELECT count(DISTINCT unit.department_code)
                  FROM scoring.published_opportunity AS published
                  JOIN scoring.opportunity_snapshot AS snapshot
                    ON snapshot.id = published.opportunity_snapshot_id
                  JOIN reference.property_unit AS unit ON unit.id = snapshot.property_unit_id
                 WHERE unit.department_code IN ('22', '29', '35', '56')
            ) <> 4 OR (
                SELECT count(DISTINCT snapshot.segment_code)
                  FROM scoring.published_opportunity AS published
                  JOIN scoring.opportunity_snapshot AS snapshot
                    ON snapshot.id = published.opportunity_snapshot_id
                 WHERE snapshot.segment_code IN (
                    'metropolitan', 'medium_city', 'periurban', 'coastal', 'rural'
                 )
            ) <> 5 THEN
                RAISE EXCEPTION 'Published candidates must cover four departments and five pilot segments';
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM scoring.published_opportunity AS published
                  JOIN scoring.opportunity_snapshot AS snapshot
                    ON snapshot.id = published.opportunity_snapshot_id
                  CROSS JOIN LATERAL jsonb_array_elements_text(snapshot.release_ids)
                    AS source_release(release_id)
                 WHERE NOT EXISTS (
                    SELECT 1 FROM meta.regional_release_member AS member
                     WHERE member.bundle_id = p_bundle_id
                       AND member.release_id = source_release.release_id
                 )
            ) THEN
                RAISE EXCEPTION 'A published snapshot uses a release outside the regional bundle';
            END IF;
            INSERT INTO meta.publication_event (
                data_source_id, scope_type, scope_code, release_id,
                replaced_release_id, action, publication_mode, actor, reason
            )
            SELECT member.data_source_id, 'department', member.department_code,
                   member.release_id, active.release_id, p_action, 'accepted', p_actor, p_reason
              FROM meta.regional_release_member AS member
              LEFT JOIN meta.active_dataset_release AS active
                ON active.data_source_id = member.data_source_id
               AND active.scope_type = 'department'
               AND active.scope_code = member.department_code
             WHERE member.bundle_id = p_bundle_id;
            INSERT INTO meta.active_dataset_release (
                data_source_id, scope_type, scope_code, release_id,
                publication_mode, published_at, published_by
            )
            SELECT data_source_id, 'department', department_code, release_id,
                   'accepted', clock_timestamp(), p_actor
              FROM meta.regional_release_member WHERE bundle_id = p_bundle_id
            ON CONFLICT (data_source_id, scope_type, scope_code) DO UPDATE SET
                release_id = EXCLUDED.release_id,
                publication_mode = EXCLUDED.publication_mode,
                published_at = EXCLUDED.published_at,
                published_by = EXCLUDED.published_by;
            SELECT bundle_id INTO replaced FROM meta.active_regional_release
             WHERE singleton FOR UPDATE;
            UPDATE meta.regional_release_bundle
               SET status = CASE WHEN id = replaced THEN 'withdrawn' ELSE status END,
                   withdrawn_at = CASE WHEN id = replaced THEN clock_timestamp() ELSE withdrawn_at END
             WHERE id = replaced AND id <> p_bundle_id;
            UPDATE meta.regional_release_bundle
               SET status = 'published', published_at = clock_timestamp(), withdrawn_at = NULL,
                   reason = p_reason
             WHERE id = p_bundle_id;
            INSERT INTO meta.active_regional_release (singleton, bundle_id, published_by)
            VALUES (true, p_bundle_id, p_actor)
            ON CONFLICT (singleton) DO UPDATE SET
                bundle_id = EXCLUDED.bundle_id,
                published_at = clock_timestamp(),
                published_by = EXCLUDED.published_by;
            INSERT INTO meta.regional_release_event (
                bundle_id, replaced_bundle_id, action, actor, reason
            ) VALUES (p_bundle_id, replaced, p_action, p_actor, p_reason);
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION meta.withdraw_brittany_release(
            p_actor text, p_reason text
        ) RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, meta
        AS $function$
        DECLARE selected text;
        BEGIN
            DELETE FROM meta.active_regional_release WHERE singleton RETURNING bundle_id INTO selected;
            IF selected IS NULL THEN RAISE EXCEPTION 'No active regional release'; END IF;
            DELETE FROM meta.active_dataset_release AS active
             USING meta.regional_release_member AS member
             WHERE member.bundle_id = selected
               AND active.data_source_id = member.data_source_id
               AND active.scope_type = 'department'
               AND active.scope_code = member.department_code
               AND active.release_id = member.release_id;
            UPDATE meta.regional_release_bundle
               SET status = 'withdrawn', withdrawn_at = clock_timestamp(), reason = p_reason
             WHERE id = selected;
            INSERT INTO meta.regional_release_event (bundle_id, action, actor, reason)
            VALUES (selected, 'withdraw', p_actor, p_reason);
        END
        $function$
        """
    )

    op.execute(
        """
        CREATE TABLE app.pilot_reviewer_identity (
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            user_id text NOT NULL REFERENCES app.app_user(id) ON DELETE CASCADE,
            pseudonym text NOT NULL DEFAULT ('evaluator:' || gen_random_uuid()::text),
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (organization_id, user_id),
            UNIQUE (organization_id, pseudonym)
        )
        """
    )
    op.execute(
        f"""
        ALTER TABLE app.candidate_review
            ADD COLUMN strategy_code text REFERENCES scoring.strategy(code),
            ADD COLUMN protocol_version text,
            ADD COLUMN protocol_arm text CHECK (
                protocol_arm IS NULL OR protocol_arm IN ('top_score', 'baseline', 'random')
            ),
            ADD COLUMN evaluation_split text CHECK (
                evaluation_split IS NULL OR evaluation_split IN ('development', 'validation', 'final')
            ),
            ADD COLUMN segment_code text CHECK (
                segment_code IS NULL OR segment_code IN {PILOT_SEGMENTS!r}
            ),
            ADD COLUMN reviewer_pseudonym text,
            ADD COLUMN blind_id text,
            ADD COLUMN double_review_group text
        """
    )
    op.execute(
        """
        CREATE TABLE app.candidate_review_outcome (
            id text PRIMARY KEY CHECK (id ~ '^outcome:[0-9a-f-]{36}$'),
            organization_id text NOT NULL REFERENCES app.organization(id) ON DELETE CASCADE,
            candidate_review_id text NOT NULL REFERENCES app.candidate_review(id) ON DELETE RESTRICT,
            stage text NOT NULL CHECK (
                stage IN ('desk_analysis', 'contact', 'visit', 'offer', 'acquisition')
            ),
            result text NOT NULL CHECK (result IN ('positive', 'negative', 'pending', 'unknown')),
            details jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details) = 'object'),
            observed_at timestamptz NOT NULL,
            author_id text NOT NULL REFERENCES app.app_user(id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    for table in ("pilot_reviewer_identity", "candidate_review_outcome"):
        op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON app.{table} "
            "USING (organization_id = nullif(current_setting('app.current_organization_id', true), '')) "
            "WITH CHECK (organization_id = nullif(current_setting('app.current_organization_id', true), ''))"
        )
    op.execute(
        "CREATE TRIGGER candidate_review_outcome_immutable BEFORE UPDATE OR DELETE "
        "ON app.candidate_review_outcome FOR EACH ROW "
        "EXECUTE FUNCTION app.reject_immutable_private_event()"
    )
    op.execute(
        "CREATE INDEX candidate_review_protocol_idx ON app.candidate_review "
        "(protocol_version, evaluation_split, segment_code, protocol_arm)"
    )
    op.execute(
        "CREATE INDEX coverage_snapshot_territory_idx ON meta.territory_coverage_snapshot "
        "(department_code, scope_type, scope_code, snapshot_at DESC)"
    )
    for signature in (
        "meta.stage_brittany_release(text,text,text)",
        "meta.publish_brittany_release(text,text,text,text)",
        "meta.withdraw_brittany_release(text,text)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO api_rw")
    op.execute(_opportunity_tiles_sql(regional_gate=True))
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(_opportunity_tiles_sql(regional_gate=False))
    for signature in (
        "meta.withdraw_brittany_release(text,text)",
        "meta.publish_brittany_release(text,text,text,text)",
        "meta.stage_brittany_release(text,text,text)",
    ):
        op.execute(f"DROP FUNCTION {signature}")
    op.execute("DROP VIEW meta.brittany_release_readiness")
    op.execute("DROP TABLE app.candidate_review_outcome")
    op.execute("DROP TABLE app.pilot_reviewer_identity")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN double_review_group")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN blind_id")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN reviewer_pseudonym")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN segment_code")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN evaluation_split")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN protocol_arm")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN protocol_version")
    op.execute("ALTER TABLE app.candidate_review DROP COLUMN strategy_code")
    op.execute("DROP TABLE meta.regional_release_event")
    op.execute("DROP TABLE meta.active_regional_release")
    op.execute("DROP TABLE meta.regional_release_member")
    op.execute("DROP TABLE meta.regional_release_bundle")
    op.execute("DROP TABLE meta.territory_coverage_snapshot")
    op.execute("DROP TABLE scoring.segment_definition")
    op.execute("RESET ROLE")
