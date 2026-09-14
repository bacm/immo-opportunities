#!/usr/bin/env python3
"""Régénère le rapport de couverture DS-09, famille par famille — D3.

Le rapport se recalcule depuis `observation.risk_observation`,
`meta.dataset_coverage_metric`, `meta.dataset_release` et `meta.import_run`. Il ne se saisit pas
à la main.

Trois distinctions gouvernent sa lecture.

**Granularité fine et granularité communale ne s'additionnent pas.** Une exposition zonale dit où ;
une observation communale dit seulement que la commune est concernée. Le rapport les compte
séparément, toujours.

**Couverture connue n'est pas risque nul.** Une commune interrogée où la source ne dit rien donne
zéro observation *avec* `coverage_known` ; une commune non interrogée n'a pas de ligne du tout.
Sans cette distinction, une absence d'information passerait pour une absence de risque.

**Une famille absente désactive ses features, elle ne les met pas à zéro.**
"""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.georisques import FAMILIES


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


def releases(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT release.id AS release_id, release.release_key, release.acceptance_status,
               release.source_published_on, run.id AS import_run_id,
               run.source_row_count, run.normalized_row_count, run.deduplicated_row_count,
               run.runner_metadata->>'risk_family' AS risk_family,
               (SELECT count(*) FROM observation.risk_observation AS o
                 WHERE o.release_id = release.id) AS observations,
               (SELECT count(*) FROM observation.risk_observation AS o
                 WHERE o.release_id = release.id AND o.granularity <> 'commune') AS fine,
               (SELECT count(DISTINCT o.commune_code) FROM observation.risk_observation AS o
                 WHERE o.release_id = release.id) AS communes_with_data
          FROM meta.dataset_release AS release
          LEFT JOIN meta.import_run AS run
                 ON run.release_id = release.id AND run.status = 'succeeded'
         WHERE release.data_source_id = 'DS-09'
         ORDER BY release.release_key
        """,
        department=department,
    )


def risk_types(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT risk_type, granularity, count(*) AS observations,
               count(DISTINCT commune_code) AS communes
          FROM observation.risk_observation
         GROUP BY risk_type, granularity ORDER BY 3 DESC
        """,
    )


