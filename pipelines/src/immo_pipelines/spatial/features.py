import math
import warnings
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal, cast

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

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
    missing_reason: MissingReason | None = None
    source_ids: tuple[str, ...] = ()
    formula: str = ""
    transformation_version: str = "morphology@1"
    confidence: float | None = None

    def __post_init__(self) -> None:
        populated = sum(
            value is not None
            for value in (self.numeric_value, self.text_value, self.missing_reason)
        )
        if populated != 1:
            raise ValueError("A feature must have exactly one value or missing reason")


@dataclass(frozen=True, slots=True)
class BuildingFootprint:
    entity_id: str
    geometry: BaseGeometry
    source_ids: tuple[str, ...]
    is_light_construction: bool | None = None


@dataclass(frozen=True, slots=True)
class ObservedValue[Observed: (str, float, int)]:
    value: Observed
    source_id: str
    dataset_id: str
    priority: int
    confidence: float
    predicted: bool = False


def _missing(code: str, reason: MissingReason, formula: str) -> FeatureResult:
    return FeatureResult(code=code, missing_reason=reason, formula=formula)


def _number(
    code: str,
    value: float,
    formula: str,
    sources: tuple[str, ...],
) -> FeatureResult:
    return FeatureResult(
        code=code,
        numeric_value=float(value),
        source_ids=sources,
        formula=formula,
    )


def _valid_geometry(geometry: BaseGeometry) -> bool:
    return not geometry.is_empty and geometry.is_valid


def _width_proxy(geometry: BaseGeometry) -> float | None:
    # GEOS can emit harmless floating-point warnings for axis-aligned rectangles.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rectangle = geometry.minimum_rotated_rectangle
    if rectangle.is_empty or not isinstance(rectangle, Polygon):
        return None
    coordinates = cast(list[tuple[float, float]], list(rectangle.exterior.coords))
    lengths = [
        math.hypot(second[0] - first[0], second[1] - first[1])
        for first, second in pairwise(coordinates)
    ]
    positive = [length for length in lengths if length > 0]
    return min(positive) if positive else None


