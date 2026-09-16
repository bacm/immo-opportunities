#!/usr/bin/env python3
"""Régénère le rapport d'appariement DPE et les distributions REN — D4 (DS-07), D9 (DS-13).

Le rapport ne se saisit pas à la main : il se recalcule depuis `observation.energy_assessment`,
`meta.attribute_quarantine`, `meta.dataset_coverage_metric` et `meta.import_run`, qui sont la
source de vérité.

Trois distinctions gouvernent la lecture des chiffres.

**« Écarté » n'est pas « non apparié ».** Le premier est un enregistrement qui n'est pas un
diagnostic exploitable — modèle inconnu, non déposé, postérieur au snapshot. Le second est un
diagnostic parfaitement valide dont aucun identifiant déclaré ne se résout chez nous. Les
additionner effacerait la différence, et le rapport ne les additionne jamais.

**« Apparié à l'adresse » n'est pas « apparié ».** Le taux publié comme *taux d'appariement* est
celui du **bâtiment**, parce que c'est le sujet des features REN. Un diagnostic rattaché à la
seule adresse est utilisable à condition d'être seul à cette adresse ; à plusieurs il devient
`ambiguous_match` au calcul, et le rapport compte cette population séparément.

**Un taux modeste est un résultat, pas un défaut.** L'adresse d'un diagnostic est saisie à la
main. Rien ici ne relâche une règle pour faire monter un chiffre.
"""

import argparse
import json
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings

SOURCE = "DS-07"
# DS-13, les logements neufs, a son propre fichier : il n'entre dans aucune mesure (ADR-021).
OUTPUT_NAMES = {
    "DS-07": "dpe-matching-{department}.md",
    "DS-13": "dpe-neuf-matching-{department}.md",
}


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


def release(
    connection: psycopg.Connection[Any], department: str, source: str = SOURCE
) -> dict[str, Any]:
    rows = fetch(
        connection,
        """
        SELECT release.id, release.release_key, release.source_published_on,
               release.acceptance_status, run.id AS import_run_id, run.source_row_count,
               run.normalized_row_count, run.quarantined_row_count,
               run.deduplicated_row_count, run.runner_metadata
          FROM meta.dataset_release AS release
          LEFT JOIN meta.import_run AS run ON run.release_id = release.id
                                          AND run.territory_code = %(department)s
                                          AND run.status = 'succeeded'
         WHERE release.data_source_id = %(source)s
         ORDER BY release.release_key DESC, run.completed_at DESC NULLS LAST
         LIMIT 1
        """,
        source=source,
        department=department,
    )
    if not rows:
        raise SystemExit(f"Aucune release {source} : rien à rapporter.")
    return rows[0]


def rejections(connection: psycopg.Connection[Any], release_id: str) -> list[dict[str, Any]]:
    """Les enregistrements écartés avant tout appariement, par motif."""
    return fetch(
        connection,
        """
        SELECT reason_code, count(*) AS records
          FROM meta.attribute_quarantine
         WHERE release_id = %(release_id)s AND entity_type = 'energy_assessment'
           AND attribute = 'record'
         GROUP BY reason_code ORDER BY 2 DESC
        """,
        release_id=release_id,
    )


def matching(connection: psycopg.Connection[Any], release_id: str) -> dict[str, Any]:
    totals = fetch(
        connection,
        """
        SELECT coalesce(sum(record_count), 0) AS eligible,
               coalesce(sum((details->>'matched_building')::bigint), 0) AS building,
               coalesce(sum((details->>'matched_address_only')::bigint), 0) AS address_only,
               coalesce(sum((details->>'unmatched')::bigint), 0) AS unmatched,
               coalesce(sum((details->>'confidence_quarantined')::bigint), 0) AS contradicted,
               count(*) AS communes
          FROM meta.dataset_coverage_metric WHERE release_id = %(release_id)s
        """,
        release_id=release_id,
    )[0]
    ambiguous = fetch(
        connection,
        """
        -- Plusieurs diagnostics a la meme adresse et aucun rattachement batiment : le calcul
        -- sortira `ambiguous_match`, et c'est la population que D6 doit revoir a la main.
        SELECT count(*) AS assessments, count(DISTINCT address_id) AS addresses
          FROM observation.energy_assessment
         WHERE release_id = %(release_id)s AND building_id IS NULL AND address_id IN (
               SELECT address_id FROM observation.energy_assessment
                WHERE release_id = %(release_id)s AND building_id IS NULL
                  AND address_id IS NOT NULL
                GROUP BY address_id HAVING count(*) > 1
         )
        """,
        release_id=release_id,
    )[0]
    return {**totals, "ambiguous": ambiguous}


