#!/usr/bin/env python3
"""Régénère le rapport qualité des données métier — D5, sources DS-06 à DS-09.

Le rapport se recalcule depuis `meta.dataset_release`, `meta.dataset_coverage_metric`,
`feature.feature_value` et les tables d'observation. Il ne se saisit pas à la main.

## La ventilation des motifs d'absence est le cœur du rapport

`source_not_accepted`, « donnée inexistante pour cette unité », « support statistique
insuffisant » et « appariement ambigu » ont des conséquences différentes sur le scoring. Les
agréger en un seul taux d'absence rendrait E1 impossible à conduire correctement — c'est la
raison d'être de ce fichier, pas un détail de présentation.

## Aucune valeur agrégée sans son volume

Un taux sans son dénominateur ne se relit pas. Chaque part publiée ici porte le compte dont elle
vient.

## Les cas défavorables sont publiés

Une commune où rien n'est calculable est une information utile pour le pilote, pas une gêne à
masquer.
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings

SOURCES = ("DS-06", "DS-07", "DS-08", "DS-09")


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


def verdicts(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT source.id AS data_source_id, source.name,
               count(release.id) AS releases,
               count(*) FILTER (WHERE release.acceptance_status = 'accepted') AS accepted,
               count(*) FILTER (WHERE release.acceptance_status = 'display_only') AS display_only,
               count(*) FILTER (WHERE release.acceptance_status = 'pending') AS pending,
               count(DISTINCT run.id) FILTER (WHERE run.status = 'succeeded') AS import_runs
          FROM meta.data_source AS source
          LEFT JOIN meta.dataset_release AS release ON release.data_source_id = source.id
          LEFT JOIN meta.import_run AS run ON run.release_id = release.id
         WHERE source.id = ANY(%(sources)s::text[])
         GROUP BY source.id, source.name ORDER BY source.id
        """,
        sources=list(SOURCES),
    )


def volumes(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT 'DS-06' AS data_source_id, 'transactions' AS unit, count(*) AS records,
               count(DISTINCT commune_code) AS communes, max(mutation_date) AS freshest
          FROM observation.transaction WHERE department_code = %(department)s
        UNION ALL
        SELECT 'DS-07', 'diagnostics', count(*), count(DISTINCT commune_code),
               max(assessment_date)
          FROM observation.energy_assessment WHERE department_code = %(department)s
        UNION ALL
        -- Une zone n'a pas de commune : c'est le **document** qui porte les siennes, et il en
        -- porte plusieurs quand c'est un PLUi. Le compte se fait donc sur les communes
        -- declarees par les documents de la release.
        SELECT 'DS-08', 'zones', count(*),
               (SELECT count(DISTINCT commune)
                  FROM observation.urban_document AS document
                  CROSS JOIN LATERAL jsonb_array_elements_text(document.commune_codes) AS commune),
               (SELECT max(published_at) FROM observation.urban_document)
          FROM observation.urban_zone AS zone
        UNION ALL
        SELECT 'DS-09', 'observations', count(*), count(DISTINCT commune_code),
               max(observed_at)
          FROM observation.risk_observation WHERE department_code = %(department)s
        ORDER BY 1
        """,
        department=department,
    )


def feature_completeness(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    """Valeurs présentes et absences **par motif**, pour chaque feature matérialisée."""
    return fetch(
        connection,
        """
        SELECT feature_code,
               count(*) AS total,
               count(*) FILTER (WHERE missing_reason IS NULL) AS present,
               count(*) FILTER (WHERE missing_reason = 'source_not_accepted') AS not_accepted,
               count(*) FILTER (WHERE missing_reason = 'source_value_missing') AS value_missing,
               count(*) FILTER (WHERE missing_reason = 'not_applicable') AS not_applicable,
               count(*) FILTER (WHERE missing_reason = 'ambiguous_match') AS ambiguous,
               count(*) FILTER (WHERE missing_reason = 'invalid_geometry') AS invalid_geometry,
               count(*) FILTER (WHERE missing_reason = 'calculation_error') AS calculation_error
          FROM feature.feature_value
         GROUP BY feature_code ORDER BY feature_code
        """,
    )


def feature_distributions(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT feature_code,
               count(*) AS observed,
               min(numeric_value) AS minimum,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY numeric_value) AS q1,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY numeric_value) AS median,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY numeric_value) AS q3,
               max(numeric_value) AS maximum
          FROM feature.feature_value
         WHERE numeric_value IS NOT NULL
         GROUP BY feature_code ORDER BY feature_code
        """,
    )


