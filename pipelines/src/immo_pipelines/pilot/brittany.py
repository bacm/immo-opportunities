from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

BRITTANY_DEPARTMENTS = ("22", "29", "35", "56")
BRITTANY_DATASETS = tuple(f"DS-{number:02d}" for number in range(1, 10))
PILOT_SEGMENTS = ("metropolitan", "medium_city", "periurban", "coastal", "rural")

AcceptanceStatus = Literal["missing", "pending", "accepted", "display_only", "rejected"]
PilotSplit = Literal["development", "validation", "final"]
ProtocolArm = Literal["top_score", "baseline", "random"]


@dataclass(frozen=True, slots=True)
class AcceptanceEvidence:
    dataset: str
    department: str
    status: AcceptanceStatus
    report_path: str | None = None
    blocking_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.dataset not in BRITTANY_DATASETS:
            raise ValueError(f"Dataset outside Brittany pilot: {self.dataset}")
        if self.department not in BRITTANY_DEPARTMENTS:
            raise ValueError(f"Department outside Brittany pilot: {self.department}")


@dataclass(frozen=True, slots=True)
class CoverageObservation:
    department: str
    scope_type: Literal["department", "epci", "commune"]
    scope_code: str
    segment: str
    expected_count: int
    observed_count: int

    def __post_init__(self) -> None:
        if self.department not in BRITTANY_DEPARTMENTS:
            raise ValueError(f"Department outside Brittany pilot: {self.department}")
        if self.segment not in PILOT_SEGMENTS:
            raise ValueError(f"Unknown pilot segment: {self.segment}")
        if self.expected_count < 0 or self.observed_count < 0:
            raise ValueError("Coverage counts cannot be negative")

    @property
    def ratio(self) -> float | None:
        return self.observed_count / self.expected_count if self.expected_count else None


@dataclass(frozen=True, slots=True)
class BlindCandidate:
    candidate_id: str
    department: str
    segment: str
    score: float
    baseline_selected: bool
    split: PilotSplit

    def __post_init__(self) -> None:
        if self.department not in BRITTANY_DEPARTMENTS:
            raise ValueError(f"Department outside Brittany pilot: {self.department}")
        if self.segment not in PILOT_SEGMENTS:
            raise ValueError(f"Unknown pilot segment: {self.segment}")


def build_acceptance_matrix(evidence: list[AcceptanceEvidence]) -> dict[str, object]:
    by_key = {(item.department, item.dataset): item for item in evidence}
    territories: dict[str, dict[str, object]] = {}
    for department in BRITTANY_DEPARTMENTS:
        sources: dict[str, dict[str, object]] = {}
        for dataset in BRITTANY_DATASETS:
            item = by_key.get((department, dataset))
            status: AcceptanceStatus = item.status if item else "missing"
            sources[dataset] = {
                "status": status,
                "report_path": item.report_path if item else None,
                "blocking_reasons": list(item.blocking_reasons) if item else ["missing_audit"],
            }
        blockers = [dataset for dataset, item in sources.items() if item["status"] != "accepted"]
        territories[department] = {
            "covered": not blockers,
            "blocking_datasets": blockers,
            "sources": sources,
        }
    return {
        "covered": all(bool(item["covered"]) for item in territories.values()),
        "territories": territories,
    }


def compare_coverage(
    previous: list[CoverageObservation],
    current: list[CoverageObservation],
    *,
    maximum_drop: float = 0.02,
) -> list[dict[str, object]]:
    if not 0 <= maximum_drop <= 1:
        raise ValueError("maximum_drop must be between zero and one")
    previous_by_key = {
        (item.department, item.scope_type, item.scope_code, item.segment): item for item in previous
    }
    regressions: list[dict[str, object]] = []
    for item in current:
        key = (item.department, item.scope_type, item.scope_code, item.segment)
        old = previous_by_key.get(key)
        if old is None or old.ratio is None or item.ratio is None:
            continue
        drop = old.ratio - item.ratio
        if drop > maximum_drop:
            regressions.append(
                {
                    "department": item.department,
                    "scope_type": item.scope_type,
                    "scope_code": item.scope_code,
                    "segment": item.segment,
                    "previous_ratio": old.ratio,
                    "current_ratio": item.ratio,
                    "drop": drop,
                }
            )
    return regressions


