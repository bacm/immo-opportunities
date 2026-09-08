"""Régénère le rapport de distribution des appariements spatiaux — B3.

Le rapport ne se saisit pas à la main : il se recalcule depuis `meta.entity_match_metric`,
`meta.entity_match` et `meta.entity_observation_link`, qui sont la source de vérité.

Deux distinctions gouvernent la lecture des chiffres produits.

**« Non apparié » n'est pas « rejeté ».** Le premier est une absence de décision, le second une
décision motivée. Les additionner effacerait la différence, et le rapport ne les additionne
jamais.

**« Non couvert » n'est pas « taux nul ».** Une commune où la source n'a aucun enregistrement
donne quatre classes à zéro ; une commune où la source est présente mais où rien n'apparie donne
un `unmatched_count` strictement positif. Les quatre classes à zéro identifient donc exactement
l'absence de couverture, sans qu'aucune colonne supplémentaire soit nécessaire.
"""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings

# Libellés des relations, dans l'ordre où le ticket les attend.
RELATIONS: tuple[tuple[str, str], ...] = (
    ("building_parcel", "Bâtiment ↔ Parcelle"),
    ("address_parcel", "Adresse ↔ Parcelle"),
    ("address_building", "Adresse ↔ Bâtiment"),
    ("bdtopo_building_rnb", "Bâtiment BD TOPO ↔ Bâtiment RNB"),
    ("bdnb_group_rnb", "Groupe BDNB ↔ Bâtiment RNB"),
)


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return [dict(row) for row in cursor.execute(sql, parameters).fetchall()]


