from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import cast

import pytest

from immo_pipelines.scoring.engine import (
    BacktestCandidate,
    BaselineDefinition,
    ConfidenceInputs,
    EligibilityRule,
    FeatureInput,
    FeatureRule,
    FinancialInputs,
    ScoreDefinition,
    ValueRange,
    ablate_features,
    baseline_select,
    compute_financial_scenarios,
    evaluate_backtest,
    load_score_definition,
    score_opportunity,
)

SNAPSHOT = date(2026, 1, 1)
CONFIDENCE = ConfidenceInputs(0.9, 0.8, 0.7, 0.6)


def simple_definition(*, publication_eligible: bool = True) -> ScoreDefinition:
    return ScoreDefinition(
        definition_id="golden-v1",
        version=1,
        strategy="division_extension",
        status="active",
        publication_eligible=publication_eligible,
        neutral_value=0.5,
        component_weights={"component": 1.0},
        rules=(
            FeatureRule(
                "POS-001",
                "component",
                0.5,
                "required",
                "local_percentile",
                "increasing",
                "Valeur {value}, percentile {comparison}.",
            ),
            FeatureRule(
                "NEG-001",
                "component",
                0.25,
                "optional",
                "local_percentile",
                "decreasing",
                "Valeur {value}, niveau {normalized}.",
            ),
            FeatureRule(
                "CONF-001",
                "component",
                0.25,
                "confidence_only",
                "identity",
                "confidence_only",
                "Confiance {value}.",
            ),
        ),
        eligibility=(EligibilityRule("POS_PRESENT", "present", ("POS-001",)),),
        confidence_weights={
            "match_quality": 0.25,
            "critical_coverage": 0.25,
            "freshness": 0.25,
            "source_consistency": 0.125,
            "comparable_quality": 0.125,
        },
        forbidden_feature_prefixes=("VACANCY-", "OWNER-"),
    )


def test_versioned_score_contracts_load_and_keep_spec_weights() -> None:
    root = Path(__file__).parents[2] / "contracts" / "scoring"
    division = load_score_definition(root / "division-extension-v1.json")
    renovation = load_score_definition(root / "renovation-resale-v1.json")

    assert division.component_weights == {
        "land_capacity": 0.4,
        "preliminary_feasibility": 0.25,
        "economic_attractiveness": 0.25,
        "risk_complexity": 0.1,
    }
    assert renovation.component_weights["scenario_economics"] == 0.4
    assert not division.publication_eligible
    assert not renovation.publication_eligible


def test_golden_formula_is_bounded_explainable_and_deterministic() -> None:
    features = [
        FeatureInput(
            "POS-001",
            80,
            local_percentile=0.8,
            source_ids=("source:positive",),
            release_ids=("DS-01:release",),
            observed_at=date(2025, 1, 1),
            confidence=0.9,
        ),
        FeatureInput("NEG-001", 20, local_percentile=0.8, confidence=0.7),
        FeatureInput("CONF-001", 0.95, confidence=0.95),
    ]
    first = score_opportunity(
        simple_definition(),
        features,
        snapshot_at=SNAPSHOT,
        release_ids=("DS-01:release",),
        confidence_inputs=CONFIDENCE,
    )
    second = score_opportunity(
        simple_definition(),
        list(reversed(features)),
        snapshot_at=SNAPSHOT,
        release_ids=("DS-01:release",),
        confidence_inputs=CONFIDENCE,
    )

    # 0.8*0.5 + (1-0.8)*0.25 + neutral(0.5)*0.25 = 0.575
    assert first.overall_score == pytest.approx(57.5)
    assert first.input_digest == second.input_digest
    assert first.overall_score == second.overall_score
    assert first.publishable
    assert {item.direction for item in first.evidence} == {"positive", "negative", "neutral"}
    assert first.evidence[0].source_ids == ("source:positive",)


def test_required_missing_blocks_publication_but_optional_missing_is_neutral() -> None:
    optional_missing = score_opportunity(
        simple_definition(),
        [
            FeatureInput("POS-001", 1, local_percentile=0.8),
            FeatureInput("NEG-001", missing_reason="source_value_missing"),
            FeatureInput("CONF-001", 0.8),
        ],
        snapshot_at=SNAPSHOT,
        release_ids=("release",),
        confidence_inputs=CONFIDENCE,
    )
    assert optional_missing.overall_score == pytest.approx(65)
    assert optional_missing.publishable
    assert optional_missing.evidence[1].direction == "neutral"

    required_missing = score_opportunity(
        simple_definition(),
        [
            FeatureInput("POS-001", missing_reason="source_value_missing"),
            FeatureInput("NEG-001", 1, local_percentile=0.2),
            FeatureInput("CONF-001", 0.8),
        ],
        snapshot_at=SNAPSHOT,
        release_ids=("release",),
        confidence_inputs=CONFIDENCE,
    )
    assert not required_missing.eligible
    assert not required_missing.publishable
    assert "required:POS-001" in required_missing.publication_blockers
    assert required_missing.confidence_level == "not_publishable"