def commune_extremes(
    connection: psycopg.Connection[Any], release_id: str, *, ascending: bool
) -> list[dict[str, Any]]:
    order = "ASC" if ascending else "DESC"
    return fetch(
        connection,
        f"""
        SELECT metric.commune_code, area.name AS commune_name, metric.record_count,
               metric.matched_record_count, metric.coverage_ratio
          FROM meta.dataset_coverage_metric AS metric
          LEFT JOIN reference.area AS area ON area.code = metric.commune_code
                                          AND area.area_type = 'commune'
         WHERE metric.release_id = %(release_id)s AND metric.record_count >= 100
         ORDER BY metric.coverage_ratio {order}, metric.record_count DESC
         LIMIT 10
        """,
        release_id=release_id,
    )


def distributions(connection: psycopg.Connection[Any], release_id: str) -> dict[str, Any]:
    """Ce dont E1 a besoin : les distributions réelles, par classe et par quartile."""
    stored = fetch(
        connection,
        "SELECT count(*) AS stored FROM observation.energy_assessment "
        "WHERE release_id = %(release_id)s",
        release_id=release_id,
    )[0]["stored"]
    labels = fetch(
        connection,
        """
        SELECT coalesce(energy_label, 'absente') AS label, count(*) AS assessments
          FROM observation.energy_assessment WHERE release_id = %(release_id)s
         GROUP BY 1 ORDER BY 1
        """,
        release_id=release_id,
    )
    quartiles = fetch(
        connection,
        """
        SELECT count(*) FILTER (WHERE energy_consumption_kwh_m2_year IS NOT NULL) AS observed,
               percentile_cont(0.25) WITHIN GROUP (
                   ORDER BY energy_consumption_kwh_m2_year
               ) AS q1,
               percentile_cont(0.5) WITHIN GROUP (
                   ORDER BY energy_consumption_kwh_m2_year
               ) AS median,
               percentile_cont(0.75) WITHIN GROUP (
                   ORDER BY energy_consumption_kwh_m2_year
               ) AS q3,
               min(assessment_date) AS oldest, max(assessment_date) AS freshest,
               -- `percentile_cont` ne connait pas les dates : la mediane se prend sur le jour
               -- julien, puis revient en date.
               (date '2000-01-01' + (percentile_cont(0.5) WITHIN GROUP (
                   ORDER BY assessment_date - date '2000-01-01'
               ))::integer) AS median_date
          FROM observation.energy_assessment WHERE release_id = %(release_id)s
        """,
        release_id=release_id,
    )[0]
    confidence = fetch(
        connection,
        """
        SELECT CASE WHEN match_confidence IS NULL THEN 'absente avec motif'
                    WHEN match_confidence = 1 THEN 'identifiant officiel (1,0)'
                    WHEN match_confidence >= 0.8 THEN 'score de géocodage ≥ 0,8'
                    WHEN match_confidence >= 0.5 THEN 'score de géocodage 0,5 à 0,8'
                    ELSE 'score de géocodage < 0,5' END AS bucket,
               count(*) AS assessments
          FROM observation.energy_assessment WHERE release_id = %(release_id)s
         GROUP BY 1 ORDER BY 2 DESC
        """,
        release_id=release_id,
    )
    envelope = fetch(
        connection,
        """
        SELECT key, count(*) AS assessments
          FROM observation.energy_assessment,
               LATERAL jsonb_object_keys(envelope_characteristics) AS key
         WHERE release_id = %(release_id)s
         GROUP BY key ORDER BY 2 DESC
        """,
        release_id=release_id,
    )
    periods = fetch(
        connection,
        """
        SELECT coalesce(properties->>'periode_construction', 'absente') AS period,
               count(*) AS assessments
          FROM observation.energy_assessment WHERE release_id = %(release_id)s
         GROUP BY 1 ORDER BY 1
        """,
        release_id=release_id,
    )
    return {
        "stored": stored,
        "labels": labels,
        "consumption": quartiles,
        "confidence": confidence,
        "envelope": envelope,
        "periods": periods,
    }


