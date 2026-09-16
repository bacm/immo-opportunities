#!/usr/bin/env python3
"""Régénère le rapport des variables communales DS-14 à DS-16 — D7, ADR-023.

Le rapport se recalcule depuis `observation.territorial_indicator`, `meta.dataset_release`,
`meta.import_run` et `meta.raw_asset`. Il ne se saisit pas à la main.

Il publie des **distributions**, pas des classes : découper appartient à E6, sur ces
distributions. Aucun seuil n'est écrit ici.
"""

import argparse
import tempfile
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.territorial import AAV_CATEGORIES, melodi_labels

SOURCES = ("DS-14", "DS-15", "DS-16")
OUTPUT = Path("docs/data/territorial-variables-35.md")


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


def releases(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT release.id AS release_id, release.data_source_id, source.name,
               release.source_published_on, release.acceptance_status,
               run.id AS import_run_id, run.completed_at::date AS imported_on,
               (SELECT count(DISTINCT i.commune_code) FROM observation.territorial_indicator i
                 WHERE i.release_id = release.id) AS communes,
               (SELECT count(*) FROM observation.territorial_indicator i
                 WHERE i.release_id = release.id) AS rows,
               (SELECT count(*) FROM observation.territorial_indicator i
                 WHERE i.release_id = release.id AND i.missing_reason IS NOT NULL) AS missing
          FROM meta.dataset_release AS release
          JOIN meta.data_source AS source ON source.id = release.data_source_id
          JOIN meta.import_run AS run
            ON run.release_id = release.id AND run.status = 'succeeded'
           AND run.territory_code = %(department)s
         WHERE release.data_source_id = ANY(%(sources)s)
           AND release.lifecycle_status <> 'retired'
         ORDER BY release.data_source_id, release.id
        """,
        department=department,
        sources=list(SOURCES),
    )


def assets(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT asset.release_id, asset.layer, asset.sha256, asset.byte_size, asset.object_key
          FROM meta.raw_asset AS asset
          JOIN meta.dataset_release AS release ON release.id = asset.release_id
         WHERE release.data_source_id = ANY(%(sources)s)
           AND release.lifecycle_status <> 'retired'
           AND asset.territory_code = %(department)s
         ORDER BY asset.release_id, asset.layer
        """,
        department=department,
        sources=list(SOURCES),
    )


def distributions(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT i.release_id, i.indicator_code, min(i.reference_period) AS period,
               min(i.unit) AS unit,
               count(*) FILTER (WHERE i.numeric_value IS NOT NULL) AS valued,
               count(*) FILTER (WHERE i.missing_reason IS NOT NULL) AS missing,
               count(*) FILTER (WHERE i.numeric_value = 0) AS zeros,
               min(i.numeric_value) AS minimum,
               percentile_cont(0.1) WITHIN GROUP (ORDER BY i.numeric_value) AS p10,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY i.numeric_value) AS q1,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY i.numeric_value) AS median,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY i.numeric_value) AS q3,
               percentile_cont(0.9) WITHIN GROUP (ORDER BY i.numeric_value) AS p90,
               max(i.numeric_value) AS maximum,
               sum(i.numeric_value) AS total
          FROM observation.territorial_indicator AS i
          JOIN meta.dataset_release AS release ON release.id = i.release_id
         WHERE release.data_source_id = ANY(%(sources)s)
           AND release.lifecycle_status <> 'retired'
           AND i.department_code = %(department)s
         GROUP BY i.release_id, i.indicator_code
        -- Un indicateur textuel n'a pas de distribution numérique, même quand il est absent.
        HAVING count(i.text_value) = 0
         ORDER BY i.release_id, i.indicator_code
        """,
        department=department,
        sources=list(SOURCES),
    )


def categories(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT i.indicator_code, coalesce(i.text_value, '(' || i.missing_reason || ')') AS value,
               count(*) AS communes
          FROM observation.territorial_indicator AS i
          JOIN meta.dataset_release AS release ON release.id = i.release_id
         WHERE release.data_source_id = 'DS-16'
           AND release.lifecycle_status <> 'retired'
           AND i.department_code = %(department)s
           AND i.indicator_code IN ('aav_code', 'aav_categorie', 'aav_tranche_taille')
         GROUP BY 1, 2
         ORDER BY 1, 3 DESC, 2
        """,
        department=department,
    )