def test_confidence_feature_never_changes_ranking_score() -> None:
    base = [
        FeatureInput("POS-001", 1, local_percentile=0.6),
        FeatureInput("NEG-001", 1, local_percentile=0.4),
        FeatureInput("CONF-001", 0.1),
    ]
    low = score_opportunity(
        simple_definition(),
        base,
        snapshot_at=SNAPSHOT,
        release_ids=("release",),
        confidence_inputs=ConfidenceInputs(0.2, 0.2, 0.2, 0.2),
    )
    high = score_opportunity(
        simple_definition(),
        [*base[:2], replace(base[2], value=0.99)],
        snapshot_at=SNAPSHOT,
        release_ids=("release",),
        confidence_inputs=ConfidenceInputs(1, 1, 1, 1),
    )
    assert low.overall_score == high.overall_score
    assert low.confidence_score < high.confidence_score


def test_duplicate_forbidden_and_future_inputs_are_rejected() -> None:
    definition = simple_definition()
    duplicate = FeatureInput("POS-001", 1, local_percentile=0.5)
    with pytest.raises(ValueError, match="double count"):
        score_opportunity(
            definition,
            [duplicate, duplicate],
            snapshot_at=SNAPSHOT,
            release_ids=(),
            confidence_inputs=CONFIDENCE,
        )
    with pytest.raises(ValueError, match="Forbidden"):
        score_opportunity(
            definition,
            [FeatureInput("VACANCY-001", 1)],
            snapshot_at=SNAPSHOT,
            release_ids=(),
            confidence_inputs=CONFIDENCE,
        )
    with pytest.raises(ValueError, match="Post-snapshot"):
        score_opportunity(
            definition,
            [FeatureInput("POS-001", 1, local_percentile=0.5, observed_at=date(2027, 1, 1))],
            snapshot_at=SNAPSHOT,
            release_ids=(),
            confidence_inputs=CONFIDENCE,
        )


def test_financial_scenarios_are_ordered_and_use_full_costs() -> None:
    scenarios = compute_financial_scenarios(
        FinancialInputs(
            purchase=ValueRange(180_000, 190_000, 200_000),
            works=ValueRange(40_000, 50_000, 60_000),
            resale=ValueRange(280_000, 300_000, 320_000),
            fees=ValueRange(12_000, 13_000, 14_000),
            financing=ValueRange(5_000, 6_000, 7_000),
            holding=ValueRange(3_000, 4_000, 5_000),
            target_return_on_cost=0.2,
        )
    )
    prudent, central, optimistic = scenarios
    assert central.total_cost_eur == 263_000
    assert central.net_margin_eur == 37_000
    assert central.return_on_cost == pytest.approx(37_000 / 263_000)
    assert prudent.net_margin_eur < central.net_margin_eur < optimistic.net_margin_eur
    assert central.break_even_purchase_price_eur == pytest.approx(177_000)


def test_ablation_reports_delta_without_hiding_required_feature_failure() -> None:
    features = [
        FeatureInput("POS-001", 1, local_percentile=0.8),
        FeatureInput("NEG-001", 1, local_percentile=0.8),
        FeatureInput("CONF-001", 0.8),
    ]
    optional = ablate_features(
        simple_definition(),
        features,
        removed_feature_codes=("NEG-001",),
        snapshot_at=SNAPSHOT,
        release_ids=("release",),
        confidence_inputs=CONFIDENCE,
    )
    assert optional.full_score == pytest.approx(57.5)
    assert optional.ablated_score == pytest.approx(65)
    assert optional.score_delta == pytest.approx(7.5)

    required = ablate_features(
        simple_definition(),
        features,
        removed_feature_codes=("POS-001",),
        snapshot_at=SNAPSHOT,
        release_ids=("release",),
        confidence_inputs=CONFIDENCE,
    )
    assert not required.ablated_publishable
    assert "required:POS-001" in required.ablated_blockers


def test_baseline_and_backtest_report_unfavorable_results_by_segment() -> None:
    selected, reasons = baseline_select(
        BaselineDefinition(
            "baseline-profiled-v1",
            "division_extension",
            minimum_parcel_area_m2=500,
            maximum_footprint_ratio=0.4,
        ),
        {
            "LAND-001": FeatureInput("LAND-001", 450),
            "LAND-003": FeatureInput("LAND-003", 0.2),
        },
    )
    assert not selected
    assert reasons == ("below_minimum_parcel_area",)

    candidates = [
        BacktestCandidate("a", "urban", 90, False, False, "validation"),
        BacktestCandidate("b", "urban", 80, True, True, "validation"),
        BacktestCandidate("c", "rural", 70, True, True, "final"),
        BacktestCandidate("training", "littoral", 100, True, True, "development"),
    ]
    report = evaluate_backtest(candidates, ks=(2,))
    assert report["development_candidates_excluded"] == 1
    assert report["metrics"] == {
        "precision_at_2": 0.5,
        "baseline_precision_at_2": 1.0,
        "lift_at_2": 0.5,
    }
    segments = cast(dict[str, dict[str, object]], report["segments"])
    assert segments["littoral"]["count"] == 0
