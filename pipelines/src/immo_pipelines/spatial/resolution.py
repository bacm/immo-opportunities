from dataclasses import dataclass
from typing import Literal

EntityType = Literal["area", "address", "parcel", "building", "property_unit"]
MatchMethod = Literal[
    "official_identifier",
    "source_relation",
    "spatial_intersection",
    "proximity",
    "normalized_address",
    "temporal_consistency",
    "manual",
]
MatchDecision = Literal["certain", "ambiguous", "rejected"]


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    candidate_group_key: str
    left_entity_type: EntityType
    left_entity_id: str
    right_entity_type: EntityType
    right_entity_id: str
    method: MatchMethod
    confidence: float
    critical: bool
    rationale: str
    evidence: dict[str, object]

    def __post_init__(self) -> None:
        if self.left_entity_type == self.right_entity_type:
            raise ValueError("A match must link different entity types")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Match confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ResolvedMatch:
    candidate: MatchCandidate
    algorithm_code: str
    algorithm_version: str
    decision: MatchDecision
    blocks_publication: bool


def canonical_entity_id(
    entity_type: EntityType,
    identity_source: str,
    source_identifier: str,
) -> str:
    """Build a stable ID from a durable source identifier, never from a release."""
    source = identity_source.strip().lower().replace("_", "-")
    identifier = source_identifier.strip()
    if not source or not identifier:
        raise ValueError("Identity source and source identifier are required")
    if entity_type == "property_unit":
        return f"property-unit:{source}:{identifier}"
    return f"{entity_type}:{source}:{identifier}"


def resolve_candidate_group(
    candidates: list[MatchCandidate],
    *,
    algorithm_code: str = "entity-resolution",
    algorithm_version: str = "1",
    certain_threshold: float = 0.9,
    reject_threshold: float = 0.5,
    ambiguity_delta: float = 0.05,
    allows_multiple: bool = False,
) -> list[ResolvedMatch]:
    """Resolve one candidate group while retaining every rejected or ambiguous option."""
    if not candidates:
        return []
    if len({candidate.candidate_group_key for candidate in candidates}) != 1:
        raise ValueError("Candidates must belong to one candidate group")
    if not 0 <= reject_threshold <= certain_threshold <= 1:
        raise ValueError("Invalid resolution thresholds")

    ranked = sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)
    top_confidence = ranked[0].confidence
    result: list[ResolvedMatch] = []

    for index, candidate in enumerate(ranked):
        competing_at_top = (
            len(ranked) > 1
            and not allows_multiple
            and top_confidence - ranked[1].confidence <= ambiguity_delta
        )
        eligible = candidate.confidence >= certain_threshold
        if allows_multiple and eligible:
            decision: MatchDecision = "certain"
        elif competing_at_top and top_confidence - candidate.confidence <= ambiguity_delta:
            decision = "ambiguous"
        elif index == 0 and eligible:
            decision = "certain"
        elif index == 0 and candidate.confidence >= reject_threshold:
            decision = "ambiguous"
        else:
            decision = "rejected"
        result.append(
            ResolvedMatch(
                candidate=candidate,
                algorithm_code=algorithm_code,
                algorithm_version=algorithm_version,
                decision=decision,
                blocks_publication=candidate.critical and decision == "ambiguous",
            )
        )
    return result
