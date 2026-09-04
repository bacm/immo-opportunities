from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from statistics import median
from typing import Literal

from shapely.geometry.base import BaseGeometry

MissingReason = Literal[
    "source_not_accepted",
    "source_value_missing",
    "not_applicable",
    "ambiguous_match",
    "invalid_geometry",
    "calculation_error",
]


@dataclass(frozen=True, slots=True)
class FeatureResult:
    code: str
    numeric_value: float | None = None
    text_value: str | None = None
    json_value: dict[str, object] | list[object] | None = None
    missing_reason: MissingReason | None = None
    source_ids: tuple[str, ...] = ()
    formula: str = ""
    transformation_version: str = "market-data@1"
    confidence: float | None = None

    def __post_init__(self) -> None:
        populated = sum(
            value is not None
            for value in (
                self.numeric_value,
                self.text_value,
                self.json_value,
                self.missing_reason,
            )
        )
        if populated != 1:
            raise ValueError("A feature must have exactly one value or missing reason")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Feature confidence must be between zero and one")


@dataclass(frozen=True, slots=True)
class TransactionProperty:
    source_id: str
    property_type: str
    surface_m2: float | None
    allocated_price_eur: float | None = None
    parcel_id: str | None = None
    building_id: str | None = None


@dataclass(frozen=True, slots=True)
class Transaction:
    source_id: str
    mutation_date: date
    price_eur: float
    segment_code: str
    distance_m: float
    properties: tuple[TransactionProperty, ...]
    is_complex: bool = False
    release_id: str = "DS-06:unknown"


@dataclass(frozen=True, slots=True)
class ComparableDecision:
    transaction_id: str
    property_id: str
    included: bool
    reason: str
    distance_m: float
    segment_code: str
    transaction_date: date
    property_type: str
    surface_m2: float | None
    normalized_price_m2: float | None
    weight: float | None
    price_transformations: tuple[str, ...]
    source_release_id: str


def _months_between(earlier: date, later: date) -> int:
    months = (later.year - earlier.year) * 12 + later.month - earlier.month
    if later.day < earlier.day:
        months -= 1
    return max(months, 0)


def select_comparables(
    transactions: list[Transaction],
    *,
    snapshot_at: date,
    target_segment: str,
    target_property_type: str,
    target_surface_m2: float | None,
    max_distance_m: float = 10_000,
    max_age_months: int = 60,
    surface_ratio_range: tuple[float, float] = (0.5, 2.0),
    price_factors_by_year: dict[int, float] | None = None,
) -> list[ComparableDecision]:
    """Select explainable comparables without decomposing complex mutations by guesswork."""
    decisions: list[ComparableDecision] = []
    factors = price_factors_by_year or {}
    for transaction in transactions:
        for property_ in transaction.properties:
            reason: str | None = None
            price_m2: float | None = None
            transformations: list[str] = []
            age_months = _months_between(transaction.mutation_date, snapshot_at)

            if transaction.mutation_date > snapshot_at:
                reason = "after_snapshot"
            elif transaction.price_eur <= 0:
                reason = "invalid_transaction_price"
            elif transaction.segment_code != target_segment:
                reason = "segment_mismatch"
            elif property_.property_type != target_property_type:
                reason = "property_type_mismatch"
            elif transaction.distance_m < 0 or transaction.distance_m > max_distance_m:
                reason = "distance_out_of_range"
            elif age_months > max_age_months:
                reason = "too_old"
            elif property_.surface_m2 is None or property_.surface_m2 <= 0:
                reason = "surface_missing_or_invalid"
            elif (
                target_surface_m2 is not None
                and not surface_ratio_range[0]
                <= property_.surface_m2 / target_surface_m2
                <= surface_ratio_range[1]
            ):
                reason = "surface_out_of_range"
            else:
                allocated_price = property_.allocated_price_eur
                if allocated_price is None and (
                    transaction.is_complex or len(transaction.properties) != 1
                ):
                    reason = "complex_mutation_not_decomposable"
                else:
                    effective_price = allocated_price or transaction.price_eur
                    factor = factors.get(transaction.mutation_date.year, 1.0)
                    if factor <= 0:
                        reason = "invalid_price_transformation"
                    else:
                        if factor != 1:
                            transformations.append(f"year_factor:{factor:g}")
                        price_m2 = effective_price * factor / property_.surface_m2
                        if price_m2 <= 0:
                            reason = "invalid_normalized_price"

            included = reason is None
            weight = None
            if included:
                recency_weight = max(0.1, 1 - age_months / max(max_age_months, 1))
                distance_weight = 1 / (1 + transaction.distance_m / 1_000)
                weight = recency_weight * distance_weight
            decisions.append(
                ComparableDecision(
                    transaction_id=transaction.source_id,
                    property_id=property_.source_id,
                    included=included,
                    reason="included" if included else str(reason),
                    distance_m=transaction.distance_m,
                    segment_code=transaction.segment_code,
                    transaction_date=transaction.mutation_date,
                    property_type=property_.property_type,
                    surface_m2=property_.surface_m2,
                    normalized_price_m2=price_m2 if included else None,
                    weight=weight,
                    price_transformations=tuple(transformations),
                    source_release_id=transaction.release_id,
                )
            )
    return decisions


