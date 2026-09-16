#!/usr/bin/env python3
"""Écrire BLD-001..003 et REN-001..008 sur le bâtiment physique — BUG-13, ADR-024.

Le sujet est le regroupement RNB de `reference.physical_building` (BUG-12), celui auquel les DPE
se rattachent par `id_rnb`. Les sources des onze features — BDNB, BD TOPO, BAN, DPE — sont
`display_only` : `SPEC.md` §13.8 interdit qu'elles alimentent un score. Chaque feature s'écrit
donc **absente, `source_not_accepted`**, une ligne par bâtiment physique, en citant les releases
lues — comme `LAND-008` pour chaque unité foncière.

Aucune valeur n'est calculée : l'écriture est ensembliste, une requête par feature. Le script
**refuse de s'exécuter** si l'une des sources compte une release acceptée : le calcul des valeurs
demande alors ses chargeurs, sous ticket, et ce script ne doit pas écrire une absence devenue
fausse.
"""

import argparse
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.settings import CadastreSettings

FEATURE_CODES: tuple[str, ...] = (
    "BLD-001",
    "BLD-002",
    "BLD-003",
    "REN-001",
    "REN-002",
    "REN-003",
    "REN-004",
    "REN-005",
    "REN-006",
    "REN-007",
    "REN-008",
)
FEATURE_VERSION = 1
GROUPING_SOURCE = "rnb"
MISSING_REASON = "source_not_accepted"
NBSP = "\N{NO-BREAK SPACE}"

UPSERT = """
INSERT INTO feature.feature_value (
    physical_building_id, feature_code, feature_version, missing_reason,
    source_release_ids, formula, transformation_version
)
SELECT building.id, definition.code, definition.version, %(reason)s,
       %(releases)s::jsonb, definition.formula, definition.transformation_version
  FROM reference.physical_building AS building
  JOIN feature.feature_definition AS definition
    ON definition.code = %(code)s AND definition.version = %(version)s
 WHERE building.source = %(grouping)s AND building.department_code = %(department)s
ON CONFLICT (property_unit_id, building_id, physical_building_id, feature_code, feature_version)
DO UPDATE SET numeric_value = NULL,
              text_value = NULL,
              json_value = NULL,
              missing_reason = excluded.missing_reason,
              source_observation_ids = '[]'::jsonb,
              source_release_ids = excluded.source_release_ids,
              formula = excluded.formula,
              transformation_version = excluded.transformation_version,
              computed_at = now()
"""


def number(value: int) -> str:
    return f"{value:,}".replace(",", NBSP)


def refusal(accepted: Mapping[str, Sequence[str]]) -> str | None:
    """Le motif du refus si une source d'une feature de bâtiment compte une release acceptée."""
    if not accepted:
        return None
    detail = "; ".join(
        f"{source} : {', '.join(releases)}" for source, releases in sorted(accepted.items())
    )
    return (
        f"Release acceptée pour une source de feature de bâtiment ({detail}). "
        f"L'absence « {MISSING_REASON} » serait fausse : le calcul des valeurs demande ses "
        "chargeurs, sous ticket."
    )


def cited_releases(datasets: Iterable[str], releases: Mapping[str, str]) -> list[str]:
    """Les releases lues pour décider l'absence : une par source déclarée, ordre du contrat."""
    return [releases[dataset] for dataset in datasets if dataset in releases]


def definitions(connection: psycopg.Connection[Any]) -> dict[str, list[str]]:
    rows = connection.execute(
        """
        SELECT code, datasets FROM feature.feature_definition
         WHERE version = %s AND code = ANY(%s)
        """,
        (FEATURE_VERSION, list(FEATURE_CODES)),
    ).fetchall()
    found = {str(code): [str(item) for item in datasets] for code, datasets in rows}
    missing = [code for code in FEATURE_CODES if code not in found]
    if missing:
        raise SystemExit(f"Définitions absentes du registre : {', '.join(missing)}")
    return found


