import pytest
from shapely.geometry import LineString, box

from immo_pipelines.spatial.features import (
    BuildingFootprint,
    ObservedValue,
    compute_building_features,
    compute_land_features,
)


def test_each_land_feature_has_a_testable_value_and_provenance() -> None:
    parcel = box(0, 0, 10, 10)
    buildings = [
        BuildingFootprint("building:rnb:A", box(2, 2, 5, 5), ("DS-02:RNB-A",), True),
        BuildingFootprint("building:rnb:B", box(6, 6, 8, 8), ("DS-02:RNB-B",), False),
    ]

    features = compute_land_features(
        [parcel],
        buildings,
        building_resolution_complete=True,
        roads=[LineString([(-1, -5), (-1, 15)])],
        roads_accepted=True,
        road_distance_threshold_m=2,
        bdtopo_accepted=True,
    )

    assert set(features) == {f"LAND-{number:03d}" for number in range(1, 11)}
    assert features["LAND-001"].numeric_value == pytest.approx(100)
    assert features["LAND-002"].numeric_value == pytest.approx(13)
    assert features["LAND-003"].numeric_value == pytest.approx(0.13)
    assert features["LAND-004"].numeric_value == pytest.approx(87)
    assert features["LAND-005"].numeric_value == pytest.approx(0.785398, rel=1e-5)
    assert features["LAND-006"].numeric_value == pytest.approx(10)
    assert features["LAND-007"].numeric_value == pytest.approx(2)
    assert features["LAND-008"].numeric_value == pytest.approx(12)
    assert features["LAND-009"].numeric_value == pytest.approx(2)
    assert features["LAND-010"].numeric_value == pytest.approx(9 / 13)
    assert "DS-02:RNB-A" in features["LAND-002"].source_ids
    assert all(feature.formula for feature in features.values())


def test_ambiguous_buildings_never_become_zero() -> None:
    features = compute_land_features([box(0, 0, 10, 10)], [], building_resolution_complete=False)

    for code in ("LAND-002", "LAND-003", "LAND-004", "LAND-007", "LAND-009"):
        assert features[code].numeric_value is None
        assert features[code].missing_reason == "ambiguous_match"
    assert features["LAND-008"].missing_reason == "source_not_accepted"
    assert features["LAND-010"].missing_reason == "source_not_accepted"


def test_multiple_parcels_and_building_spanning_boundary_use_geometric_union() -> None:
    features = compute_land_features(
        [box(0, 0, 10, 10), box(10, 0, 20, 10)],
        [BuildingFootprint("building:rnb:A", box(8, 2, 12, 8), ("DS-02:A",))],
        building_resolution_complete=True,
    )

    assert features["LAND-001"].numeric_value == pytest.approx(200)
    assert features["LAND-002"].numeric_value == pytest.approx(24)
    assert features["LAND-009"].numeric_value == pytest.approx(1)


def test_building_features_prefer_observed_primary_source_and_exclude_prediction() -> None:
    features = compute_building_features(
        uses=[
            ObservedValue("residential", "DS-04:use:A", "DS-04", 100, 0.9),
            ObservedValue("industrial", "DS-03:expert:A", "DS-03", 200, 0.99, predicted=True),
        ],
        heights_m=[ObservedValue(7.5, "DS-04:height:A", "DS-04", 100, 0.85)],
        dwelling_counts=[ObservedValue(1, "DS-03:dwellings:A", "DS-03", 100, 0.8)],
    )

    assert features["BLD-001"].text_value == "residential"
    assert features["BLD-002"].numeric_value == pytest.approx(7.5)
    assert features["BLD-003"].numeric_value == pytest.approx(1)
    assert features["BLD-001"].source_ids == ("DS-04:use:A",)


def test_equal_priority_building_contradiction_is_absent_not_arbitrarily_selected() -> None:
    features = compute_building_features(
        uses=[
            ObservedValue("residential", "DS-04:A", "DS-04", 100, 0.9),
            ObservedValue("industrial", "DS-03:A", "DS-03", 100, 0.9),
        ],
        heights_m=[],
        dwelling_counts=[],
    )

    assert features["BLD-001"].missing_reason == "ambiguous_match"
    assert features["BLD-002"].missing_reason == "source_value_missing"
    assert features["BLD-003"].missing_reason == "source_value_missing"
