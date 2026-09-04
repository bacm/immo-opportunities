from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
from typing import Literal, cast

Requirement = Literal["required", "optional", "confidence_only"]
Direction = Literal["increasing", "decreasing", "confidence_only", "context_only"]
Transformation = Literal["local_percentile", "profiled_score", "identity"]


@dataclass(frozen=True, slots=True)
class FeatureInput:
    code: str
    value: float | int | str | dict[str, object] | None = None
    missing_reason: str | None = None
    local_percentile: float | None = None
    profiled_score: float | None = None
    source_ids: tuple[str, ...] = ()
    release_ids: tuple[str, ...] = ()
    observed_at: date | None = None
    confidence: float | None = None
    segment_code: str | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.missing_reason is None):
            raise ValueError("A feature input must contain exactly one value or missing reason")
        for candidate, label in (
            (self.local_percentile, "local_percentile"),
            (self.profiled_score, "profiled_score"),
            (self.confidence, "confidence"),
        ):
            if candidate is not None and not 0 <= candidate <= 1:
                raise ValueError(f"{label} must be between zero and one")


@dataclass(frozen=True, slots=True)
class FeatureRule:
    feature: str
    component: str | None
    weight: float
    requirement: Requirement
    transformation: Transformation
    direction: Direction
    template: str


@dataclass(frozen=True, slots=True)
class EligibilityRule:
    code: str
    predicate: Literal["present", "any_present", "all_present"]
    features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScoreDefinition:
    definition_id: str
    version: int
    strategy: Literal["division_extension", "renovation_resale"]
    status: Literal["draft", "active", "retired"]
    publication_eligible: bool
    neutral_value: float
    component_weights: dict[str, float]
    rules: tuple[FeatureRule, ...]
    eligibility: tuple[EligibilityRule, ...]
    confidence_weights: dict[str, float]
    forbidden_feature_prefixes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.neutral_value <= 1:
            raise ValueError("Neutral value must be between zero and one")
        if abs(sum(self.component_weights.values()) - 1) > 1e-9:
            raise ValueError("Component weights must sum to one")
        if abs(sum(self.confidence_weights.values()) - 1) > 1e-9:
            raise ValueError("Confidence weights must sum to one")
        codes = [rule.feature for rule in self.rules]
        if len(codes) != len(set(codes)):
            raise ValueError("A feature can contribute at most once")
        for component in self.component_weights:
            weight = sum(rule.weight for rule in self.rules if rule.component == component)
            if abs(weight - 1) > 1e-9:
                raise ValueError(f"Rules in component {component} must sum to one")
        for rule in self.rules:
            if rule.component is None and rule.weight != 0:
                raise ValueError("A confidence-only rule outside components must have zero weight")
            if rule.component is not None and rule.component not in self.component_weights:
                raise ValueError(f"Unknown component: {rule.component}")
            if any(rule.feature.startswith(prefix) for prefix in self.forbidden_feature_prefixes):
                raise ValueError(f"Forbidden feature in score definition: {rule.feature}")


def load_score_definition(path: Path) -> ScoreDefinition:
    raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    rules = tuple(
        FeatureRule(
            feature=str(item["feature"]),
            component=str(item["component"]) if item.get("component") is not None else None,
            weight=float(cast(float | int, item["weight"])),
            requirement=cast(Requirement, item["requirement"]),
            transformation=cast(Transformation, item["transformation"]),
            direction=cast(Direction, item["direction"]),
            template=str(item["template"]),
        )
        for item in cast(list[dict[str, object]], raw["rules"])
    )
    eligibility: list[EligibilityRule] = []
    for item in cast(list[dict[str, object]], raw["eligibility"]):
        feature_list = item.get("all_features") or item.get("any_features")
        features = (
            tuple(str(value) for value in cast(list[object], feature_list))
            if feature_list is not None
            else (str(item["feature"]),)
        )
        eligibility.append(
            EligibilityRule(
                code=str(item["code"]),
                predicate=cast(Literal["present", "any_present", "all_present"], item["predicate"]),
                features=features,
            )
        )
    return ScoreDefinition(
        definition_id=str(raw["definition_id"]),
        version=int(cast(int, raw["definition_version"])),
        strategy=cast(Literal["division_extension", "renovation_resale"], raw["strategy"]),
        status=cast(Literal["draft", "active", "retired"], raw["status"]),
        publication_eligible=bool(raw["publication_eligible"]),
        neutral_value=float(cast(float, raw["neutral_normalized_value"])),
        component_weights={
            str(key): float(cast(float | int, value))
            for key, value in cast(dict[str, object], raw["component_weights"]).items()
        },
        rules=rules,
        eligibility=tuple(eligibility),
        confidence_weights={
            str(key): float(cast(float | int, value))
            for key, value in cast(dict[str, object], raw["confidence"]).items()
        },
        forbidden_feature_prefixes=tuple(
            str(value) for value in cast(list[object], raw["forbidden_feature_prefixes"])
        ),
    )