def _weighted_quantile(values: list[tuple[float, float]], quantile: float) -> float:
    if not values:
        raise ValueError("weighted quantile requires values")
    ordered = sorted(values)
    total = sum(weight for _, weight in ordered)
    threshold = total * quantile
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def _number(code: str, value: float, formula: str, sources: tuple[str, ...]) -> FeatureResult:
    return FeatureResult(code=code, numeric_value=float(value), formula=formula, source_ids=sources)


def _missing(code: str, reason: MissingReason, formula: str) -> FeatureResult:
    return FeatureResult(code=code, missing_reason=reason, formula=formula)


def compute_market_features(
    decisions: list[ComparableDecision],
    *,
    strategy: Literal["division_extension", "renovation_resale"],
    snapshot_at: date,
    source_accepted: bool,
    observable_stock: int | None = None,
    scenario_surface_m2: float | None = None,
    minimum_trend_count: int = 6,
    minimum_trend_span_days: int = 365,
) -> dict[str, FeatureResult]:
    codes = (
        ("MKT-001", "MKT-002", "MKT-003", "MKT-004", "MKT-005")
        if strategy == "division_extension"
        else ("MKT-101", "MKT-102", "MKT-103", "MKT-104", "MKT-105")
    )
    if not source_accepted:
        return {
            code: _missing(code, "source_not_accepted", "accepted DS-06 selection")
            for code in codes
        }

    included = [item for item in decisions if item.included]
    if any(item.transaction_date > snapshot_at for item in included):
        raise ValueError("Comparable selection contains post-snapshot data")
    prices = [
        (float(item.normalized_price_m2), float(item.weight))
        for item in included
        if item.normalized_price_m2 is not None and item.weight is not None
    ]
    sources = tuple(sorted({item.source_release_id for item in included}))
    count_code = "MKT-003" if strategy == "division_extension" else "MKT-102"
    dispersion_code = "MKT-004" if strategy == "division_extension" else "MKT-103"
    result: dict[str, FeatureResult] = {
        count_code: _number(count_code, len(included), "count(included comparables)", sources)
    }
    if prices:
        median_price = _weighted_quantile(prices, 0.5)
        level_code = "MKT-001" if strategy == "division_extension" else "MKT-101"
        result[level_code] = _number(
            level_code, median_price, "weighted median(included normalized prices)", sources
        )
    else:
        level_code = "MKT-001" if strategy == "division_extension" else "MKT-101"
        result[level_code] = _missing(
            level_code,
            "source_value_missing",
            "weighted median(included normalized prices)",
        )

    if len(prices) >= 4:
        dispersion = _weighted_quantile(prices, 0.75) - _weighted_quantile(prices, 0.25)
        result[dispersion_code] = _number(
            dispersion_code, dispersion, "weighted Q3 - weighted Q1", sources
        )
    else:
        result[dispersion_code] = _missing(
            dispersion_code, "source_value_missing", "weighted Q3 - weighted Q1"
        )

    if strategy == "division_extension":
        if prices and scenario_surface_m2 is not None and scenario_surface_m2 > 0:
            result["MKT-002"] = FeatureResult(
                code="MKT-002",
                json_value={
                    "lower_eur": _weighted_quantile(prices, 0.25) * scenario_surface_m2,
                    "upper_eur": _weighted_quantile(prices, 0.75) * scenario_surface_m2,
                    "surface_m2": scenario_surface_m2,
                },
                formula="weighted comparable quartiles * explicit scenario surface",
                source_ids=sources,
            )
        else:
            result["MKT-002"] = _missing(
                "MKT-002",
                "source_value_missing",
                "weighted comparable quartiles * scenario surface",
            )
        if observable_stock is None or observable_stock <= 0:
            result["MKT-005"] = _missing(
                "MKT-005", "source_value_missing", "recent transactions / observable stock"
            )
        else:
            recent = sum(
                _months_between(item.transaction_date, snapshot_at) <= 12 for item in included
            )
            result["MKT-005"] = _number(
                "MKT-005",
                recent / observable_stock,
                "recent transactions / observable stock",
                sources,
            )
        return result

    if included:
        ages = [_months_between(item.transaction_date, snapshot_at) for item in included]
        result["MKT-104"] = _number(
            "MKT-104", median(ages), "median comparable age at snapshot", sources
        )
    else:
        result["MKT-104"] = _missing(
            "MKT-104", "source_value_missing", "median comparable age at snapshot"
        )

    dated_prices = sorted(
        (item.transaction_date, float(item.normalized_price_m2))
        for item in included
        if item.normalized_price_m2 is not None
    )
    span_days = (dated_prices[-1][0] - dated_prices[0][0]).days if dated_prices else 0
    if len(dated_prices) < minimum_trend_count or span_days < minimum_trend_span_days:
        result["MKT-105"] = _missing(
            "MKT-105", "source_value_missing", "robust annualized median-price trend"
        )
    else:
        middle = len(dated_prices) // 2
        old_price = median(value for _, value in dated_prices[:middle])
        new_price = median(value for _, value in dated_prices[middle:])
        years = span_days / 365.25
        trend = (new_price / old_price) ** (1 / years) - 1 if old_price > 0 else 0
        result["MKT-105"] = _number(
            "MKT-105", trend, "robust annualized median-price trend", sources
        )
    return result


