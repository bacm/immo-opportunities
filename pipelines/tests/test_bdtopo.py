"""Lecture du GeoPackage BD TOPO (DS-04) — B2b.

Les fixtures sont construites ici, en SQLite, plutot que copiees de l'archive reelle : un
GeoPackage de 3,1 Go n'a pas sa place dans le depot, et ce qu'il faut prouver est la
normalisation, pas la donnee.
"""

import sqlite3
import struct
from pathlib import Path

import pytest
from shapely import to_wkb
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from immo_pipelines.cadastre.contract import SchemaChangeError
from immo_pipelines.spatial.bdtopo import (
    BdtopoBuilding,
    BdtopoQuarantine,
    BdtopoRoad,
    iter_bdtopo_buildings,
    iter_bdtopo_rnb_links,
    iter_bdtopo_roads,
)

BUILDING_COLUMNS = (
    "cleabs TEXT",
    "geometrie BLOB",
    "nature TEXT",
    "usage_1 TEXT",
    "usage_2 TEXT",
    "construction_legere BOOLEAN",
    "etat_de_l_objet TEXT",
    "hauteur REAL",
    "nombre_de_logements INTEGER",
    "nombre_d_etages INTEGER",
    "identifiants_rnb TEXT",
)
ROAD_COLUMNS = (
    "cleabs TEXT",
    "geometrie BLOB",
    "nature TEXT",
    "importance TEXT",
    "prive BOOLEAN",
    "fictif BOOLEAN",
    "insee_commune_gauche TEXT",
    "insee_commune_droite TEXT",
)


def gpkg_blob(geometry: BaseGeometry, *, srid: int = 2154, with_envelope: bool = False) -> bytes:
    """Envelopper du WKB dans un en-tete GPKG, comme le fait l'IGN."""
    flags = 0x01 | (0x02 if with_envelope else 0x00)
    header = b"GP" + bytes([0, flags]) + struct.pack("<i", srid)
    envelope = b""
    if with_envelope:
        min_x, min_y, max_x, max_y = geometry.bounds
        envelope = struct.pack("<dddd", min_x, max_x, min_y, max_y)
    return header + envelope + to_wkb(geometry)


def build_geopackage(
    path: Path, buildings: list[tuple], roads: list[tuple], links: list[tuple]
) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        f"CREATE TABLE batiment (fid INTEGER PRIMARY KEY, {', '.join(BUILDING_COLUMNS)})"
    )
    connection.execute(
        f"CREATE TABLE troncon_de_route (fid INTEGER PRIMARY KEY, {', '.join(ROAD_COLUMNS)})"
    )
    connection.execute(
        "CREATE TABLE batiment_rnb_lien_bdtopo ("
        "fid INTEGER PRIMARY KEY, cleabs TEXT, identifiant_rnb TEXT, liens_vers_batiment TEXT)"
    )
    connection.executemany(
        f"INSERT INTO batiment ({', '.join(c.split()[0] for c in BUILDING_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(BUILDING_COLUMNS))})",
        buildings,
    )
    connection.executemany(
        f"INSERT INTO troncon_de_route ({', '.join(c.split()[0] for c in ROAD_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(ROAD_COLUMNS))})",
        roads,
    )
    connection.executemany(
        "INSERT INTO batiment_rnb_lien_bdtopo (cleabs, identifiant_rnb, liens_vers_batiment) "
        "VALUES (?, ?, ?)",
        links,
    )
    connection.commit()
    connection.close()


SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
SQUARE_3D = Polygon([(0, 0, 12.5), (10, 0, 12.5), (10, 10, 13.0), (0, 10, 13.0)])
LINE_3D = LineString([(0, 0, 5.0), (10, 10, 6.0)])


def one_building(**overrides: object) -> tuple:
    row = {
        "cleabs": "BATIMENT0000000000000001",
        "geometrie": gpkg_blob(SQUARE_3D),
        "nature": "Indifférenciée",
        "usage_1": "Résidentiel",
        "usage_2": None,
        "construction_legere": 0,
        "etat_de_l_objet": "En service",
        "hauteur": 6.5,
        "nombre_de_logements": 2,
        "nombre_d_etages": 1,
        "identifiants_rnb": "AAAA1111BBBB",
    }
    row.update(overrides)
    return tuple(row[column.split()[0]] for column in BUILDING_COLUMNS)


