"""Le kit de session terrain — E8h.

Un consommateur de fichiers : il se teste sur des CSV temporaires, sans base. L'invariant central
est qu'il ne peut pas trahir l'origine d'un candidat, parce qu'il ne la lit jamais.
"""

import csv
import importlib.util
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "field_test_kit.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("field_test_kit", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixtures(root: Path) -> None:
    write(
        root / "exploratory-candidates" / "35051" / "liste-aveugle.csv",
        [
            {
                "reference": "C001",
                "cadastral_id": "35051000YE0133",
                "built_year": "1978",
                "parcel_area_m2": "2320.2",
                "footprint_ratio": "0.067",
                "unbuilt_area_m2": "2164.7",
                "width_m": "62.68",
                "boundary_distance_m": "0",
                "building_count": "3",
                "zone": "U|UE3",
                "last_mutation": "",
                "dpe_label": "",
                "dpe_note": "",
                "risks": "clay",
                "latitude": "48.12345",
                "longitude": "-1.60001",
                "map_url": "https://www.geoportail.gouv.fr/carte?c=-1.600010,48.123450&z=19",
                "position_missing": "",
            },
            {
                "reference": "C002",
                "cadastral_id": "35051000ZV0217",
                "built_year": "2006",
                "parcel_area_m2": "1926.7",
                "footprint_ratio": "0.158",
                "unbuilt_area_m2": "1622.2",
                "width_m": "37.6",
                "boundary_distance_m": "5.6",
                "building_count": "1",
                "zone": "U|UE3",
                "last_mutation": "2019-03-04",
                "dpe_label": "D",
                "dpe_note": "",
                "risks": "",
                "latitude": "",
                "longitude": "",
                "map_url": "",
                "position_missing": "géométrie absente",
            },
        ],
    )
    write(
        root / "biens-en-vente" / "35051" / "liste-aveugle.csv",
        [
            {
                "reference": "C001",
                "cadastral_id": "35051000AN0260",
                "dpe_deposited_at": "2026-08-19",
                "dpe_age_months": "0",
                "residual_probability": "0.219",
                "energy_label": "D",
                "label_rate": "0.385",
                "living_area_m2": "80.1",
                "built_year": "1932",
                "parcel_area_m2": "193",
                "zone": "U|UE2c(d)",
                "last_mutation": "",
                "diagnostics": "1",
                "dpe_address": "12 Rue de Rennes 35510 Cesson-Sévigné",
                "latitude": "48.1",
                "longitude": "-1.6",
                "map_url": "https://www.geoportail.gouv.fr/carte?c=-1.600000,48.100000&z=19",
                "position_missing": "",
            },
            {
                "reference": "C002",
                "cadastral_id": "35051000BH0260",
                "dpe_deposited_at": "2024-06-14",
                "dpe_age_months": "26",
                "residual_probability": "",
                "energy_label": "",
                "label_rate": "",
                "living_area_m2": "",
                "built_year": "1995",
                "parcel_area_m2": "608",
                "zone": "U|UE2c(d)",
                "last_mutation": "",
                "diagnostics": "1",
                "dpe_address": "",
                "latitude": "48.2",
                "longitude": "-1.7",
                "map_url": "https://www.geoportail.gouv.fr/carte?c=-1.700000,48.200000&z=19",
                "position_missing": "",
            },
        ],
    )


def test_le_kit_ne_lit_jamais_la_correspondance() -> None:
    """S'il ne la lit pas, il ne peut pas la trahir."""
    source = GENERATOR.read_text(encoding="utf-8")
    assert "correspondance.csv" not in source
    assert '"origine"' not in source and "property_unit_id" not in source
    module = load()
    assert "origine" not in module.GRID_COLUMNS and "property_unit_id" not in module.GRID_COLUMNS


def test_chaque_reference_a_sa_fiche_et_sa_ligne_de_grille(tmp_path: Path) -> None:
    module = load()
    fixtures(tmp_path)
    written = module.build(tmp_path, "35051", "2026-09-15")
    assert {path.name for path in written} == {
        "fiches-parcelles-divisibles.html",
        "grille-parcelles-divisibles.csv",
        "fiches-biens-en-vente.html",
        "grille-biens-en-vente.csv",
    }
    for slug in ("parcelles-divisibles", "biens-en-vente"):
        page = (tmp_path / "field-test-35" / "35051" / f"fiches-{slug}.html").read_text()
        assert 'class="ref">C001<' in page and 'class="ref">C002<' in page
        with (tmp_path / "field-test-35" / "35051" / f"grille-{slug}.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        assert [row["reference"] for row in rows] == ["C001", "C002"]
        assert list(rows[0]) == module.GRID_COLUMNS
        assert all(row["verdict"] == "" and row["motif"] == "" for row in rows)


def test_une_adresse_ou_une_position_absente_s_affiche_absente_avec_son_motif(
    tmp_path: Path,
) -> None:
    module = load()
    fixtures(tmp_path)
    module.build(tmp_path, "35051", "2026-09-15")
    vente = (tmp_path / "field-test-35" / "35051" / "fiches-biens-en-vente.html").read_text()
    assert "12 Rue de Rennes 35510 Cesson-Sévigné" in vente
    assert "Adresse :</b> absente — non déclarée sur le diagnostic" in vente
    assert "<td>absent</td>" in vente  # étiquette, taux et surface absents sur C002
    divisibles = (
        tmp_path / "field-test-35" / "35051" / "fiches-parcelles-divisibles.html"
    ).read_text()
    assert "Position :</b> absente — géométrie absente" in divisibles
    assert "Adresse" not in divisibles  # aucune adresse n'est rattachée à une parcelle divisible


def test_le_lien_de_carte_n_est_emis_qu_avec_une_position(tmp_path: Path) -> None:
    module = load()
    fixtures(tmp_path)
    module.build(tmp_path, "35051", "2026-09-15")
    divisibles = (
        tmp_path / "field-test-35" / "35051" / "fiches-parcelles-divisibles.html"
    ).read_text()
    assert divisibles.count("parcellaire sur orthophoto") == 1
    assert "48.12345, -1.60001" in divisibles


def test_les_taux_se_lisent_en_pourcentage_et_les_ratios_aussi(tmp_path: Path) -> None:
    module = load()
    assert module.percent("0.219") == "21,9 %"
    assert module.ratio_percent("0.067") == "7 %"
    fixtures(tmp_path)
    module.build(tmp_path, "35051", "2026-09-15")
    vente = (tmp_path / "field-test-35" / "35051" / "fiches-biens-en-vente.html").read_text()
    assert "<td>21,9 %</td>" in vente and "<td>38,5 %</td>" in vente


def test_une_liste_manquante_arrete_le_kit_sans_rien_fabriquer(tmp_path: Path) -> None:
    module = load()
    fixtures(tmp_path)
    (tmp_path / "biens-en-vente" / "35051" / "liste-aveugle.csv").unlink()
    try:
        module.build(tmp_path, "35051", "2026-09-15")
    except FileNotFoundError as error:
        assert "biens-en-vente" in str(error)
    else:
        raise AssertionError("une liste absente doit arrêter le kit")
    assert not (tmp_path / "field-test-35" / "35051" / "fiches-biens-en-vente.html").exists()
