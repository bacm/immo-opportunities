"""Lire les variables communales de l'INSEE, DS-14 à DS-16 — D7, ADR-023.

Trois sources, une forme de sortie : une valeur par commune et par indicateur, ou un motif
d'absence. Tout ce qui décide d'une valeur est ici, sans base ; l'import ne fait qu'écrire.

## Une commune absente n'est pas une commune à zéro

Chaque lecture part de la liste des communes du référentiel. Une commune que la source ne cite
pas reçoit `source_value_missing`, jamais zéro.

La BPE est l'exception, et elle est bornée : c'est un **dénombrement**. Une commune que la BPE
cite, mais pas pour un sous-domaine donné, n'a aucun équipement recensé de ce sous-domaine — le
zéro est la valeur observée. Une commune que la BPE ne cite pas du tout reste absente.

## Les fichiers de l'INSEE

- DS-14 et DS-15 : distribution Melodi, un zip contenant `*_data.csv` et `*_metadata.csv`,
  séparateur `;`, une ligne par observation (`GEO`, `GEO_OBJECT`, dimensions, `OBS_VALUE`).
- DS-16 : un classeur XLSX. Il est lu avec la bibliothèque standard — un XLSX est un zip de XML —
  plutôt qu'avec une dépendance de plus pour une seule feuille.
"""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ElementTree
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

# 1 : premier import. Valeurs communales telles que publiees ; zero BPE = denombrement nul.
TERRITORIAL_TRANSFORMATION_VERSION = "1"

GEOGRAPHY_VINTAGE = 2025

_XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_RELATIONSHIP = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PACKAGE = "{http://schemas.openxmlformats.org/package/2006/relationships}"


@dataclass(frozen=True, slots=True)
class Indicator:
    commune_code: str
    code: str
    reference_period: str
    numeric_value: float | None = None
    text_value: str | None = None
    missing_reason: str | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        present = [
            value
            for value in (self.numeric_value, self.text_value, self.missing_reason)
            if value is not None
        ]
        if len(present) != 1:
            raise ValueError(
                f"{self.commune_code} {self.code}: exactly one of value, text or missing reason"
            )


def missing(commune: str, code: str, period: str, unit: str | None = None) -> Indicator:
    return Indicator(commune, code, period, missing_reason="source_value_missing", unit=unit)


# --- Melodi ---------------------------------------------------------------------------------


def melodi_rows(path: Path, suffix: str = "_data.csv") -> Iterator[dict[str, str]]:
    """Les lignes communales d'une distribution Melodi, sans décompresser sur disque."""
    with zipfile.ZipFile(path) as archive:
        (member,) = [name for name in archive.namelist() if name.endswith(suffix)]
        with archive.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter=";")
            for row in reader:
                if row.get("GEO_OBJECT") == "COM":
                    yield row


def melodi_labels(path: Path) -> dict[tuple[str, str], str]:
    """(variable, modalité) → libellé, depuis `*_metadata.csv`."""
    labels: dict[tuple[str, str], str] = {}
    with zipfile.ZipFile(path) as archive:
        (member,) = [name for name in archive.namelist() if name.endswith("_metadata.csv")]
        with archive.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter=";")
            for row in reader:
                labels[(row["COD_VAR"], row["COD_MOD"])] = row["LIB_MOD"]
    return labels


# --- DS-14 : populations de référence --------------------------------------------------------

TOTAL = "_T"

POPULATION_MEASURES = {
    "PMUN": "population_municipale",
    "PCAP": "population_comptee_a_part",
    "PTOT": "population_totale",
}


def population_indicators(
    rows: Iterable[dict[str, str]], communes: Iterable[str], period: str
) -> list[Indicator]:
    wanted = set(communes)
    seen: dict[tuple[str, str], float] = {}
    for row in rows:
        code = POPULATION_MEASURES.get(row["POPREF_MEASURE"])
        if code is None or row["GEO"] not in wanted or row["TIME_PERIOD"] != period:
            continue
        key = (row["GEO"], code)
        if key in seen:
            raise ValueError(f"population en double pour {key}")
        seen[key] = float(row["OBS_VALUE"])
    return [
        Indicator(commune, code, period, numeric_value=seen[(commune, code)], unit="habitants")
        if (commune, code) in seen
        else missing(commune, code, period, "habitants")
        for commune in sorted(wanted)
        for code in POPULATION_MEASURES.values()
    ]