def distance_gaps(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT distance.commune_code, area.name, centre.text_value AS centre,
               distance.missing_reason
          FROM observation.territorial_indicator AS distance
          JOIN observation.territorial_indicator AS centre
            ON centre.release_id = distance.release_id
           AND centre.commune_code = distance.commune_code
           AND centre.indicator_code = 'aav_commune_centre'
          JOIN meta.dataset_release AS release ON release.id = distance.release_id
          LEFT JOIN reference.area AS area
                 ON area.area_type = 'commune' AND area.code = distance.commune_code
         WHERE release.data_source_id = 'DS-16'
           AND release.lifecycle_status <> 'retired'
           AND distance.department_code = %(department)s
           AND distance.indicator_code = 'aav_distance_centre_m'
           AND distance.missing_reason = 'source_value_missing'
         ORDER BY 1
        """,
        department=department,
    )


def bpe_labels(store: MinioObjectStore, rows: list[dict[str, Any]]) -> dict[str, str]:
    """Libellés de la nomenclature BPE, lus dans le fichier archivé importé."""
    (entry,) = [row for row in rows if row["layer"] == "equipments"]
    with tempfile.TemporaryDirectory(prefix="immo-territorial-report-") as temporary:
        local = Path(temporary) / "equipments.zip"
        store.get_file(str(entry["object_key"]), local)
        labels = melodi_labels(local)
    result = {"equipements_total": "Ensemble des équipements"}
    for (variable, modality), label in labels.items():
        if variable == "FACILITY_DOM" and modality != "_T":
            result[f"equipements_domaine_{modality.lower()}"] = label
        if variable == "FACILITY_SDOM" and modality != "_T":
            result[f"equipements_sous_domaine_{modality.lower()}"] = label
    return result


def number(value: Any) -> str:
    if value is None:
        return "—"
    # Arrondi au plus proche, demi vers le haut : le format de Python arrondirait 10,5 à 10.
    rounded = Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return f"{rounded:,}".replace(",", " ")


def render(data: dict[str, Any], labels: dict[str, str], department: str, generated_on: str) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Variables communales du {department} — population, logements, équipements, aires")
    add("")
    add(
        f"**Généré le :** {generated_on} · **Ticket :** "
        "[D7](../backlog/D7-sources-territoriales.md) · **Décision :** "
        "[ADR-023](../decisions/ADR-023-sources-territoriales.md)"
    )
    add("")
    add("Ce fichier est **régénéré** par `make territorial-report`. Ne pas l'éditer à la main.")
    add("")
    add(
        "Ces variables décrivent une **commune**, pas une parcelle : les rattacher à une parcelle "
        "est une jointure administrative. Elles servent la segmentation des marchés "
        "([E6](../backlog/E6-segmentation-observee.md)) et n'entrent dans aucune mesure du "
        "baromètre ni du radar. Ce rapport publie des distributions ; il ne découpe rien."
    )
    add("")
    add("## Releases et verdicts")
    add("")
    add("| Release | Source | Publiée le | Communes | Lignes | dont absentes | Run | Verdict |")
    add("|---|---|---|---:|---:|---:|---|---|")
    for row in data["releases"]:
        add(
            f"| `{row['release_id']}` | {row['name']} | {row['source_published_on']} "
            f"| {row['communes']} | {number(row['rows'])} | {number(row['missing'])} "
            f"| `{row['import_run_id']}` | `{row['acceptance_status']}` |"
        )
    add("")
    add(
        "**Verdict `display_only`** pour les trois : licence, millésime, empreinte, schéma et "
        "couverture sont établis ; la maille est la commune, appariée par code officiel "
        "géographique 2025, le même que celui du référentiel. Le passage à `accepted` attend le "
        "profiling d'E6, seul à dire si ces variables séparent réellement les marchés."
    )
    add("")
    add("| Release | Fichier | SHA-256 | Octets |")
    add("|---|---|---|---:|")
    for row in data["assets"]:
        add(
            f"| `{row['release_id']}` | `{row['layer']}` | `{row['sha256'][:16]}…` "
            f"| {number(row['byte_size'])} |"
        )
    add("")
    add("## Distributions sur les communes")
    add("")
    add(
        "Effectif = communes valuées ; « abs. » = communes sans valeur, avec motif. Quantiles "
        "par interpolation (`percentile_cont`), sur les seules communes valuées ; valeurs "
        "arrondies à l'unité, demi vers le haut. « Lignes » compte les lignes en table, "
        "distances au pôle comprises."
    )
    add("")
    add(
        "| Indicateur | Période | Unité | Effectif | abs. | à zéro | Min | P10 | Q1 | Médiane "
        "| Q3 | P90 | Max | Somme |"
    )
    add("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in data["distributions"]:
        code = str(row["indicator_code"])
        name = f"`{code}`"
        if code in labels:
            name += f" — {labels[code]}"
        total = "—" if code == "aav_distance_centre_m" else number(row["total"])
        add(
            f"| {name} | {row['period']} | {row['unit'] or '—'} | {row['valued']} "
            f"| {row['missing']} | {row['zeros']} | {number(row['minimum'])} "
            f"| {number(row['p10'])} | {number(row['q1'])} "
            f"| {number(row['median'])} | {number(row['q3'])} "
            f"| {number(row['p90'])} | {number(row['maximum'])} | {total} |"
        )
    add("")
    add("Lecture :")
    add("")
    add(
        "- **Population** : populations de référence millésimées 2023. "
        "La population totale ajoute la population comptée à part à la population municipale ; "
        "sommer les populations totales compte deux fois certaines personnes."
    )
    add(
        "- **Logements** : estimations pondérées du recensement 2023, non arrondies. Les "
        "logements vacants ne sont pas importés (`SPEC.md` §12) ; les maisons et appartements ne "
        "couvrent pas tout le parc (autres types exclus)."
    )
    add(
        "- **Équipements** : dénombrement de la BPE 2025. Un zéro dit qu'aucun équipement du "
        "sous-domaine n'est recensé dans la commune — c'est la valeur observée, pas une absence."
    )
    add(
        "- **Distance au pôle** : entre centroïdes Lambert-93 de la commune et de la "
        "commune-centre de son aire d'attraction ; zéro pour la commune-centre elle-même. "
        "Absente (`not_applicable`) hors attraction."
    )
    add("")
    add("## Aires d'attraction des villes")
    add("")
    add("| Variable | Valeur | Communes |")
    add("|---|---|---:|")
    for row in data["categories"]:
        value = str(row["value"])
        if row["indicator_code"] == "aav_categorie" and value in AAV_CATEGORIES:
            value = f"{value} — {AAV_CATEGORIES[value]}"
        add(f"| `{row['indicator_code']}` | {value} | {row['communes']} |")
    add("")
    add(
        "La tranche de taille (`TAAV2017`) est celle de l'INSEE, calculée sur la population 2017 "
        "de l'aire ; elle n'est pas un seuil de ce projet."
    )
    add("")
    add("### Communes sans distance au pôle")
    add("")
    add(
        "Leur commune-centre est hors du référentiel importé (le 35 seul) : la distance reste "
        "absente, avec le motif `source_value_missing`."
    )
    add("")
    add("| Commune | Nom | Commune-centre de l'aire |")
    add("|---|---|---|")
    for row in data["gaps"]:
        add(f"| `{row['commune_code']}` | {row['name'] or '—'} | `{row['centre']}` |")
    add("")
    add("## Limites")
    add("")
    add(
        "- Une commune n'est pas homogène : Rennes a une valeur, ses quartiers n'en ont pas. "
        "Toute lecture à la parcelle hérite de cette imprécision."
    )
    add("- La distance entre centroïdes n'est ni un temps de trajet ni une distance par la route.")
    add(
        "- Les communes du 35 dont l'aire déborde du département ont une commune-centre voisine "
        "dont la distance ne peut pas se mesurer tant que le référentiel se limite au 35."
    )
    add("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), default="35")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    settings = CadastreSettings.from_environment()
    store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        data = {
            "releases": releases(connection, arguments.department),
            "assets": assets(connection, arguments.department),
            "distributions": distributions(connection, arguments.department),
            "categories": categories(connection, arguments.department),
            "gaps": distance_gaps(connection, arguments.department),
        }
    labels = bpe_labels(store, data["assets"])
    arguments.output.write_text(
        render(data, labels, arguments.department, date.today().isoformat()), encoding="utf-8"
    )
    print(f"écrit {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