@dataclass(frozen=True, slots=True)
class EnergyAssessment:
    source_id: str
    assessment_date: date
    energy_label: str | None
    consumption_kwh_m2_year: float | None
    deposited: bool
    simulated: bool = False
    cancelled_at: date | None = None
    address_id: str | None = None
    building_id: str | None = None
    match_confidence: float | None = None
    envelope: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class EnergySelection:
    assessment: EnergyAssessment | None
    missing_reason: MissingReason | None
    rationale: str


def select_energy_assessment(
    assessments: list[EnergyAssessment],
    *,
    building_id: str,
    address_ids: set[str],
    snapshot_at: date,
) -> EnergySelection:
    eligible = [
        item
        for item in assessments
        if item.deposited
        and not item.simulated
        and item.assessment_date <= snapshot_at
        and (item.cancelled_at is None or item.cancelled_at > snapshot_at)
    ]
    direct = [item for item in eligible if item.building_id == building_id]
    if direct:
        selected = max(direct, key=lambda item: (item.assessment_date, item.source_id))
        return EnergySelection(selected, None, "latest deposited DPE resolved directly to building")

    at_address = [
        item for item in eligible if item.address_id in address_ids and item.building_id is None
    ]
    if len(at_address) == 1:
        return EnergySelection(at_address[0], None, "single deposited address-level DPE candidate")
    if len(at_address) > 1:
        return EnergySelection(None, "ambiguous_match", "multiple DPE candidates at address")
    return EnergySelection(None, "source_value_missing", "no deposited DPE resolved to building")


@dataclass(frozen=True, slots=True)
class BuildingObservation:
    source_id: str
    construction_period: str | None = None
    area_proxy_m2: float | None = None
    height_m: float | None = None
    floor_count: int | None = None
    predicted: bool = False
    priority: int = 0
    confidence: float = 1.0


