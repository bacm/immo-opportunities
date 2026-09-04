import csv
import hashlib
import io
import json
import sys
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pyproj import Transformer
from shapely import MultiPolygon, from_wkt, make_valid
from shapely.geometry import GeometryCollection, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from immo_pipelines.cadastre.contract import SchemaChangeError

RNB_REQUIRED_COLUMNS = frozenset(
    {"rnb_id", "point", "shape", "status", "ext_ids", "addresses", "plots", "validated_by"}
)


@dataclass(frozen=True, slots=True)
class RnbRecord:
    source_row_number: int
    rnb_id: str
    status: str
    commune_code: str | None
    geometry_wkt: str
    geometry_type: str
    external_ids: tuple[dict[str, object], ...]
    addresses: tuple[dict[str, object], ...]
    plots: tuple[dict[str, object], ...]
    validated_by: tuple[dict[str, object], ...]
    record_checksum: str


@dataclass(frozen=True, slots=True)
class RnbQuarantine:
    source_row_number: int
    rnb_id: str | None
    reason_code: str
    reason_detail: str
    source_properties: dict[str, object]


def _json_array(value: str, column: str) -> tuple[dict[str, object], ...]:
    try:
        parsed: object = json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {column} JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"{column} must be an array of objects")
    items = cast(list[object], parsed)
    if any(not isinstance(item, dict) for item in items):
        raise ValueError(f"{column} must be an array of objects")
    return tuple(cast(list[dict[str, object]], items))


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


def _canonical_geometry(value: str, transformer: Transformer) -> tuple[str, str]:
    prefix, separator, source_wkt = value.partition(";")
    if separator != ";" or prefix != "SRID=4326":
        raise ValueError("RNB geometry must declare SRID=4326")
    source: BaseGeometry = from_wkt(source_wkt)
    if source.is_empty:
        raise ValueError("RNB geometry is empty")
    if source.geom_type == "Point":
        canonical_point = transform(transformer.transform, source)
        return canonical_point.wkt, "Point"
    if source.geom_type not in {"Polygon", "MultiPolygon", "GeometryCollection"}:
        raise ValueError(f"Unsupported RNB geometry type {source.geom_type}")
    repaired: BaseGeometry = make_valid(source) if not source.is_valid else source
    polygonal = _polygonal_only(repaired)
    if polygonal is None or polygonal.is_empty or not polygonal.is_valid:
        raise ValueError("RNB geometry has no valid polygonal component")
    canonical = transform(transformer.transform, polygonal)
    canonical_repaired = make_valid(canonical) if not canonical.is_valid else canonical
    canonical_polygonal = _polygonal_only(canonical_repaired)
    if (
        canonical_polygonal is None
        or canonical_polygonal.is_empty
        or not canonical_polygonal.is_valid
    ):
        raise ValueError("RNB geometry is invalid after reprojection")
    return canonical_polygonal.wkt, "MultiPolygon"


def _commune_code(
    plots: tuple[dict[str, object], ...], addresses: tuple[dict[str, object], ...]
) -> str | None:
    for plot in plots:
        identifier = plot.get("id")
        if isinstance(identifier, str) and len(identifier) >= 5:
            return identifier[:5]
    for address in addresses:
        identifier = address.get("cle_interop_ban")
        if isinstance(identifier, str) and len(identifier) >= 5:
            return identifier[:5]
    return None


def _checksum(row: dict[str, str]) -> str:
    canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def iter_rnb_records(path: Path) -> Iterator[RnbRecord | RnbQuarantine]:
    transformer = Transformer.from_crs(4326, 2154, always_xy=True)
    csv.field_size_limit(sys.maxsize)
    with zipfile.ZipFile(path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise SchemaChangeError("RNB archive must contain exactly one CSV file")
        with (
            archive.open(csv_names[0]) as binary,
            io.TextIOWrapper(binary, encoding="utf-8", newline="") as text_stream,
        ):
            reader = csv.DictReader(text_stream, delimiter=";")
            columns = frozenset(reader.fieldnames or [])
            missing = RNB_REQUIRED_COLUMNS - columns
            if missing:
                raise SchemaChangeError(f"RNB CSV is missing columns: {sorted(missing)}")
            for row_number, raw in enumerate(reader, start=1):
                row = {str(key): str(value or "") for key, value in raw.items()}
                rnb_id = row["rnb_id"].strip()
                try:
                    if not rnb_id:
                        raise ValueError("rnb_id is empty")
                    external_ids = _json_array(row["ext_ids"], "ext_ids")
                    addresses = _json_array(row["addresses"], "addresses")
                    plots = _json_array(row["plots"], "plots")
                    validated_by = _json_array(row["validated_by"], "validated_by")
                    geometry_wkt, geometry_type = _canonical_geometry(row["shape"], transformer)
                except ValueError as exc:
                    yield RnbQuarantine(
                        source_row_number=row_number,
                        rnb_id=rnb_id or None,
                        reason_code="invalid_rnb_record",
                        reason_detail=str(exc),
                        source_properties=cast(dict[str, object], row),
                    )
                    continue
                yield RnbRecord(
                    source_row_number=row_number,
                    rnb_id=rnb_id,
                    status=row["status"],
                    commune_code=_commune_code(plots, addresses),
                    geometry_wkt=geometry_wkt,
                    geometry_type=geometry_type,
                    external_ids=external_ids,
                    addresses=addresses,
                    plots=plots,
                    validated_by=validated_by,
                    record_checksum=_checksum(row),
                )