def relation_totals(connection: psycopg.Connection[Any], department: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT metric.relation_type, metric.release_id, metric.algorithm_code,
               count(*) AS communes,
               sum(metric.certain_count) AS certain,
               sum(metric.ambiguous_count) AS ambiguous,
               sum(metric.rejected_count) AS rejected,
               sum(metric.unmatched_count) AS unmatched,
               count(*) FILTER (
                   WHERE metric.certain_count + metric.ambiguous_count
                       + metric.rejected_count + metric.unmatched_count = 0
               ) AS communes_not_covered
          FROM meta.entity_match_metric AS metric
          JOIN reference.area AS commune
            ON commune.area_type = 'commune'
           AND commune.code = metric.commune_code
           AND commune.department_code = %(department)s
         GROUP BY metric.relation_type, metric.release_id, metric.algorithm_code
         ORDER BY metric.relation_type
        """,
        department=department,
    )


def method_volumes(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    """Volume par méthode, en réunissant les deux tables de décision.

    `meta.entity_match` porte les relations entre deux entités canoniques ;
    `meta.entity_observation_link` porte le rattachement d'une observation à une entité, que la
    première ne peut pas exprimer — sa contrainte impose deux types différents.
    """
    return fetch(
        connection,
        """
        SELECT algorithm_code, method, decision, count(*) AS volume,
               round(min(confidence), 5) AS confidence_min,
               round(max(confidence), 5) AS confidence_max
          FROM (
              SELECT algorithm_code, method, decision, confidence FROM meta.entity_match
              UNION ALL
              SELECT algorithm_code, method, decision, confidence
                FROM meta.entity_observation_link
          ) AS decisions
         GROUP BY algorithm_code, method, decision
         ORDER BY algorithm_code, method, decision
        """,
    )


# Au-dela de ce nombre de valeurs distinctes, une confiance n'est plus une etiquette posee par
# une regle mais une grandeur continue : la detailler valeur par valeur produirait des centaines
# de lignes illisibles, et c'est en tranches qu'elle se lit.
DISCRETE_CONFIDENCE_LIMIT = 12


def confidence_distribution(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    """Distribution des confiances, et non leur seule moyenne.

    Deux natures coexistent. `bdtopo-rnb-link` ou `bdnb-group-rnb-link` posent une confiance
    **discrete**, choisie par une regle : la detailler valeur par valeur est exactement ce
    qu'il faut lire. `rnb-plot-relation` reporte un taux de recouvrement **continu** : en
    detailler chaque valeur donnait plusieurs centaines de lignes sans rien apprendre.
    """
    shapes = fetch(
        connection,
        """
        SELECT algorithm_code, count(DISTINCT confidence) AS distinct_values
          FROM (
              SELECT algorithm_code, confidence FROM meta.entity_match
              UNION ALL
              SELECT algorithm_code, confidence FROM meta.entity_observation_link
          ) AS decisions
         GROUP BY algorithm_code ORDER BY algorithm_code
        """,
    )
    discrete = {
        str(row["algorithm_code"])
        for row in shapes
        if int(row["distinct_values"]) <= DISCRETE_CONFIDENCE_LIMIT
    }
    exact = fetch(
        connection,
        """
        SELECT algorithm_code, confidence, decision, count(*) AS volume
          FROM (
              SELECT algorithm_code, confidence, decision FROM meta.entity_match
              UNION ALL
              SELECT algorithm_code, confidence, decision FROM meta.entity_observation_link
          ) AS decisions
         WHERE algorithm_code = ANY(%(discrete)s)
         GROUP BY algorithm_code, confidence, decision
         ORDER BY algorithm_code, confidence DESC
        """,
        discrete=sorted(discrete),
    )
    buckets = fetch(
        connection,
        """
        SELECT algorithm_code, decision,
               (width_bucket(confidence, 0, 1, 10) - 1) * 0.1 AS lower_bound,
               count(*) AS volume,
               round(min(confidence), 5) AS observed_min,
               round(max(confidence), 5) AS observed_max
          FROM (
              SELECT algorithm_code, confidence, decision FROM meta.entity_match
              UNION ALL
              SELECT algorithm_code, confidence, decision FROM meta.entity_observation_link
          ) AS decisions
         WHERE NOT (algorithm_code = ANY(%(discrete)s))
         GROUP BY algorithm_code, decision, width_bucket(confidence, 0, 1, 10)
         ORDER BY algorithm_code, lower_bound DESC
        """,
        discrete=sorted(discrete),
    )
    return {"shapes": shapes, "exact": exact, "buckets": buckets}


def cardinality(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    """La cardinalité réelle, qu'un ratio moyen masquerait."""
    return fetch(
        connection,
        """
        SELECT 'building_parcel' AS relation_type,
               max(parcels) AS maximum, round(avg(parcels), 3) AS mean,
               count(*) FILTER (WHERE parcels > 1) AS above_one
          FROM (
              SELECT building_id, count(*) AS parcels
                FROM reference.building_parcel GROUP BY building_id
          ) AS per_building
        UNION ALL
        SELECT 'bdnb_group_rnb',
               max(buildings), round(avg(buildings), 3),
               count(*) FILTER (WHERE buildings > 1)
          FROM (
              SELECT link.observation_id, count(*) AS buildings
                FROM meta.entity_observation_link AS link
               WHERE link.algorithm_code = 'bdnb-group-rnb-link'
               GROUP BY link.observation_id
          ) AS per_group
        UNION ALL
        SELECT 'bdtopo_building_rnb',
               max(buildings), round(avg(buildings), 3),
               count(*) FILTER (WHERE buildings > 1)
          FROM (
              SELECT link.observation_id, count(*) AS buildings
                FROM meta.entity_observation_link AS link
               WHERE link.algorithm_code = 'bdtopo-rnb-link'
               GROUP BY link.observation_id
          ) AS per_observation
        """,
    )


def extreme_communes(
    connection: psycopg.Connection[Any], relation_type: str, department: str
) -> list[dict[str, Any]]:
    """Les communes extrêmes, avec leur volume : un taux sans volume ne se publie pas."""
    return fetch(
        connection,
        """
        WITH rated AS (
            SELECT metric.commune_code, commune.name,
                   metric.certain_count, metric.ambiguous_count,
                   metric.rejected_count, metric.unmatched_count,
                   metric.certain_count + metric.ambiguous_count
                     + metric.rejected_count + metric.unmatched_count AS total
              FROM meta.entity_match_metric AS metric
              JOIN reference.area AS commune
                ON commune.area_type = 'commune'
               AND commune.code = metric.commune_code
               AND commune.department_code = %(department)s
             WHERE metric.relation_type = %(relation_type)s
        )
        SELECT commune_code, name, total, certain_count, ambiguous_count,
               rejected_count, unmatched_count,
               round(certain_count::numeric / total, 4) AS certain_rate
          FROM rated WHERE total >= 500
         ORDER BY certain_count::numeric / total ASC, total DESC
         LIMIT 5
        """,
        relation_type=relation_type,
        department=department,
    )


def largest_communes(
    connection: psycopg.Connection[Any], relation_type: str, department: str
) -> list[dict[str, Any]]:
    return fetch(
        connection,
        """
        SELECT metric.commune_code, commune.name,
               metric.certain_count + metric.ambiguous_count
                 + metric.rejected_count + metric.unmatched_count AS total,
               metric.certain_count, metric.ambiguous_count,
               metric.rejected_count, metric.unmatched_count,
               round(metric.certain_count::numeric / nullif(
                   metric.certain_count + metric.ambiguous_count
                     + metric.rejected_count + metric.unmatched_count, 0), 4) AS certain_rate
          FROM meta.entity_match_metric AS metric
          JOIN reference.area AS commune
            ON commune.area_type = 'commune'
           AND commune.code = metric.commune_code
           AND commune.department_code = %(department)s
         WHERE metric.relation_type = %(relation_type)s
         ORDER BY total DESC LIMIT 5
        """,
        relation_type=relation_type,
        department=department,
    )


def unmatched_reasons(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    """Les motifs de rejet, qui sont des décisions — à ne pas confondre avec une absence."""
    return fetch(
        connection,
        """
        SELECT algorithm_code, decision, left(rationale, 90) AS rationale, count(*) AS volume
          FROM (
              SELECT algorithm_code, decision, rationale FROM meta.entity_match
               WHERE decision IN ('rejected', 'ambiguous')
              UNION ALL
              SELECT algorithm_code, decision, rationale FROM meta.entity_observation_link
               WHERE decision IN ('rejected', 'ambiguous')
          ) AS decisions
         GROUP BY algorithm_code, decision, left(rationale, 90)
         ORDER BY volume DESC LIMIT 12
        """,
    )


def thousands(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return str(value)


def render(data: dict[str, Any], department: str, generated_on: str) -> str:
    lines: list[str] = [
        "# Distribution des appariements spatiaux — département 35",
        "",
        f"**Date :** {generated_on}",
        "**Portée :** les cinq relations du référentiel spatial de v0.3, sur les "
        f"{thousands(data['commune_count'])} communes du {department}.",
        "",
        "Ce document est **généré**. Il ne se corrige pas à la main :",
        "",
        "```bash",
        f"make matching-report DEPARTMENT={department}",
        "```",
        "",
        "## Deux distinctions qui gouvernent la lecture",
        "",
        "**« Non apparié » n'est pas « rejeté ».** Le premier est une absence de décision, le",
        "second une décision motivée. Ils ne sont jamais additionnés.",
        "",
        "**« Non couvert » n'est pas « taux nul ».** Une commune sans aucun enregistrement source",
        "donne quatre classes à zéro ; une commune où la source est présente mais où rien",
        "n'apparie donne un nombre de non appariés strictement positif. Les quatre classes à zéro",
        "identifient donc exactement l'absence de couverture.",
        "",
        "## Distribution en quatre classes, jamais trois",
        "",
        "| Relation | certain | ambigu | rejeté | non apparié | total | communes non couvertes |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    totals = {row["relation_type"]: row for row in data["relations"]}
    for relation_type, label in RELATIONS:
        row = totals.get(relation_type)
        if row is None:
            lines.append(f"| {label} | — | — | — | — | — | relation absente |")
            continue
        total = (
            int(row["certain"])
            + int(row["ambiguous"])
            + int(row["rejected"])
            + int(row["unmatched"])
        )
        lines.append(
            f"| {label} | {thousands(int(row['certain']))} "
            f"| {thousands(int(row['ambiguous']))} | {thousands(int(row['rejected']))} "
            f"| {thousands(int(row['unmatched']))} | {thousands(total)} "
            f"| {thousands(int(row['communes_not_covered']))} |"
        )
    lines += [
        "",
        "Releases et algorithmes derrière ces chiffres :",
        "",
        "| Relation | Release | Algorithme | Communes mesurées |",
        "|---|---|---|---:|",
    ]
    for relation_type, label in RELATIONS:
        row = totals.get(relation_type)
        if row is not None:
            lines.append(
                f"| {label} | `{row['release_id']}` | `{row['algorithm_code']}` "
                f"| {thousands(int(row['communes']))} |"
            )

    lines += [
        "",
        "## Volume par méthode d'appariement",
        "",
        "L'ordre de préférence de v0.3 est : identifiant officiel, relation source explicite,",
        "intersection spatiale, proximité, adresse normalisée, cohérence temporelle.",
        "",
        "| Algorithme | Méthode | Décision | Volume | Confiance min | max |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in data["methods"]:
        lines.append(
            f"| `{row['algorithm_code']}` | `{row['method']}` | {row['decision']} "
            f"| {thousands(int(row['volume']))} | {row['confidence_min']} "
            f"| {row['confidence_max']} |"
        )

    confidences = data["confidences"]
    lines += [
        "",
        "## Distribution des confiances",
        "",
        "Les valeurs, non leur moyenne. Deux natures coexistent et se lisent différemment : une",
        "confiance posée par une règle est une étiquette, qu'il faut détailler ; un taux de",
        "recouvrement est une grandeur continue, qui se lit en tranches.",
        "",
        "| Algorithme | Valeurs distinctes | Nature |",
        "|---|---:|---|",
    ]
    for row in confidences["shapes"]:
        distinct = int(row["distinct_values"])
        nature = "discrète" if distinct <= DISCRETE_CONFIDENCE_LIMIT else "continue"
        lines.append(f"| `{row['algorithm_code']}` | {thousands(distinct)} | {nature} |")

    if confidences["exact"]:
        lines += [
            "",
            "### Confiances discrètes, valeur par valeur",
            "",
            "| Algorithme | Confiance | Décision | Volume |",
            "|---|---:|---|---:|",
        ]
        for row in confidences["exact"]:
            lines.append(
                f"| `{row['algorithm_code']}` | {row['confidence']} | {row['decision']} "
                f"| {thousands(int(row['volume']))} |"
            )
    if confidences["buckets"]:
        lines += [
            "",
            "### Confiances continues, par tranche de 0,1",
            "",
            "| Algorithme | Tranche | Décision | Volume | Min observé | Max observé |",
            "|---|---|---|---:|---:|---:|",
        ]
        for row in confidences["buckets"]:
            lower = float(row["lower_bound"])
            lines.append(
                f"| `{row['algorithm_code']}` | [{lower:.1f} a {lower + 0.1:.1f}[ "
                f"| {row['decision']} | {thousands(int(row['volume']))} "
                f"| {row['observed_min']} | {row['observed_max']} |"
            )

    lines += [
        "",
        "## Cardinalité réelle",
        "",
        "Un ratio moyen masquerait ce que le modèle porte nativement.",
        "",
        "| Relation | Maximum observé | Moyenne | Cas au-delà de 1 |",
        "|---|---:|---:|---:|",
    ]
    for row in data["cardinality"]:
        lines.append(
            f"| `{row['relation_type']}` | {thousands(int(row['maximum'] or 0))} "
            f"| {row['mean']} | {thousands(int(row['above_one'] or 0))} |"
        )

    lines += [
        "",
        "## Par commune : aucun taux sans son volume",
        "",
        "Un taux élevé sur une commune à faible volume ne vaut pas un taux identique sur Rennes.",
        "Chaque tableau expose donc le volume à côté du taux.",
    ]
    for relation_type, label in RELATIONS:
        if relation_type not in totals:
            continue
        lines += [
            "",
            f"### {label}",
            "",
            "Les cinq communes au plus fort volume :",
            "",
            "| Commune | INSEE | total | certain | ambigu | rejeté | non apparié | taux certain |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in data["largest"][relation_type]:
            lines.append(
                f"| {row['name'] or '—'} | `{row['commune_code']}` "
                f"| {thousands(int(row['total']))} | {thousands(int(row['certain_count']))} "
                f"| {thousands(int(row['ambiguous_count']))} "
                f"| {thousands(int(row['rejected_count']))} "
                f"| {thousands(int(row['unmatched_count']))} | {row['certain_rate']} |"
            )
        worst = data["worst"][relation_type]
        if worst:
            lines += [
                "",
                "Les cinq taux les plus faibles, à volume significatif — au moins 500 unités :",
                "",
                "| Commune | INSEE | total | certain | ambigu | rejeté | non apparié "
                "| taux certain |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
            for row in worst:
                lines.append(
                    f"| {row['name'] or '—'} | `{row['commune_code']}` "
                    f"| {thousands(int(row['total']))} | {thousands(int(row['certain_count']))} "
                    f"| {thousands(int(row['ambiguous_count']))} "
                    f"| {thousands(int(row['rejected_count']))} "
                    f"| {thousands(int(row['unmatched_count']))} | {row['certain_rate']} |"
                )

    lines += [
        "",
        "## Motifs des décisions non certaines",
        "",
        "Un ambigu et un rejeté portent tous deux un motif. Une absence d'appariement n'en porte",
        "aucun, et c'est précisément ce qui les distingue.",
        "",
        "| Algorithme | Décision | Motif | Volume |",
        "|---|---|---|---:|",
    ]
    for row in data["reasons"]:
        rationale = str(row["rationale"]).replace("|", "\\|")
        lines.append(
            f"| `{row['algorithm_code']}` | {row['decision']} | {rationale} "
            f"| {thousands(int(row['volume']))} |"
        )

    lines += [
        "",
        "## Où ces chiffres sont persistés",
        "",
        "`meta.entity_match_metric`, une ligne par release, commune, relation et algorithme.",
        "Ils sont exposés à l'administration sous `GET /api/v1/admin/match-metrics`, réservé au",
        "rôle `organization_admin` — exigence FR-012.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the spatial matching report")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), default="35")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="print the raw figures instead")
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
        commune_count = fetch(
            connection,
            """
            SELECT count(*) AS communes FROM reference.area
             WHERE area_type = 'commune' AND department_code = %(department)s
            """,
            department=department,
        )[0]["communes"]
        data: dict[str, Any] = {
            "commune_count": int(cast(int, commune_count)),
            "relations": relation_totals(connection, department),
            "methods": method_volumes(connection),
            "confidences": confidence_distribution(connection),
            "cardinality": cardinality(connection),
            "reasons": unmatched_reasons(connection),
            "largest": {},
            "worst": {},
        }
        for relation_type, _ in RELATIONS:
            data["largest"][relation_type] = largest_communes(connection, relation_type, department)
            data["worst"][relation_type] = extreme_communes(connection, relation_type, department)

    if arguments.json:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0

    output = arguments.output or (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "data"
        / f"spatial-matching-distribution-{department}.md"
    )
    # La date vient de l'horloge de la base, pas de celle de l'operateur.
    output.write_text(render(data, department, date.today().isoformat()), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
