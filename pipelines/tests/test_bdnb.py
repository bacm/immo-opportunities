"""Lecture du GeoPackage BDNB Open et politique de champs (DS-03) — B2a.

Les fixtures sont construites ici, en SQLite : le GeoPackage reel pese 2,7 Go et ce qu'il
faut prouver est la normalisation et le perimetre, pas la donnee.
"""

import sqlite3
import struct
from pathlib import Path

import pytest
from shapely import to_wkb
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry

from immo_pipelines.cadastre.contract import SchemaChangeError
from immo_pipelines.spatial.bdnb import (
    FFO_FIELDS,
    BdnbGroup,
    BdnbQuarantine,
    RestrictedFieldError,
    iter_bdnb_group_rnb_links,
    iter_bdnb_groups,
    verify_field_policy,
)

GROUP_COLUMNS = (
    "batiment_groupe_id TEXT",
    "geom_groupe BLOB",
    "code_commune_insee TEXT",
    "code_departement_insee TEXT",
    "code_iris TEXT",
    "code_epci_insee TEXT",
    "s_geom_groupe REAL",
    "contient_fictive_geom_groupe BOOLEAN",
    "ffo_bat_annee_construction INTEGER",
    "ffo_bat_nb_niveau INTEGER",
    "ffo_bat_nb_log INTEGER",
    "ffo_bat_usage_niveau_1_txt TEXT",
    "ffo_bat_mat_mur_txt TEXT",
    "ffo_bat_mat_toit_txt TEXT",
    # Une colonne qui recopie une source primaire : elle ne doit pas etre lue.
    "dpe_representatif_logement_classe_bilan_dpe TEXT",
)

SQUARE_3D = Polygon([(0, 0, 5.0), (10, 0, 5.0), (10, 10, 6.0), (0, 10, 6.0)])


def gpkg_blob(geometry: BaseGeometry, *, srid: int = 2154) -> bytes:
    return b"GP" + bytes([0, 0x01]) + struct.pack("<i", srid) + to_wkb(geometry)


def build_geopackage(
    path: Path,
    groups: list[tuple],
    constructions: list[tuple] | None = None,
    links: list[tuple] | None = None,
    dictionary: list[tuple] | None = None,
) -> None:
    constructions = constructions or []
    links = links or []
    dictionary = dictionary or []
    connection = sqlite3.connect(path)
    columns = ", ".join(GROUP_COLUMNS)
    connection.execute(f"CREATE TABLE batiment_groupe_compile (fid INTEGER PRIMARY KEY, {columns})")
    connection.execute(
        "CREATE TABLE batiment_construction (fid INTEGER PRIMARY KEY, "
        "batiment_construction_id TEXT, batiment_groupe_id TEXT, hauteur REAL)"
    )
    connection.execute(
        "CREATE TABLE rel_batiment_construction_rnb (fid INTEGER PRIMARY KEY, "
        "batiment_construction_id TEXT, rnb_id TEXT, type_appariement TEXT)"
    )
    connection.execute(
        "CREATE TABLE metadonnees_colonne (nom_colonne TEXT, nom_table TEXT, "
        "contrainte_acces TEXT, statut TEXT)"
    )
    connection.execute(
        "CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT, srs_id INTEGER)"
    )
    names = [c.split()[0] for c in GROUP_COLUMNS]
    connection.executemany(
        f"INSERT INTO batiment_groupe_compile ({', '.join(names)}) "
        f"VALUES ({', '.join('?' * len(names))})",
        groups,
    )
    connection.executemany(
        "INSERT INTO batiment_construction "
        "(batiment_construction_id, batiment_groupe_id, hauteur) VALUES (?, ?, ?)",
        constructions,
    )
    connection.executemany(
        "INSERT INTO rel_batiment_construction_rnb "
        "(batiment_construction_id, rnb_id, type_appariement) VALUES (?, ?, ?)",
        links,
    )
    connection.executemany(
        "INSERT INTO metadonnees_colonne "
        "(nom_colonne, nom_table, contrainte_acces, statut) VALUES (?, ?, ?, ?)",
        dictionary,
    )
    connection.executemany(
        "INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES (?, ?, ?)",
        [
            ("batiment_groupe_compile", "features", 2154),
            ("batiment_construction", "features", 2154),
            ("rel_batiment_construction_rnb", "features", 2154),
        ],
    )
    connection.commit()
    connection.close()


