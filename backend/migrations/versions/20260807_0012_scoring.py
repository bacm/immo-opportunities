"""Add immutable explainable scoring snapshots and atomic publication.

Revision ID: 20260807_0012
Revises: 20260806_0011
Create Date: 2026-08-07 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260807_0012"
down_revision: str | None = "20260806_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCORING_TABLES = (
    "strategy",
    "score_definition",
    "score_definition_component",
    "score_definition_feature",
    "score_eligibility_rule",
    "active_score_definition",
    "score_definition_publication_event",
    "estimate_scenario",
    "opportunity_snapshot",
    "score_component",
    "score_evidence",
    "published_opportunity",
    "opportunity_publication_event",
    "backtest_run",
    "backtest_metric",
    "ablation_result",
)

FINANCIAL_FEATURES = (
    ("FIN-001", "division_scenario_margin_range", "division_extension", "json", "EUR"),
    ("FIN-002", "division_return_on_cost", "division_extension", "number", "ratio"),
    ("FIN-101", "purchase_estimate_range", "renovation_resale", "json", "EUR"),
    ("FIN-102", "works_cost_range", "renovation_resale", "json", "EUR"),
    ("FIN-103", "resale_estimate_range", "renovation_resale", "json", "EUR"),
    ("FIN-104", "net_margin_range", "renovation_resale", "json", "EUR"),
    ("FIN-105", "return_on_cost", "renovation_resale", "number", "ratio"),
    ("FIN-106", "break_even_purchase_price", "renovation_resale", "number", "EUR"),
)

SCORE_DEFINITIONS = (
    {
        "id": "division-extension-v0.1",
        "version": 1,
        "strategy_code": "division_extension",
        "contract_path": "contracts/scoring/division-extension-v1.json",
        "contract_digest": "eaf8d3dea4078fc278ddad3851d93c625f10732e9c00d53485429321c3d26394",
        "publication_eligible": False,
        "parameters": {"parameter_status": "profiling_required"},
    },
    {
        "id": "renovation-resale-v0.1",
        "version": 1,
        "strategy_code": "renovation_resale",
        "contract_path": "contracts/scoring/renovation-resale-v1.json",
        "contract_digest": "f6aa34b3148faaef3f80272cbae5ffa13e85b7ca43f18173ec938d4130058eb6",
        "publication_eligible": False,
        "parameters": {"parameter_status": "profiling_required"},
    },
)

COMPONENTS = (
    ("division-extension-v0.1", 1, "land_capacity", "Capacité foncière apparente", 0.40, 1),
    (
        "division-extension-v0.1",
        1,
        "preliminary_feasibility",
        "Faisabilité préliminaire",
        0.25,
        2,
    ),
    (
        "division-extension-v0.1",
        1,
        "economic_attractiveness",
        "Attractivité économique",
        0.25,
        3,
    ),
    ("division-extension-v0.1", 1, "risk_complexity", "Risques et complexité", 0.10, 4),
    ("renovation-resale-v0.1", 1, "scenario_economics", "Économie du scénario", 0.40, 1),
    (
        "renovation-resale-v0.1",
        1,
        "renovation_need_potential",
        "Besoin et potentiel de rénovation",
        0.25,
        2,
    ),
    ("renovation-resale-v0.1", 1, "market_liquidity", "Liquidité du marché", 0.20, 3),
    ("renovation-resale-v0.1", 1, "risk_complexity", "Risques et complexité", 0.15, 4),
)

SCORE_RULES = (
    # definition, feature, component, weight, requirement, transformation, direction
    (
        "division-extension-v0.1",
        "LAND-004",
        "land_capacity",
        0.25,
        "required",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "LAND-003",
        "land_capacity",
        0.20,
        "required",
        "local_percentile",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "LAND-006",
        "land_capacity",
        0.15,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "LAND-007",
        "land_capacity",
        0.15,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "LAND-008",
        "land_capacity",
        0.10,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "LAND-005",
        "land_capacity",
        0.10,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "LAND-009",
        "land_capacity",
        0.05,
        "optional",
        "local_percentile",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "URB-002",
        "preliminary_feasibility",
        0.40,
        "required",
        "profiled_score",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "URB-004",
        "preliminary_feasibility",
        0.35,
        "required",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "URB-003",
        "preliminary_feasibility",
        0.25,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "FIN-001",
        "economic_attractiveness",
        0.30,
        "required",
        "profiled_score",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "FIN-002",
        "economic_attractiveness",
        0.20,
        "required",
        "profiled_score",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "MKT-001",
        "economic_attractiveness",
        0.25,
        "required",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "MKT-005",
        "economic_attractiveness",
        0.15,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "division-extension-v0.1",
        "MKT-004",
        "economic_attractiveness",
        0.10,
        "optional",
        "local_percentile",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "RISK-001",
        "risk_complexity",
        0.25,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "RISK-002",
        "risk_complexity",
        0.25,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "RISK-003",
        "risk_complexity",
        0.25,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "RISK-004",
        "risk_complexity",
        0.25,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "division-extension-v0.1",
        "URB-005",
        None,
        0.00,
        "confidence_only",
        "identity",
        "confidence_only",
    ),
    (
        "renovation-resale-v0.1",
        "FIN-104",
        "scenario_economics",
        0.50,
        "required",
        "profiled_score",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "FIN-105",
        "scenario_economics",
        0.30,
        "required",
        "profiled_score",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "FIN-106",
        "scenario_economics",
        0.20,
        "required",
        "profiled_score",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "REN-005",
        "renovation_need_potential",
        0.40,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "REN-007",
        "renovation_need_potential",
        0.25,
        "optional",
        "profiled_score",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "REN-001",
        "renovation_need_potential",
        0.20,
        "optional",
        "profiled_score",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "REN-003",
        "renovation_need_potential",
        0.15,
        "optional",
        "profiled_score",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "MKT-102",
        "market_liquidity",
        0.35,
        "required",
        "local_percentile",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "MKT-103",
        "market_liquidity",
        0.30,
        "optional",
        "local_percentile",
        "decreasing",
    ),
    (
        "renovation-resale-v0.1",
        "MKT-104",
        "market_liquidity",
        0.25,
        "confidence_only",
        "local_percentile",
        "confidence_only",
    ),
    (
        "renovation-resale-v0.1",
        "MKT-105",
        "market_liquidity",
        0.10,
        "optional",
        "local_percentile",
        "increasing",
    ),
    (
        "renovation-resale-v0.1",
        "RISK-101",
        "risk_complexity",
        0.60,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "renovation-resale-v0.1",
        "FIN-102",
        "risk_complexity",
        0.25,
        "required",
        "profiled_score",
        "decreasing",
    ),
    (
        "renovation-resale-v0.1",
        "URB-003",
        "risk_complexity",
        0.15,
        "optional",
        "profiled_score",
        "decreasing",
    ),
    (
        "renovation-resale-v0.1",
        "REN-008",
        None,
        0.00,
        "confidence_only",
        "identity",
        "confidence_only",
    ),
)

ELIGIBILITY_RULES = (
    ("division-extension-v0.1", "VALID_PARCEL_GEOMETRY", "present", ["LAND-001"]),
    ("division-extension-v0.1", "RESOLVED_BUILDING_FOOTPRINT", "present", ["LAND-002"]),
    ("division-extension-v0.1", "GPU_ZONE_AVAILABLE", "present", ["URB-001"]),
    ("division-extension-v0.1", "GPU_RULE_PROFILE_VALIDATED", "present", ["URB-002"]),
    (
        "division-extension-v0.1",
        "MARKET_OR_SCENARIO_AVAILABLE",
        "any_present",
        ["MKT-001", "FIN-001"],
    ),
    ("renovation-resale-v0.1", "RESOLVED_PROPERTY_UNIT", "present", ["LAND-002"]),
    ("renovation-resale-v0.1", "RESIDENTIAL_USE_OBSERVED", "present", ["BLD-001"]),
    ("renovation-resale-v0.1", "USABLE_AREA_AVAILABLE", "present", ["REN-002"]),
    ("renovation-resale-v0.1", "MARKET_AVAILABLE", "present", ["MKT-101"]),
    (
        "renovation-resale-v0.1",
        "FINANCIAL_SCENARIO_COMPLETE",
        "all_present",
        ["FIN-101", "FIN-102", "FIN-103", "FIN-104", "FIN-105", "FIN-106"],
    ),
)


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("ALTER TABLE feature.feature_definition DROP CONSTRAINT feature_definition_code")
    op.execute(
        """
        ALTER TABLE feature.feature_definition
        ADD CONSTRAINT feature_definition_code
        CHECK (code ~ '^(LAND|BLD|MKT|REN|URB|RISK|FIN)-[0-9]{3}$')
        """
    )

    op.execute(
        """
        CREATE TABLE scoring.strategy (
            code text PRIMARY KEY,
            name text NOT NULL,
            description text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT strategy_code CHECK (code IN ('division_extension', 'renovation_resale'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_definition (
            id text NOT NULL,
            version integer NOT NULL CHECK (version > 0),
            strategy_code text NOT NULL REFERENCES scoring.strategy(code),
            contract_path text NOT NULL,
            contract_digest char(64) NOT NULL CHECK (contract_digest ~ '^[0-9a-f]{64}$'),
            feature_registry_version integer NOT NULL,
            parameters jsonb NOT NULL,
            publication_eligible boolean NOT NULL,
            meaning text NOT NULL,
            created_by text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, version),
            CONSTRAINT score_definition_id CHECK (id ~ '^[a-z0-9.-]+$'),
            CONSTRAINT score_definition_parameters_object CHECK (jsonb_typeof(parameters) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_definition_component (
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            code text NOT NULL,
            label text NOT NULL,
            weight numeric(8, 7) NOT NULL CHECK (weight > 0 AND weight <= 1),
            display_order integer NOT NULL CHECK (display_order > 0),
            PRIMARY KEY (definition_id, definition_version, code),
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT,
            CONSTRAINT score_definition_component_order UNIQUE (
                definition_id, definition_version, display_order
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_definition_feature (
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            feature_code text NOT NULL,
            feature_version integer NOT NULL,
            component_code text,
            weight numeric(8, 7) NOT NULL CHECK (weight >= 0 AND weight <= 1),
            requirement text NOT NULL CHECK (
                requirement IN ('required', 'optional', 'confidence_only')
            ),
            transformation text NOT NULL CHECK (
                transformation IN ('local_percentile', 'profiled_score', 'identity')
            ),
            direction text NOT NULL CHECK (
                direction IN ('increasing', 'decreasing', 'confidence_only', 'context_only')
            ),
            transformation_parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
            explanation_template text NOT NULL,
            PRIMARY KEY (definition_id, definition_version, feature_code),
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT,
            FOREIGN KEY (feature_code, feature_version)
                REFERENCES feature.feature_definition(code, version) ON DELETE RESTRICT,
            FOREIGN KEY (definition_id, definition_version, component_code)
                REFERENCES scoring.score_definition_component(
                    definition_id, definition_version, code
                ) ON DELETE RESTRICT,
            CONSTRAINT score_definition_feature_component CHECK (
                (component_code IS NULL AND weight = 0)
                OR component_code IS NOT NULL
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_eligibility_rule (
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            code text NOT NULL,
            predicate text NOT NULL CHECK (predicate IN ('present', 'any_present', 'all_present')),
            feature_codes jsonb NOT NULL CHECK (
                jsonb_typeof(feature_codes) = 'array' AND jsonb_array_length(feature_codes) > 0
            ),
            failure_message text NOT NULL,
            PRIMARY KEY (definition_id, definition_version, code),
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.active_score_definition (
            strategy_code text PRIMARY KEY REFERENCES scoring.strategy(code),
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            published_at timestamptz NOT NULL DEFAULT now(),
            published_by text NOT NULL,
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_definition_publication_event (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            strategy_code text NOT NULL REFERENCES scoring.strategy(code),
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            action text NOT NULL CHECK (action IN ('published', 'withdrawn')),
            actor text NOT NULL,
            reason text NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE scoring.estimate_scenario (
            id text PRIMARY KEY,
            strategy_code text NOT NULL REFERENCES scoring.strategy(code),
            assumptions jsonb NOT NULL,
            prudent jsonb NOT NULL,
            central jsonb NOT NULL,
            optimistic jsonb NOT NULL,
            input_digest char(64) NOT NULL CHECK (input_digest ~ '^[0-9a-f]{64}$'),
            transformation_version text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT estimate_scenario_id CHECK (id ~ '^scenario:[a-z0-9_-]+:.+$'),
            CONSTRAINT estimate_scenario_json_objects CHECK (
                jsonb_typeof(assumptions) = 'object'
                AND jsonb_typeof(prudent) = 'object'
                AND jsonb_typeof(central) = 'object'
                AND jsonb_typeof(optimistic) = 'object'
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.opportunity_snapshot (
            id text PRIMARY KEY,
            property_unit_id text NOT NULL
                REFERENCES reference.property_unit(id) ON DELETE RESTRICT,
            strategy_code text NOT NULL REFERENCES scoring.strategy(code),
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            estimate_scenario_id text REFERENCES scoring.estimate_scenario(id) ON DELETE RESTRICT,
            snapshot_at date NOT NULL,
            calculated_at timestamptz NOT NULL DEFAULT now(),
            release_ids jsonb NOT NULL CHECK (
                jsonb_typeof(release_ids) = 'array' AND jsonb_array_length(release_ids) > 0
            ),
            segment_code text NOT NULL,
            eligible boolean NOT NULL,
            eligibility_results jsonb NOT NULL,
            publication_eligible boolean NOT NULL,
            publication_blockers jsonb NOT NULL,
            overall_score numeric(8, 5) CHECK (overall_score IS NULL OR overall_score BETWEEN 0 AND 100),
            score_class text CHECK (
                score_class IS NULL OR score_class IN ('low', 'review', 'interesting', 'high_priority')
            ),
            confidence_score numeric(8, 5) NOT NULL CHECK (confidence_score BETWEEN 0 AND 100),
            confidence_level text NOT NULL CHECK (
                confidence_level IN ('high', 'medium', 'low', 'not_publishable')
            ),
            missing_features jsonb NOT NULL,
            feature_input_digest char(64) NOT NULL CHECK (feature_input_digest ~ '^[0-9a-f]{64}$'),
            baseline_definition_id text NOT NULL,
            baseline_selected boolean NOT NULL,
            baseline_reasons jsonb NOT NULL,
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT,
            CONSTRAINT opportunity_snapshot_id CHECK (id ~ '^opportunity:[a-z0-9_-]+:.+$'),
            CONSTRAINT opportunity_snapshot_score_consistency CHECK (
                (overall_score IS NULL AND score_class IS NULL) OR
                (overall_score IS NOT NULL AND score_class IS NOT NULL)
            ),
            CONSTRAINT opportunity_snapshot_publication_consistency CHECK (
                NOT publication_eligible OR (
                    eligible AND overall_score IS NOT NULL AND confidence_level <> 'not_publishable'
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_component (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            component_code text NOT NULL,
            weight numeric(8, 7) NOT NULL CHECK (weight > 0 AND weight <= 1),
            score numeric(8, 5) NOT NULL CHECK (score BETWEEN 0 AND 100),
            weighted_score numeric(8, 5) NOT NULL CHECK (weighted_score BETWEEN 0 AND 100),
            formula text NOT NULL,
            CONSTRAINT score_component_identity UNIQUE (
                opportunity_snapshot_id, component_code
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.score_evidence (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            feature_code text NOT NULL,
            component_code text,
            direction text NOT NULL CHECK (direction IN ('positive', 'negative', 'neutral')),
            impact numeric(10, 6) NOT NULL,
            raw_value jsonb,
            normalized_value numeric(8, 7) NOT NULL CHECK (normalized_value BETWEEN 0 AND 1),
            comparison text,
            source_observation_ids jsonb NOT NULL,
            source_release_ids jsonb NOT NULL,
            observed_at date,
            quality text NOT NULL CHECK (quality IN ('high', 'medium', 'low', 'unknown')),
            formula text NOT NULL,
            explanation text NOT NULL,
            CONSTRAINT score_evidence_identity UNIQUE (
                opportunity_snapshot_id, feature_code
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.published_opportunity (
            property_unit_id text NOT NULL REFERENCES reference.property_unit(id) ON DELETE RESTRICT,
            strategy_code text NOT NULL REFERENCES scoring.strategy(code),
            opportunity_snapshot_id text NOT NULL UNIQUE
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            published_at timestamptz NOT NULL DEFAULT now(),
            published_by text NOT NULL,
            PRIMARY KEY (property_unit_id, strategy_code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.opportunity_publication_event (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            property_unit_id text NOT NULL REFERENCES reference.property_unit(id),
            strategy_code text NOT NULL REFERENCES scoring.strategy(code),
            opportunity_snapshot_id text NOT NULL
                REFERENCES scoring.opportunity_snapshot(id) ON DELETE RESTRICT,
            action text NOT NULL CHECK (action IN ('published', 'withdrawn', 'rolled_back')),
            actor text NOT NULL,
            reason text NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE scoring.backtest_run (
            id text PRIMARY KEY,
            definition_id text NOT NULL,
            definition_version integer NOT NULL,
            snapshot_at date NOT NULL,
            baseline_definition_id text NOT NULL,
            dataset_release_ids jsonb NOT NULL,
            development_count integer NOT NULL CHECK (development_count >= 0),
            validation_count integer NOT NULL CHECK (validation_count >= 0),
            final_holdout_count integer NOT NULL CHECK (final_holdout_count >= 0),
            status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
            report jsonb,
            started_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz,
            FOREIGN KEY (definition_id, definition_version)
                REFERENCES scoring.score_definition(id, version) ON DELETE RESTRICT,
            CONSTRAINT backtest_run_id CHECK (id ~ '^backtest:.+$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.backtest_metric (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            backtest_run_id text NOT NULL REFERENCES scoring.backtest_run(id) ON DELETE RESTRICT,
            segment_code text NOT NULL,
            metric_code text NOT NULL,
            k integer CHECK (k IS NULL OR k > 0),
            score_value numeric,
            baseline_value numeric,
            lift numeric,
            sample_count integer NOT NULL CHECK (sample_count >= 0),
            CONSTRAINT backtest_metric_identity UNIQUE NULLS NOT DISTINCT (
                backtest_run_id, segment_code, metric_code, k
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE scoring.ablation_result (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            backtest_run_id text NOT NULL REFERENCES scoring.backtest_run(id) ON DELETE RESTRICT,
            removed_feature_codes jsonb NOT NULL,
            segment_code text NOT NULL,
            metric_code text NOT NULL,
            k integer,
            full_score_value numeric,
            ablated_score_value numeric,
            delta numeric,
            CONSTRAINT ablation_result_identity UNIQUE NULLS NOT DISTINCT (
                backtest_run_id, removed_feature_codes, segment_code, metric_code, k
            )
        )
        """
    )

    op.execute(
        """
        CREATE FUNCTION scoring.reject_immutable_change()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        BEGIN
            RAISE EXCEPTION '% is immutable; create a new version or snapshot', TG_TABLE_NAME;
        END
        $function$
        """
    )
    for table in (
        "score_definition",
        "score_definition_component",
        "score_definition_feature",
        "score_eligibility_rule",
        "estimate_scenario",
        "opportunity_snapshot",
        "score_component",
        "score_evidence",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON scoring.{table} "
            "FOR EACH ROW EXECUTE FUNCTION scoring.reject_immutable_change()"
        )

    op.execute(
        """
        CREATE FUNCTION scoring.validate_snapshot_time()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM jsonb_array_elements_text(NEW.release_ids) AS item(release_id)
                  LEFT JOIN meta.dataset_release AS release ON release.id = item.release_id
                 WHERE release.id IS NULL
                    OR COALESCE(release.source_published_on, release.discovered_at::date)
                       > NEW.snapshot_at
            ) THEN
                RAISE EXCEPTION 'Snapshot contains an unknown or post-snapshot dataset release';
            END IF;
            RETURN NEW;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER opportunity_snapshot_time_guard
        BEFORE INSERT ON scoring.opportunity_snapshot
        FOR EACH ROW EXECUTE FUNCTION scoring.validate_snapshot_time()
        """
    )
    op.execute(
        """
        CREATE FUNCTION scoring.validate_evidence_time()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        DECLARE
            target_snapshot scoring.opportunity_snapshot%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT target_snapshot
              FROM scoring.opportunity_snapshot WHERE id = NEW.opportunity_snapshot_id;
            IF NEW.observed_at IS NOT NULL AND NEW.observed_at > target_snapshot.snapshot_at THEN
                RAISE EXCEPTION 'Evidence is newer than its snapshot';
            END IF;
            IF NOT NEW.source_release_ids <@ target_snapshot.release_ids THEN
                RAISE EXCEPTION 'Evidence release is absent from the snapshot release set';
            END IF;
            RETURN NEW;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER score_evidence_time_guard
        BEFORE INSERT ON scoring.score_evidence
        FOR EACH ROW EXECUTE FUNCTION scoring.validate_evidence_time()
        """
    )

    op.execute(
        """
        CREATE FUNCTION scoring.publish_score_definition(
            p_definition_id text, p_definition_version integer, p_actor text, p_reason text
        ) RETURNS void LANGUAGE plpgsql AS $function$
        DECLARE
            selected scoring.score_definition%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT selected FROM scoring.score_definition
             WHERE id = p_definition_id AND version = p_definition_version;
            IF NOT selected.publication_eligible THEN
                RAISE EXCEPTION 'Definition requires profiling and is not publication eligible';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM scoring.score_eligibility_rule
                 WHERE definition_id = selected.id AND definition_version = selected.version
            ) THEN
                RAISE EXCEPTION 'Definition has no eligibility rules';
            END IF;
            IF ABS((
                SELECT COALESCE(sum(weight), 0)
                  FROM scoring.score_definition_component
                 WHERE definition_id = selected.id AND definition_version = selected.version
            ) - 1) > 0.000001 THEN
                RAISE EXCEPTION 'Definition component weights do not sum to one';
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM scoring.score_definition_component AS component
                 WHERE component.definition_id = selected.id
                   AND component.definition_version = selected.version
                   AND ABS((
                       SELECT COALESCE(sum(feature.weight), 0)
                         FROM scoring.score_definition_feature AS feature
                        WHERE feature.definition_id = component.definition_id
                          AND feature.definition_version = component.definition_version
                          AND feature.component_code = component.code
                   ) - 1) > 0.000001
            ) THEN
                RAISE EXCEPTION 'A component feature weight set does not sum to one';
            END IF;
            INSERT INTO scoring.active_score_definition (
                strategy_code, definition_id, definition_version, published_by
            ) VALUES (
                selected.strategy_code, selected.id, selected.version, p_actor
            ) ON CONFLICT (strategy_code) DO UPDATE SET
                definition_id = EXCLUDED.definition_id,
                definition_version = EXCLUDED.definition_version,
                published_at = clock_timestamp(),
                published_by = EXCLUDED.published_by;
            INSERT INTO scoring.score_definition_publication_event (
                strategy_code, definition_id, definition_version, action, actor, reason
            ) VALUES (
                selected.strategy_code, selected.id, selected.version,
                'published', p_actor, p_reason
            );
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION scoring.publish_opportunity_snapshot(
            p_snapshot_id text, p_actor text, p_reason text
        ) RETURNS void LANGUAGE plpgsql AS $function$
        DECLARE
            selected scoring.opportunity_snapshot%ROWTYPE;
            active_definition scoring.active_score_definition%ROWTYPE;
            previous_snapshot_id text;
            previous_calculated_at timestamptz;
        BEGIN
            SELECT * INTO STRICT selected FROM scoring.opportunity_snapshot
             WHERE id = p_snapshot_id;
            IF NOT selected.publication_eligible THEN
                RAISE EXCEPTION 'Snapshot is not publication eligible';
            END IF;
            SELECT * INTO STRICT active_definition FROM scoring.active_score_definition
             WHERE strategy_code = selected.strategy_code;
            IF active_definition.definition_id <> selected.definition_id
               OR active_definition.definition_version <> selected.definition_version THEN
                RAISE EXCEPTION 'Snapshot does not use the active score definition';
            END IF;
            IF EXISTS (
                SELECT 1
                  FROM jsonb_array_elements_text(selected.release_ids) AS item(release_id)
                  JOIN meta.dataset_release AS release ON release.id = item.release_id
                 WHERE release.acceptance_status <> 'accepted'
            ) THEN
                RAISE EXCEPTION 'Snapshot uses a dataset release that is not accepted';
            END IF;
            IF (
                SELECT count(*) FROM scoring.score_component
                 WHERE opportunity_snapshot_id = selected.id
            ) <> (
                SELECT count(*) FROM scoring.score_definition_component
                 WHERE definition_id = selected.definition_id
                   AND definition_version = selected.definition_version
            ) THEN
                RAISE EXCEPTION 'Snapshot component set is incomplete';
            END IF;
            IF EXISTS (
                SELECT 1 FROM scoring.score_definition_feature AS feature
                 WHERE feature.definition_id = selected.definition_id
                   AND feature.definition_version = selected.definition_version
                   AND NOT EXISTS (
                       SELECT 1 FROM scoring.score_evidence AS evidence
                        WHERE evidence.opportunity_snapshot_id = selected.id
                          AND evidence.feature_code = feature.feature_code
                   )
            ) THEN
                RAISE EXCEPTION 'Snapshot evidence set is incomplete';
            END IF;
            SELECT published.opportunity_snapshot_id, previous.calculated_at
              INTO previous_snapshot_id, previous_calculated_at
              FROM scoring.published_opportunity AS published
              JOIN scoring.opportunity_snapshot AS previous
                ON previous.id = published.opportunity_snapshot_id
             WHERE published.property_unit_id = selected.property_unit_id
               AND published.strategy_code = selected.strategy_code
             FOR UPDATE OF published;
            INSERT INTO scoring.published_opportunity (
                property_unit_id, strategy_code, opportunity_snapshot_id, published_by
            ) VALUES (
                selected.property_unit_id, selected.strategy_code, selected.id, p_actor
            ) ON CONFLICT (property_unit_id, strategy_code) DO UPDATE SET
                opportunity_snapshot_id = EXCLUDED.opportunity_snapshot_id,
                published_at = clock_timestamp(),
                published_by = EXCLUDED.published_by;
            INSERT INTO scoring.opportunity_publication_event (
                property_unit_id, strategy_code, opportunity_snapshot_id,
                action, actor, reason
            ) VALUES (
                selected.property_unit_id, selected.strategy_code, selected.id,
                CASE
                    WHEN previous_snapshot_id IS NOT NULL
                     AND selected.calculated_at < previous_calculated_at THEN 'rolled_back'
                    ELSE 'published'
                END,
                p_actor, p_reason
            );
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE FUNCTION scoring.withdraw_opportunity_snapshot(
            p_snapshot_id text, p_actor text, p_reason text
        ) RETURNS void LANGUAGE plpgsql AS $function$
        DECLARE
            selected scoring.opportunity_snapshot%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT selected FROM scoring.opportunity_snapshot
             WHERE id = p_snapshot_id;
            DELETE FROM scoring.published_opportunity
             WHERE property_unit_id = selected.property_unit_id
               AND strategy_code = selected.strategy_code
               AND opportunity_snapshot_id = selected.id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Snapshot is not currently published';
            END IF;
            INSERT INTO scoring.opportunity_publication_event (
                property_unit_id, strategy_code, opportunity_snapshot_id,
                action, actor, reason
            ) VALUES (
                selected.property_unit_id, selected.strategy_code, selected.id,
                'withdrawn', p_actor, p_reason
            );
        END
        $function$
        """
    )
    for function in (
        "scoring.publish_score_definition(text,integer,text,text)",
        "scoring.publish_opportunity_snapshot(text,text,text)",
        "scoring.withdraw_opportunity_snapshot(text,text,text)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {function} TO pipeline_rw")

    op.execute(
        """
        INSERT INTO scoring.strategy (code, name, description) VALUES
            ('division_extension', 'Division / extension',
             'Classement du potentiel apparent de division ou extension.'),
            ('renovation_resale', 'Rénovation / revente',
             'Classement du potentiel de rénovation et revente selon un scénario explicite.')
        """
    )

    feature_definition = sa.table(
        "feature_definition",
        sa.column("code", sa.Text),
        sa.column("version", sa.Integer),
        sa.column("name", sa.Text),
        sa.column("strategy", sa.Text),
        sa.column("datasets", JSONB),
        sa.column("formula", sa.Text),
        sa.column("transformation_version", sa.Text),
        sa.column("value_type", sa.Text),
        sa.column("unit", sa.Text),
        sa.column("valid_min", sa.Numeric),
        sa.column("valid_max", sa.Numeric),
        sa.column("out_of_range_policy", sa.Text),
        sa.column("requirement", sa.Text),
        sa.column("missing_value_policy", sa.Text),
        sa.column("description", sa.Text),
        schema="feature",
    )
    op.bulk_insert(
        feature_definition,
        [
            {
                "code": code,
                "version": 1,
                "name": name,
                "strategy": strategy,
                "datasets": ["FIN", "scenario"],
                "formula": "See contracts/scoring/feature-registry-v1.json",
                "transformation_version": "financial-scenarios@1",
                "value_type": value_type,
                "unit": unit,
                "valid_min": None,
                "valid_max": None,
                "out_of_range_policy": "flag",
                "requirement": "required",
                "missing_value_policy": "Missing financial scenario blocks publication",
                "description": "Versioned financial scenario feature",
            }
            for code, name, strategy, value_type, unit in FINANCIAL_FEATURES
        ],
    )

    score_definition = sa.table(
        "score_definition",
        sa.column("id", sa.Text),
        sa.column("version", sa.Integer),
        sa.column("strategy_code", sa.Text),
        sa.column("contract_path", sa.Text),
        sa.column("contract_digest", sa.Text),
        sa.column("feature_registry_version", sa.Integer),
        sa.column("parameters", JSONB),
        sa.column("publication_eligible", sa.Boolean),
        sa.column("meaning", sa.Text),
        sa.column("created_by", sa.Text),
        schema="scoring",
    )
    op.bulk_insert(
        score_definition,
        [
            {
                **definition,
                "feature_registry_version": 1,
                "meaning": "Relative ranking index; never a calibrated probability",
                "created_by": "migration:20260807_0012",
            }
            for definition in SCORE_DEFINITIONS
        ],
    )

    component = sa.table(
        "score_definition_component",
        sa.column("definition_id", sa.Text),
        sa.column("definition_version", sa.Integer),
        sa.column("code", sa.Text),
        sa.column("label", sa.Text),
        sa.column("weight", sa.Numeric),
        sa.column("display_order", sa.Integer),
        schema="scoring",
    )
    op.bulk_insert(
        component,
        [
            {
                "definition_id": definition_id,
                "definition_version": definition_version,
                "code": code,
                "label": label,
                "weight": weight,
                "display_order": display_order,
            }
            for definition_id, definition_version, code, label, weight, display_order in COMPONENTS
        ],
    )

    score_feature = sa.table(
        "score_definition_feature",
        sa.column("definition_id", sa.Text),
        sa.column("definition_version", sa.Integer),
        sa.column("feature_code", sa.Text),
        sa.column("feature_version", sa.Integer),
        sa.column("component_code", sa.Text),
        sa.column("weight", sa.Numeric),
        sa.column("requirement", sa.Text),
        sa.column("transformation", sa.Text),
        sa.column("direction", sa.Text),
        sa.column("transformation_parameters", JSONB),
        sa.column("explanation_template", sa.Text),
        schema="scoring",
    )
    op.bulk_insert(
        score_feature,
        [
            {
                "definition_id": definition_id,
                "definition_version": 1,
                "feature_code": feature_code,
                "feature_version": 1,
                "component_code": component_code,
                "weight": weight,
                "requirement": requirement,
                "transformation": transformation,
                "direction": direction,
                "transformation_parameters": {
                    "parameters": "profiling_required",
                    "contract_is_authoritative": True,
                },
                "explanation_template": (
                    "Controlled template from the versioned score definition contract"
                ),
            }
            for (
                definition_id,
                feature_code,
                component_code,
                weight,
                requirement,
                transformation,
                direction,
            ) in SCORE_RULES
        ],
    )

    eligibility_rule = sa.table(
        "score_eligibility_rule",
        sa.column("definition_id", sa.Text),
        sa.column("definition_version", sa.Integer),
        sa.column("code", sa.Text),
        sa.column("predicate", sa.Text),
        sa.column("feature_codes", JSONB),
        sa.column("failure_message", sa.Text),
        schema="scoring",
    )
    op.bulk_insert(
        eligibility_rule,
        [
            {
                "definition_id": definition_id,
                "definition_version": 1,
                "code": code,
                "predicate": predicate,
                "feature_codes": feature_codes,
                "failure_message": f"Eligibility rule failed: {code}",
            }
            for definition_id, code, predicate, feature_codes in ELIGIBILITY_RULES
        ],
    )

    op.execute(
        "CREATE INDEX opportunity_snapshot_rank_idx ON scoring.opportunity_snapshot "
        "(strategy_code, definition_id, definition_version, overall_score DESC)"
    )
    op.execute(
        "CREATE INDEX opportunity_snapshot_history_idx ON scoring.opportunity_snapshot "
        "(property_unit_id, strategy_code, calculated_at DESC)"
    )
    op.execute(
        "CREATE INDEX opportunity_snapshot_confidence_idx ON scoring.opportunity_snapshot "
        "(strategy_code, confidence_level, overall_score DESC)"
    )
    op.execute(
        "CREATE INDEX score_evidence_snapshot_idx ON scoring.score_evidence "
        "(opportunity_snapshot_id, abs(impact) DESC)"
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    for function in (
        "scoring.withdraw_opportunity_snapshot(text,text,text)",
        "scoring.publish_opportunity_snapshot(text,text,text)",
        "scoring.publish_score_definition(text,integer,text,text)",
        "scoring.validate_evidence_time()",
        "scoring.validate_snapshot_time()",
        "scoring.reject_immutable_change()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function} CASCADE")
    for table in reversed(SCORING_TABLES):
        op.execute(f"DROP TABLE scoring.{table}")
    op.execute("DELETE FROM feature.feature_definition WHERE code LIKE 'FIN-%' AND version = 1")
    op.execute("ALTER TABLE feature.feature_definition DROP CONSTRAINT feature_definition_code")
    op.execute(
        "ALTER TABLE feature.feature_definition ADD CONSTRAINT feature_definition_code "
        "CHECK (code ~ '^(LAND|BLD|MKT|REN|URB|RISK)-[0-9]{3}$')"
    )
    op.execute("RESET ROLE")