def compute_renovation_features(
    observations: list[BuildingObservation],
    energy_selection: EnergySelection,
    *,
    snapshot_at: date,
    dpe_source_accepted: bool,
) -> dict[str, FeatureResult]:
    observed = sorted(
        (item for item in observations if not item.predicted),
        key=lambda item: (item.priority, item.confidence),
        reverse=True,
    )
    period = next((item for item in observed if item.construction_period), None)
    area = next((item for item in observed if item.area_proxy_m2 and item.area_proxy_m2 > 0), None)
    dimensional = next(
        (item for item in observed if item.height_m is not None and item.floor_count), None
    )
    result: dict[str, FeatureResult] = {}
    if period is not None and period.construction_period is not None:
        result["REN-001"] = FeatureResult(
            code="REN-001",
            text_value=period.construction_period,
            source_ids=(period.source_id,),
            formula="best non-predicted observed construction period",
            confidence=period.confidence,
        )
    else:
        result["REN-001"] = _missing(
            "REN-001", "source_value_missing", "best observed construction period"
        )
    if area is not None and area.area_proxy_m2 is not None:
        result["REN-002"] = FeatureResult(
            code="REN-002",
            numeric_value=float(area.area_proxy_m2),
            source_ids=(area.source_id,),
            formula="best non-predicted observed building area proxy",
            confidence=area.confidence,
        )
    else:
        result["REN-002"] = _missing(
            "REN-002", "source_value_missing", "best observed building area proxy"
        )
    if (
        dimensional is not None
        and dimensional.height_m is not None
        and dimensional.floor_count is not None
    ):
        floor_height = float(dimensional.height_m) / int(dimensional.floor_count)
        status = "consistent" if 2 <= floor_height <= 5 else "review"
        result["REN-003"] = FeatureResult(
            code="REN-003",
            text_value=status,
            source_ids=(dimensional.source_id,),
            formula="2m <= observed height / observed floors <= 5m",
            confidence=dimensional.confidence,
        )
    else:
        result["REN-003"] = _missing(
            "REN-003", "not_applicable", "height/floors consistency when both are observed"
        )

    if not dpe_source_accepted:
        for code in ("REN-004", "REN-005", "REN-006", "REN-007", "REN-008"):
            result[code] = _missing(code, "source_not_accepted", "selected deposited DPE")
        return result
    if energy_selection.assessment is None:
        reason = energy_selection.missing_reason or "source_value_missing"
        for code in ("REN-004", "REN-005", "REN-006", "REN-007", "REN-008"):
            result[code] = _missing(code, reason, "selected deposited DPE")
        return result

    assessment = energy_selection.assessment
    result["REN-004"] = (
        FeatureResult(
            code="REN-004",
            text_value=assessment.energy_label,
            source_ids=(assessment.source_id,),
            formula="energy label from selected deposited DPE",
        )
        if assessment.energy_label
        else _missing("REN-004", "source_value_missing", "energy label from selected DPE")
    )
    result["REN-005"] = (
        _number(
            "REN-005",
            assessment.consumption_kwh_m2_year,
            "consumption from selected deposited DPE",
            (assessment.source_id,),
        )
        if assessment.consumption_kwh_m2_year is not None
        else _missing("REN-005", "source_value_missing", "consumption from selected DPE")
    )
    result["REN-006"] = _number(
        "REN-006",
        _months_between(assessment.assessment_date, snapshot_at),
        "complete months between DPE and snapshot",
        (assessment.source_id,),
    )
    result["REN-007"] = (
        FeatureResult(
            code="REN-007",
            json_value=assessment.envelope,
            source_ids=(assessment.source_id,),
            formula="declared envelope fields from selected deposited DPE",
        )
        if assessment.envelope
        else _missing("REN-007", "source_value_missing", "declared DPE envelope fields")
    )
    result["REN-008"] = (
        _number(
            "REN-008",
            assessment.match_confidence,
            "DPE-address-building match confidence",
            (assessment.source_id,),
        )
        if assessment.match_confidence is not None
        else _missing("REN-008", "source_value_missing", "DPE match confidence")
    )
    return result


@dataclass(frozen=True, slots=True)
class UrbanDocument:
    source_id: str
    version: str
    published_at: date
    valid_from: date
    valid_to: date | None
    status: Literal["opposable", "superseded", "cancelled", "informational"]

    def applies_at(self, snapshot_at: date) -> bool:
        return (
            self.status == "opposable"
            and self.published_at <= snapshot_at
            and self.valid_from <= snapshot_at
            and (self.valid_to is None or self.valid_to >= snapshot_at)
        )


@dataclass(frozen=True, slots=True)
class UrbanZone:
    source_id: str
    document: UrbanDocument
    code: str
    geometry: BaseGeometry
    rule_profile: dict[str, object] | None = None
    rule_profile_validated: bool = False
    required_rules: tuple[str, ...] = ()
    validated_rules: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UrbanConstraint:
    source_id: str
    document: UrbanDocument
    constraint_type: str
    geometry: BaseGeometry