def one_group(**overrides: object) -> tuple:
    row = {
        "batiment_groupe_id": "bdnb-bg-0001-AAAA-BBBB",
        "geom_groupe": gpkg_blob(SQUARE_3D),
        "code_commune_insee": "35238",
        "code_departement_insee": "35",
        "code_iris": "352380000",
        "code_epci_insee": "243500139",
        "s_geom_groupe": 100.0,
        "contient_fictive_geom_groupe": 0,
        "ffo_bat_annee_construction": 1967,
        "ffo_bat_nb_niveau": 2,
        "ffo_bat_nb_log": 1,
        "ffo_bat_usage_niveau_1_txt": "Résidentiel individuel",
        "ffo_bat_mat_mur_txt": "AGGLOMERE",
        "ffo_bat_mat_toit_txt": "ARDOISES",
        "dpe_representatif_logement_classe_bilan_dpe": "D",
    }
    row.update(overrides)
    return tuple(row[c.split()[0]] for c in GROUP_COLUMNS)


ALIGNED = "Alignement 1 BC = 1 RNB, recouvrement géométrique ≥ 95%"
DIVERGING = "Association 1 RNB pour 1 BC, mais surfaces divergentes"


@pytest.fixture
def geopackage(tmp_path: Path) -> Path:
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(path, [one_group()])
    return path


def test_the_six_retained_fields_are_read(geopackage: Path) -> None:
    (record,) = list(iter_bdnb_groups(geopackage))
    assert isinstance(record, BdnbGroup)
    assert record.construction_year == 1967
    assert record.storey_count == 2
    assert record.dwelling_count == 1
    assert record.usage_label == "Résidentiel individuel"
    assert record.wall_material == "AGGLOMERE"
    assert record.roof_material == "ARDOISES"


def test_columns_copying_a_primary_source_are_not_read(geopackage: Path) -> None:
    """149 colonnes DPE et 34 DVF recopient DS-07 et DS-06 : ne pas les charger."""
    (record,) = list(iter_bdnb_groups(geopackage))
    assert isinstance(record, BdnbGroup)
    assert not any("dpe" in key for key in record.properties)
    assert len(FFO_FIELDS) == 6


def test_group_altimetry_is_dropped(geopackage: Path) -> None:
    (record,) = list(iter_bdnb_groups(geopackage))
    assert isinstance(record, BdnbGroup)
    assert record.geometry_wkt.startswith("MULTIPOLYGON")
    assert " 5" not in record.geometry_wkt.split("((")[-1].split(",")[0]


def test_fictitious_geometry_is_flagged_not_hidden(tmp_path: Path) -> None:
    """Une geometrie fictive est declaree par le producteur : la conserver etiquetee."""
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(path, [one_group(contient_fictive_geom_groupe=1)])
    (record,) = list(iter_bdnb_groups(path))
    assert isinstance(record, BdnbGroup)
    assert record.has_fictitious_geometry is True


def test_an_absent_attribute_stays_absent(tmp_path: Path) -> None:
    """Jamais converti en zero : une annee inconnue reste inconnue."""
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(path, [one_group(ffo_bat_annee_construction=None, ffo_bat_nb_log=None)])
    (record,) = list(iter_bdnb_groups(path))
    assert isinstance(record, BdnbGroup)
    assert record.construction_year is None
    assert record.dwelling_count is None


