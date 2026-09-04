import pytest

from immo_pipelines.pilot import (
    BRITTANY_DATASETS,
    BRITTANY_DEPARTMENTS,
    AcceptanceEvidence,
    BlindCandidate,
    CoverageObservation,
    build_acceptance_matrix,
    build_blind_protocol,
    compare_coverage,
    evaluate_pilot,
    rank_stability,
)


def test_acceptance_matrix_never_hides_a_missing_department() -> None:
    evidence = [
        AcceptanceEvidence(dataset, department, "accepted")
        for department in BRITTANY_DEPARTMENTS
        for dataset in BRITTANY_DATASETS
        if department != "56"
    ]
    matrix = build_acceptance_matrix(evidence)

    assert matrix["covered"] is False
    assert matrix["territories"]["35"]["covered"] is True
    assert matrix["territories"]["56"]["blocking_datasets"] == list(BRITTANY_DATASETS)


def test_blind_protocol_excludes_development_and_is_reproducible() -> None:
    candidates = [
        BlindCandidate("dev", "35", "metropolitan", 100, True, "development"),
        BlindCandidate("a", "35", "metropolitan", 90, True, "validation"),
        BlindCandidate("b", "35", "metropolitan", 80, True, "final"),
        BlindCandidate("c", "35", "metropolitan", 70, False, "validation"),
    ]
    first = build_blind_protocol(candidates, per_arm=2, seed="pilot-1", double_review_ratio=0.5)
    second = build_blind_protocol(candidates, per_arm=2, seed="pilot-1", double_review_ratio=0.5)

    assert first == second
    assert all(item["candidate_id"] != "dev" for item in first)
    assert {item["protocol_arm"] for item in first} == {"top_score", "baseline", "random"}
    assert sum(bool(item["double_review"]) for item in first) == round(len(first) * 0.5)


def test_coverage_regression_and_rank_stability_are_segmented() -> None:
    previous = [CoverageObservation("22", "commune", "22001", "rural", 100, 98)]
    current = [CoverageObservation("22", "commune", "22001", "rural", 100, 90)]

    regressions = compare_coverage(previous, current, maximum_drop=0.02)

    assert regressions[0]["department"] == "22"
    assert regressions[0]["drop"] == pytest.approx(0.08)
    assert rank_stability(["a", "b", "c"], ["a", "c", "d"], k=3) == 0.5


def test_pilot_decision_refuses_to_infer_missing_business_evidence() -> None:
    result = evaluate_pilot(
        acceptance={"covered": False},
        hypothesis_results={code: None for code in ("H1", "H2", "H3", "H4", "H5")},
        professional_count=0,
        committed_count=0,
        top20_precision=None,
        baseline20_precision=None,
        minimum_lift=1.2,
    )

    assert result["decision_ready"] is False
    assert result["recommended_decision"] is None
    assert "regional_data_not_covered" in result["blockers"]
