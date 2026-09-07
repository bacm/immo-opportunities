"""Lecture du GeoPackage BDNB Open (DS-03) : groupes, pont vers le RNB, politique de champs.

Trois decisions de perimetre, mesurees sur l'archive epinglee et consignees dans
[l'audit spatial](../../../../docs/data/spatial-sources-audit.md).

**Le niveau « batiment physique » de la BDNB est la BD TOPO.** `batiment_construction.hauteur`
et sa geometrie sont documentees `(ign)` par le producteur. DS-04 les fournit nativement : les
importer serait un doublon, pas un apport. `batiment_construction` ne sert donc ici que de
**pont** entre le groupe et le RNB, sans qu'aucune de ses valeurs soit persistee.

**L'apport propre de la BDNB tient en six champs** issus des Fichiers Fonciers :
`annee_construction` et `nb_niveau` que nulle autre source du MVP ne fournit, `nb_log` et
`usage_niveau_1_txt` qui en corroborent d'autres, `mat_mur_txt` et `mat_toit_txt` pour la
renovation. Tout le reste de la vue compilee recopie une source primaire — 149 colonnes DPE,
34 DVF, 13 BD TOPO — ou releve d'un calcul BDNB.

**Un groupe n'est pas un batiment.** 546 301 groupes couvrent 783 684 constructions physiques :
la cardinalite est reelle et le contrat interdit de l'aplatir. Un attribut publie au niveau
groupe n'est donc attribuable a un batiment canonique que si le groupe se resout en **un seul**
batiment — sinon la valeur reste au niveau groupe, et le lien est ambigu avec son motif.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from shapely import (
    force_2d,  # pyright: ignore[reportUnknownVariableType]
    from_wkb,
    make_valid,
)
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from immo_pipelines.cadastre.contract import SchemaChangeError

BDNB_TRANSFORMATION_VERSION = "bdnb-open-normalize@1"

GROUP_TABLE = "batiment_groupe_compile"
CONSTRUCTION_TABLE = "batiment_construction"
RNB_LINK_TABLE = "rel_batiment_construction_rnb"
COLUMN_DICTIONARY_TABLE = "metadonnees_colonne"

# Seul regime d'acces admis par le contrat. Le producteur le declare colonne par colonne.
OPEN_ACCESS_CONSTRAINT = "open_data_lo"

# Le type d'appariement construction <-> RNB qui enonce son critere : cardinalite 1:1 et
# recouvrement geometrique >= 95 %. Ce n'est pas une confiance opaque mais la description de la
# relation observee, et le seuil est celui du producteur — aucun seuil n'est invente ici.
ALIGNED_MATCH_PREFIX = "Alignement 1 BC = 1 RNB"

# Les six champs Fichiers Fonciers retenus, sous leur nom dans la vue compilee.
FFO_FIELDS: tuple[str, ...] = (
    "ffo_bat_annee_construction",
    "ffo_bat_nb_niveau",
    "ffo_bat_nb_log",
    "ffo_bat_usage_niveau_1_txt",
    "ffo_bat_mat_mur_txt",
    "ffo_bat_mat_toit_txt",
)

GROUP_REQUIRED_COLUMNS = frozenset(
    {"batiment_groupe_id", "geom_groupe", "code_commune_insee", "code_departement_insee"}
)
CONSTRUCTION_REQUIRED_COLUMNS = frozenset({"batiment_construction_id", "batiment_groupe_id"})
RNB_LINK_REQUIRED_COLUMNS = frozenset({"batiment_construction_id", "rnb_id", "type_appariement"})

_ENVELOPE_SIZES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


@dataclass(frozen=True, slots=True)
class BdnbGroup:
    source_row_number: int
    group_id: str
    geometry_wkt: str
    commune_code: str | None
    department_code: str | None
    iris_code: str | None
    epci_code: str | None
    ground_area_m2: float | None
    has_fictitious_geometry: bool | None
    construction_year: int | None
    storey_count: int | None
    dwelling_count: int | None
    usage_label: str | None
    wall_material: str | None
    roof_material: str | None
    properties: dict[str, object]
    record_checksum: str


@dataclass(frozen=True, slots=True)
class BdnbGroupRnbLink:
    """Un couple (groupe, batiment RNB), qualifie par le producteur.

    `aligned_relation_count` et `relation_count` comptent les relations construction <-> RNB
    qui contribuent au couple : c'est ce qui permet de distinguer un groupe entierement
    aligne d'un groupe dont une partie seulement l'est.
    """

    group_id: str
    rnb_id: str
    rnb_count_for_group: int
    relation_count: int
    aligned_relation_count: int
    match_types: tuple[str, ...]

    @property
    def is_single_building_group(self) -> bool:
        return self.rnb_count_for_group == 1

    @property
    def is_fully_aligned(self) -> bool:
        return self.relation_count > 0 and self.aligned_relation_count == self.relation_count


@dataclass(frozen=True, slots=True)
class BdnbQuarantine:
    source_row_number: int
    source_feature_id: str | None
    reason_code: str
    reason_detail: str
    source_properties: dict[str, object]


class RestrictedFieldError(RuntimeError):
    """Une colonne reservee a des ayants droit figure dans un export declare Open."""


def _strip_gpkg_header(blob: bytes) -> bytes:
    if len(blob) < 8 or blob[:2] != b"GP":
        raise ValueError("Geometry is not a GeoPackage blob")
    envelope_code = (blob[3] >> 1) & 0x07
    envelope_size = _ENVELOPE_SIZES.get(envelope_code)
    if envelope_size is None:
        raise ValueError(f"Unsupported GeoPackage envelope code {envelope_code}")
    return blob[8 + envelope_size :]


def _polygonal_2d(value: BaseGeometry) -> MultiPolygon | None:
    flat = force_2d(value)
    repaired: BaseGeometry = flat if flat.is_valid else make_valid(flat)
    if isinstance(repaired, Polygon):
        return MultiPolygon([repaired])
    if isinstance(repaired, MultiPolygon):
        return repaired
    polygons: list[Polygon] = []
    for geometry in cast(Any, getattr(repaired, "geoms", ())):
        if isinstance(geometry, Polygon):
            polygons.append(geometry)
        elif isinstance(geometry, MultiPolygon):
            polygons.extend(geometry.geoms)
    return MultiPolygon(polygons) if polygons else None


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().strip('"')
    return text or None


def _integer(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(cast(int, value))
    except (TypeError, ValueError):
        return None


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(cast(float, value))
    except (TypeError, ValueError):
        return None


def _boolean(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _columns(connection: sqlite3.Connection, table: str) -> frozenset[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise SchemaChangeError(f"BDNB GeoPackage has no table {table}")
    return frozenset(str(row["name"]) for row in rows)


def _require_columns(
    connection: sqlite3.Connection, table: str, required: frozenset[str]
) -> frozenset[str]:
    columns = _columns(connection, table)
    missing = required - columns
    if missing:
        raise SchemaChangeError(f"BDNB table {table} is missing columns: {sorted(missing)}")
    return columns


def verify_field_policy(path: Path) -> dict[str, Any]:
    """Verifier contre le dictionnaire du producteur qu'aucune colonne reservee n'est presente.

    Le contrat exige un controle bloquant `expert_fields_excluded`. Le faire contre
    `metadonnees_colonne`, livre dans l'archive, l'appuie sur la declaration du producteur
    plutot que sur une liste que nous aurions redigee — et le rend valable au millesime suivant.
    """
    connection = _connect(path)
    try:
        _require_columns(
            connection,
            COLUMN_DICTIONARY_TABLE,
            frozenset({"nom_colonne", "nom_table", "contrainte_acces", "statut"}),
        )
        dictionary: dict[tuple[str, str], sqlite3.Row] = {}
        for row in connection.execute(
            "SELECT nom_colonne, nom_table, contrainte_acces, statut "
            f"FROM {COLUMN_DICTIONARY_TABLE}"
        ):
            dictionary[(str(row["nom_table"]), str(row["nom_colonne"]))] = row

        tables = [
            str(row["table_name"])
            for row in connection.execute(
                "SELECT table_name FROM gpkg_contents ORDER BY table_name"
            )
        ]
        restricted: list[str] = []
        experimental: list[str] = []
        for table in tables:
            for column in sorted(_columns(connection, table)):
                entry = dictionary.get((table, column))
                if entry is None:
                    continue
                constraint = str(entry["contrainte_acces"] or "")
                if constraint and constraint != OPEN_ACCESS_CONSTRAINT:
                    restricted.append(f"{table}.{column} [{constraint}]")
                if str(entry["statut"] or "") == "expérimental":
                    experimental.append(f"{table}.{column}")
        if restricted:
            raise RestrictedFieldError(
                "Export declared Open carries rights-holder columns: " + ", ".join(restricted[:10])
            )
        return {
            "documented_columns": len(dictionary),
            "inspected_tables": len(tables),
            "restricted_columns": 0,
            "experimental_columns": len(experimental),
        }
    finally:
        connection.close()


def _checksum(row: dict[str, object]) -> str:
    scalars = {
        key: value
        for key, value in row.items()
        if not isinstance(value, bytes) and key not in {"fid"}
    }
    canonical = json.dumps(scalars, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def iter_bdnb_groups(path: Path) -> Iterator[BdnbGroup | BdnbQuarantine]:
    """Les groupes BDNB, reduits aux colonnes retenues.

    La vue compilee porte 293 colonnes ; n'en lire que les seize utiles evite de charger
    149 colonnes DPE et 34 colonnes DVF qui recopient des sources primaires du projet.
    """
    connection = _connect(path)
    try:
        columns = _require_columns(connection, GROUP_TABLE, GROUP_REQUIRED_COLUMNS)
        selected = [
            "batiment_groupe_id",
            "geom_groupe",
            "code_commune_insee",
            "code_departement_insee",
            "code_iris",
            "code_epci_insee",
            "s_geom_groupe",
            "contient_fictive_geom_groupe",
            *FFO_FIELDS,
        ]
        available = [column for column in selected if column in columns]
        cursor = connection.execute(
            f"SELECT {', '.join(available)} FROM {GROUP_TABLE} ORDER BY batiment_groupe_id"
        )
        for row_number, raw in enumerate(cursor, start=1):
            row = dict(raw)
            group_id = _text(row.get("batiment_groupe_id"))
            blob = row.get("geom_groupe")
            try:
                if group_id is None:
                    raise ValueError("batiment_groupe_id is empty")
                if not isinstance(blob, bytes):
                    raise ValueError("geometry is absent")
                geometry = from_wkb(_strip_gpkg_header(blob))
                if geometry.is_empty:
                    raise ValueError("geometry is empty")
                polygonal = _polygonal_2d(geometry)
                if polygonal is None or polygonal.is_empty or not polygonal.is_valid:
                    raise ValueError("geometry has no valid polygonal component")
            except ValueError as exc:
                yield BdnbQuarantine(
                    source_row_number=row_number,
                    source_feature_id=group_id,
                    reason_code="invalid_bdnb_group",
                    reason_detail=str(exc),
                    source_properties={
                        key: value for key, value in row.items() if not isinstance(value, bytes)
                    },
                )
                continue
            yield BdnbGroup(
                source_row_number=row_number,
                group_id=group_id,
                geometry_wkt=polygonal.wkt,
                commune_code=_text(row.get("code_commune_insee")),
                department_code=_text(row.get("code_departement_insee")),
                iris_code=_text(row.get("code_iris")),
                epci_code=_text(row.get("code_epci_insee")),
                ground_area_m2=_number(row.get("s_geom_groupe")),
                has_fictitious_geometry=_boolean(row.get("contient_fictive_geom_groupe")),
                construction_year=_integer(row.get("ffo_bat_annee_construction")),
                storey_count=_integer(row.get("ffo_bat_nb_niveau")),
                dwelling_count=_integer(row.get("ffo_bat_nb_log")),
                usage_label=_text(row.get("ffo_bat_usage_niveau_1_txt")),
                wall_material=_text(row.get("ffo_bat_mat_mur_txt")),
                roof_material=_text(row.get("ffo_bat_mat_toit_txt")),
                properties={
                    key: value for key, value in row.items() if not isinstance(value, bytes)
                },
                record_checksum=_checksum(row),
            )
    finally:
        connection.close()


def iter_bdnb_group_rnb_links(path: Path) -> Iterator[BdnbGroupRnbLink]:
    """Le pont groupe -> construction physique -> RNB, agrege par couple.

    `batiment_construction` n'est traverse que pour sa cle : ni sa geometrie ni sa hauteur ne
    sont lues, puisque le producteur les documente `(ign)` et que DS-04 les fournit.
    """
    connection = _connect(path)
    try:
        _require_columns(connection, CONSTRUCTION_TABLE, CONSTRUCTION_REQUIRED_COLUMNS)
        _require_columns(connection, RNB_LINK_TABLE, RNB_LINK_REQUIRED_COLUMNS)
        cursor = connection.execute(
            f"""
            WITH pair AS (
                SELECT construction.batiment_groupe_id AS group_id,
                       link.rnb_id AS rnb_id,
                       link.type_appariement AS match_type
                  FROM {CONSTRUCTION_TABLE} AS construction
                  JOIN {RNB_LINK_TABLE} AS link
                    ON link.batiment_construction_id = construction.batiment_construction_id
                 WHERE construction.batiment_groupe_id IS NOT NULL
                   AND link.rnb_id IS NOT NULL
            ), grouped AS (
                SELECT group_id, rnb_id,
                       count(*) AS relation_count,
                       sum(CASE WHEN match_type LIKE ? THEN 1 ELSE 0 END) AS aligned_count,
                       group_concat(DISTINCT match_type) AS match_types
                  FROM pair
                 GROUP BY group_id, rnb_id
            )
            SELECT grouped.group_id, grouped.rnb_id, grouped.relation_count,
                   grouped.aligned_count, grouped.match_types,
                   count(*) OVER (PARTITION BY grouped.group_id) AS rnb_count_for_group
              FROM grouped
             ORDER BY grouped.group_id, grouped.rnb_id
            """,
            (f"{ALIGNED_MATCH_PREFIX}%",),
        )
        for row in cursor:
            raw_types = _text(row["match_types"]) or ""
            yield BdnbGroupRnbLink(
                group_id=str(row["group_id"]),
                rnb_id=str(row["rnb_id"]),
                rnb_count_for_group=int(row["rnb_count_for_group"]),
                relation_count=int(row["relation_count"]),
                aligned_relation_count=int(row["aligned_count"]),
                match_types=tuple(part for part in raw_types.split(",") if part),
            )
    finally:
        connection.close()