def worst_communes(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    """Les communes où le moins de choses sont calculables. Un cas défavorable est publiable."""
    return fetch(
        connection,
        """
        SELECT unit.commune_code,
               area.name AS commune_name,
               count(DISTINCT unit.id) AS units,
               count(*) FILTER (WHERE value.missing_reason IS NULL) AS present,
               count(*) AS feature_rows
          FROM reference.property_unit AS unit
          LEFT JOIN reference.area AS area
                 ON area.code = unit.commune_code AND area.area_type = 'commune'
          JOIN feature.feature_value AS value ON value.property_unit_id = unit.id
         WHERE unit.department_code = %(department)s
         GROUP BY unit.commune_code, area.name
         ORDER BY (count(*) FILTER (WHERE value.missing_reason IS NULL))::numeric
                  / greatest(count(*), 1) ASC, count(DISTINCT unit.id) DESC
         LIMIT 10
        """,
        department=department,
    )


def vocabulary_gap(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    """Un écart entre sources, mesuré et **non arbitré**.

    Le BRGM cartographie l'exposition au retrait-gonflement des argiles. GASPAR recense, commune
    par commune, les risques faisant l'objet d'une procédure. Les deux parlent du même phénomène
    et **n'emploient pas le même vocabulaire** : sur le 35, GASPAR n'écrit jamais
    « Retrait-gonflement des argiles ».

    Le rapport publie donc les deux vocabulaires côte à côte plutôt qu'une équivalence. Décréter
    ici que deux libellés désignent le même aléa serait une interprétation que le contrat ne
    porte pas.
    """
    mapped = fetch(
        connection,
        """
        SELECT count(DISTINCT commune_code) AS communes
          FROM observation.risk_observation
         WHERE risk_type = 'clay' AND granularity = 'zone'
        """,
    )
    labels = fetch(
        connection,
        """
        SELECT risk_type, count(DISTINCT commune_code) AS communes
          FROM observation.risk_observation
         WHERE granularity = 'commune'
           AND release_id LIKE %(prefix)s
         GROUP BY risk_type ORDER BY 2 DESC
        """,
        prefix="DS-09@gaspar-risks%",
    )
    return {"clay_zone_communes": mapped[0]["communes"] if mapped else 0, "gaspar_labels": labels}


def thousands(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and not float(value).is_integer():
        return f"{float(value):,.1f}".replace(",", " ").replace(".", ",")
    return f"{int(value):,}".replace(",", " ")


def percent(part: Any, whole: Any) -> str:
    if not whole:
        return "—"
    return f"{100 * float(part) / float(whole):.2f} %".replace(".", ",")


def render(data: dict[str, Any], department: str, generated_on: str) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"# Qualité des données métier — département {department}")
    add("")
    add(
        f"**Généré le :** {generated_on} · "
        "**Ticket :** [D5](../backlog/D5-rapports-qualite-metier.md)"
    )
    add("")
    add("Ce fichier est **régénéré** par `make market-data-quality`. Ne pas l'éditer à la main.")
    add("")
    add(
        "Les rapports par source restent la référence de détail : "
        "[DVF](./dvf-quality-35.md), [GPU](./gpu-coverage-35.md), "
        "[DPE](./dpe-matching-35.md), [Géorisques](./georisques-coverage-35.md)."
    )
    add("")
    add("## Verdicts et traçabilité")
    add("")
    add("| Source | Releases | acceptées | `display_only` | `pending` | Runs d'import |")
    add("|---|---:|---:|---:|---:|---:|")
    for entry in data["verdicts"]:
        add(
            f"| {entry['data_source_id']} {entry['name']} | {thousands(entry['releases'])} | "
            f"{thousands(entry['accepted'])} | {thousands(entry['display_only'])} | "
            f"{thousands(entry['pending'])} | {thousands(entry['import_runs'])} |"
        )
    add("")
    add(
        "**Aucune source métier n'est `accepted`.** Les quatre attendent la revue manuelle "
        "stratifiée de [D6](../backlog/D6-revue-manuelle-metier.md)."
    )
    add("")
    # Le constat se **derive** du tableau. L'ecrire en dur l'aurait laisse affirmer un defaut
    # corrige : c'est exactement ce qui s'est produit entre la premiere generation de ce rapport
    # et la cloture de BUG-14.
    untraced = [entry for entry in data["verdicts"] if not int(entry["import_runs"] or 0)]
    if untraced:
        names = ", ".join(str(entry["data_source_id"]) for entry in untraced)
        add(
            f"**La colonne des runs d'import est celle à lire en premier.** {names} n'en a "
            "aucun : son import n'écrit pas dans `meta.import_run`. Une release sans import "
            "traçable ne doit pas être publiable, et la porte d'acceptation la refuse — à juste "
            "titre. Voir [BUG-14](../backlog/BUG-14-import-gpu-sans-trace.md)."
        )
    else:
        add(
            "**Chaque release porte au moins un run d'import réussi.** Ce n'était pas le cas "
            "avant [BUG-14](../backlog/BUG-14-import-gpu-sans-trace.md) : DS-06 et DS-08 "
            "n'écrivaient aucun run, et le second ne pouvait donc recevoir aucun verdict. Le "
            "ticket relate ce que la réimportation a révélé ; ce rapport ne porte que l'état "
            "courant."
        )
    add("")
    add("## Volumétrie et fraîcheur par source")
    add("")
    add("| Source | Unité | Enregistrements | Communes | Donnée la plus récente |")
    add("|---|---|---:|---:|---|")
    for entry in data["volumes"]:
        add(
            f"| {entry['data_source_id']} | {entry['unit']} | {thousands(entry['records'])} | "
            f"{thousands(entry['communes'])} | {entry['freshest'] or '—'} |"
        )
    add("")
    add("## Complétude par feature, ventilée par motif d'absence")
    add("")
    add(
        "C'est le cœur du rapport. Quatre motifs différents n'appellent pas la même décision : "
        "une source non acceptée s'ignore en bloc, une valeur absente se mesure, un appariement "
        "ambigu se revoit à la main, une feature non applicable ne se compte pas comme un manque."
    )
    add("")
    add(
        "| Feature | Total | Présentes | `source_not_accepted` | `source_value_missing` "
        "| `not_applicable` | `ambiguous_match` | Somme vérifiée |"
    )
    add("|---|---:|---:|---:|---:|---:|---:|---|")
    for entry in data["completeness"]:
        total = int(entry["total"])
        parts = sum(
            int(entry[key])
            for key in (
                "present",
                "not_accepted",
                "value_missing",
                "not_applicable",
                "ambiguous",
                "invalid_geometry",
                "calculation_error",
            )
        )
        add(
            f"| `{entry['feature_code']}` | {thousands(total)} | "
            f"{thousands(entry['present'])} | {thousands(entry['not_accepted'])} | "
            f"{thousands(entry['value_missing'])} | {thousands(entry['not_applicable'])} | "
            f"{thousands(entry['ambiguous'])} | {'oui' if parts == total else '**NON**'} |"
        )
    add("")
    add(
        "La dernière colonne vérifie l'invariant que D5 impose : présentes + absences par motif "
        "= volume total, par feature. Un `NON` serait un motif d'absence non prévu."
    )
    add("")
    add("## Distributions observées")
    add("")
    add("| Feature | Observations | Min | Q1 | Médiane | Q3 | Max |")
    add("|---|---:|---:|---:|---:|---:|---:|")
    for entry in data["distributions"]:
        add(
            f"| `{entry['feature_code']}` | {thousands(entry['observed'])} | "
            f"{thousands(entry['minimum'])} | {thousands(entry['q1'])} | "
            f"{thousands(entry['median'])} | {thousands(entry['q3'])} | "
            f"{thousands(entry['maximum'])} |"
        )
    add("")
    add("## Les communes où le moins de choses sont calculables")
    add("")
    add("Un cas défavorable est une information pour le pilote, pas une gêne à masquer.")
    add("")
    add("| Commune | Unités | Valeurs présentes | Lignes de feature | Part présente |")
    add("|---|---:|---:|---:|---:|")
    for entry in data["worst"]:
        add(
            f"| {entry['commune_name'] or entry['commune_code']} ({entry['commune_code']}) | "
            f"{thousands(entry['units'])} | {thousands(entry['present'])} | "
            f"{thousands(entry['feature_rows'])} | "
            f"{percent(entry['present'], entry['feature_rows'])} |"
        )
    add("")
    add("## Un écart de vocabulaire entre sources, mesuré et non arbitré")
    add("")
    gap = data["vocabulary"]
    add(
        f"Le BRGM cartographie l'exposition au retrait-gonflement des argiles sur "
        f"**{thousands(gap['clay_zone_communes'])} communes** du département, en zones. GASPAR "
        "recense commune par commune les risques faisant l'objet d'une procédure — et, sur le 35, "
        "**n'écrit jamais « Retrait-gonflement des argiles »**. Voici ce qu'il écrit :"
    )
    add("")
    add("| Libellé GASPAR, ou type canonique quand il est sourcé | Communes |")
    add("|---|---:|")
    for entry in gap["gaspar_labels"]:
        add(f"| `{entry['risk_type']}` | {thousands(entry['communes'])} |")
    add("")
    add(
        "Les libellés restés en français sont ceux que notre table de correspondance ne couvre "
        "pas. Décréter ici que « Tassements différentiels » désigne le même aléa que la couche "
        "du BRGM serait une interprétation que le contrat DS-09 ne porte pas — la même faute que "
        "celle commise sur le champ `ETAT` du CNIG pendant D2."
    )
    add("")
    add(
        "L'écart est donc publié tel quel. Le combler demande la table de correspondance du "
        "producteur, pas une décision de notre part, et c'est une entrée pour "
        "[E1](../backlog/E1-profiling-distributions.md)."
    )
    add("")
    add("## Ce qui n'est pas encore profilable, et pourquoi")
    add("")
    add("| Famille | État | Obstacle |")
    add("|---|---|---|")
    add(
        "| `MKT-001..005`, `MKT-101..105` | non matérialisées | calculées au moment du score, "
        "à partir des comparables ; les segments de marché relèvent de "
        "[E1](../backlog/E1-profiling-distributions.md) |"
    )
    add(
        "| `REN-001..008` | non matérialisées | sujet invalidé — "
        "[BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md). Distributions "
        "d'observations dans [`dpe-matching-35.md`](./dpe-matching-35.md) |"
    )
    add(
        "| `RISK-001..004`, `RISK-101` | non matérialisées | même sujet, et DS-09 `display_only`. "
        "Distributions dans [`georisques-coverage-35.md`](./georisques-coverage-35.md) |"
    )
    add(
        "| `BLD-001..003` | non matérialisées | "
        "[BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md) |"
    )
    add("")
    add(
        "Les distributions d'observations existent pour toutes ces familles, dans les rapports "
        "par source. Ce qui manque est leur matérialisation par unité, et deux obstacles la "
        "tiennent : le sujet des features de bâtiment, et le verdict de DS-08."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the market data quality report")
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
        connection.execute("SET LOCAL statement_timeout = '1800s'")
        data: dict[str, Any] = {
            "verdicts": verdicts(connection),
            "volumes": volumes(connection, department),
            "completeness": feature_completeness(connection),
            "distributions": feature_distributions(connection),
            "worst": worst_communes(connection, department),
            "vocabulary": vocabulary_gap(connection),
        }

    output = arguments.output or (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "data"
        / f"market-data-quality-{department}.md"
    )
    output.write_text(render(data, department, date.today().isoformat()), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