def one_road(**overrides: object) -> tuple:
    row = {
        "cleabs": "TRONROUT0000000000000001",
        "geometrie": gpkg_blob(LINE_3D),
        "nature": "Route à 1 chaussée",
        "importance": "5",
        "prive": 0,
        "fictif": 0,
        "insee_commune_gauche": "35238",
        "insee_commune_droite": "35239",
    }
    row.update(overrides)
    return tuple(row[column.split()[0]] for column in ROAD_COLUMNS)


@pytest.fixture
def geopackage(tmp_path: Path) -> Path:
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [one_building()], [one_road()], [])
    return path


def test_building_altimetry_is_dropped_and_geometry_stays_polygonal(geopackage: Path) -> None:
    """Les colonnes canoniques sont 2D : l'altitude est perdue, la geometrie ne l'est pas."""
    (record,) = list(iter_bdtopo_buildings(geopackage))
    assert isinstance(record, BdtopoBuilding)
    assert record.geometry_wkt.startswith("MULTIPOLYGON")
    assert " 12.5" not in record.geometry_wkt
    assert record.height_m == 6.5


def test_building_attributes_are_preserved(geopackage: Path) -> None:
    (record,) = list(iter_bdtopo_buildings(geopackage))
    assert isinstance(record, BdtopoBuilding)
    assert record.rnb_identifiers == ("AAAA1111BBBB",)
    assert record.is_light_construction is False
    assert record.lifecycle_state == "En service"
    assert record.dwelling_count == 2
    assert "nature" in record.properties


def test_light_construction_absence_is_not_false(tmp_path: Path) -> None:
    """`construction_legere` NULL veut dire inconnu, jamais « construction ordinaire »."""
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [one_building(construction_legere=None)], [], [])
    (record,) = list(iter_bdtopo_buildings(path))
    assert isinstance(record, BdtopoBuilding)
    assert record.is_light_construction is None


def test_several_rnb_identifiers_are_all_kept(tmp_path: Path) -> None:
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [one_building(identifiants_rnb="AAAA1111BBBB/CCCC2222DDDD")], [], [])
    (record,) = list(iter_bdtopo_buildings(path))
    assert isinstance(record, BdtopoBuilding)
    assert record.rnb_identifiers == ("AAAA1111BBBB", "CCCC2222DDDD")


def test_building_without_rnb_identifier_is_not_an_error(tmp_path: Path) -> None:
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [one_building(identifiants_rnb=None)], [], [])
    (record,) = list(iter_bdtopo_buildings(path))
    assert isinstance(record, BdtopoBuilding)
    assert record.rnb_identifiers == ()


def test_envelope_header_is_skipped(tmp_path: Path) -> None:
    """L'en-tete GPKG peut porter une enveloppe : la sauter, sinon le WKB est illisible."""
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [one_building(geometrie=gpkg_blob(SQUARE, with_envelope=True))], [], [])
    (record,) = list(iter_bdtopo_buildings(path))
    assert isinstance(record, BdtopoBuilding)
    assert record.geometry_wkt.startswith("MULTIPOLYGON")


@pytest.mark.parametrize(
    ("geometry_value", "reason"),
    [
        (gpkg_blob(Point(1, 1)), "no valid polygonal component"),
        (None, "geometry is absent"),
        (b"NOTGPKG", "not a GeoPackage blob"),
    ],
)
def test_unusable_building_geometry_is_quarantined_with_a_motive(
    tmp_path: Path, geometry_value: object, reason: str
) -> None:
    """Un enregistrement inutilisable est retenu avec son motif, jamais ecarte en silence."""
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [one_building(geometrie=geometry_value)], [], [])
    (record,) = list(iter_bdtopo_buildings(path))
    assert isinstance(record, BdtopoQuarantine)
    assert reason in record.reason_detail
    assert record.source_feature_id == "BATIMENT0000000000000001"
    assert record.source_properties["nature"] == "Indifférenciée"


