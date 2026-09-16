"""Le baromètre mis en forme — H2.

Le générateur ne lit que des CSV : il se teste sur un jeu écrit par le test, sans base. Trois
exigences du ticket sont testées nommément : la sortie se régénère à l'identique, une rubrique
sans support affiche son effectif et jamais une valeur, et aucun identifiant cadastral ni adresse
ne sort.
"""

import csv
import importlib.util
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "market_barometer_kit.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("market_barometer_kit", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()
RICH = "240000001"
POOR = "240000002"


def write(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def volume(scope_type: str, code: str, year: int, kind: str, sales: int, value: Any) -> dict:
    supported = value != ""
    return {
        "scope_type": scope_type,
        "scope_code": code,
        "year": year,
        "property_type": kind,
        "sales": sales,
        "q1_eur_m2": value - 400 if supported else "",
        "median_eur_m2": value,
        "q3_eur_m2": value + 500 if supported else "",
        "reason": "" if supported else f"support insuffisant : {sales} < 15",
    }


def margin(scope_type: str, code: str, band: str, pairs: int, excess: Any) -> dict:
    supported = excess != ""
    return {
        "scope_type": scope_type,
        "scope_code": code,
        "entry_band": band,
        "pairs": pairs,
        "median_excess": excess,
        "q3_excess": excess + 0.2 if supported else "",
        "share_above_threshold_pct": 50.0 if supported else "",
        "reason": "" if supported else f"support insuffisant : {pairs} < 30",
    }


def label(scope_type: str, code: str, letter: str, sales: int, ratio: Any) -> dict:
    supported = ratio != ""
    return {
        "scope_type": scope_type,
        "scope_code": code,
        "energy_label": letter,
        "sales": sales,
        "q1_ratio": ratio - 0.1 if supported else "",
        "median_ratio": ratio,
        "q3_ratio": ratio + 0.1 if supported else "",
        "reason": "" if supported else f"support insuffisant : {sales} < 30",
    }


def rate(scope_type: str, code: str, parcels: int, sold: int, supported: bool) -> dict:
    return {
        "scope_type": scope_type,
        "scope_code": code,
        "cohort_year": 2024,
        "cohort_parcels": parcels,
        "sold_within_12_months": sold,
        "rate_pct": round(100 * sold / parcels, 1) if supported else "",
        "reason": "" if supported else f"support insuffisant : {parcels} < 200",
    }


def curve(scope_type: str, code: str, parcels: int, supported: bool) -> list[dict]:
    return [
        {
            "scope_type": scope_type,
            "scope_code": code,
            "cohort_year": 2024,
            "month": month,
            "cohort_parcels": parcels,
            "sold_cumulative": month * 10,
            "cumulative_pct": round(100 * month * 10 / parcels, 1) if supported else "",
            "reason": "" if supported else f"support insuffisant : {parcels} < 200",
        }
        for month in (1, 2, 3, 6, 9, 12)
    ]


def delay(scope_type: str, code: str, parcels: int, supported: bool) -> dict:
    return {
        "scope_type": scope_type,
        "scope_code": code,
        "cohort_parcels": parcels,
        "sold_within_window": 100,
        "q1_days": 120 if supported else "",
        "median_days": 170 if supported else "",
        "q3_days": 240 if supported else "",
        "reason": "" if supported else f"support insuffisant : {parcels} < 200",
    }


@pytest.fixture
def barometer_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "barometre-marche-35"
    directory.mkdir()
    scopes = [("departement", "35", True), ("epci", RICH, True), ("epci", POOR, False)]
    write(
        directory / "bar-001-002-volumes-prix.csv",
        [
            volume(scope, code, year, kind, 40 if rich else 6, 2500 + year if rich else "")
            for scope, code, rich in scopes
            for year in (2024, 2025)
            for kind in ("Maison", "Appartement")
        ]
        # L'EPCI pauvre a tout de même des maisons publiables : il a donc une page.
        + [volume("epci", POOR, 2025, "Maison", 20, 1900)],
    )
    bands = ["< 60 % de la médiane", "60 % à 80 %", "80 % à 100 %", "100 % et plus"]
    write(
        directory / "bar-003-plus-value-prix-entree.csv",
        [
            margin(scope, code, band, 40 if rich else 4, 1.5 if rich else "")
            for scope, code, rich in scopes
            for band in bands
        ],
    )
    write(
        directory / "bar-004-etiquette.csv",
        [
            label(scope, code, letter, 50 if rich else 3, 0.97 if rich else "")
            for scope, code, rich in scopes
            for letter in "ABCDEFG"
        ],
    )
    write(
        directory / "bar-005-delai-dpe-acte.csv",
        [delay(scope, code, 300 if rich else 150, rich) for scope, code, rich in scopes],
    )
    write(
        directory / "bar-006-taux-mutation-12-mois.csv",
        [
            rate(scope, code, 300 if rich else 150, 105 if rich else 47, rich)
            for scope, code, rich in scopes
        ],
    )
    write(
        directory / "bar-007-courbe-conversion.csv",
        [
            row
            for scope, code, rich in scopes
            for row in curve(scope, code, 300 if rich else 150, rich)
        ],
    )
    write(
        directory / "bar-008-extension-surface.csv",
        [
            {
                "scope_type": "departement",
                "scope_code": "35",
                "window": "revente en 1095 jours au plus",
                "pairs": 205,
                "median_price_ratio": 1.37,
                "median_price_per_m2_ratio": 1.0,
                "reason": "",
            }
        ],
    )
    write(
        directory / "epci-communes.csv",
        [
            {"epci_code": RICH, "commune_code": "35001", "commune_name": "ALPHA"},
            {"epci_code": POOR, "commune_code": "35002", "commune_name": "BETA"},
            {"epci_code": "240000003", "commune_code": "35003", "commune_name": "GAMMA"},
        ],
    )
    metadata = {
        "department": "35",
        "generated_on": "2026-09-16",
        "last_mutation": "2025-12-31",
        "first_deposit": "2021-07-01",
        "last_deposit": "2026-09-07",
        "cohort_year": "2024",
        "sales_first_year": "2024",
        "sales_last_year": "2025",
        "label_from_year": "2022",
        "release_ds01": "2026-06-01",
        "release_ds02": "2026-09-05",
        "release_ds03": "2026-02-a",
        "release_ds06": "2026-09-13",
        "release_ds07": "2026-09-14-extract",
        "support_sales_per_cell": "15",
        "support_repeat_pairs": "30",
        "support_label_sales": "30",
        "support_dpe_cohort_parcels": "200",
        "repeat_max_days": "1095",
        "curve_month_days": "30",
        "fingerprint": "d08dba5d179c319e" + "0" * 48,
        "recounted_on": "",
        "recount_note": "non recompté",
    }
    write(directory / "metadonnees.csv", [{"key": k, "value": v} for k, v in metadata.items()])
    return directory


def documents(directory: Path) -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in MODULE.build(directory)}