def compute_urban_features(
    unit_geometry: BaseGeometry,
    zones: list[UrbanZone],
    constraints: list[UrbanConstraint],
    *,
    snapshot_at: date,
    source_accepted: bool,
    existing_footprint_m2: float | None = None,
    ambiguity_ratio_tolerance: float = 0.05,
) -> dict[str, FeatureResult]:
    codes = tuple(f"URB-{number:03d}" for number in range(1, 6))
    if not source_accepted:
        return {
            code: _missing(code, "source_not_accepted", "accepted DS-08 document") for code in codes
        }
    if unit_geometry.is_empty or not unit_geometry.is_valid or unit_geometry.area <= 0:
        return {code: _missing(code, "invalid_geometry", "urban intersection") for code in codes}

    overlaps: list[tuple[float, UrbanZone]] = []
    for zone in zones:
        if zone.document.applies_at(snapshot_at) and zone.geometry.is_valid:
            overlap = zone.geometry.intersection(unit_geometry).area / unit_geometry.area
            if overlap > 0:
                overlaps.append((float(overlap), zone))
    overlaps.sort(key=lambda item: (item[0], item[1].source_id), reverse=True)
    if not overlaps:
        return {
            code: _missing(code, "source_value_missing", "opposable zone overlap") for code in codes
        }
    if len(overlaps) > 1 and overlaps[0][0] - overlaps[1][0] <= ambiguity_ratio_tolerance:
        result = {
            code: _missing(code, "ambiguous_match", "materially overlapping opposable zones")
            for code in ("URB-001", "URB-002", "URB-004", "URB-005")
        }
    else:
        ratio, zone = overlaps[0]
        result = {
            "URB-001": FeatureResult(
                code="URB-001",
                text_value=zone.code,
                source_ids=(zone.source_id, zone.document.source_id),
                formula="largest unambiguous overlap with opposable zone",
                confidence=ratio,
            )
        }
        completeness = (
            len(set(zone.validated_rules) & set(zone.required_rules)) / len(zone.required_rules)
            if zone.required_rules
            else 0.0
        )
        result["URB-005"] = _number(
            "URB-005", completeness, "validated required rules / required rules", (zone.source_id,)
        )
        if zone.rule_profile is not None and zone.rule_profile_validated:
            result["URB-002"] = FeatureResult(
                code="URB-002",
                json_value=zone.rule_profile,
                source_ids=(zone.source_id, zone.document.source_id),
                formula="manually validated structured profile for exact document version",
            )
        else:
            result["URB-002"] = _missing(
                "URB-002", "source_value_missing", "validated exact-version rule profile"
            )
        maximum_ratio = (
            zone.rule_profile.get("max_footprint_ratio")
            if zone.rule_profile and zone.rule_profile_validated
            else None
        )
        if (
            completeness == 1
            and existing_footprint_m2 is not None
            and isinstance(maximum_ratio, (int, float))
            and 0 <= maximum_ratio <= 1
        ):
            residual = max(
                float(unit_geometry.area) * float(maximum_ratio) - existing_footprint_m2,
                0,
            )
            result["URB-004"] = _number(
                "URB-004",
                residual,
                "area * validated max footprint ratio - existing footprint",
                (zone.source_id,),
            )
        else:
            result["URB-004"] = _missing(
                "URB-004", "source_value_missing", "all indispensable structured rules validated"
            )

    applicable_constraints = [
        item
        for item in constraints
        if item.document.applies_at(snapshot_at)
        and item.geometry.is_valid
        and item.geometry.intersects(unit_geometry)
    ]
    by_type: dict[str, float] = {}
    for item in applicable_constraints:
        by_type[item.constraint_type] = by_type.get(item.constraint_type, 0.0) + float(
            item.geometry.intersection(unit_geometry).area
        )
    result["URB-003"] = FeatureResult(
        code="URB-003",
        json_value={"count": len(applicable_constraints), "overlap_m2_by_type": by_type},
        source_ids=tuple(item.source_id for item in applicable_constraints),
        formula="typed constraint count and intersection area",
    )
    return result


@dataclass(frozen=True, slots=True)
class RiskObservation:
    source_id: str
    risk_type: Literal["clay", "flood", "soil_pollution", "cavity"] | str
    granularity: Literal["point", "zone", "parcel", "commune"]
    commune_code: str
    geometry: BaseGeometry | None
    coverage_known: bool
    severity: str | None = None
    value: dict[str, object] = field(default_factory=lambda: dict[str, object]())
    valid_from: date | None = None
    valid_to: date | None = None

    def applies_at(self, snapshot_at: date) -> bool:
        return (self.valid_from is None or self.valid_from <= snapshot_at) and (
            self.valid_to is None or self.valid_to >= snapshot_at
        )


