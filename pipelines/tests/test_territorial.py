"""Variables communales DS-14 à DS-16 : absence motivée, zéro borné, classeur lu juste — D7.

Les règles de lecture sont pures et se testent sur des fichiers construits ici, à la forme des
fichiers INSEE. Les invariants de l'import sont vérifiés sur son texte, faute de banc
PostgreSQL dans `make check` — même convention que `test_georisques.py`.
"""

import csv
import io
import zipfile
from pathlib import Path

import pytest

from immo_pipelines.cadastre.manifest import load_release_manifest, require_reproducible
from immo_pipelines.market_data.territorial import (
    Indicator,
    attraction_areas,
    attraction_indicators,
    equipment_indicators,
    housing_indicators,
    melodi_rows,
    population_indicators,
)

REPO = Path(__file__).resolve().parents[2]
IMPORTER = REPO / "pipelines" / "scripts" / "import_territorial_release.py"


def melodi_zip(path: Path, rows: list[dict[str, str]]) -> Path:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("DS_TEST_data.csv", buffer.getvalue())
        archive.writestr("DS_TEST_metadata.csv", '"COD_VAR";"LIB_VAR";"COD_MOD";"LIB_MOD"\n')
    return path


def population_row(geo: str, measure: str, value: str, obj: str = "COM") -> dict[str, str]:
    return {
        "GEO": geo,
        "GEO_OBJECT": obj,
        "FREQ": "A",
        "POPREF_MEASURE": measure,
        "TIME_PERIOD": "2023",
        "OBS_VALUE": value,
    }


def test_an_indicator_carries_exactly_one_value() -> None:
    with pytest.raises(ValueError):
        Indicator("35238", "population_municipale", "2023")
    with pytest.raises(ValueError):
        Indicator("35238", "x", "2023", numeric_value=1.0, missing_reason="not_applicable")


def test_a_commune_the_source_does_not_cite_is_missing_never_zero(tmp_path: Path) -> None:
    path = melodi_zip(
        tmp_path / "pop.zip",
        [
            population_row("35238", "PMUN", "230890"),
            population_row("35238", "PCAP", "4060"),
            population_row("35238", "PTOT", "234950"),
            # Un arrondissement portant le même code ne doit pas être lu comme une commune.
            population_row("35001", "PMUN", "999", obj="ARR"),
        ],
    )
    result = {
        (item.commune_code, item.code): item
        for item in population_indicators(melodi_rows(path), ["35238", "35001"], "2023")
    }
    assert result[("35238", "population_municipale")].numeric_value == 230890
    absent = result[("35001", "population_municipale")]
    assert absent.numeric_value is None
    assert absent.missing_reason == "source_value_missing"


def test_a_duplicated_population_is_a_schema_error(tmp_path: Path) -> None:
    path = melodi_zip(
        tmp_path / "pop.zip",
        [population_row("35238", "PMUN", "1"), population_row("35238", "PMUN", "2")],
    )
    with pytest.raises(ValueError):
        population_indicators(melodi_rows(path), ["35238"], "2023")


def equipment_row(geo: str, domain: str, subdomain: str, value: str) -> dict[str, str]:
    return {
        "GEO": geo,
        "GEO_OBJECT": "COM",
        "FACILITY_DOM": domain,
        "FACILITY_SDOM": subdomain,
        "FACILITY_TYPE": "_T",
        "BPE_MEASURE": "FACILITIES",
        "TIME_PERIOD": "2025",
        "OBS_VALUE": value,
    }


def test_the_bpe_zero_is_bounded_to_communes_the_bpe_cites() -> None:
    """Un dénombrement dit zéro pour un sous-domaine absent ; pas pour une commune absente."""
    rows = [
        equipment_row("35238", "_T", "_T", "8009"),
        equipment_row("35238", "C", "C1", "99"),
        equipment_row("35001", "_T", "_T", "171"),
        # Le détail par type n'est pas lu.
        {**equipment_row("35001", "C", "C1", "3"), "FACILITY_TYPE": "C104"},
    ]
    result = {
        (item.commune_code, item.code): item
        for item in equipment_indicators(rows, ["35238", "35001", "35999"], "2025")
    }
    assert result[("35238", "equipements_sous_domaine_c1")].numeric_value == 99
    assert result[("35001", "equipements_sous_domaine_c1")].numeric_value == 0
    assert result[("35999", "equipements_total")].missing_reason == "source_value_missing"
    assert result[("35999", "equipements_sous_domaine_c1")].numeric_value is None


def housing_row(ocs: str, tdw: str, value: str, **other: str) -> dict[str, str]:
    row = {
        "GEO": "35238",
        "GEO_OBJECT": "COM",
        "OCS": ocs,
        "TDW": tdw,
        "RP_MEASURE": "DWELLINGS",
        "TIME_PERIOD": "2023",
        "OBS_VALUE": value,
    }
    for name in ("L_STAY", "CARS", "CARPARK", "NOR", "TSH", "BUILD_END", "NRG_SRC"):
        row[name] = other.get(name, "_T")
    return row


def test_vacant_dwellings_are_never_read() -> None:
    """La vacance est retirée du produit (SPEC §12)."""
    rows = [
        housing_row("_T", "_T", "137847.26"),
        housing_row("DW_VAC", "_T", "8000"),
        housing_row("DW_MAIN", "_T", "122334.1"),
        # Une ventilation par époque d'achèvement n'est pas le total.
        housing_row("DW_MAIN", "_T", "5", BUILD_END="Y_LT1919"),
    ]
    result = housing_indicators(rows, ["35238"], "2023")
    codes = {item.code for item in result}
    assert not any("vacant" in code for code in codes)
    by_code = {item.code: item for item in result}
    assert by_code["residences_principales"].numeric_value == pytest.approx(122334.1)
    assert by_code["logements_total"].numeric_value == pytest.approx(137847.26)
    assert by_code["logements_maisons"].missing_reason == "source_value_missing"


