from dataclasses import replace
from datetime import date

import pytest
from shapely.geometry import Point, box

from immo_pipelines.market_data.features import (
    BuildingObservation,
    EnergyAssessment,
    RiskObservation,
    Transaction,
    TransactionProperty,
    UrbanConstraint,
    UrbanDocument,
    UrbanZone,
    compute_market_features,
    compute_renovation_features,
    compute_risk_features,
    compute_urban_features,
    select_comparables,
    select_energy_assessment,
)

SNAPSHOT = date(2026, 1, 1)


def transaction(
    source_id: str,
    mutation_date: date,
    price: float,
    *,
    distance: float = 500,
    segment: str = "rennes-urban",
    properties: tuple[TransactionProperty, ...] | None = None,
    complex_: bool = False,
) -> Transaction:
    return Transaction(
        source_id,
        mutation_date,
        price,
        segment,
        distance,
        properties or (TransactionProperty(f"{source_id}:house", "house", 100),),
        complex_,
        "DS-06:2025-10-35",
    )


def test_comparables_explain_inclusion_and_all_material_exclusions() -> None:
    transactions = [
        transaction("kept", date(2025, 6, 1), 250_000),
        transaction("future", date(2026, 2, 1), 260_000),
        transaction("rural", date(2025, 6, 1), 180_000, segment="rural"),
        transaction(
            "complex",
            date(2025, 6, 1),
            500_000,
            complex_=True,
            properties=(
                TransactionProperty("complex:house", "house", 100),
                TransactionProperty("complex:land", "land", 500),
            ),
        ),
    ]
    decisions = select_comparables(
        transactions,
        snapshot_at=SNAPSHOT,
        target_segment="rennes-urban",
        target_property_type="house",
        target_surface_m2=100,
    )

    assert decisions[0].included
    assert decisions[0].normalized_price_m2 == pytest.approx(2_500)
    reasons = {item.transaction_id: item.reason for item in decisions}
    assert reasons["future"] == "after_snapshot"
    assert reasons["rural"] == "segment_mismatch"
    assert any(item.reason == "complex_mutation_not_decomposable" for item in decisions)


def test_complex_mutation_is_usable_only_with_a_sourced_price_allocation() -> None:
    properties = (
        TransactionProperty("house", "house", 100, allocated_price_eur=220_000),
        TransactionProperty("land", "land", 500, allocated_price_eur=80_000),
    )
    decisions = select_comparables(
        [transaction("allocated", date(2025, 1, 1), 300_000, properties=properties, complex_=True)],
        snapshot_at=SNAPSHOT,
        target_segment="rennes-urban",
        target_property_type="house",
        target_surface_m2=100,
    )

    assert decisions[0].included
    assert decisions[0].normalized_price_m2 == pytest.approx(2_200)


def test_market_features_preserve_no_coverage_and_block_temporal_leakage() -> None:
    decisions = select_comparables(
        [transaction("kept", date(2025, 1, 1), 200_000)],
        snapshot_at=SNAPSHOT,
        target_segment="rennes-urban",
        target_property_type="house",
        target_surface_m2=100,
    )
    unavailable = compute_market_features(
        decisions,
        strategy="renovation_resale",
        snapshot_at=SNAPSHOT,
        source_accepted=False,
    )
    assert unavailable["MKT-102"].missing_reason == "source_not_accepted"

    leaked = [replace(decisions[0], transaction_date=date(2027, 1, 1))]
    with pytest.raises(ValueError, match="post-snapshot"):
        compute_market_features(
            leaked,
            strategy="renovation_resale",
            snapshot_at=SNAPSHOT,
            source_accepted=True,
        )


def test_multiple_address_dpes_stay_ambiguous_and_absence_is_neutral() -> None:
    assessments = [
        EnergyAssessment("dpe-1", date(2025, 1, 1), "F", 350, True, address_id="a"),
        EnergyAssessment("dpe-2", date(2025, 2, 1), "C", 130, True, address_id="a"),
        EnergyAssessment(
            "simulation", date(2025, 3, 1), "G", 500, True, simulated=True, building_id="b"
        ),
    ]
    selection = select_energy_assessment(
        assessments, building_id="b", address_ids={"a"}, snapshot_at=SNAPSHOT
    )
    assert selection.assessment is None
    assert selection.missing_reason == "ambiguous_match"

    features = compute_renovation_features(
        [], selection, snapshot_at=SNAPSHOT, dpe_source_accepted=True
    )
    assert features["REN-004"].numeric_value is None
    assert features["REN-004"].missing_reason == "ambiguous_match"