def test_road_geometry_becomes_multilinestring_in_two_dimensions(geopackage: Path) -> None:
    (record,) = list(iter_bdtopo_roads(geopackage))
    assert isinstance(record, BdtopoRoad)
    assert record.geometry_wkt.startswith("MULTILINESTRING")
    assert " 5" not in record.geometry_wkt.split("(")[-1]
    assert record.commune_code_left == "35238"
    assert record.is_private is False


def test_road_with_a_polygon_geometry_is_quarantined(tmp_path: Path) -> None:
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [], [one_road(geometrie=gpkg_blob(MultiPolygon([SQUARE])))], [])
    (record,) = list(iter_bdtopo_roads(path))
    assert isinstance(record, BdtopoQuarantine)
    assert "no valid linear component" in record.reason_detail


def test_out_of_department_commune_code_is_kept_as_read(tmp_path: Path) -> None:
    """L'export du 35 deborde : un code hors departement est une observation, pas une erreur."""
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [], [one_road(insee_commune_gauche="49248")], [])
    (record,) = list(iter_bdtopo_roads(path))
    assert isinstance(record, BdtopoRoad)
    assert record.commune_code_left == "49248"


def test_malformed_commune_code_becomes_absent(tmp_path: Path) -> None:
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(path, [], [one_road(insee_commune_gauche="35")], [])
    (record,) = list(iter_bdtopo_roads(path))
    assert isinstance(record, BdtopoRoad)
    assert record.commune_code_left is None


def test_rnb_link_table_is_read_and_split(tmp_path: Path) -> None:
    path = tmp_path / "bdtopo.gpkg"
    build_geopackage(
        path,
        [],
        [],
        [("BAT_RNB_1", "AAAA1111BBBB", "BATIMENT0000000000000001/BATIMENT0000000000000002")],
    )
    (link,) = list(iter_bdtopo_rnb_links(path))
    assert link.rnb_identifier == "AAAA1111BBBB"
    assert link.building_cleabs == (
        "BATIMENT0000000000000001",
        "BATIMENT0000000000000002",
    )


def test_checksum_ignores_the_local_geopackage_row_id(tmp_path: Path) -> None:
    """Le checksum decrit le contenu : reordonner le fichier ne doit pas le changer."""
    first = tmp_path / "a.gpkg"
    second = tmp_path / "b.gpkg"
    build_geopackage(first, [one_building()], [], [])
    build_geopackage(second, [one_building(), one_building(cleabs="OTHER")], [], [])
    (left,) = list(iter_bdtopo_buildings(first))
    right = next(iter(iter_bdtopo_buildings(second)))
    assert isinstance(left, BdtopoBuilding) and isinstance(right, BdtopoBuilding)
    assert left.record_checksum == right.record_checksum


def test_a_changed_attribute_changes_the_checksum(tmp_path: Path) -> None:
    first = tmp_path / "a.gpkg"
    second = tmp_path / "b.gpkg"
    build_geopackage(first, [one_building()], [], [])
    build_geopackage(second, [one_building(hauteur=9.0)], [], [])
    (left,) = list(iter_bdtopo_buildings(first))
    (right,) = list(iter_bdtopo_buildings(second))
    assert isinstance(left, BdtopoBuilding) and isinstance(right, BdtopoBuilding)
    assert left.record_checksum != right.record_checksum


def test_a_missing_required_column_stops_the_import(tmp_path: Path) -> None:
    """Un schema source qui change doit arreter l'import, pas produire des valeurs vides."""
    path = tmp_path / "bdtopo.gpkg"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE batiment (fid INTEGER PRIMARY KEY, cleabs TEXT)")
    connection.commit()
    connection.close()

    with pytest.raises(SchemaChangeError, match="missing columns"):
        list(iter_bdtopo_buildings(path))


def test_an_export_without_the_rnb_link_table_is_tolerated(tmp_path: Path) -> None:
    """Les editions anciennes n'ont pas cette table : son absence n'est pas une erreur."""
    path = tmp_path / "bdtopo.gpkg"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE unrelated (fid INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    assert list(iter_bdtopo_rnb_links(path)) == []