def record_contract_checks(
    connection: psycopg.Connection[Any], *, release_id: str, import_run_id: str, department: str
) -> dict[str, str]:
    """Consigner les contrôles que le contrat DS-07 déclare, avec leur mesure.

    Sans eux, le verdict d'acceptation serait un récit : `set_acceptance` lit cette table, et un
    contrôle bloquant en échec y refuse la publication mécaniquement.

    `label_consumption_consistency` ne compare pas l'étiquette à une table de seuils. Le DPE 2021
    classe sur un **double seuil** énergie et GES, et reconstituer cette table ici serait inventer
    une interprétation que le contrat ne porte pas. Le contrôle vérifie ce qui se mesure sans
    seuil : que la consommation médiane **croît** de A vers G. Si les deux champs se
    contredisaient, elle ne croîtrait pas.
    """
    medians = connection.execute(
        """
        SELECT energy_label,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY energy_consumption_kwh_m2_year)
          FROM observation.energy_assessment
         WHERE release_id = %(release_id)s AND energy_label IS NOT NULL
           AND energy_consumption_kwh_m2_year IS NOT NULL
         GROUP BY 1 ORDER BY 1
        """,
        {"release_id": release_id},
    ).fetchall()
    ordered = [float(value) for _, value in medians if value is not None]
    monotonic = all(left <= right for left, right in pairwise(ordered))

    totals = connection.execute(
        """
        SELECT (SELECT coalesce(sum(record_count), 0)
                  FROM meta.dataset_coverage_metric WHERE release_id = %(release_id)s),
               count(*) FILTER (WHERE building_id IS NOT NULL),
               count(*) FILTER (WHERE NOT is_deposited OR is_simulated)
          FROM observation.energy_assessment WHERE release_id = %(release_id)s
        """,
        {"release_id": release_id},
    ).fetchone()
    assert totals is not None
    # `eligible` compte aussi les diagnostics qu'aucun identifiant ne rattache : les exclure du
    # denominateur ferait passer un taux d'appariement pour meilleur qu'il n'est.
    eligible, matched, not_deposited = (int(value) for value in totals)

    shared = connection.execute(
        """
        SELECT count(*) FROM (
            SELECT address_id FROM observation.energy_assessment
             WHERE release_id = %(release_id)s AND building_id IS NULL AND address_id IS NOT NULL
             GROUP BY address_id HAVING count(*) > 1
        ) AS crowded
        """,
        {"release_id": release_id},
    ).fetchone()
    assert shared is not None

    checks = (
        (
            "deposited_only",
            "row",
            department,
            not_deposited == 0,
            True,
            float(not_deposited),
            {"eligible": eligible, "not_deposited_or_simulated": not_deposited},
        ),
        (
            "label_consumption_consistency",
            "row",
            department,
            monotonic,
            False,
            None,
            {"median_by_label": [float(value) for _, value in medians if value is not None]},
        ),
        (
            "building_match_rate",
            "commune",
            department,
            True,
            False,
            round(matched / eligible, 6) if eligible else None,
            {"matched_building": matched, "eligible": eligible},
        ),
        (
            "multiple_dpe_resolution",
            "address",
            department,
            True,
            True,
            float(shared[0]),
            {
                "addresses_with_several_assessments": int(shared[0]),
                "resolution": (
                    "aucune sélection arbitraire : le calcul sort `ambiguous_match` tant "
                    "qu'aucun bâtiment ne tranche"
                ),
            },
        ),
    )
    connection.cursor().executemany(
        """
        INSERT INTO meta.data_quality_check (
            release_id, import_run_id, check_code, check_version, scope_type, scope_code,
            layer, status, severity, blocks_publication, observed_value, details
        ) VALUES (%s, %s, %s, '1', %s, %s, 'assessments',
                  CASE WHEN %s::boolean THEN 'passed' ELSE 'failed' END,
                  CASE WHEN %s::boolean THEN 'info' ELSE 'error' END,
                  %s, %s, %s::jsonb)
        ON CONFLICT ON CONSTRAINT data_quality_result_identity DO UPDATE SET
            status = EXCLUDED.status, severity = EXCLUDED.severity,
            observed_value = EXCLUDED.observed_value, details = EXCLUDED.details,
            checked_at = now()
        """,
        [
            (
                release_id,
                import_run_id,
                code,
                scope,
                code_scope,
                passed,
                passed,
                blocking,
                observed,
                json.dumps(details, ensure_ascii=False),
            )
            for code, scope, code_scope, passed, blocking, observed, details in checks
        ],
    )
    connection.commit()
    return {code: ("passed" if passed else "failed") for code, _, _, passed, _, _, _ in checks}


