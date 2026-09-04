import pytest

from immo_pipelines.spatial.resolution import (
    MatchCandidate,
    canonical_entity_id,
    resolve_candidate_group,
)


def candidate(
    group: str,
    left_id: str,
    right_id: str,
    confidence: float,
    *,
    critical: bool = True,
) -> MatchCandidate:
    return MatchCandidate(
        candidate_group_key=group,
        left_entity_type="building",
        left_entity_id=left_id,
        right_entity_type="parcel",
        right_entity_id=right_id,
        method="spatial_intersection",
        confidence=confidence,
        critical=critical,
        rationale="surface overlap",
        evidence={"overlap": confidence},
    )


def test_stable_ids_do_not_include_release() -> None:
    first = canonical_entity_id("building", "RNB", "RNB-35-A")
    after_reimport = canonical_entity_id("building", "RNB", "RNB-35-A")

    assert first == after_reimport == "building:rnb:RNB-35-A"


def test_one_to_one_resolution_keeps_rejected_candidate() -> None:
    resolved = resolve_candidate_group(
        [candidate("building:B1", "B1", "P1", 0.98), candidate("building:B1", "B1", "P2", 0.4)]
    )

    assert [match.decision for match in resolved] == ["certain", "rejected"]
    assert not resolved[0].blocks_publication


def test_one_to_many_building_covering_parcels() -> None:
    resolved = resolve_candidate_group(
        [
            candidate("building:B1:parcels", "B1", "P1", 0.96),
            candidate("building:B1:parcels", "B1", "P2", 0.94),
        ],
        allows_multiple=True,
    )

    assert [match.decision for match in resolved] == ["certain", "certain"]


def test_many_to_many_relations_are_not_collapsed() -> None:
    first_building = resolve_candidate_group(
        [candidate("B1:parcels", "B1", "P1", 0.99), candidate("B1:parcels", "B1", "P2", 0.95)],
        allows_multiple=True,
    )
    second_building = resolve_candidate_group(
        [candidate("B2:parcels", "B2", "P1", 0.97), candidate("B2:parcels", "B2", "P2", 0.93)],
        allows_multiple=True,
    )

    pairs = {
        (match.candidate.left_entity_id, match.candidate.right_entity_id)
        for match in [*first_building, *second_building]
        if match.decision == "certain"
    }
    assert pairs == {("B1", "P1"), ("B1", "P2"), ("B2", "P1"), ("B2", "P2")}


def test_close_candidates_remain_ambiguous_and_block() -> None:
    resolved = resolve_candidate_group(
        [candidate("address:A1", "B1", "P1", 0.93), candidate("address:A1", "B1", "P2", 0.91)]
    )

    assert [match.decision for match in resolved] == ["ambiguous", "ambiguous"]
    assert all(match.blocks_publication for match in resolved)


def test_resolution_rejects_mixed_groups() -> None:
    with pytest.raises(ValueError, match="one candidate group"):
        resolve_candidate_group(
            [candidate("group-1", "B1", "P1", 1), candidate("group-2", "B1", "P2", 1)]
        )
