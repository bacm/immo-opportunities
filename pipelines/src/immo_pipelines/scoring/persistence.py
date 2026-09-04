from dataclasses import asdict, dataclass
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from immo_pipelines.scoring.engine import FinancialInputs, FinancialScenario, ScoreResult


@dataclass(frozen=True, slots=True)
class SnapshotPersistenceOutcome:
    snapshot_id: str
    skipped_as_identical: bool


def persist_estimate_scenario(
    connection: Connection[Any],
    *,
    scenario_id: str,
    strategy_code: str,
    inputs: FinancialInputs,
    scenarios: tuple[FinancialScenario, ...],
    input_digest: str,
) -> None:
    by_name = {scenario.name: asdict(scenario) for scenario in scenarios}
    connection.execute("SET LOCAL ROLE pipeline_rw")
    connection.execute(
        """
        INSERT INTO scoring.estimate_scenario (
            id, strategy_code, assumptions, prudent, central, optimistic,
            input_digest, transformation_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'financial-scenarios@1')
        ON CONFLICT (id) DO NOTHING
        """,
        (
            scenario_id,
            strategy_code,
            Jsonb(asdict(inputs)),
            Jsonb(by_name["prudent"]),
            Jsonb(by_name["central"]),
            Jsonb(by_name["optimistic"]),
            input_digest,
        ),
    )


def persist_score_snapshot(
    connection: Connection[Any],
    *,
    snapshot_id: str,
    property_unit_id: str,
    result: ScoreResult,
    release_ids: tuple[str, ...],
    segment_code: str,
    baseline_definition_id: str,
    baseline_selected: bool,
    baseline_reasons: tuple[str, ...],
    estimate_scenario_id: str | None,
) -> SnapshotPersistenceOutcome:
    existing = connection.execute(
        """
        SELECT feature_input_digest
          FROM scoring.opportunity_snapshot WHERE id = %s
        """,
        (snapshot_id,),
    ).fetchone()
    if existing is not None:
        if str(existing[0]) != result.input_digest:
            raise ValueError("Snapshot id already exists with different immutable inputs")
        return SnapshotPersistenceOutcome(snapshot_id, True)

    connection.execute("SET LOCAL ROLE pipeline_rw")
    connection.execute(
        """
        INSERT INTO scoring.opportunity_snapshot (
            id, property_unit_id, strategy_code, definition_id, definition_version,
            estimate_scenario_id, snapshot_at, release_ids, segment_code,
            eligible, eligibility_results, publication_eligible, publication_blockers,
            overall_score, score_class, confidence_score, confidence_level,
            missing_features, feature_input_digest,
            baseline_definition_id, baseline_selected, baseline_reasons
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            snapshot_id,
            property_unit_id,
            result.strategy,
            result.definition_id,
            result.definition_version,
            estimate_scenario_id,
            result.snapshot_at,
            Jsonb(list(release_ids)),
            segment_code,
            result.eligible,
            Jsonb([{"code": failure, "passed": False} for failure in result.eligibility_failures]),
            result.publishable,
            Jsonb(list(result.publication_blockers)),
            result.overall_score,
            result.score_class,
            result.confidence_score,
            result.confidence_level,
            Jsonb(list(result.missing_features)),
            result.input_digest,
            baseline_definition_id,
            baseline_selected,
            Jsonb(list(baseline_reasons)),
        ),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO scoring.score_component (
                opportunity_snapshot_id, component_code, weight,
                score, weighted_score, formula
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    snapshot_id,
                    component.code,
                    component.weight,
                    component.score,
                    component.weighted_score,
                    "fixed component and feature weights from score definition",
                )
                for component in result.components
            ],
        )
        cursor.executemany(
            """
            INSERT INTO scoring.score_evidence (
                opportunity_snapshot_id, feature_code, component_code,
                direction, impact, raw_value, normalized_value, comparison,
                source_observation_ids, source_release_ids, observed_at,
                quality, formula, explanation
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            [
                (
                    snapshot_id,
                    evidence.feature_code,
                    evidence.component_code,
                    evidence.direction,
                    evidence.impact,
                    Jsonb(evidence.value),
                    evidence.normalized_value,
                    evidence.comparison,
                    Jsonb(list(evidence.source_ids)),
                    Jsonb(list(evidence.release_ids)),
                    evidence.observed_at,
                    evidence.quality,
                    evidence.formula,
                    evidence.explanation,
                )
                for evidence in result.evidence
            ],
        )
    return SnapshotPersistenceOutcome(snapshot_id, False)


def publish_snapshot(
    connection: Connection[Any], *, snapshot_id: str, actor: str, reason: str
) -> None:
    connection.execute(
        "SELECT scoring.publish_opportunity_snapshot(%s, %s, %s)",
        (snapshot_id, actor, reason),
    )
