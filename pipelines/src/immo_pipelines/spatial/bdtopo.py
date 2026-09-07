"""Lecture du GeoPackage BD TOPO (DS-04) : batiments, voirie, et liens RNB publies.

Le GeoPackage est un SQLite dont les geometries sont du WKB precede d'un en-tete GPKG. Le
lire avec `sqlite3` et `shapely` evite d'ajouter GDAL a l'image pour une seule source ; le
projet normalise deja ses geometries avec shapely pour le RNB.

Trois particularites de cet export, mesurees a l'audit :

- les geometries portent une altitude (`has_z`), que les colonnes canoniques 2D refusent :
  elles sont ramenees en 2D, ce qui perd l'altimetrie et rien d'autre ;
- l'export du 35 deborde sur 143 communes limitrophes, donc le departement de rattachement
  ne peut pas etre deduit du nom du fichier ;
- l'identifiant RNB officiel est transporte par la source, dans `batiment.identifiants_rnb`
  et dans la table `batiment_rnb_lien_bdtopo`. Plusieurs identifiants sont separes par `/`.
"""

import hashlib
import json
import sqlite3
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from shapely import (
    force_2d,  # pyright: ignore[reportUnknownVariableType]
    from_wkb,
    make_valid,
)
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from immo_pipelines.cadastre.contract import SchemaChangeError

BDTOPO_TRANSFORMATION_VERSION = "bdtopo-normalize@1"

BUILDING_TABLE = "batiment"
ROAD_TABLE = "troncon_de_route"
RNB_LINK_TABLE = "batiment_rnb_lien_bdtopo"

BUILDING_REQUIRED_COLUMNS = frozenset(
    {"cleabs", "geometrie", "nature", "usage_1", "construction_legere", "etat_de_l_objet"}
)
ROAD_REQUIRED_COLUMNS = frozenset({"cleabs", "geometrie", "nature", "importance"})
RNB_LINK_REQUIRED_COLUMNS = frozenset({"cleabs", "identifiant_rnb", "liens_vers_batiment"})

# Plusieurs valeurs dans un champ BD TOPO sont separees par `/`.
MULTI_VALUE_SEPARATOR = "/"

# Taille de l'enveloppe optionnelle de l'en-tete GPKG, selon le code d'indicateur.
_ENVELOPE_SIZES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


@dataclass(frozen=True, slots=True)
class BdtopoBuilding:
    source_row_number: int
    cleabs: str
    geometry_wkt: str
    rnb_identifiers: tuple[str, ...]
    nature: str | None
    usage_1: str | None
    usage_2: str | None
    is_light_construction: bool | None
    lifecycle_state: str | None
    height_m: float | None
    dwelling_count: int | None
    storey_count: int | None
    properties: dict[str, object]
    record_checksum: str


@dataclass(frozen=True, slots=True)
class BdtopoRoad:
    source_row_number: int
    cleabs: str
    geometry_wkt: str
    commune_code_left: str | None
    commune_code_right: str | None
    nature: str | None
    importance: str | None
    is_private: bool | None
    is_fictitious: bool | None
    properties: dict[str, object]
    record_checksum: str


@dataclass(frozen=True, slots=True)
class BdtopoRnbLink:
    source_row_number: int
    cleabs: str
    rnb_identifier: str
    building_cleabs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BdtopoQuarantine:
    source_row_number: int
    source_feature_id: str | None
    reason_code: str
    reason_detail: str
    source_properties: dict[str, object]


def _strip_gpkg_header(blob: bytes) -> bytes:
    """Retirer l'en-tete GPKG pour ne garder que le WKB."""
    if len(blob) < 8 or blob[:2] != b"GP":
        raise ValueError("Geometry is not a GeoPackage blob")
    envelope_code = (blob[3] >> 1) & 0x07
    envelope_size = _ENVELOPE_SIZES.get(envelope_code)
    if envelope_size is None:
        raise ValueError(f"Unsupported GeoPackage envelope code {envelope_code}")
    return blob[8 + envelope_size :]