# --- DS-14 : logements du recensement --------------------------------------------------------

# (catégorie de logement OCS, type de logement TDW) → indicateur ; toutes les autres dimensions
# à `_T`. Les logements vacants (`DW_VAC`) ne sont pas lus : la vacance est retirée du produit
# (SPEC §12). Les valeurs sont des estimations pondérées du recensement, non arrondies.
HOUSING_CELLS = {
    ("_T", "_T"): "logements_total",
    ("DW_MAIN", "_T"): "residences_principales",
    ("DW_SEC_DW_OCC", "_T"): "residences_secondaires_occasionnelles",
    ("_T", "1"): "logements_maisons",
    ("_T", "2"): "logements_appartements",
}
HOUSING_OTHER_DIMENSIONS = ("L_STAY", "CARS", "CARPARK", "NOR", "TSH", "BUILD_END", "NRG_SRC")


def housing_indicators(
    rows: Iterable[dict[str, str]], communes: Iterable[str], period: str
) -> list[Indicator]:
    wanted = set(communes)
    seen: dict[tuple[str, str], float] = {}
    for row in rows:
        if row["GEO"] not in wanted or row["TIME_PERIOD"] != period:
            continue
        if row["RP_MEASURE"] != "DWELLINGS":
            continue
        code = HOUSING_CELLS.get((row["OCS"], row["TDW"]))
        if code is None or any(row[name] != TOTAL for name in HOUSING_OTHER_DIMENSIONS):
            continue
        key = (row["GEO"], code)
        if key in seen:
            raise ValueError(f"logements en double pour {key}")
        seen[key] = float(row["OBS_VALUE"])
    return [
        Indicator(commune, code, period, numeric_value=seen[(commune, code)], unit="logements")
        if (commune, code) in seen
        else missing(commune, code, period, "logements")
        for commune in sorted(wanted)
        for code in HOUSING_CELLS.values()
    ]


# --- DS-15 : base permanente des équipements -------------------------------------------------


def equipment_code(domain: str, subdomain: str) -> str:
    if domain == TOTAL:
        return "equipements_total"
    if subdomain == TOTAL:
        return f"equipements_domaine_{domain.lower()}"
    return f"equipements_sous_domaine_{subdomain.lower()}"


def equipment_indicators(
    rows: Iterable[dict[str, str]], communes: Iterable[str], period: str
) -> list[Indicator]:
    """Nombre d'équipements par commune : total, domaine, sous-domaine.

    Seules les lignes agrégées sur le type (`FACILITY_TYPE = _T`) sont lues : le détail par type
    compte près de deux cents modalités, et E6 n'en a pas l'usage déclaré.
    """
    wanted = set(communes)
    counts: dict[tuple[str, str], float] = {}
    codes: set[str] = set()
    cited: set[str] = set()
    for row in rows:
        if row["TIME_PERIOD"] != period or row["BPE_MEASURE"] != "FACILITIES":
            continue
        if row["FACILITY_TYPE"] != TOTAL:
            continue
        code = equipment_code(row["FACILITY_DOM"], row["FACILITY_SDOM"])
        codes.add(code)
        if row["GEO"] not in wanted:
            continue
        cited.add(row["GEO"])
        key = (row["GEO"], code)
        if key in counts:
            raise ValueError(f"équipements en double pour {key}")
        counts[key] = float(row["OBS_VALUE"])
    indicators: list[Indicator] = []
    for commune in sorted(wanted):
        for code in sorted(codes):
            if commune not in cited:
                indicators.append(missing(commune, code, period, "équipements"))
            else:
                indicators.append(
                    Indicator(
                        commune,
                        code,
                        period,
                        numeric_value=counts.get((commune, code), 0.0),
                        unit="équipements",
                    )
                )
    return indicators


# --- DS-16 : aires d'attraction des villes ----------------------------------------------------

AAV_PERIOD = "AAV2020"
AAV_CENTRE = "11"
AAV_OUTSIDE = "30"
# Catégorie de la commune dans l'aire, nomenclature INSEE.
AAV_CATEGORIES = {
    "11": "commune-centre",
    "12": "autre commune du pôle principal",
    "13": "commune d'un pôle secondaire",
    "20": "commune de la couronne",
    "30": "commune hors attraction des villes",
}