@dataclass(frozen=True, slots=True)
class ConfidenceInputs:
    match_quality: float
    freshness: float
    source_consistency: float
    comparable_quality: float

    def __post_init__(self) -> None:
        for field_name, value in asdict(self).items():
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between zero and one")


@dataclass(frozen=True, slots=True)
class ScoreComponentResult:
    code: str
    weight: float
    score: float
    weighted_score: float


@dataclass(frozen=True, slots=True)
class ScoreEvidenceResult:
    feature_code: str
    component_code: str | None
    direction: Literal["positive", "negative", "neutral"]
    impact: float
    value: float | int | str | dict[str, object] | None
    normalized_value: float
    comparison: str | None
    source_ids: tuple[str, ...]
    release_ids: tuple[str, ...]
    observed_at: date | None
    quality: Literal["high", "medium", "low", "unknown"]
    formula: str
    explanation: str


@dataclass(frozen=True, slots=True)
class ScoreResult:
    definition_id: str
    definition_version: int
    strategy: str
    snapshot_at: date
    eligible: bool
    eligibility_failures: tuple[str, ...]
    publishable: bool
    publication_blockers: tuple[str, ...]
    overall_score: float | None
    score_class: str | None
    confidence_score: float
    confidence_level: Literal["high", "medium", "low", "not_publishable"]
    components: tuple[ScoreComponentResult, ...]
    evidence: tuple[ScoreEvidenceResult, ...]
    missing_features: tuple[str, ...]
    input_digest: str


@dataclass(frozen=True, slots=True)
class AblationComparison:
    removed_feature_codes: tuple[str, ...]
    full_score: float | None
    ablated_score: float | None
    score_delta: float | None
    ablated_publishable: bool
    ablated_blockers: tuple[str, ...]


def _quality(confidence: float | None) -> Literal["high", "medium", "low", "unknown"]:
    if confidence is None:
        return "unknown"
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def _transformed(rule: FeatureRule, feature: FeatureInput) -> float | None:
    if feature.value is None:
        return None
    if rule.transformation == "local_percentile":
        normalized = feature.local_percentile
    elif rule.transformation == "profiled_score":
        normalized = feature.profiled_score
    elif isinstance(feature.value, (int, float)):
        normalized = min(max(float(feature.value), 0), 1)
    else:
        normalized = None
    if normalized is None:
        return None
    if rule.direction == "decreasing":
        return 1 - normalized
    return normalized


def _is_present(features: dict[str, FeatureInput], code: str) -> bool:
    feature = features.get(code)
    return feature is not None and feature.value is not None