SHEET = (
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>{rows}</sheetData></worksheet>"
)


def xlsx(path: Path, sheets: dict[str, list[list[str]]]) -> Path:
    """Un classeur minimal dont l'ordre des fichiers ne suit pas l'ordre des feuilles.

    C'est le cas du fichier INSEE : la dernière feuille, « Documentation », est `sheet1.xml`.
    """
    strings: list[str] = []

    def cell(value: str) -> str:
        strings.append(value)
        return f'<c t="s"><v>{len(strings) - 1}</v></c>'

    names = list(sheets)
    files = {name: f"sheet{len(names) - index}.xml" for index, name in enumerate(names)}
    with zipfile.ZipFile(path, "w") as archive:
        workbook_sheets = "".join(
            f'<sheet name="{name}" sheetId="{index + 1}" r:id="rId{index + 1}"/>'
            for index, name in enumerate(names)
        )
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{workbook_sheets}</sheets></workbook>",
        )
        relations = "".join(
            f'<Relationship Id="rId{index + 1}" Target="worksheets/{files[name]}" Type="x"/>'
            for index, name in enumerate(names)
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{relations}</Relationships>",
        )
        for name, rows in sheets.items():
            body = "".join("<row>" + "".join(cell(v) for v in row) + "</row>" for row in rows)
            archive.writestr(f"xl/worksheets/{files[name]}", SHEET.format(rows=body))
        shared = "".join(f"<si><t>{value}</t></si>" for value in strings)
        archive.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"{shared}</sst>",
        )
    return path


def aav_workbook(path: Path) -> Path:
    head = ["Aires d'attraction des villes 2020"]
    return xlsx(
        path,
        {
            "AAV2020": [
                head,
                ["AAV2020", "LIBAAV2020", "TAAV2017", "TDAAV2017", "NB_COM"],
                ["013", "Rennes", "4", "41", "181"],
                ["431", "Guer", "1", "11", "8"],
                ["GEN", "Genève (partie française)", "4", "42", "150"],
                ["000", "Commune hors attraction des villes", "0", "00", "8897"],
            ],
            "Composition_communale": [
                head,
                ["CODGEO", "LIBGEO", "AAV2020", "LIBAAV2020", "CATEAAV2020", "DEP", "REG"],
                ["35238", "Rennes", "013", "Rennes", "11", "35", "53"],
                ["35024", "Betton", "013", "Rennes", "20", "35", "53"],
                ["56075", "Guer", "431", "Guer", "11", "56", "53"],
                ["35046", "Les Brulais", "431", "Guer", "20", "35", "53"],
                ["74012", "Annemasse", "GEN", "Genève", "12", "74", "84"],
                ["35002", "Amanlis", "000", "Hors", "30", "35", "53"],
            ],
            "Documentation": [head],
        },
    )


def test_the_workbook_is_read_through_its_relations(tmp_path: Path) -> None:
    areas = attraction_areas(aav_workbook(tmp_path / "aav.xlsx"))
    assert areas["35024"].centre_commune_code == "35238"
    assert areas["35024"].size_band == "4"
    # Aire transfrontalière : la commune-centre est hors de France.
    assert areas["74012"].centre_commune_code is None


def test_a_pole_is_the_centre_commune_and_no_threshold_decides_it(tmp_path: Path) -> None:
    areas = attraction_areas(aav_workbook(tmp_path / "aav.xlsx"))
    result = {
        (item.commune_code, item.code): item
        for item in attraction_indicators(areas, ["35238", "35024", "35046", "35002", "35999"])
    }
    assert result[("35024", "aav_commune_centre")].text_value == "35238"
    # La commune-centre voisine existe dans la source : c'est la distance qui manquera.
    assert result[("35046", "aav_commune_centre")].text_value == "56075"
    assert result[("35002", "aav_commune_centre")].missing_reason == "not_applicable"
    assert result[("35002", "aav_categorie")].text_value == "30"
    assert result[("35999", "aav_code")].missing_reason == "source_value_missing"


def test_the_centre_distance_keeps_its_provenance_and_its_gaps() -> None:
    source = IMPORTER.read_text(encoding="utf-8")
    block = source[source.index("def insert_centre_distance") :]
    assert "data_source_id = 'DS-01'" in block
    assert "jsonb_build_array(centre.release_id, %(ds01)s::text)" in block
    assert "WHEN pole.id IS NULL OR commune.id IS NULL THEN 'source_value_missing'" in block


def test_the_importer_purges_its_release_before_writing() -> None:
    source = IMPORTER.read_text(encoding="utf-8")
    assert "DELETE FROM observation.territorial_indicator WHERE release_id = %s" in source


@pytest.mark.parametrize(
    ("source", "release", "layers"),
    [
        ("DS-14", "rp-2023", {"population", "housing"}),
        ("DS-15", "bpe-2025", {"equipments"}),
        ("DS-16", "aav2020-geo2025", {"areas"}),
    ],
)
def test_the_three_manifests_are_reproducible(source: str, release: str, layers: set[str]) -> None:
    """Les URL de l'INSEE ne sont pas datées : chaque fichier nomme sa copie archivée."""
    manifest = load_release_manifest(source, release, "35", root=REPO)
    assert {asset.layer for asset in manifest.assets} == layers
    for asset in manifest.assets:
        require_reproducible(manifest.release_id, asset)
        assert asset.archive_object_key is not None
        assert asset.member_path is not None