def test_the_document_regenerates_identically(barometer_dir: Path) -> None:
    first = documents(barometer_dir)
    second = documents(barometer_dir)
    assert first == second


def test_one_document_for_the_department_and_one_per_supported_epci(barometer_dir: Path) -> None:
    names = set(documents(barometer_dir))
    assert names == {
        "document-departement-35.html",
        f"document-epci-{RICH}.html",
        f"document-epci-{POOR}.html",
    }


def test_an_epci_without_any_supported_measure_gets_no_page(barometer_dir: Path) -> None:
    assert "document-epci-240000003.html" not in documents(barometer_dir)


def test_a_rubric_without_support_shows_its_effectif_never_a_value(barometer_dir: Path) -> None:
    page = documents(barometer_dir)[f"document-epci-{POOR}.html"]
    # Marge : 16 reventes au total, pas de pourcentage publié.
    assert "16 reventes au total" in page
    # Tempo : l'effectif de la cohorte est écrit, le taux ne l'est pas.
    assert "150 parcelles en 2024" in page
    assert "31,3" not in page
    # Énergie : l'étiquette F n'est pas publiée, son effectif l'est.
    assert "Étiquette F non publiée" in page
    # Et rien n'est repris du département.
    assert "n'est pas remplacée par celle du département" in page