def xlsx_rows(path: Path, sheet_name: str) -> Iterator[list[str | None]]:
    with zipfile.ZipFile(path) as archive:
        strings = [
            "".join(node.text or "" for node in item.iter(f"{_XLSX}t"))
            for item in ElementTree.fromstring(archive.read("xl/sharedStrings.xml")).iter(
                f"{_XLSX}si"
            )
        ]
        # Le nom d'une feuille ne dit pas son fichier : le classeur INSEE range « Documentation »
        # dans `sheet1.xml` bien qu'elle vienne en dernier. Le lien passe par les relations.
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        (relation,) = [
            sheet.get(f"{_RELATIONSHIP}id")
            for sheet in workbook.iter(f"{_XLSX}sheet")
            if sheet.get("name") == sheet_name
        ]
        relations = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        (target,) = [
            str(item.get("Target"))
            for item in relations.iter(f"{_PACKAGE}Relationship")
            if item.get("Id") == relation
        ]
        root = ElementTree.fromstring(archive.read(f"xl/{target.removeprefix('/xl/')}"))
        for row in root.iter(f"{_XLSX}row"):
            values: list[str | None] = []
            for cell in row.iter(f"{_XLSX}c"):
                node = cell.find(f"{_XLSX}v")
                text = node.text if node is not None else None
                if cell.get("t") == "s" and text is not None:
                    text = strings[int(text)]
                values.append(text)
            yield values


def table(rows: Iterable[list[str | None]], first_column: str) -> list[dict[str, str | None]]:
    """Les lignes sous l'en-tête technique (`CODGEO`, `AAV2020`…), en ignorant le cartouche."""
    header: list[str | None] | None = None
    records: list[dict[str, str | None]] = []
    for row in rows:
        if header is None:
            if row and row[0] == first_column:
                header = row
            continue
        if not row or row[0] is None:
            continue
        records.append(dict(zip([str(name) for name in header], row, strict=False)))
    if header is None:
        raise ValueError(f"en-tête {first_column} introuvable")
    return records


@dataclass(frozen=True, slots=True)
class AttractionArea:
    commune_code: str
    area_code: str
    category: str
    size_band: str
    # None hors attraction, ou quand la commune-centre est hors de France.
    centre_commune_code: str | None


def attraction_areas(path: Path) -> dict[str, AttractionArea]:
    """Commune → aire, catégorie, tranche de taille et commune-centre de l'aire."""
    areas = {
        str(row["AAV2020"]): str(row["TAAV2017"])
        for row in table(xlsx_rows(path, "AAV2020"), "AAV2020")
    }
    composition = table(xlsx_rows(path, "Composition_communale"), "CODGEO")
    centres: dict[str, str] = {}
    for row in composition:
        if row["CATEAAV2020"] == AAV_CENTRE:
            area = str(row["AAV2020"])
            if area in centres:
                raise ValueError(f"deux communes-centres pour l'aire {area}")
            centres[area] = str(row["CODGEO"])
    result: dict[str, AttractionArea] = {}
    for row in composition:
        area = str(row["AAV2020"])
        category = str(row["CATEAAV2020"])
        if category not in AAV_CATEGORIES:
            raise ValueError(f"catégorie AAV inconnue : {category}")
        result[str(row["CODGEO"])] = AttractionArea(
            commune_code=str(row["CODGEO"]),
            area_code=area,
            category=category,
            size_band=areas[area],
            # Une aire transfrontalière (Genève, Bâle…) a sa commune-centre hors de France.
            centre_commune_code=centres.get(area),
        )
    return result


def attraction_indicators(
    areas: dict[str, AttractionArea], communes: Iterable[str]
) -> list[Indicator]:
    """Aire, catégorie et tranche ; la distance au pôle est calculée à l'import, en base."""
    indicators: list[Indicator] = []
    for commune in sorted(set(communes)):
        area = areas.get(commune)
        for code, value in (
            ("aav_code", area.area_code if area else None),
            ("aav_categorie", area.category if area else None),
            ("aav_tranche_taille", area.size_band if area else None),
            ("aav_commune_centre", area.centre_commune_code if area else None),
        ):
            if area is None:
                indicators.append(missing(commune, code, AAV_PERIOD))
            elif value is None and area.category == AAV_OUTSIDE:
                indicators.append(
                    Indicator(commune, code, AAV_PERIOD, missing_reason="not_applicable")
                )
            elif value is None:
                indicators.append(missing(commune, code, AAV_PERIOD))
            else:
                indicators.append(Indicator(commune, code, AAV_PERIOD, text_value=value))
    return indicators
