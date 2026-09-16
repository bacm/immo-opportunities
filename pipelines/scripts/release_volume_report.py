#!/usr/bin/env python3
"""Le volume porté par chaque release, pour décider d'un retrait — BUG-08, ADR-022.

Le retrait d'une release remplacée est un geste explicite ; ce rapport en donne le chiffre. Il
compte, release par release, les lignes des tables que `meta.purge_dataset_release_rows` retire,
et dit ce qui protège chaque release : active, membre d'un bundle, déjà retirée.
"""

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from immo_pipelines.cadastre.settings import CadastreSettings

# Les tables purgées par ADR-022, sans leurs enfants en cascade.
COUNTED_TABLES: tuple[str, ...] = (
    "observation.transaction",
    "observation.energy_assessment",
    "observation.urban_document",
    "observation.risk_observation",
    "observation.road_segment",
    "meta.entity_source_observation",
    "meta.attribute_quarantine",
    "meta.geometry_quarantine",
    "meta.dataset_coverage_metric",
    "meta.entity_match_metric",
    "meta.data_quality_check",
    "reference.cadastral_parcel",
    "reference.cadastral_building",
    "reference.administrative_area",
    "meta.import_run",
)

NBSP = "\N{NO-BREAK SPACE}"


def number(value: int) -> str:
    return f"{value:,}".replace(",", NBSP)


def fetch(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    releases = connection.execute(
        """
        SELECT release.data_source_id, release.id, release.lifecycle_status,
               release.acceptance_status,
               EXISTS (SELECT 1 FROM meta.active_dataset_release AS active
                        WHERE active.release_id = release.id) AS active,
               EXISTS (SELECT 1 FROM meta.regional_release_member AS member
                        WHERE member.release_id = release.id) AS bundled,
               EXISTS (SELECT 1 FROM meta.publication_event AS event
                        WHERE event.release_id = release.id) AS published
          FROM meta.dataset_release AS release
         ORDER BY 1, 2
        """
    ).fetchall()
    rows: dict[str, dict[str, int]] = defaultdict(dict)
    for table in COUNTED_TABLES:
        schema, name = table.split(".")
        query = sql.SQL("SELECT release_id, count(*) FROM {} GROUP BY 1").format(
            sql.Identifier(schema, name)
        )
        for release_id, count in connection.execute(query).fetchall():
            rows[str(release_id)][table] = int(count)
    size = connection.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    database_size = size.fetchone()
    return {
        "releases": releases,
        "rows": rows,
        "database_size": database_size[0] if database_size else None,
    }


def protection(active: bool, bundled: bool, lifecycle: str) -> str:
    if lifecycle == "retired":
        return "déjà retirée"
    if active:
        return "active — non retirable"
    if bundled:
        return "membre d'un bundle — non retirable"
    return "retirable si remplacée"


def render(data: dict[str, Any], generated_on: date) -> str:
    lines = [
        "# Volume par release",
        "",
        f"**Généré le** {generated_on.isoformat()} par `make release-volume` — ticket "
        "[BUG-08](../backlog/BUG-08-cycle-de-vie-des-releases-remplacees.md), "
        "[ADR-022](../decisions/ADR-022-retrait-des-releases-remplacees.md).",
        "",
        f"Base entière : **{data['database_size']}** (unités binaires). Les lignes comptées sont",
        "celles des tables que le retrait purge directement ; les enfants en cascade (liens",
        "d'observation, lots de vente, zones et prescriptions d'urbanisme) partent avec elles",
        "et ne sont pas comptés. « Publiée » : au moins un événement de publication, même si la",
        "release n'est plus active. « Retirable » ne veut pas dire « remplacée » : deux releases",
        "d'une source peuvent se compléter, comme les deux releases DVF ; le motif écrit du",
        "retrait porte ce jugement. Les valeurs dérivées d'une release retirée gardent sa",
        "référence mais plus ses données (ADR-022).",
        "",
        "| Source | Release | Cycle | Acceptation | Publiée | Lignes | Statut |",
        "|---|---|---|---|:---:|---:|---|",
    ]
    for source, release, lifecycle, acceptance, active, bundled, published in data["releases"]:
        total = sum(data["rows"].get(release, {}).values())
        lines.append(
            f"| {source} | `{release}` | {lifecycle} | {acceptance} | "
            f"{'oui' if published else 'non'} | {number(total)} | "
            f"{protection(active, bundled, lifecycle)} |"
        )
    lines += ["", "## Détail par table", "", "| Release | Table | Lignes |", "|---|---|---:|"]
    for release in sorted(data["rows"]):
        for table, count in sorted(data["rows"][release].items()):
            lines.append(f"| `{release}` | `{table}` | {number(count)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/data/release-volume-35.md"))
    arguments = parser.parse_args()
    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        data = fetch(connection)
    arguments.output.write_text(render(data, date.today()), encoding="utf-8")
    print(f"Rapport écrit : {arguments.output}")


if __name__ == "__main__":
    main()