def _polygonal_2d(value: BaseGeometry) -> MultiPolygon | None:
    """Ne conserver que la composante polygonale, en deux dimensions."""
    flat = force_2d(value)
    repaired: BaseGeometry = flat if flat.is_valid else make_valid(flat)
    if isinstance(repaired, Polygon):
        return MultiPolygon([repaired])
    if isinstance(repaired, MultiPolygon):
        return repaired
    polygons: list[Polygon] = []
    geometries = cast(Any, getattr(repaired, "geoms", ()))
    for geometry in geometries:
        if isinstance(geometry, Polygon):
            polygons.append(geometry)
        elif isinstance(geometry, MultiPolygon):
            polygons.extend(geometry.geoms)
    return MultiPolygon(polygons) if polygons else None


def _linear_2d(value: BaseGeometry) -> MultiLineString | None:
    flat = force_2d(value)
    if isinstance(flat, LineString):
        return MultiLineString([flat]) if not flat.is_empty else None
    if isinstance(flat, MultiLineString):
        return flat if not flat.is_empty else None
    lines: list[LineString] = []
    geometries = cast(Any, getattr(flat, "geoms", ()))
    for geometry in geometries:
        if isinstance(geometry, LineString):
            lines.append(geometry)
        elif isinstance(geometry, MultiLineString):
            lines.extend(geometry.geoms)
    return MultiLineString(lines) if lines else None


