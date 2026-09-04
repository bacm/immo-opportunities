import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

from pyproj import Transformer
from shapely import MultiPolygon, make_valid
from shapely.geometry import GeometryCollection, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from immo_pipelines.cadastre.contract import DatasetContract, validate_properties


@dataclass(frozen=True)
class NormalizedFeature:
    layer: str
    source_feature_id: str
    source_row_number: int
    properties: dict[str, Any]
    geometry_wkt: str
    record_checksum: str
    was_repaired: bool
    repair_method: str | None
    transformation_version: str
    unknown_properties: tuple[str, ...]


@dataclass(frozen=True)
class QuarantinedFeature:
    layer: str
    source_feature_id: str | None
    source_row_number: int
    reason_code: str
    reason_detail: str
    source_geometry: dict[str, Any] | None
    source_properties: dict[str, Any]
    repair_attempted: bool
    transformation_version: str


class CadastreFeatureProcessor:
    def __init__(self, contract: DatasetContract) -> None:
        self.contract = contract
        self._transformer = Transformer.from_crs(
            contract.source_srid,
            contract.canonical_srid,
            always_xy=True,
        )

    def process(
        self, layer: str, row_number: int, feature: dict[str, Any]
    ) -> NormalizedFeature | QuarantinedFeature:
        layer_contract = self.contract.layer(layer)
        properties_value = feature.get("properties")
        if not isinstance(properties_value, dict):
            properties: dict[str, Any] = {}
        else:
            properties = cast(dict[str, Any], properties_value)
        unknown = validate_properties(layer_contract, properties)
        source_id_value = feature.get("id") or properties.get("id")
        source_id = str(source_id_value) if source_id_value is not None else None
        if source_id is None and layer == "batiments":
            source_id = _record_checksum(feature)

        geometry_value = feature.get("geometry")
        source_geometry = (
            cast(dict[str, Any], geometry_value) if isinstance(geometry_value, dict) else None
        )
        if source_geometry is None:
            return self._quarantine(
                layer,
                source_id,
                row_number,
                "missing_geometry",
                "Geometry is null",
                properties,
                None,
            )

        try:
            source_shape = shape(source_geometry)
        except (TypeError, ValueError) as exc:
            return self._quarantine(
                layer,
                source_id,
                row_number,
                "unreadable_geometry",
                str(exc),
                properties,
                source_geometry,
            )

        source_type = source_shape.geom_type
        if source_type not in self.contract.allowed_geometry_types:
            return self._quarantine(
                layer,
                source_id,
                row_number,
                "unsupported_geometry_type",
                f"Expected polygonal geometry, got {source_type}",
                properties,
                source_geometry,
            )

        source_was_repaired = not source_shape.is_valid
        candidate = make_valid(source_shape) if source_was_repaired else source_shape
        polygonal = _polygonal_only(candidate)
        if polygonal is None or polygonal.is_empty or not polygonal.is_valid:
            return self._quarantine(
                layer,
                source_id,
                row_number,
                "unrepairable_geometry",
                "make_valid did not produce a non-empty valid polygonal geometry",
                properties,
                source_geometry,
                repair_attempted=source_was_repaired,
            )

        canonical = transform(self._transformer.transform, polygonal)
        canonical_was_repaired = not canonical.is_valid
        canonical_candidate = make_valid(canonical) if canonical_was_repaired else canonical
        canonical_polygonal = _polygonal_only(canonical_candidate)
        if (
            canonical_polygonal is None
            or canonical_polygonal.is_empty
            or not canonical_polygonal.is_valid
        ):
            return self._quarantine(
                layer,
                source_id,
                row_number,
                "invalid_canonical_geometry",
                "Reprojection did not produce a repairable valid polygonal geometry",
                properties,
                source_geometry,
                repair_attempted=canonical_was_repaired,
            )
        if source_id is None:
            return self._quarantine(
                layer,
                None,
                row_number,
                "missing_source_id",
                "Layer requires a stable source id",
                properties,
                source_geometry,
            )
        was_repaired = source_was_repaired or canonical_was_repaired
        return NormalizedFeature(
            layer=layer,
            source_feature_id=source_id,
            source_row_number=row_number,
            properties=properties,
            geometry_wkt=canonical_polygonal.wkt,
            record_checksum=_record_checksum(feature),
            was_repaired=was_repaired,
            repair_method=self.contract.repair_version if was_repaired else None,
            transformation_version=self.contract.normalization_version,
            unknown_properties=unknown,
        )

    def _quarantine(
        self,
        layer: str,
        source_id: str | None,
        row_number: int,
        reason_code: str,
        reason_detail: str,
        properties: dict[str, Any],
        source_geometry: dict[str, Any] | None,
        *,
        repair_attempted: bool = False,
    ) -> QuarantinedFeature:
        return QuarantinedFeature(
            layer=layer,
            source_feature_id=source_id,
            source_row_number=row_number,
            reason_code=reason_code,
            reason_detail=reason_detail,
            source_geometry=source_geometry,
            source_properties=properties,
            repair_attempted=repair_attempted,
            transformation_version=self.contract.repair_version,
        )


def _polygonal_only(value: BaseGeometry) -> MultiPolygon | None:
    if isinstance(value, Polygon):
        return MultiPolygon([value])
    if isinstance(value, MultiPolygon):
        return value
    if isinstance(value, GeometryCollection):
        polygons: list[Polygon] = []
        geometries = cast(Sequence[BaseGeometry], value.geoms)  # pyright: ignore[reportUnknownMemberType]
        for geometry in geometries:
            if isinstance(geometry, Polygon):
                polygons.append(geometry)
            elif isinstance(geometry, MultiPolygon):
                polygons.extend(geometry.geoms)
        return MultiPolygon(polygons) if polygons else None
    return None


def _record_checksum(feature: dict[str, Any]) -> str:
    canonical = json.dumps(feature, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