def test_latest_direct_deposited_dpe_wins_and_predictions_are_excluded() -> None:
    selection = select_energy_assessment(
        [
            EnergyAssessment(
                "old", date(2024, 1, 1), "E", 280, True, building_id="b", match_confidence=1
            ),
            EnergyAssessment(
                "latest",
                date(2025, 6, 1),
                "D",
                210,
                True,
                building_id="b",
                match_confidence=0.98,
                envelope={"wall_insulation": "partial"},
            ),
        ],
        building_id="b",
        address_ids=set(),
        snapshot_at=SNAPSHOT,
    )
    features = compute_renovation_features(
        [BuildingObservation("DS-04:b", "1949-1974", 95, 6, 2, priority=10, confidence=0.9)],
        selection,
        snapshot_at=SNAPSHOT,
        dpe_source_accepted=True,
    )

    assert features["REN-004"].text_value == "D"
    assert features["REN-005"].numeric_value == 210
    assert features["REN-008"].numeric_value == pytest.approx(0.98)
    assert features["REN-003"].text_value == "consistent"


def test_gpu_ignores_expired_document_and_requires_validated_complete_rules() -> None:
    current = UrbanDocument(
        "gpu:current", "2025", date(2025, 1, 1), date(2025, 2, 1), None, "opposable"
    )
    expired = UrbanDocument(
        "gpu:old", "2020", date(2020, 1, 1), date(2020, 1, 1), date(2024, 12, 31), "opposable"
    )
    unit = box(0, 0, 10, 10)
    features = compute_urban_features(
        unit,
        [
            UrbanZone("old-U", expired, "U-old", unit),
            UrbanZone(
                "new-U",
                current,
                "U",
                unit,
                {"max_footprint_ratio": 0.6},
                True,
                ("max_footprint_ratio",),
                ("max_footprint_ratio",),
            ),
        ],
        [UrbanConstraint("constraint", current, "heritage", box(0, 0, 2, 2))],
        snapshot_at=SNAPSHOT,
        source_accepted=True,
        existing_footprint_m2=20,
    )

    assert features["URB-001"].text_value == "U"
    assert features["URB-004"].numeric_value == pytest.approx(40)
    assert features["URB-003"].json_value == {
        "count": 1,
        "overlap_m2_by_type": {"heritage": 4.0},
    }


def test_overlapping_gpu_zones_with_no_representative_winner_are_ambiguous() -> None:
    document = UrbanDocument("gpu", "1", date(2025, 1, 1), date(2025, 1, 1), None, "opposable")
    features = compute_urban_features(
        box(0, 0, 10, 10),
        [
            UrbanZone("left", document, "UA", box(0, 0, 5, 10)),
            UrbanZone("right", document, "UB", box(5, 0, 10, 10)),
        ],
        [],
        snapshot_at=SNAPSHOT,
        source_accepted=True,
    )
    assert features["URB-001"].missing_reason == "ambiguous_match"


def test_commune_risk_is_context_only_and_never_parcel_exposure() -> None:
    observations = [
        RiskObservation("commune-clay", "clay", "commune", "35000", None, True, "high"),
        RiskObservation("flood-zone", "flood", "zone", "35000", box(20, 20, 30, 30), True),
        RiskObservation("cavity", "cavity", "point", "35000", Point(15, 5), True),
    ]
    features = compute_risk_features(
        box(0, 0, 10, 10),
        observations,
        commune_code="35000",
        snapshot_at=SNAPSHOT,
        source_accepted=True,
    )

    assert features["RISK-001"].missing_reason == "source_value_missing"
    assert features["RISK-002"].json_value == {"overlap": False, "observations": []}
    assert features["RISK-004"].numeric_value == pytest.approx(5)
    profile = features["RISK-101"].json_value
    assert isinstance(profile, dict)
    assert profile["commune_context_only"][0]["source_id"] == "commune-clay"