def thousands(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) or (hasattr(value, "is_integer") and not float(value).is_integer()):
        return f"{float(value):,.1f}".replace(",", " ").replace(".", ",")
    return f"{int(value):,}".replace(",", " ")


def percent(part: Any, whole: Any) -> str:
    if not whole:
        return "—"
    return f"{100 * float(part) / float(whole):.2f} %".replace(".", ",")


def render(data: dict[str, Any], department: str, generated_on: str, source: str = SOURCE) -> str:
    head = data["release"]
    match = data["matching"]
    dist = data["distributions"]
    eligible = int(match["eligible"])
    # Les distributions decrivent les diagnostics **stockes**. Les rapporter aux eligibles
    # melangerait deux populations et ferait passer un champ present partout pour lacunaire.
    stored = int(dist["stored"])
    lines: list[str] = []
    add = lines.append

    title = "DPE logements neufs" if source == "DS-13" else "DPE"
    add(f"# {source} {title} — appariement et distributions sur le {department}")
    add("")
    add(f"**Généré le :** {generated_on} · **Release :** `{head['id']}`")
    add(f"· **Publiée par la source le :** {head['source_published_on']}")
    add(f"· **Run d'import :** `{head['import_run_id']}`")
    add(f"· **Verdict :** `{head['acceptance_status']}`")
    add("")
    command = "make dpe-report" + ("" if source == SOURCE else f" SOURCE={source}")
    add(f"Ce fichier est **régénéré** par `{command}`. Ne pas l'éditer à la main.")
    if source == "DS-13":
        add("")
        add(
            "Diagnostics établis à la réception d'une construction. Affichés dans l'outil de "
            "vérification, **exclus de toute mesure** du baromètre et du radar : un DPE neuf "
            "accompagne une livraison, il n'annonce pas une vente (ADR-021)."
        )
    add("")
    add("## Volumétrie")
    add("")
    add("| Étape | Enregistrements |")
    add("|---|---|")
    add(f"| Lignes de l'extrait | {thousands(head['source_row_count'])} |")
    add(f"| Diagnostics éligibles | {thousands(eligible)} |")
    add(f"| Rattachés à un bâtiment | {thousands(match['building'])} |")
    add(f"| Rattachés à la seule adresse | {thousands(match['address_only'])} |")
    add(f"| Non rattachés | {thousands(match['unmatched'])} |")
    add("")
    add("### Enregistrements écartés avant appariement")
    add("")
    if data["rejections"]:
        add("| Motif | Enregistrements |")
        add("|---|---|")
        for entry in data["rejections"]:
            add(f"| `{entry['reason_code']}` | {thousands(entry['records'])} |")
    else:
        add("Aucun. Toutes les lignes de l'extrait sont des diagnostics exploitables.")
    add("")
    add(
        "Le jeu accessible est la vue virtuelle de l'ADEME, filtrée en amont sur "
        "`dpe_desactive = 0` : **un diagnostic annulé n'y apparaît jamais**. La règle qui "
        "l'écarterait existe et est testée, mais c'est le producteur qui garantit l'exclusion, "
        "pas notre code."
    )
    add("")
    add("## Appariement")
    add("")
    add("| Classe | Diagnostics | Part |")
    add("|---|---|---|")
    add(
        f"| Bâtiment, par `id_rnb` | {thousands(match['building'])} | "
        f"{percent(match['building'], eligible)} |"
    )
    add(
        f"| Adresse seule, par `identifiant_ban` | {thousands(match['address_only'])} | "
        f"{percent(match['address_only'], eligible)} |"
    )
    add(
        f"| Non rattaché | {thousands(match['unmatched'])} | "
        f"{percent(match['unmatched'], eligible)} |"
    )
    add("")
    add(
        f"**Taux d'appariement au bâtiment : {percent(match['building'], eligible)}** des "
        f"diagnostics éligibles, répartis sur {thousands(match['communes'])} communes déclarées "
        "par la source."
    )
    add("")
    add(
        f"Parmi les diagnostics rattachés à la seule adresse, "
        f"**{thousands(match['ambiguous']['assessments'])}** partagent leur adresse avec un "
        f"autre diagnostic sans rattachement bâtiment, sur "
        f"**{thousands(match['ambiguous']['addresses'])}** adresses. "
        + (
            "La cardinalité est réelle — un programme neuf dépose un DPE par logement — et aucune "
            "feature ne lit ces diagnostics (ADR-021)."
            if source == "DS-13"
            else "Le calcul les rendra `ambiguous_match` : la cardinalité est réelle — un immeuble "
            "a plusieurs DPE légitimes — et c'est la population que D6 doit revoir à la main."
        )
    )
    add("")
    add("### La source se contredit sur son propre géocodage")
    add("")
    add(
        f"Parmi les diagnostics rattachés à la seule adresse, "
        f"**{thousands(match['contradicted'])}** portent un `identifiant_ban` qui se "
        "résout dans notre référentiel alors que `statut_geocodage` annonce « aucune "
        "correspondance trouvée ». L'adresse est conservée — la jointure d'identifiant, elle, "
        "est vérifiable — et c'est la **confiance** qui devient absente avec le motif "
        "`contradictory_geocoding_status`. Quarantaine par attribut de BUG-03 : "
        "l'enregistrement reste, l'attribut invérifiable s'en va motivé. Un diagnostic rattaché "
        "au bâtiment peut porter le même statut : sa confiance vient alors de l'identifiant RNB, "
        "pas du géocodage, et il n'est pas compté ici."
    )
    add("")
    add("### Communes aux taux extrêmes")
    add("")
    for title, key in (("Les plus faibles", "worst"), ("Les plus élevées", "best")):
        add(f"**{title}** (communes d'au moins 100 diagnostics)")
        add("")
        add("| Commune | Diagnostics | Rattachés bâtiment | Taux |")
        add("|---|---|---|---|")
        for entry in data[key]:
            ratio = entry["coverage_ratio"]
            add(
                f"| {entry['commune_name'] or entry['commune_code']} "
                f"({entry['commune_code']}) | {thousands(entry['record_count'])} | "
                f"{thousands(entry['matched_record_count'])} | "
                f"{percent(entry['matched_record_count'], entry['record_count'])} |"
            )
            assert ratio is not None
        add("")
    add("## Distributions descriptives" if source == "DS-13" else "## Distributions pour E1")
    add("")
    add(
        f"Sur les **{thousands(stored)} diagnostics conservés** — les "
        f"{thousands(match['unmatched'])} sans sujet ne sont dans aucune table ci-dessous, "
        "seulement en quarantaine avec leur motif."
    )
    add("")
    add("### `REN-004` — étiquette énergétique observée")
    add("")
    add("| Classe | Diagnostics | Part |")
    add("|---|---|---|")
    for entry in dist["labels"]:
        add(
            f"| {entry['label']} | {thousands(entry['assessments'])} | "
            f"{percent(entry['assessments'], stored)} |"
        )
    add("")
    consumption = dist["consumption"]
    add("### `REN-005` — consommation en énergie primaire, kWh/m²/an")
    add("")
    add("| Mesure | Valeur |")
    add("|---|---|")
    add(f"| Observations | {thousands(consumption['observed'])} |")
    add(f"| Q1 | {thousands(consumption['q1'])} |")
    add(f"| Médiane | {thousands(consumption['median'])} |")
    add(f"| Q3 | {thousands(consumption['q3'])} |")
    add("")
    add("### `REN-006` — fraîcheur des diagnostics")
    add("")
    add(
        f"Date d'établissement du diagnostic : du {consumption['oldest']} au "
        f"{consumption['freshest']}, médiane au "
        f"{str(consumption['median_date'])[:10]}. Un diagnostic ancien reste un diagnostic "
        "valide : sa fraîcheur alimente la confiance, elle n'invalide pas la valeur."
    )
    add("")
    add("### `REN-007` — caractéristiques déclarées présentes")
    add("")
    add("| Caractéristique | Diagnostics | Part |")
    add("|---|---|---|")
    for entry in dist["envelope"]:
        add(
            f"| `{entry['key']}` | {thousands(entry['assessments'])} | "
            f"{percent(entry['assessments'], stored)} |"
        )
    add("")
    add("### `REN-008` — confiance d'appariement")
    add("")
    add("| Provenance de la confiance | Diagnostics |")
    add("|---|---|")
    for entry in dist["confidence"]:
        add(f"| {entry['bucket']} | {thousands(entry['assessments'])} |")
    add("")
    add(
        "La valeur 1,0 n'est pas un seuil choisi : c'est la convention que `meta.entity_match` "
        "porte déjà pour `rnb-ban-identifier`, un identifiant officiel déclaré par le "
        "producteur. Les autres valeurs sont le `score_ban` de la source, repris tel quel."
    )
    add("")
    add("### `REN-001` — période de construction déclarée au diagnostic")
    add("")
    add("| Période | Diagnostics |")
    add("|---|---|")
    for entry in dist["periods"]:
        add(f"| {entry['period']} | {thousands(entry['assessments'])} |")
    add("")
    add(f"## Contrôles du contrat {source}")
    add("")
    add("| Contrôle | Résultat | Bloque la publication |")
    add("|---|---|---|")
    for code, status in sorted(data["checks"].items()):
        blocking = "oui" if code in {"deposited_only", "multiple_dpe_resolution"} else "non"
        add(f"| `{code}` | {status} | {blocking} |")
    add("")
    add(
        "`label_consumption_consistency` ne compare pas l'étiquette à une table de seuils : le "
        "DPE 2021 classe sur un **double seuil** énergie et GES, et reconstituer cette table "
        "ici serait inventer une interprétation que le contrat ne porte pas. Le contrôle vérifie "
        "ce qui se mesure sans seuil — que la consommation médiane croît de A vers G."
    )
    add("")
    add("## Ce que ce rapport ne dit pas")
    add("")
    add(
        "- **`REN-001..008` ne portent aucune valeur.** Elles sont écrites sur le bâtiment "
        "physique, absentes avec le motif `source_not_accepted` : les DPE sont `display_only` "
        "([BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md), "
        "[`building-features-35.md`](./building-features-35.md)). Les distributions ci-dessus "
        "sont ce dont E1 a besoin."
    )
    add(
        "- **Aucune estimation d'état du bâti.** Une classe F ou G est l'observation d'un "
        "diagnostic, pas une preuve de dégradation."
    )
    add(
        "- **Aucun signal tiré d'une absence.** Un bâtiment sans diagnostic n'est pas suspect : "
        "il est sans diagnostic. L'absence ne pèse sur aucune composante de score, elle ne "
        "réduit que la confiance — vérifié par test."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate a DPE matching report")
    parser.add_argument("--source", choices=sorted(OUTPUT_NAMES), default=SOURCE)
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
        source = cast(str, arguments.source)
        head = release(connection, department, source)
        release_id = cast(str, head["id"])
        data: dict[str, Any] = {
            "release": head,
            "rejections": rejections(connection, release_id),
            "matching": matching(connection, release_id),
            "worst": commune_extremes(connection, release_id, ascending=True),
            "best": commune_extremes(connection, release_id, ascending=False),
            "distributions": distributions(connection, release_id),
        }
        # Les controles du contrat sont une **mesure**, pas une etape d'import : les recalculer
        # ici les rend rejouables sans reimporter 458 Mo, et `set_acceptance` lit leur resultat.
        connection.execute("SET ROLE pipeline_rw")
        data["checks"] = record_contract_checks(
            connection,
            release_id=release_id,
            import_run_id=cast(str, head["import_run_id"]),
            department=department,
        )

    if arguments.json:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0

    output = arguments.output or (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "data"
        / OUTPUT_NAMES[source].format(department=department)
    )
    output.write_text(render(data, department, date.today().isoformat(), source), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