def test_a_supported_rubric_publishes_its_value_with_its_effectif(barometer_dir: Path) -> None:
    page = documents(barometer_dir)[f"document-epci-{RICH}.html"]
    assert "35,0\u00a0%" in page
    assert "105 sur 300" in page


def test_no_cadastral_identifier_or_address_leaves_the_generator(barometer_dir: Path) -> None:
    for name, page in documents(barometer_dir).items():
        assert not MODULE.CADASTRAL_ID.search(page), name
        for token in ("adresse :", "rue ", "avenue ", "numero_voie"):
            assert token not in page.lower(), (name, token)


def test_a_cadastral_identifier_blocks_the_write() -> None:
    with pytest.raises(ValueError):
        MODULE.check_publishable("<p>350010000AB0001</p>")


def test_an_unrecounted_barometer_is_marked_not_for_distribution(barometer_dir: Path) -> None:
    page = documents(barometer_dir)["document-departement-35.html"]
    assert "Non recompté" in page
    assert "ne pas diffuser" in page


def test_a_recounted_barometer_carries_the_date(barometer_dir: Path) -> None:
    path = barometer_dir / "metadonnees.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for row in rows:
        if row["key"] == "recounted_on":
            row["value"] = "2026-09-16"
    write(path, rows)
    page = documents(barometer_dir)["document-departement-35.html"]
    assert "Chiffres recomptés le 16 sept. 2026" in page
    assert "ne pas diffuser" not in page


def test_every_page_carries_the_mandatory_mentions(barometer_dir: Path) -> None:
    for name, page in documents(barometer_dir).items():
        assert "Aucune parcelle ni adresse n'est identifiable dans ce document" in page, name
        assert "Licence Ouverte 2.0" in page, name
        assert "DGFiP" in page and "ADEME" in page, name
        assert "Mesures générées le 16 sept. 2026" in page, name


def test_a_missing_measure_file_fails_rather_than_inventing_one(barometer_dir: Path) -> None:
    (barometer_dir / "bar-004-etiquette.csv").unlink()
    with pytest.raises(FileNotFoundError):
        MODULE.build(barometer_dir)


def test_numbers_are_written_the_french_way() -> None:
    assert MODULE.grouped(2588) == "2\u202f588"
    assert MODULE.signed_percent(-3.2) == "\u22123\u00a0%"
    assert MODULE.signed_percent(0.2) == "0\u00a0%"
    assert MODULE.percent(35.47) == "35,5\u00a0%"
    assert MODULE.entry_phrase("60\u00a0% à 80\u00a0%") == "entre 60\u00a0% et 80\u00a0%"


def test_a_year_without_support_is_a_gap_in_the_line_not_a_zero() -> None:
    series = MODULE.Series("Maisons", "--series-1", ((2023, 2000.0), (2024, None), (2025, 2100.0)))
    svg = MODULE.line_chart([series])
    # Deux points isolés, aucune ligne qui les relie à travers l'année manquante.
    assert 'class="line"' not in svg
    assert svg.count('class="dot"') >= 2


def test_the_document_computes_no_figure_of_its_own(barometer_dir: Path) -> None:
    """Un chiffre dérivé de médianes arrondies peut être faux d'un point : le recompte en a
    trouvé quatre. Le document ne publie que ce que les CSV portent."""
    for name, page in documents(barometer_dir).items():
        assert "sur un an" not in page, name
        assert "F / D" not in page, name


def test_the_energy_figure_is_the_label_f_as_measured(barometer_dir: Path) -> None:
    page = documents(barometer_dir)[f"document-epci-{RICH}.html"]
    # Médiane du ratio 0,97 dans le jeu de test : -3 %, lu tel quel.
    assert "\u22123\u00a0%</p>" in page
    assert "classée D : \u22123\u00a0%" in page


def test_a_year_without_any_sale_is_a_dash_not_a_zero(barometer_dir: Path) -> None:
    page = documents(barometer_dir)[f"document-epci-{POOR}.html"]
    # L'EPCI pauvre n'a aucun appartement en 2025 dans le jeu : la cellule est absente.
    row = page.split("<td>2025</td>")[1].split("</tr>")[0]
    assert '<td class="n">0</td>' not in row
    assert "aucune vente exploitable" in page