def source_releases(
    connection: psycopg.Connection[Any], sources: Sequence[str]
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """La dernière release non retirée de chaque source, et les releases acceptées."""
    rows = connection.execute(
        """
        SELECT data_source_id, id, acceptance_status
          FROM meta.dataset_release
         WHERE data_source_id = ANY(%s) AND lifecycle_status <> 'retired'
         ORDER BY data_source_id, source_published_on DESC NULLS LAST, id DESC
        """,
        (list(sources),),
    ).fetchall()
    latest: dict[str, str] = {}
    accepted: dict[str, list[str]] = {}
    for source, release, acceptance in rows:
        latest.setdefault(str(source), str(release))
        if acceptance == "accepted":
            accepted.setdefault(str(source), []).append(str(release))
    return latest, accepted


def counts(connection: psycopg.Connection[Any], department: str) -> dict[str, Any]:
    by_feature = connection.execute(
        """
        SELECT value.feature_code, value.missing_reason, value.source_release_ids::text,
               count(*)
          FROM feature.feature_value AS value
          JOIN reference.physical_building AS building
            ON building.id = value.physical_building_id
         WHERE building.department_code = %s
         GROUP BY 1, 2, 3 ORDER BY 1
        """,
        (department,),
    ).fetchall()
    subjects = connection.execute(
        """
        SELECT count(*) FILTER (WHERE property_unit_id IS NOT NULL),
               count(*) FILTER (WHERE building_id IS NOT NULL),
               count(*) FILTER (WHERE physical_building_id IS NOT NULL),
               count(*) FILTER (WHERE physical_building_id IS NOT NULL
                                  AND feature_code !~ '^(BLD|REN)-')
          FROM feature.feature_value
        """
    ).fetchone()
    groupings = connection.execute(
        """
        SELECT source, count(*), sum(member_count) FROM reference.physical_building
         WHERE department_code = %s GROUP BY 1 ORDER BY 1
        """,
        (department,),
    ).fetchall()
    return {"by_feature": by_feature, "subjects": subjects, "groupings": groupings}


def render(department: str, data: Mapping[str, Any], generated_on: date) -> str:
    unit_rows, record_rows, physical_rows, foreign_rows = data["subjects"]
    lines = [
        f"# Features de bâtiment — département {department}",
        "",
        f"**Généré le** {generated_on.isoformat()} par `make building-features` — ticket "
        "[BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md), "
        "[ADR-024](../decisions/ADR-024-sujet-des-features-batiment.md).",
        "",
        "Les features `BLD-001..003` et `REN-001..008` portent sur le **bâtiment physique**, "
        f"regroupement `{GROUPING_SOURCE}` de `reference.physical_building` (BUG-12). Leurs "
        "sources sont `display_only` : chacune est écrite absente, "
        f"`{MISSING_REASON}`, pour chaque bâtiment physique `{GROUPING_SOURCE}` du département.",
        "",
        "## Regroupements",
        "",
        "| Regroupement | Bâtiments physiques | Enregistrements regroupés |",
        "|---|---:|---:|",
    ]
    for source, buildings, members in data["groupings"]:
        lines.append(f"| `{source}` | {number(int(buildings))} | {number(int(members))} |")
    lines += [
        "",
        "## Lignes écrites",
        "",
        "| Feature | Motif d'absence | Releases citées | Bâtiments physiques |",
        "|---|---|---|---:|",
    ]
    for code, reason, releases, count in data["by_feature"]:
        cited = ", ".join(f"`{release}`" for release in json.loads(releases))
        lines.append(f"| {code} | `{reason}` | {cited} | {number(int(count))} |")
    lines += [
        "",
        "## Sujets de `feature.feature_value`, tout le territoire",
        "",
        "| Sujet | Lignes |",
        "|---|---:|",
        f"| unité foncière | {number(int(unit_rows))} |",
        f"| enregistrement RNB (`building_id`) | {number(int(record_rows))} |",
        f"| bâtiment physique | {number(int(physical_rows))} |",
        f"| bâtiment physique, feature hors `BLD`/`REN` | {number(int(foreign_rows))} |",
        "",
        "La base refuse une feature `BLD-*` ou `REN-*` sur un enregistrement "
        "(`feature_value_building_family_subject`). Qu'aucune autre feature ne porte sur un "
        "bâtiment physique est un constat de ce rapport, pas une contrainte.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    output = arguments.output or Path(f"docs/data/building-features-{arguments.department}.md")

    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        declared = definitions(connection)
        sources = sorted({dataset for datasets in declared.values() for dataset in datasets})
        latest, accepted = source_releases(connection, sources)
        reason = refusal(accepted)
        if reason is not None:
            raise SystemExit(reason)
        for code in FEATURE_CODES:
            cursor = connection.execute(
                UPSERT,
                {
                    "reason": MISSING_REASON,
                    "releases": json.dumps(cited_releases(declared[code], latest)),
                    "code": code,
                    "version": FEATURE_VERSION,
                    "grouping": GROUPING_SOURCE,
                    "department": arguments.department,
                },
            )
            connection.commit()
            print(f"{code} : {number(cursor.rowcount)} bâtiments physiques", flush=True)
        data = counts(connection, arguments.department)
    output.write_text(render(arguments.department, data, date.today()), encoding="utf-8")
    print(f"Rapport écrit : {output}")


if __name__ == "__main__":
    main()