def _digest(
    definition: ScoreDefinition,
    feature_inputs: list[FeatureInput],
    snapshot_at: date,
    release_ids: tuple[str, ...],
) -> str:
    payload = {
        "definition": [definition.definition_id, definition.version],
        "snapshot_at": snapshot_at.isoformat(),
        "release_ids": sorted(release_ids),
        "features": [
            {
                "code": item.code,
                "value": item.value,
                "missing_reason": item.missing_reason,
                "local_percentile": item.local_percentile,
                "profiled_score": item.profiled_score,
                "source_ids": sorted(item.source_ids),
                "release_ids": sorted(item.release_ids),
                "observed_at": item.observed_at.isoformat() if item.observed_at else None,
                "confidence": item.confidence,
                "segment_code": item.segment_code,
            }
            for item in sorted(feature_inputs, key=lambda value: value.code)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def score_opportunity(
    definition: ScoreDefinition,
    feature_inputs: list[FeatureInput],
    *,
    snapshot_at: date,
    release_ids: tuple[str, ...],
    confidence_inputs: ConfidenceInputs,
) -> ScoreResult:
    codes = [item.code for item in feature_inputs]
    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate feature input would double count a value")
    features = {item.code: item for item in feature_inputs}
    forbidden = sorted(
        code
        for code in features
        if any(code.startswith(prefix) for prefix in definition.forbidden_feature_prefixes)
    )
    if forbidden:
        raise ValueError(f"Forbidden feature inputs: {', '.join(forbidden)}")
    leaked = sorted(
        item.code
        for item in feature_inputs
        if item.observed_at is not None and item.observed_at > snapshot_at
    )
    if leaked:
        raise ValueError(f"Post-snapshot feature inputs: {', '.join(leaked)}")
    declared_codes = {rule.feature for rule in definition.rules}
    declared_codes.update(
        feature_code for rule in definition.eligibility for feature_code in rule.features
    )
    unknown = sorted(set(codes) - declared_codes)
    if unknown:
        raise ValueError(f"Inputs not declared in score definition: {', '.join(unknown)}")

    eligibility_failures: list[str] = []
    for rule in definition.eligibility:
        presence = [_is_present(features, code) for code in rule.features]
        passes = (
            presence[0]
            if rule.predicate == "present"
            else any(presence)
            if rule.predicate == "any_present"
            else all(presence)
        )
        if not passes:
            eligibility_failures.append(rule.code)

    missing: list[str] = []
    required_blockers: list[str] = []
    normalized: dict[str, float] = {}
    for rule in definition.rules:
        feature = features.get(rule.feature)
        transformed = _transformed(rule, feature) if feature else None
        if transformed is None:
            missing.append(rule.feature)
            if rule.requirement == "required":
                required_blockers.append(rule.feature)
            normalized[rule.feature] = definition.neutral_value
        elif rule.requirement == "confidence_only" or rule.direction == "confidence_only":
            normalized[rule.feature] = definition.neutral_value
        else:
            normalized[rule.feature] = transformed

    component_results: list[ScoreComponentResult] = []
    evidence: list[ScoreEvidenceResult] = []
    for component, component_weight in definition.component_weights.items():
        component_rules = [rule for rule in definition.rules if rule.component == component]
        component_score = sum(normalized[rule.feature] * rule.weight for rule in component_rules)
        component_results.append(
            ScoreComponentResult(
                code=component,
                weight=component_weight,
                score=round(component_score * 100, 6),
                weighted_score=round(component_score * component_weight * 100, 6),
            )
        )
        for rule in component_rules:
            feature = features.get(rule.feature)
            normalized_value = normalized[rule.feature]
            impact = (
                (normalized_value - definition.neutral_value) * component_weight * rule.weight * 100
            )
            direction: Literal["positive", "negative", "neutral"] = (
                "positive" if impact > 1e-12 else "negative" if impact < -1e-12 else "neutral"
            )
            comparison = (
                f"percentile_{round(float(feature.local_percentile) * 100)}_local_segment"
                if feature and feature.local_percentile is not None
                else None
            )
            explanation = rule.template.format(
                value=feature.value if feature and feature.value is not None else "indisponible",
                normalized=round(normalized_value, 3),
                comparison=(
                    round(float(feature.local_percentile) * 100)
                    if feature and feature.local_percentile is not None
                    else "indisponible"
                ),
            )
            evidence.append(
                ScoreEvidenceResult(
                    feature_code=rule.feature,
                    component_code=component,
                    direction=direction,
                    impact=round(impact, 6),
                    value=feature.value if feature else None,
                    normalized_value=round(normalized_value, 6),
                    comparison=comparison,
                    source_ids=feature.source_ids if feature else (),
                    release_ids=feature.release_ids if feature else (),
                    observed_at=feature.observed_at if feature else None,
                    quality=_quality(feature.confidence if feature else None),
                    formula=f"{rule.transformation}:{rule.direction}",
                    explanation=explanation,
                )
            )

    for rule in (rule for rule in definition.rules if rule.component is None):
        feature = features.get(rule.feature)
        normalized_value = normalized[rule.feature]
        evidence.append(
            ScoreEvidenceResult(
                feature_code=rule.feature,
                component_code=None,
                direction="neutral",
                impact=0,
                value=feature.value if feature else None,
                normalized_value=round(normalized_value, 6),
                comparison=None,
                source_ids=feature.source_ids if feature else (),
                release_ids=feature.release_ids if feature else (),
                observed_at=feature.observed_at if feature else None,
                quality=_quality(feature.confidence if feature else None),
                formula=f"{rule.transformation}:{rule.direction}",
                explanation=rule.template.format(
                    value=(
                        feature.value
                        if feature is not None and feature.value is not None
                        else "indisponible"
                    ),
                    normalized=round(normalized_value, 3),
                    comparison="indisponible",
                ),
            )
        )

    critical_rules = [
        rule for rule in definition.rules if rule.requirement in ("required", "confidence_only")
    ]
    present_critical = sum(_is_present(features, rule.feature) for rule in critical_rules)
    critical_coverage = present_critical / len(critical_rules) if critical_rules else 1.0
    confidence_factors = {
        "match_quality": confidence_inputs.match_quality,
        "critical_coverage": critical_coverage,
        "freshness": confidence_inputs.freshness,
        "source_consistency": confidence_inputs.source_consistency,
        "comparable_quality": confidence_inputs.comparable_quality,
    }
    confidence_score = 100 * sum(
        confidence_factors[name] * weight for name, weight in definition.confidence_weights.items()
    )
    eligible = not eligibility_failures
    blockers = [*(f"eligibility:{code}" for code in eligibility_failures)]
    blockers.extend(f"required:{code}" for code in sorted(set(required_blockers)))
    if not definition.publication_eligible:
        blockers.append("definition_not_publication_eligible")
    publishable = eligible and not required_blockers and definition.publication_eligible
    if not publishable:
        confidence_level: Literal["high", "medium", "low", "not_publishable"] = "not_publishable"
    elif confidence_score >= 80:
        confidence_level = "high"
    elif confidence_score >= 60:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    overall = sum(item.weighted_score for item in component_results) if eligible else None
    overall = round(min(max(overall, 0), 100), 6) if overall is not None else None
    score_class = (
        None
        if overall is None
        else "low"
        if overall < 40
        else "review"
        if overall < 60
        else "interesting"
        if overall < 80
        else "high_priority"
    )
    return ScoreResult(
        definition_id=definition.definition_id,
        definition_version=definition.version,
        strategy=definition.strategy,
        snapshot_at=snapshot_at,
        eligible=eligible,
        eligibility_failures=tuple(eligibility_failures),
        publishable=publishable,
        publication_blockers=tuple(blockers),
        overall_score=overall,
        score_class=score_class,
        confidence_score=round(min(max(confidence_score, 0), 100), 6),
        confidence_level=confidence_level,
        components=tuple(component_results),
        evidence=tuple(evidence),
        missing_features=tuple(sorted(set(missing))),
        input_digest=_digest(definition, feature_inputs, snapshot_at, release_ids),
    )


def ablate_features(
    definition: ScoreDefinition,
    feature_inputs: list[FeatureInput],
    *,
    removed_feature_codes: tuple[str, ...],
    snapshot_at: date,
    release_ids: tuple[str, ...],
    confidence_inputs: ConfidenceInputs,
) -> AblationComparison:
    removed = set(removed_feature_codes)
    unknown = removed - {item.code for item in feature_inputs}
    if unknown:
        raise ValueError(f"Cannot ablate unavailable features: {', '.join(sorted(unknown))}")
    full = score_opportunity(
        definition,
        feature_inputs,
        snapshot_at=snapshot_at,
        release_ids=release_ids,
        confidence_inputs=confidence_inputs,
    )
    ablated_inputs = [
        replace(
            item,
            value=None,
            missing_reason="ablation",
            local_percentile=None,
            profiled_score=None,
        )
        if item.code in removed
        else item
        for item in feature_inputs
    ]
    ablated = score_opportunity(
        definition,
        ablated_inputs,
        snapshot_at=snapshot_at,
        release_ids=release_ids,
        confidence_inputs=confidence_inputs,
    )
    delta = (
        ablated.overall_score - full.overall_score
        if ablated.overall_score is not None and full.overall_score is not None
        else None
    )
    return AblationComparison(
        removed_feature_codes=tuple(sorted(removed)),
        full_score=full.overall_score,
        ablated_score=ablated.overall_score,
        score_delta=round(delta, 6) if delta is not None else None,
        ablated_publishable=ablated.publishable,
        ablated_blockers=ablated.publication_blockers,
    )


@dataclass(frozen=True, slots=True)
class ValueRange:
    low: float
    central: float
    high: float

    def __post_init__(self) -> None:
        if not 0 <= self.low <= self.central <= self.high:
            raise ValueError("A financial range must be non-negative and ordered")


@dataclass(frozen=True, slots=True)
class FinancialInputs:
    purchase: ValueRange
    works: ValueRange
    resale: ValueRange
    fees: ValueRange
    financing: ValueRange
    holding: ValueRange
    target_return_on_cost: float = 0.15

    def __post_init__(self) -> None:
        if self.target_return_on_cost < 0:
            raise ValueError("Target return on cost cannot be negative")


@dataclass(frozen=True, slots=True)
class FinancialScenario:
    name: Literal["prudent", "central", "optimistic"]
    purchase_eur: float
    works_eur: float
    resale_eur: float
    fees_eur: float
    financing_eur: float
    holding_eur: float
    total_cost_eur: float
    net_margin_eur: float
    return_on_cost: float
    break_even_purchase_price_eur: float


def compute_financial_scenarios(inputs: FinancialInputs) -> tuple[FinancialScenario, ...]:
    selections: tuple[tuple[str, str, str], ...] = (
        ("prudent", "high", "low"),
        ("central", "central", "central"),
        ("optimistic", "low", "high"),
    )
    scenarios: list[FinancialScenario] = []
    for name, cost_case, resale_case in selections:
        purchase = float(getattr(inputs.purchase, cost_case))
        works = float(getattr(inputs.works, cost_case))
        resale = float(getattr(inputs.resale, resale_case))
        fees = float(getattr(inputs.fees, cost_case))
        financing = float(getattr(inputs.financing, cost_case))
        holding = float(getattr(inputs.holding, cost_case))
        non_purchase_cost = works + fees + financing + holding
        total_cost = purchase + non_purchase_cost
        margin = resale - total_cost
        return_on_cost = margin / total_cost if total_cost > 0 else 0
        break_even = max(
            resale / (1 + inputs.target_return_on_cost) - non_purchase_cost,
            0,
        )
        scenarios.append(
            FinancialScenario(
                name=name,
                purchase_eur=purchase,
                works_eur=works,
                resale_eur=resale,
                fees_eur=fees,
                financing_eur=financing,
                holding_eur=holding,
                total_cost_eur=total_cost,
                net_margin_eur=margin,
                return_on_cost=return_on_cost,
                break_even_purchase_price_eur=break_even,
            )
        )
    return tuple(scenarios)


@dataclass(frozen=True, slots=True)
class BaselineDefinition:
    definition_id: str
    strategy: Literal["division_extension", "renovation_resale"]
    minimum_parcel_area_m2: float | None = None
    maximum_footprint_ratio: float | None = None
    minimum_unbuilt_area_m2: float | None = None
    allowed_building_uses: tuple[str, ...] = ()


def baseline_select(
    definition: BaselineDefinition, features: dict[str, FeatureInput]
) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    numeric_checks = (
        ("LAND-001", definition.minimum_parcel_area_m2, "below_minimum_parcel_area", "minimum"),
        (
            "LAND-003",
            definition.maximum_footprint_ratio,
            "above_maximum_footprint_ratio",
            "maximum",
        ),
        ("LAND-004", definition.minimum_unbuilt_area_m2, "below_minimum_unbuilt_area", "minimum"),
    )
    for code, threshold, failure, mode in numeric_checks:
        if threshold is None:
            continue
        feature = features.get(code)
        if feature is None or not isinstance(feature.value, (int, float)):
            failures.append(f"missing:{code}")
        elif (mode == "minimum" and float(feature.value) < threshold) or (
            mode == "maximum" and float(feature.value) > threshold
        ):
            failures.append(failure)
    if definition.allowed_building_uses:
        use = features.get("BLD-001")
        if use is None or use.value not in definition.allowed_building_uses:
            failures.append("building_use_not_allowed")
    return not failures, tuple(failures)


@dataclass(frozen=True, slots=True)
class BacktestCandidate:
    candidate_id: str
    segment: Literal["urban", "periurban", "littoral", "rural"]
    score: float
    baseline_selected: bool
    positive_label: bool
    split: Literal["development", "validation", "final"]


def _precision(candidates: list[BacktestCandidate], k: int) -> float | None:
    selected = candidates[:k]
    return sum(item.positive_label for item in selected) / len(selected) if selected else None


def evaluate_backtest(
    candidates: list[BacktestCandidate], *, ks: tuple[int, ...] = (10, 20, 50)
) -> dict[str, object]:
    evaluation = [item for item in candidates if item.split in ("validation", "final")]
    ranked = sorted(evaluation, key=lambda item: (-item.score, item.candidate_id))
    baseline = sorted(
        (item for item in evaluation if item.baseline_selected),
        key=lambda item: item.candidate_id,
    )
    metrics: dict[str, object] = {}
    for k in ks:
        score_precision = _precision(ranked, k)
        baseline_precision = _precision(baseline, k)
        metrics[f"precision_at_{k}"] = score_precision
        metrics[f"baseline_precision_at_{k}"] = baseline_precision
        metrics[f"lift_at_{k}"] = (
            score_precision / baseline_precision
            if score_precision is not None and baseline_precision not in (None, 0)
            else None
        )
    segments: dict[str, dict[str, float | int | None]] = {}
    for segment in ("urban", "periurban", "littoral", "rural"):
        segment_ranked = [item for item in ranked if item.segment == segment]
        segments[segment] = {
            "count": len(segment_ranked),
            "precision_at_10": _precision(segment_ranked, 10),
        }
    return {
        "candidate_count": len(evaluation),
        "development_candidates_excluded": sum(item.split == "development" for item in candidates),
        "metrics": metrics,
        "segments": segments,
    }