def test_unusable_geometry_is_quarantined_with_a_motive(tmp_path: Path) -> None:
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(path, [one_group(geom_groupe=gpkg_blob(LineString([(0, 0), (1, 1)])))])
    (record,) = list(iter_bdnb_groups(path))
    assert isinstance(record, BdnbQuarantine)
    assert "no valid polygonal component" in record.reason_detail
    assert record.source_feature_id == "bdnb-bg-0001-AAAA-BBBB"


def test_a_group_resolving_to_one_aligned_building_is_single_and_aligned(tmp_path: Path) -> None:
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(
        path,
        [one_group()],
        constructions=[("BC1", "bdnb-bg-0001-AAAA-BBBB", 6.0)],
        links=[("BC1", "RNB0001", ALIGNED)],
    )
    (link,) = list(iter_bdnb_group_rnb_links(path))
    assert link.is_single_building_group
    assert link.is_fully_aligned
    assert link.rnb_id == "RNB0001"


def test_a_group_spanning_several_buildings_is_never_single(tmp_path: Path) -> None:
    """Le contrat interdit de reduire un groupe a un batiment : la cardinalite est reelle."""
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(
        path,
        [one_group()],
        constructions=[
            ("BC1", "bdnb-bg-0001-AAAA-BBBB", 6.0),
            ("BC2", "bdnb-bg-0001-AAAA-BBBB", 7.0),
        ],
        links=[("BC1", "RNB0001", ALIGNED), ("BC2", "RNB0002", ALIGNED)],
    )
    links = list(iter_bdnb_group_rnb_links(path))
    assert len(links) == 2
    assert all(not link.is_single_building_group for link in links)
    assert all(link.rnb_count_for_group == 2 for link in links)


def test_a_diverging_relation_breaks_the_alignment(tmp_path: Path) -> None:
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(
        path,
        [one_group()],
        constructions=[
            ("BC1", "bdnb-bg-0001-AAAA-BBBB", 6.0),
            ("BC2", "bdnb-bg-0001-AAAA-BBBB", 7.0),
        ],
        links=[("BC1", "RNB0001", ALIGNED), ("BC2", "RNB0001", DIVERGING)],
    )
    (link,) = list(iter_bdnb_group_rnb_links(path))
    assert link.is_single_building_group
    assert not link.is_fully_aligned
    assert link.relation_count == 2
    assert link.aligned_relation_count == 1


def test_a_restricted_column_blocks_the_import(tmp_path: Path) -> None:
    """Controle bloquant du contrat, appuye sur le dictionnaire du producteur."""
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(
        path,
        [one_group()],
        dictionary=[
            ("batiment_groupe_id", "batiment_groupe_compile", "open_data_lo", "maintenu"),
            (
                "ffo_bat_annee_construction",
                "batiment_groupe_compile",
                "ayant_droit_ffo_expert",
                "maintenu",
            ),
        ],
    )
    with pytest.raises(RestrictedFieldError, match="rights-holder"):
        verify_field_policy(path)


def test_an_export_with_only_open_columns_passes_the_policy(tmp_path: Path) -> None:
    path = tmp_path / "bdnb.gpkg"
    build_geopackage(
        path,
        [one_group()],
        dictionary=[
            ("batiment_groupe_id", "batiment_groupe_compile", "open_data_lo", "maintenu"),
            ("ffo_bat_nb_log", "batiment_groupe_compile", "open_data_lo", "expérimental"),
        ],
    )
    result = verify_field_policy(path)
    assert result["restricted_columns"] == 0
    assert result["experimental_columns"] == 1


def test_a_missing_required_column_stops_the_import(tmp_path: Path) -> None:
    path = tmp_path / "bdnb.gpkg"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE batiment_groupe_compile (fid INTEGER PRIMARY KEY, batiment_groupe_id TEXT)"
    )
    connection.commit()
    connection.close()

    with pytest.raises(SchemaChangeError, match="missing columns"):
        list(iter_bdnb_groups(path))