def _seed(seed: str, *parts: str) -> int:
    digest = hashlib.sha256(":".join((seed, *parts)).encode()).digest()
    return int.from_bytes(digest[:8])


def build_blind_protocol(
    candidates: list[BlindCandidate],
    *,
    per_arm: int,
    seed: str,
    double_review_ratio: float = 0.2,
) -> list[dict[str, object]]:
    """Create concealed, stratified arms without allowing development rows into evaluation."""
    if per_arm < 1:
        raise ValueError("per_arm must be positive")
    if not 0 <= double_review_ratio <= 1:
        raise ValueError("double_review_ratio must be between zero and one")
    evaluation = [item for item in candidates if item.split in ("validation", "final")]
    groups: dict[tuple[str, str], list[BlindCandidate]] = defaultdict(list)
    for candidate in evaluation:
        groups[(candidate.department, candidate.segment)].append(candidate)

    assignments: list[dict[str, object]] = []
    seen: set[tuple[str, ProtocolArm]] = set()
    for (department, segment), group in sorted(groups.items()):
        score_ranked = sorted(group, key=lambda item: (-item.score, item.candidate_id))
        baseline = sorted(
            (item for item in group if item.baseline_selected), key=lambda item: item.candidate_id
        )
        shuffled = group.copy()
        random.Random(_seed(seed, department, segment)).shuffle(shuffled)
        arms: tuple[tuple[ProtocolArm, list[BlindCandidate]], ...] = (
            ("top_score", score_ranked),
            ("baseline", baseline),
            ("random", shuffled),
        )
        for arm, pool in arms:
            selected = 0
            for candidate in pool:
                identity = (candidate.candidate_id, arm)
                if identity in seen:
                    continue
                seen.add(identity)
                blind_digest = hashlib.sha256(
                    f"{seed}:{candidate.candidate_id}:{arm}".encode()
                ).hexdigest()
                assignments.append(
                    {
                        "blind_id": f"blind:{blind_digest[:20]}",
                        "candidate_id": candidate.candidate_id,
                        "department": department,
                        "segment": segment,
                        "split": candidate.split,
                        "protocol_arm": arm,
                        "double_review": False,
                    }
                )
                selected += 1
                if selected == per_arm:
                    break

    double_count = round(len(assignments) * double_review_ratio)
    double_order = sorted(
        range(len(assignments)),
        key=lambda index: hashlib.sha256(
            f"{seed}:double:{assignments[index]['blind_id']}".encode()
        ).hexdigest(),
    )
    for index in double_order[:double_count]:
        assignments[index]["double_review"] = True
    return sorted(assignments, key=lambda item: str(item["blind_id"]))


def rank_stability(previous: list[str], current: list[str], *, k: int) -> float | None:
    """Return top-k Jaccard stability; missing evidence stays explicit as None."""
    if k < 1:
        raise ValueError("k must be positive")
    left, right = set(previous[:k]), set(current[:k])
    union = left | right
    return len(left & right) / len(union) if union else None


def evaluate_pilot(
    *,
    acceptance: dict[str, object],
    hypothesis_results: dict[str, bool | None],
    professional_count: int,
    committed_count: int,
    top20_precision: float | None,
    baseline20_precision: float | None,
    minimum_lift: float,
) -> dict[str, object]:
    missing_hypotheses = [
        code for code in ("H1", "H2", "H3", "H4", "H5") if hypothesis_results.get(code) is None
    ]
    lift = (
        top20_precision / baseline20_precision
        if top20_precision is not None and baseline20_precision not in (None, 0)
        else None
    )
    blockers: list[str] = []
    if not acceptance.get("covered"):
        blockers.append("regional_data_not_covered")
    if missing_hypotheses:
        blockers.append("hypotheses_not_measured")
    if professional_count < 3:
        blockers.append("fewer_than_three_professionals")
    if committed_count < 2:
        blockers.append("fewer_than_two_commitments")
    if lift is None:
        blockers.append("top20_lift_not_measured")
    elif lift < minimum_lift:
        blockers.append("top20_lift_below_threshold")
    return {
        "decision_ready": not blockers,
        "recommended_decision": "pursue" if not blockers else None,
        "blockers": blockers,
        "missing_hypotheses": missing_hypotheses,
        "top20_lift": lift,
    }