def compute_land_features(
    parcel_geometries: list[BaseGeometry],
    buildings: list[BuildingFootprint],
    *,
    building_resolution_complete: bool,
    roads: list[BaseGeometry] | None = None,
    roads_accepted: bool = False,
    road_distance_threshold_m: float = 3.0,
    bdtopo_accepted: bool = False,
) -> dict[str, FeatureResult]:
    """Compute LAND-001..010 without turning unavailable values into zero."""
    formulas = {
        "LAND-001": "area(union(resolved parcels))",
        "LAND-002": "area(intersection(unit, union(resolved buildings)))",
        "LAND-003": "LAND-002 / LAND-001",
        "LAND-004": "LAND-001 - LAND-002",
        "LAND-005": "4 * pi * area / perimeter^2",
        "LAND-006": "shortest edge(minimum rotated rectangle(unit))",
        "LAND-007": "distance(union(resolved buildings), boundary(unit))",
        "LAND-008": "length(intersection(boundary(unit), buffer(public roads, threshold)))",
        "LAND-009": "count(distinct resolved physical buildings)",
        "LAND-010": "area(union(light buildings)) / LAND-002",
    }
    if not parcel_geometries or any(not _valid_geometry(item) for item in parcel_geometries):
        return {
            code: _missing(code, "invalid_geometry", formula) for code, formula in formulas.items()
        }

    unit_geometry = unary_union(parcel_geometries)
    if not _valid_geometry(unit_geometry) or unit_geometry.area <= 0:
        return {
            code: _missing(code, "invalid_geometry", formula) for code, formula in formulas.items()
        }

    parcel_sources = tuple(f"parcel:{index}" for index in range(len(parcel_geometries)))
    results: dict[str, FeatureResult] = {}
    parcel_area = float(unit_geometry.area)
    results["LAND-001"] = _number("LAND-001", parcel_area, formulas["LAND-001"], parcel_sources)

    perimeter = float(unit_geometry.length)
    results["LAND-005"] = (
        _number(
            "LAND-005",
            4 * math.pi * parcel_area / (perimeter * perimeter),
            formulas["LAND-005"],
            parcel_sources,
        )
        if perimeter > 0
        else _missing("LAND-005", "invalid_geometry", formulas["LAND-005"])
    )
    width = _width_proxy(unit_geometry)
    results["LAND-006"] = (
        _number("LAND-006", width, formulas["LAND-006"], parcel_sources)
        if width is not None
        else _missing("LAND-006", "invalid_geometry", formulas["LAND-006"])
    )

    valid_buildings = [item for item in buildings if _valid_geometry(item.geometry)]
    building_sources = tuple(
        source for item in valid_buildings for source in (item.entity_id, *item.source_ids)
    )
    if not building_resolution_complete:
        for code in ("LAND-002", "LAND-003", "LAND-004", "LAND-007", "LAND-009"):
            results[code] = _missing(code, "ambiguous_match", formulas[code])
        building_footprint = None
        building_union: BaseGeometry | None = None
    else:
        building_union = unary_union([item.geometry for item in valid_buildings])
        building_footprint = (
            float(building_union.intersection(unit_geometry).area) if valid_buildings else 0.0
        )
        results["LAND-002"] = _number(
            "LAND-002", building_footprint, formulas["LAND-002"], building_sources
        )
        results["LAND-003"] = _number(
            "LAND-003", building_footprint / parcel_area, formulas["LAND-003"], building_sources
        )
        results["LAND-004"] = _number(
            "LAND-004",
            max(parcel_area - building_footprint, 0.0),
            formulas["LAND-004"],
            building_sources,
        )
        results["LAND-007"] = (
            _number(
                "LAND-007",
                float(building_union.distance(unit_geometry.boundary)),
                formulas["LAND-007"],
                building_sources,
            )
            if valid_buildings
            else _missing("LAND-007", "not_applicable", formulas["LAND-007"])
        )
        results["LAND-009"] = _number(
            "LAND-009", float(len(valid_buildings)), formulas["LAND-009"], building_sources
        )

    if not roads_accepted:
        results["LAND-008"] = _missing("LAND-008", "source_not_accepted", formulas["LAND-008"])
    elif not roads:
        results["LAND-008"] = _missing("LAND-008", "source_value_missing", formulas["LAND-008"])
    else:
        road_union = unary_union(roads)
        access_length = unit_geometry.boundary.intersection(
            road_union.buffer(road_distance_threshold_m)
        ).length
        results["LAND-008"] = _number(
            "LAND-008", float(access_length), formulas["LAND-008"], ("DS-04:roads",)
        )

    if not bdtopo_accepted:
        results["LAND-010"] = _missing("LAND-010", "source_not_accepted", formulas["LAND-010"])
    elif building_footprint is None:
        results["LAND-010"] = _missing("LAND-010", "ambiguous_match", formulas["LAND-010"])
    elif building_footprint == 0:
        results["LAND-010"] = _missing("LAND-010", "not_applicable", formulas["LAND-010"])
    else:
        light_geometries = [
            item.geometry for item in valid_buildings if item.is_light_construction is True
        ]
        light_area = (
            float(unary_union(light_geometries).intersection(unit_geometry).area)
            if light_geometries
            else 0.0
        )
        results["LAND-010"] = _number(
            "LAND-010", light_area / building_footprint, formulas["LAND-010"], building_sources
        )
    return results


def _select_observation[Observed: (str, float, int)](
    code: str,
    observations: list[ObservedValue[Observed]],
    formula: str,
) -> FeatureResult:
    observed = [item for item in observations if not item.predicted]
    if not observed:
        return _missing(code, "source_value_missing", formula)
    ranked = sorted(observed, key=lambda item: (item.priority, item.confidence), reverse=True)
    best = ranked[0]
    contradictions = [
        item for item in ranked[1:] if item.priority == best.priority and item.value != best.value
    ]
    if contradictions:
        return _missing(code, "ambiguous_match", formula)
    if isinstance(best.value, str):
        return FeatureResult(
            code=code,
            text_value=best.value,
            source_ids=(best.source_id,),
            formula=formula,
            transformation_version="building-observation@1",
            confidence=best.confidence,
        )
    return FeatureResult(
        code=code,
        numeric_value=float(best.value),
        source_ids=(best.source_id,),
        formula=formula,
        transformation_version="building-observation@1",
        confidence=best.confidence,
    )


def compute_building_features(
    *,
    uses: list[ObservedValue[str]],
    heights_m: list[ObservedValue[float]],
    dwelling_counts: list[ObservedValue[int]],
) -> dict[str, FeatureResult]:
    return {
        "BLD-001": _select_observation(
            "BLD-001", uses, "highest-priority observed use without prediction"
        ),
        "BLD-002": _select_observation(
            "BLD-002", heights_m, "highest-priority observed height without imputation"
        ),
        "BLD-003": _select_observation(
            "BLD-003",
            dwelling_counts,
            "highest-priority observed dwelling count without imputation",
        ),
    }