def _boolean(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(cast(float, value))
    except (TypeError, ValueError):
        return None


def _integer(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(cast(int, value))
    except (TypeError, ValueError):
        return None


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _multi_value(value: object) -> tuple[str, ...]:
    text = _text(value)
    if text is None:
        return ()
    return tuple(
        part for part in (item.strip() for item in text.split(MULTI_VALUE_SEPARATOR)) if part
    )


def _commune_code(value: object) -> str | None:
    code = _text(value)
    if code is None or len(code) != 5 or not code[:2].isalnum():
        return None
    return code


def _checksum(row: dict[str, object], geometry: bytes) -> str:
    """Decrire le contenu de l'enregistrement, jamais sa position dans le fichier.

    `fid` est un identifiant local au GeoPackage : l'inclure ferait dependre le checksum de
    l'ordre des lignes, donc changer sans que la donnee change.
    """
    scalars = {
        key: value
        for key, value in row.items()
        if key not in {"fid", "geometrie"} and not isinstance(value, bytes)
    }
    canonical = json.dumps(scalars, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(canonical.encode())
    digest.update(struct.pack("<Q", len(geometry)))
    digest.update(geometry)
    return digest.hexdigest()


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _require_columns(
    connection: sqlite3.Connection, table: str, required: frozenset[str]
) -> frozenset[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise SchemaChangeError(f"BD TOPO GeoPackage has no table {table}")
    columns = frozenset(str(row["name"]) for row in rows)
    missing = required - columns
    if missing:
        raise SchemaChangeError(f"BD TOPO table {table} is missing columns: {sorted(missing)}")
    return columns


def iter_bdtopo_buildings(path: Path) -> Iterator[BdtopoBuilding | BdtopoQuarantine]:
    connection = _connect(path)
    try:
        _require_columns(connection, BUILDING_TABLE, BUILDING_REQUIRED_COLUMNS)
        cursor = connection.execute(f"SELECT * FROM {BUILDING_TABLE} ORDER BY fid")
        for row_number, raw in enumerate(cursor, start=1):
            row = dict(raw)
            cleabs = _text(row.get("cleabs"))
            blob = row.get("geometrie")
            try:
                if cleabs is None:
                    raise ValueError("cleabs is empty")
                if not isinstance(blob, bytes):
                    raise ValueError("geometry is absent")
                geometry = from_wkb(_strip_gpkg_header(blob))
                if geometry.is_empty:
                    raise ValueError("geometry is empty")
                polygonal = _polygonal_2d(geometry)
                if polygonal is None or polygonal.is_empty or not polygonal.is_valid:
                    raise ValueError("geometry has no valid polygonal component")
            except ValueError as exc:
                yield BdtopoQuarantine(
                    source_row_number=row_number,
                    source_feature_id=cleabs,
                    reason_code="invalid_bdtopo_building",
                    reason_detail=str(exc),
                    source_properties=_scalar_properties(row),
                )
                continue
            yield BdtopoBuilding(
                source_row_number=row_number,
                cleabs=cleabs,
                geometry_wkt=polygonal.wkt,
                rnb_identifiers=_multi_value(row.get("identifiants_rnb")),
                nature=_text(row.get("nature")),
                usage_1=_text(row.get("usage_1")),
                usage_2=_text(row.get("usage_2")),
                is_light_construction=_boolean(row.get("construction_legere")),
                lifecycle_state=_text(row.get("etat_de_l_objet")),
                height_m=_number(row.get("hauteur")),
                dwelling_count=_integer(row.get("nombre_de_logements")),
                storey_count=_integer(row.get("nombre_d_etages")),
                properties=_scalar_properties(row),
                record_checksum=_checksum(row, blob),
            )
    finally:
        connection.close()


def iter_bdtopo_roads(path: Path) -> Iterator[BdtopoRoad | BdtopoQuarantine]:
    connection = _connect(path)
    try:
        _require_columns(connection, ROAD_TABLE, ROAD_REQUIRED_COLUMNS)
        cursor = connection.execute(f"SELECT * FROM {ROAD_TABLE} ORDER BY fid")
        for row_number, raw in enumerate(cursor, start=1):
            row = dict(raw)
            cleabs = _text(row.get("cleabs"))
            blob = row.get("geometrie")
            try:
                if cleabs is None:
                    raise ValueError("cleabs is empty")
                if not isinstance(blob, bytes):
                    raise ValueError("geometry is absent")
                geometry = from_wkb(_strip_gpkg_header(blob))
                if geometry.is_empty:
                    raise ValueError("geometry is empty")
                linear = _linear_2d(geometry)
                if linear is None or linear.is_empty or not linear.is_valid:
                    raise ValueError("geometry has no valid linear component")
            except ValueError as exc:
                yield BdtopoQuarantine(
                    source_row_number=row_number,
                    source_feature_id=cleabs,
                    reason_code="invalid_bdtopo_road",
                    reason_detail=str(exc),
                    source_properties=_scalar_properties(row),
                )
                continue
            yield BdtopoRoad(
                source_row_number=row_number,
                cleabs=cleabs,
                geometry_wkt=linear.wkt,
                commune_code_left=_commune_code(row.get("insee_commune_gauche")),
                commune_code_right=_commune_code(row.get("insee_commune_droite")),
                nature=_text(row.get("nature")),
                importance=_text(row.get("importance")),
                is_private=_boolean(row.get("prive")),
                is_fictitious=_boolean(row.get("fictif")),
                properties=_scalar_properties(row),
                record_checksum=_checksum(row, blob),
            )
    finally:
        connection.close()


def iter_bdtopo_rnb_links(path: Path) -> Iterator[BdtopoRnbLink]:
    """Liens RNB publies par la source. Absents d'un export ancien : pas une erreur."""
    connection = _connect(path)
    try:
        try:
            _require_columns(connection, RNB_LINK_TABLE, RNB_LINK_REQUIRED_COLUMNS)
        except SchemaChangeError:
            return
        cursor = connection.execute(
            f"SELECT fid, cleabs, identifiant_rnb, liens_vers_batiment FROM {RNB_LINK_TABLE} "
            "ORDER BY fid"
        )
        for row_number, raw in enumerate(cursor, start=1):
            cleabs = _text(raw["cleabs"])
            rnb_identifier = _text(raw["identifiant_rnb"])
            if cleabs is None or rnb_identifier is None:
                continue
            yield BdtopoRnbLink(
                source_row_number=row_number,
                cleabs=cleabs,
                rnb_identifier=rnb_identifier,
                building_cleabs=_multi_value(raw["liens_vers_batiment"]),
            )
    finally:
        connection.close()


def _scalar_properties(row: dict[str, object]) -> dict[str, object]:
    """Conserver tous les attributs source, sans la geometrie ni l'identifiant local."""
    return {
        key: (value if value is None or isinstance(value, (str, int, float, bool)) else str(value))
        for key, value in row.items()
        if key not in {"fid", "geometrie"} and not isinstance(value, bytes)
    }