def compute_risk_features(
    unit_geometry: BaseGeometry,
    observations: list[RiskObservation],
    *,
    commune_code: str,
    snapshot_at: date,
    source_accepted: bool,
) -> dict[str, FeatureResult]:
    codes = ("RISK-001", "RISK-002", "RISK-003", "RISK-004", "RISK-101")
    if not source_accepted:
        return {
            code: _missing(code, "source_not_accepted", "accepted DS-09 observations")
            for code in codes
        }
    if unit_geometry.is_empty or not unit_geometry.is_valid:
        return {code: _missing(code, "invalid_geometry", "risk geometry context") for code in codes}

    current = [
        item
        for item in observations
        if item.commune_code == commune_code and item.applies_at(snapshot_at)
    ]
    contextual = [item for item in current if item.granularity == "commune"]
    fine = [item for item in current if item.granularity != "commune"]
    intersecting = [
        item
        for item in fine
        if item.geometry is not None
        and item.geometry.is_valid
        and item.geometry.intersects(unit_geometry)
    ]
    sources = tuple(item.source_id for item in current)

    clay = [item for item in intersecting if item.risk_type == "clay"]
    result: dict[str, FeatureResult] = {}
    if clay:
        result["RISK-001"] = FeatureResult(
            code="RISK-001",
            text_value=max(item.severity or "unknown" for item in clay),
            source_ids=tuple(item.source_id for item in clay),
            formula="fine-grained intersecting clay exposure only",
        )
    else:
        result["RISK-001"] = _missing(
            "RISK-001", "source_value_missing", "fine-grained intersecting clay exposure"
        )

    flood = [item for item in intersecting if item.risk_type == "flood"]
    known_flood_coverage = any(item.risk_type == "flood" and item.coverage_known for item in fine)
    if flood or known_flood_coverage:
        result["RISK-002"] = FeatureResult(
            code="RISK-002",
            json_value={
                "overlap": bool(flood),
                "observations": [
                    {
                        "source_id": item.source_id,
                        "severity": item.severity,
                        "granularity": item.granularity,
                    }
                    for item in flood
                ],
            },
            source_ids=tuple(item.source_id for item in flood),
            formula="typed overlap with covered fine-grained flood zones",
        )
    else:
        result["RISK-002"] = _missing("RISK-002", "source_value_missing", "covered flood zones")

    pollution = [item for item in fine if item.risk_type == "soil_pollution" and item.geometry]
    if pollution and any(item.coverage_known for item in pollution):
        nearest = min(
            float(item.geometry.distance(unit_geometry)) for item in pollution if item.geometry
        )
        result["RISK-003"] = FeatureResult(
            code="RISK-003",
            json_value={"intersects": nearest == 0, "distance_m": nearest},
            source_ids=tuple(item.source_id for item in pollution),
            formula="SIS intersection or distance to covered known sites",
        )
    else:
        result["RISK-003"] = _missing(
            "RISK-003", "source_value_missing", "covered soil pollution geometries"
        )

    cavities = [item for item in fine if item.risk_type == "cavity" and item.geometry]
    if cavities and any(item.coverage_known for item in cavities):
        nearest_cavity = min(
            float(item.geometry.distance(unit_geometry)) for item in cavities if item.geometry
        )
        result["RISK-004"] = _number(
            "RISK-004",
            nearest_cavity,
            "distance to covered recorded cavities",
            tuple(item.source_id for item in cavities),
        )
    else:
        result["RISK-004"] = _missing(
            "RISK-004", "source_value_missing", "covered cavity observations"
        )

    result["RISK-101"] = FeatureResult(
        code="RISK-101",
        json_value={
            "applicable": [
                {
                    "source_id": item.source_id,
                    "risk_type": item.risk_type,
                    "granularity": item.granularity,
                    "severity": item.severity,
                }
                for item in intersecting
            ],
            "commune_context_only": [
                {
                    "source_id": item.source_id,
                    "risk_type": item.risk_type,
                    "granularity": item.granularity,
                    "severity": item.severity,
                }
                for item in contextual
            ],
        },
        source_ids=sources,
        formula="preserve applicable and commune-context observations separately",
    )
    return result


def serialize_decision(decision: ComparableDecision) -> str:
    """Stable representation suitable for audit fixtures and manual review."""
    return json.dumps(
        {
            "transaction_id": decision.transaction_id,
            "property_id": decision.property_id,
            "included": decision.included,
            "reason": decision.reason,
            "distance_m": decision.distance_m,
            "segment_code": decision.segment_code,
            "transaction_date": decision.transaction_date.isoformat(),
            "property_type": decision.property_type,
            "surface_m2": decision.surface_m2,
            "normalized_price_m2": decision.normalized_price_m2,
            "price_transformations": decision.price_transformations,
            "source_release_id": decision.source_release_id,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