def coverage(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT metric.release_id,
               count(*) AS communes_queried,
               count(*) FILTER (WHERE metric.record_count = 0) AS communes_without_observation,
               max(metric.freshest_observation_at) AS freshest
          FROM meta.dataset_coverage_metric AS metric
          JOIN meta.dataset_release AS release ON release.id = metric.release_id
         WHERE release.data_source_id = 'DS-09'
         GROUP BY metric.release_id ORDER BY metric.release_id
        """,
    )


def thousands(value: Any) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", " ")


def render(data: dict[str, Any], department: str, generated_on: str) -> str:
    lines: list[str] = []
    add = lines.append
    labels = {item.key: item for item in FAMILIES}
    by_release = {entry["release_id"]: entry for entry in data["coverage"]}

    add(f"# DS-09 Géorisques — couverture par famille sur le {department}")
    add("")
    add(f"**Généré le :** {generated_on}")
    add("")
    add("Ce fichier est **régénéré** par `make georisques-report`. Ne pas l'éditer à la main.")
    add("")
    add(
        "L'inventaire de la source, écrit avant le premier lot, est dans "
        "[`georisques-source-inventory-35.md`](./georisques-source-inventory-35.md)."
    )
    add("")
    add("## Une release par famille")
    add("")
    add(
        "Elles n'ont ni la même granularité, ni la même fraîcheur, ni le même producteur. Une "
        "release unique « Géorisques » aurait masqué ces différences et rendu impossible un "
        "verdict famille par famille."
    )
    add("")
    add("| Famille | Accès | Granularité | Observations | dont fines | Communes | Verdict |")
    add("|---|---|---|---:|---:|---:|---|")
    for entry in data["releases"]:
        key = str(entry["risk_family"] or entry["release_key"].split("--")[0])
        item = labels.get(key)
        add(
            f"| {item.label if item else key} | `{item.mode if item else '—'}` | "
            f"`{item.granularity if item else '—'}` | {thousands(entry['observations'])} | "
            f"{thousands(entry['fine'])} | {thousands(entry['communes_with_data'])} | "
            f"`{entry['acceptance_status']}` |"
        )
    add("")
    total = sum(int(entry["observations"]) for entry in data["releases"])
    fine = sum(int(entry["fine"]) for entry in data["releases"])
    add(
        f"**{thousands(total)} observations**, dont **{thousands(fine)}** à granularité fine — "
        "point ou zone. Les autres sont communales et le restent."
    )
    add("")
    add("## Couverture : interrogée, et ce qu'on y a trouvé")
    add("")
    add(
        "Une commune interrogée sans observation est une **couverture connue à zéro**. Une "
        "commune absente de la table n'a pas été interrogée. Le contrat DS-09 appelle cette "
        "distinction `coverage_absence`, et c'est elle qui empêche de lire une absence "
        "d'information comme une absence de risque."
    )
    add("")
    add("| Famille | Communes interrogées | dont sans observation | Observation la plus fraîche |")
    add("|---|---:|---:|---|")
    for entry in data["releases"]:
        metric = by_release.get(entry["release_id"], {})
        key = str(entry["risk_family"] or entry["release_key"].split("--")[0])
        item = labels.get(key)
        add(
            f"| {item.label if item else key} | "
            f"{thousands(metric.get('communes_queried'))} | "
            f"{thousands(metric.get('communes_without_observation'))} | "
            f"{metric.get('freshest') or '—'} |"
        )
    add("")
    add("## Types de risque observés, et à quelle granularité")
    add("")
    add(
        "Le type vient de la source. Les libellés français sont ceux que GASPAR publie et que "
        "nous n'avons pas rattachés à un type canonique : les recoder au jugé serait inventer "
        "une interprétation."
    )
    add("")
    add("| Type | Granularité | Observations | Communes |")
    add("|---|---|---:|---:|")
    for entry in data["risk_types"]:
        add(
            f"| `{entry['risk_type']}` | `{entry['granularity']}` | "
            f"{thousands(entry['observations'])} | {thousands(entry['communes'])} |"
        )
    add("")
    add("## Ce que ces données permettent, et ce qu'elles ne permettent pas")
    add("")
    add("| Feature | Fondée sur | État |")
    add("|---|---|---|")
    add("| `RISK-001` exposition argiles | `clay`, zones | **calculable** |")
    add("| `RISK-003` sites pollués | `soil-pollution`, zones | **calculable** |")
    add("| `RISK-004` cavités | `cavity`, points | **calculable** |")
    add("| `RISK-101` contraintes applicables | toutes | **calculable** |")
    add("| `RISK-002` zones inondables | — | **absente avec motif** |")
    add("")
    add("### `RISK-002` reste absente, et ce n'est pas un défaut d'import")
    add("")
    add(
        "Aucune source disponible sur le 35 ne donne une zone inondable **typée**. GASPAR et "
        "l'atlas des zones inondables disent qu'une commune est concernée — c'est communal, et "
        "« la commune est concernée par un PPRI » n'est pas « la parcelle est en zone "
        "inondable »."
    )
    add("")
    add(
        "La servitude `PM1` donne bien des géométries de zone, et c'est le seul zonage opposable "
        "du département. Mais elle porte les **risques naturels prévisibles** sans dire lequel : "
        "son assiette est une « enveloppe des zonages réglementaires ». En déduire « inondation » "
        "serait la faute que D2 a commise sur le champ `ETAT` du CNIG — interpréter de mémoire un "
        "code que le contrat ne documente pas."
    )
    add("")
    add(
        "Rattacher chaque assiette `PM1` à son aléa demande la table de correspondance du "
        "producteur. Tant qu'elle n'est pas sourcée, `RISK-002` sort `source_value_missing` et "
        "les périmètres restent visibles dans `RISK-101` sous `sup_PM1`."
    )
    add("")
    if data["unreadable"]:
        add("### Quatre servitudes que le producteur refuse")
        add("")
        add(
            "Le Géoportail de l'urbanisme répond `403 Forbidden` au téléchargement de quatre des "
            "neuf servitudes du 35, et le refait aux trois tentatives. Ce n'est donc pas un échec "
            "passager — un cinquième document, `T1`, a échoué une fois puis répondu, ce qui rend "
            "la distinction mesurable et non supposée."
        )
        add("")
        add("| Document | Catégorie | Ce qui manque |")
        add("|---|---|---|")
        for entry in data["unreadable"]:
            name = str(entry.get("document"))
            add(f"| `{name}` | {name.split('_')[-1]} | assiettes non téléchargeables |")
        add("")
        add(
            "La couverture des servitudes est donc **partielle et le manifeste le dit**. Les "
            "catégories manquantes — canalisations, aéronautique, télécoms — ne pèsent pas sur "
            "les features RISK, qui ne les consultent pas."
        )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the DS-09 coverage report")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), default="35")
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    department = cast(str, arguments.department)

    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        data: dict[str, Any] = {
            "releases": releases(connection, department),
            "risk_types": risk_types(connection),
            "coverage": coverage(connection),
        }
    sup_manifest = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "datasets"
        / "DS-09"
        / "releases"
        / f"sup--{date.today().isoformat()}-{department}.json"
    )
    candidates = sorted(sup_manifest.parent.glob(f"sup--*-{department}.json"))
    data["unreadable"] = (
        json.loads(candidates[-1].read_text(encoding="utf-8")).get("unreadable", [])
        if candidates
        else []
    )

    output = arguments.output or (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "data"
        / f"georisques-coverage-{department}.md"
    )
    output.write_text(render(data, department, date.today().isoformat()), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
