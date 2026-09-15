#!/usr/bin/env python3
"""Les biens probablement en vente, d'après la fraîcheur du dépôt de DPE — E8f.

Ce script **ne publie rien**, comme celui de E8 : il lit la base et écrit des fichiers.

## Le signal est administratif, pas statistique

Un DPE est obligatoire pour mettre un logement en vente. Son dépôt est un fait daté et public,
explicable parcelle par parcelle. Mesuré sur le 35 dans `docs/data/dpe-signal-vente-35.md` :
**35,65 %** des parcelles dont le premier DPE a été déposé en 2024 mutent dans les douze mois,
contre **3,03 %** de l'ensemble des parcelles bâties — lift 11,8 fois. Le dépôt précède l'acte de
169 jours en médiane, soit environ 80 jours avant le compromis.

## La baseline isole la revendication

Même population résidentielle individuelle, mais **DPE ancien**. Un tri par surface ne dirait rien
de la fraîcheur, qui est tout ce que cette liste revendique.

## La fenêtre se compte depuis la date d'extrait

Jamais depuis l'horloge : la liste se viderait toute seule à mesure que l'extrait vieillit, sans
que rien ne le signale.
"""

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.exploratory import (
    blind,
    cell,
    has_non_residential_nature,
    is_residential,
    locate,
    write_csv,
    zone_type,
)

# Fenêtres arbitraires, déclarées comme telles et publiées dans le rapport.
RANK_SIGNALS: tuple[tuple[str, bool], ...] = (("dpe_deposited_at", True),)


@dataclass(frozen=True)
class Parameters:
    fresh_months: int = 6
    stale_months: int = 24
    zone_type: str = "U"
    max_dwellings_per_building: int = 2
    # Horizon de la chance résiduelle, lu sur la courbe observée. Arbitraire, publié.
    horizon_months: int = 6
    # Portée de la courbe : douze mois, ce que la cohorte de référence couvre par construction.
    curve_months: int = 12


@dataclass(frozen=True)
class CohortRow:
    """Une parcelle de la cohorte de référence : premier DPE de maison, et première vente après."""

    parcel_id: str
    commune_code: str
    deposited_at: date
    energy_label: str | None
    first_mutation: date | None


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


def reference_date(connection: psycopg.Connection[Any]) -> date:
    """Le dépôt le plus récent de l'extrait — la fenêtre part de là, pas d'aujourd'hui."""
    rows = fetch(
        connection,
        "SELECT max(coalesce(deposited_at, assessment_date)) AS extracted FROM"
        " observation.energy_assessment",
    )
    return cast(date, rows[0]["extracted"])


def population(connection: psycopg.Connection[Any], commune: str) -> list[dict[str, Any]]:
    """Parcelles résidentielles individuelles de la commune, avec leur DPE le plus récent."""
    return fetch(
        connection,
        """
        WITH bdtopo AS (
            SELECT unnest(string_to_array(properties->>'identifiants_rnb', '/')) AS rnb_id,
                   properties->>'usage_1' AS use,
                   properties->>'nature' AS nature,
                   nullif(properties->>'nombre_de_logements', '')::int AS dwellings,
                   nullif(left(properties->>'date_d_apparition', 4), '')::int AS built_year
              FROM meta.entity_source_observation
             WHERE source_entity_type = 'bdtopo_building'
               AND properties->>'identifiants_rnb' IS NOT NULL
        ),
        parcel AS (
            SELECT parcel.id, parcel.cadastral_id
              FROM reference.parcel AS parcel
             WHERE parcel.commune_code = %(commune)s
        ),
        use AS (
            SELECT link.parcel_id,
                   string_agg(DISTINCT bdtopo.use, ' · ') AS uses,
                   string_agg(DISTINCT bdtopo.nature, ' · ') AS natures,
                   max(bdtopo.dwellings) AS max_dwellings,
                   min(bdtopo.built_year) AS built_year
              FROM parcel
              JOIN reference.building_parcel AS link
                ON link.parcel_id = parcel.id AND link.relation_status = 'certain'
              JOIN bdtopo ON 'building:rnb:' || bdtopo.rnb_id = link.building_id
             GROUP BY link.parcel_id
        ),
        diagnostic AS (
            SELECT link.parcel_id,
                   max(coalesce(assessment.deposited_at, assessment.assessment_date))
                       AS dpe_deposited_at,
                   (array_agg(assessment.energy_label ORDER BY
                        coalesce(assessment.deposited_at, assessment.assessment_date) DESC))[1]
                       AS energy_label,
                   (array_agg(assessment.properties->>'surface_habitable_logement' ORDER BY
                        coalesce(assessment.deposited_at, assessment.assessment_date) DESC))[1]
                       AS living_area_m2,
                   -- L'adresse déclarée sur le diagnostic : du DPE, pas d'un appariement.
                   (array_agg(assessment.properties->>'adresse_ban' ORDER BY
                        coalesce(assessment.deposited_at, assessment.assessment_date) DESC))[1]
                       AS dpe_address,
                   count(*) AS diagnostics
              FROM parcel
              JOIN reference.building_parcel AS link
                ON link.parcel_id = parcel.id AND link.relation_status = 'certain'
              JOIN observation.energy_assessment AS assessment
                ON assessment.building_id = link.building_id
             GROUP BY link.parcel_id
        ),
        mutation AS (
            SELECT property.parcel_id, max(mutation.mutation_date) AS last_mutation
              FROM parcel
              JOIN observation.transaction_property AS property ON property.parcel_id = parcel.id
              JOIN observation.transaction AS mutation ON mutation.id = property.transaction_id
             GROUP BY property.parcel_id
        ),
        zone AS (
            SELECT member.entity_id AS parcel_id,
                   max(fv.text_value) FILTER (WHERE fv.feature_code = 'URB-001') AS zone,
                   max(fv.numeric_value) FILTER (WHERE fv.feature_code = 'LAND-001')
                       AS parcel_area_m2
              FROM reference.property_unit AS pu
              JOIN reference.property_unit_member AS member
                ON member.property_unit_id = pu.id
               AND member.entity_type = 'parcel'
               AND member.member_role = 'primary'
              JOIN feature.feature_value AS fv ON fv.property_unit_id = pu.id
             WHERE pu.commune_code = %(commune)s
             GROUP BY member.entity_id
        )
        SELECT parcel.id AS property_unit_id, parcel.cadastral_id,
               use.uses, use.natures, use.max_dwellings, use.built_year,
               diagnostic.dpe_deposited_at, diagnostic.energy_label,
               diagnostic.living_area_m2, diagnostic.dpe_address, diagnostic.diagnostics,
               mutation.last_mutation, zone.zone, zone.parcel_area_m2
          FROM parcel
          JOIN use ON use.parcel_id = parcel.id
          JOIN diagnostic ON diagnostic.parcel_id = parcel.id
          LEFT JOIN mutation ON mutation.parcel_id = parcel.id
          LEFT JOIN zone ON zone.parcel_id = parcel.id
        """,
        commune=commune,
    )


def dvf_end(connection: psycopg.Connection[Any]) -> date:
    """La dernière mutation connue — c'est elle qui borne la cohorte mesurable."""
    rows = fetch(
        connection, "SELECT max(mutation_date) AS last_mutation FROM observation.transaction"
    )
    return cast(date, rows[0]["last_mutation"])


def reference_cohort_year(latest_mutation: date) -> int:
    """La dernière année civile dont les douze mois de suivi sont couverts par DVF.

    Dérivée, jamais choisie : elle avance seule quand un millésime arrive. Un dépôt du
    31 décembre de l'année Y demande une couverture jusqu'au 31 décembre de Y+1.
    """
    if latest_mutation >= date(latest_mutation.year, 12, 31):
        return latest_mutation.year - 1
    return latest_mutation.year - 2


def cohort(connection: psycopg.Connection[Any], department: str, year: int) -> list[CohortRow]:
    """Cohorte de référence sur le département : premier DPE de **maison** par parcelle.

    Les DPE d'appartement générés depuis un DPE d'immeuble convertissent à 0,6 % et
    pollueraient tout taux départemental ; la liste ne porte que de l'habitat individuel.
    Relations bâtiment ↔ parcelle certaines seulement, comme la liste.

    Deux DPE de maison le même jour sur une parcelle : le premier par numéro de DPE est retenu.
    Le recompte du 15 septembre 2026 a montré que sans ce départage, les effectifs par
    étiquette ne se reproduisent pas à l'unité près — 79 parcelles concernées sur 8 028.
    """
    rows = fetch(
        connection,
        """
        WITH first_dpe AS (
            SELECT DISTINCT ON (link.parcel_id)
                   link.parcel_id, assessment.commune_code,
                   coalesce(assessment.deposited_at, assessment.assessment_date) AS deposited_at,
                   assessment.energy_label
              FROM observation.energy_assessment AS assessment
              JOIN reference.building_parcel AS link
                ON link.building_id = assessment.building_id
               AND link.relation_status = 'certain'
             WHERE assessment.department_code = %(department)s
               AND assessment.properties->>'type_batiment' = 'maison'
             ORDER BY link.parcel_id,
                      coalesce(assessment.deposited_at, assessment.assessment_date),
                      assessment.dpe_number
        )
        SELECT first_dpe.parcel_id, first_dpe.commune_code, first_dpe.deposited_at,
               first_dpe.energy_label,
               (SELECT min(mutation.mutation_date)
                  FROM observation.transaction_property AS property
                  JOIN observation.transaction AS mutation ON mutation.id = property.transaction_id
                 WHERE property.parcel_id = first_dpe.parcel_id
                   AND mutation.mutation_date > first_dpe.deposited_at) AS first_mutation
          FROM first_dpe
         WHERE first_dpe.deposited_at >= %(start)s AND first_dpe.deposited_at < %(end)s
        """,
        department=department,
        start=date(year, 1, 1),
        end=date(year + 1, 1, 1),
    )
    return [
        CohortRow(
            parcel_id=row["parcel_id"],
            commune_code=row["commune_code"],
            deposited_at=row["deposited_at"],
            energy_label=row["energy_label"],
            first_mutation=row["first_mutation"],
        )
        for row in rows
    ]


def sold_within(row: CohortRow, months: int) -> bool:
    return row.first_mutation is not None and row.first_mutation <= months_after(
        row.deposited_at, months
    )


def conversion_curve(rows: list[CohortRow], months: int) -> list[float | None]:
    """Part vendue à 0, 1, … `months` mois après le dépôt. Vide → absente, jamais zéro."""
    if not rows:
        return [None] * (months + 1)
    return [sum(sold_within(row, m) for row in rows) / len(rows) for m in range(months + 1)]


def residual_probability(
    curve: list[float | None], age_months: int, horizon_months: int
) -> float | None:
    """Chance de vente sur l'horizon, sachant aucune vente après `age_months` mois.

    Lue sur la courbe, jamais extrapolée : au-delà de sa portée, la valeur manque.
    """
    if age_months < 0 or age_months + horizon_months >= len(curve):
        return None
    start, end = curve[age_months], curve[age_months + horizon_months]
    if start is None or end is None or start >= 1:
        return None
    return (end - start) / (1 - start)


def rate(rows: list[CohortRow], months: int) -> tuple[int, float | None]:
    """Effectif et taux à `months` mois — l'effectif accompagne toujours le taux."""
    if not rows:
        return 0, None
    return len(rows), sum(sold_within(row, months) for row in rows) / len(rows)


def label_rates(rows: list[CohortRow], months: int) -> dict[str, tuple[int, float | None]]:
    """Taux par étiquette. Une étiquette absente n'est pas une étiquette : elle ne compte pas."""
    labels = sorted({row.energy_label for row in rows if row.energy_label})
    return {
        label: rate([row for row in rows if row.energy_label == label], months) for label in labels
    }


def age_in_months(deposited_at: date, reference: date) -> int:
    """Mois révolus entre le dépôt et la date d'extrait."""
    months = (reference.year * 12 + reference.month) - (deposited_at.year * 12 + deposited_at.month)
    return months - 1 if reference.day < deposited_at.day else months


def annotate(
    rows: list[dict[str, Any]],
    curve: list[float | None],
    labels: dict[str, tuple[int, float | None]],
    reference: date,
    parameters: Parameters,
) -> None:
    """Trois lectures par candidat, indépendantes : elles ne se combinent jamais en un score."""
    for row in rows:
        age = age_in_months(row["dpe_deposited_at"], reference)
        row["dpe_age_months"] = age
        row["residual_probability"] = residual_probability(curve, age, parameters.horizon_months)
        label = row.get("energy_label")
        row["label_rate"] = labels[label][1] if label in labels else None


def percent(value: float | None, missing: str = "absent") -> str:
    return missing if value is None else f"{100 * value:.1f} %".replace(".", ",")


def thousands(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def months_before(reference: date, months: int) -> date:
    """Recul en mois, sans dépendance externe — le jour est conservé quand il existe."""
    year, month = divmod((reference.year * 12 + reference.month - 1) - months, 12)
    day = min(
        reference.day,
        [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month],
    )
    return date(year, month + 1, day)


def months_after(reference: date, months: int) -> date:
    return months_before(reference, -months)


def eligible(
    rows: list[dict[str, Any]], parameters: Parameters
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Population commune aux deux cohortes : résidentiel individuel, en zone constructible."""
    funnel = {"parcelles avec diagnostic": len(rows)}
    steps: tuple[tuple[str, Any], ...] = (
        ("usage résidentiel connu", is_residential),
        ("nature résidentielle", lambda r: not has_non_residential_nature(r)),
        (
            "habitat individuel",
            lambda r: (
                r["max_dwellings"] is None
                or r["max_dwellings"] <= parameters.max_dwellings_per_building
            ),
        ),
        ("zone connue", lambda r: r["zone"] is not None),
        ("zone constructible", lambda r: zone_type(r["zone"]) == parameters.zone_type),
        # Une mutation postérieure au dépôt : le bien a déjà changé de mains.
        (
            "pas de mutation depuis le diagnostic",
            lambda r: r["last_mutation"] is None or r["last_mutation"] <= r["dpe_deposited_at"],
        ),
    )
    kept = rows
    for label, predicate in steps:
        kept = [row for row in kept if predicate(row)]
        funnel[label] = len(kept)
    return kept, funnel


def cohorts(
    rows: list[dict[str, Any]], parameters: Parameters, reference: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Signal et baseline, tirés de la même population par la seule fraîcheur du dépôt."""
    fresh_from = months_before(reference, parameters.fresh_months)
    stale_before = months_before(reference, parameters.stale_months)
    signal = sorted(
        (row for row in rows if row["dpe_deposited_at"] >= fresh_from),
        key=lambda row: row["dpe_deposited_at"],
        reverse=True,
    )
    baseline = sorted(
        (row for row in rows if row["dpe_deposited_at"] < stale_before),
        key=lambda row: row["dpe_deposited_at"],
        reverse=True,
    )
    return signal, baseline


def render(data: dict[str, Any], today: str) -> str:
    parameters: Parameters = data["parameters"]
    rows: list[dict[str, Any]] = data["blind"]
    stats: dict[str, Any] = data["statistics"]
    lines: list[str] = []
    add = lines.append

    add(f"# Biens probablement en vente — commune {data['commune']}")
    add("")
    add(
        f"**Généré le :** {today} · **Ticket :** [E8f](../backlog/E8f-liste-biens-en-vente.md)"
        f" · **Graine :** `{data['seed']}` · **Extrait DPE au :** {data['reference']}"
    )
    add("")
    add("Ce fichier est **régénéré** par `make biens-en-vente`. Ne pas l'éditer à la main.")
    add("")
    add("## Ce que cette liste dit, et ce qu'elle ne dit pas")
    add("")
    add(
        "Elle dit : **un DPE a été déposé à cette date**. C'est un fait administratif, daté et "
        "public, obligatoire pour mettre un logement en vente. Ce n'est pas un modèle : rien n'est "
        "appris, aucun seuil n'est inventé, et chaque ligne s'explique par sa date."
    )
    add("")
    add(
        "Elle **ne dit pas** que le bien sera vendu. Mesuré sur le 35 dans "
        "[`dpe-signal-vente-35.md`](./dpe-signal-vente-35.md) : **35,65 %** des parcelles dont le "
        "premier DPE a été déposé en 2024 ont muté dans les douze mois, contre **3,03 %** de "
        "l'ensemble des parcelles bâties — lift 11,8 fois. **Deux tiers ne mutent donc pas dans "
        "l'année.**"
    )
    add("")
    add(
        "Le dépôt précède l'acte de **169 jours en médiane**, soit environ 80 jours avant le "
        "compromis : le signal arrive à la mise en vente, pas après."
    )
    add("")
    add("## Quatre limites, dont deux sérieuses")
    add("")
    add(
        "**Le motif du diagnostic n'est pas publié.** `methode_application_dpe` donne le périmètre "
        "de calcul — maison, appartement, immeuble — jamais la raison. Un DPE de **location** est "
        "indiscernable d'un DPE de vente. Cette dilution est déjà dans le 35,65 %."
    )
    add("")
    add(
        "**DVF s'arrête au 31 décembre 2025.** Pour les dépôts récents, « aucune mutation depuis » "
        "est un défaut de données autant qu'un fait de marché. Le filtre l'applique là où "
        "la donnée existe, et ne peut rien affirmer au-delà."
    )
    add("")
    add(
        "**Le rattachement du DPE au bâtiment plafonne à 59 %** — voir "
        "[`dpe-matching-35.md`](./dpe-matching-35.md). Les diagnostics rattachés à la seule "
        "adresse sont absents de cette liste."
    )
    add("")
    add(
        "**Un seul département, une seule cohorte annuelle** fondent le lift — et les taux "
        "ci-dessous, mesurés à la génération sur la cohorte de référence."
    )
    add("")
    add("## Les deux cohortes, et pourquoi la baseline est celle-là")
    add("")
    add(
        f"La fenêtre se compte depuis la **date d'extrait**, {data['reference']}, jamais depuis "
        "l'horloge : sinon la liste se viderait toute seule à mesure que l'extrait vieillit, sans "
        "que rien ne le signale."
    )
    add("")
    add("| Cohorte | Définition | Unités |")
    add("|---|---|---:|")
    add(
        f"| **Signal** | DPE déposé depuis moins de {parameters.fresh_months} mois | "
        f"{data['signal_total']:,} |".replace(",", " ")
    )
    add(
        f"| Baseline | DPE déposé il y a plus de {parameters.stale_months} mois | "
        f"{data['baseline_total']:,} |".replace(",", " ")
    )
    add("")
    add(
        "Les deux sortent de **la même population** — résidentiel individuel en zone constructible "
        "— et ne diffèrent que par la fraîcheur du dépôt. C'est exactement ce que la liste "
        "revendique ; un tri par surface n'y répondrait pas."
    )
    add("")
    add("## Entonnoir")
    add("")
    add("| Étape | Unités restantes |")
    add("|---|---:|")
    for label, count in data["funnel"].items():
        add(f"| {label} | {count:,} |".replace(",", " "))
    add("")
    add("## Ce que la cohorte de référence dit — trois lectures, jamais combinées")
    add("")
    add(
        f"Cohorte : parcelles du département {stats['department']} dont le premier DPE de "
        f"**maison** a été déposé en **{stats['year']}** — la dernière année civile dont les douze "
        f"mois de suivi sont couverts par DVF, arrêtée au {stats['dvf_end']}. Issue : au moins "
        "une mutation dans les douze mois. Relations bâtiment ↔ parcelle certaines seulement ; "
        "à date égale, le premier DPE par numéro. Les DPE d'appartement générés depuis un DPE "
        "d'immeuble, qui convertissent à moins de 1 %, en sont exclus."
    )
    add("")
    add("| Population | Parcelles | Vendues dans les 12 mois |")
    add("|---|---:|---:|")
    add(
        f"| Département {stats['department']}, maisons | {thousands(stats['size'])} | "
        f"{percent(stats['rate'])} |"
    )
    add(
        f"| Commune {data['commune']}, maisons | {thousands(stats['commune_size'])} | "
        f"{percent(stats['commune_rate'], 'aucune parcelle mesurée')} |"
    )
    add("")
    add(
        "Le taux de la commune est donné avec son effectif, **jamais masqué sous un minimum** : "
        "le relecteur juge lui-même ce que vaut un taux sur quelques dizaines de parcelles."
    )
    add("")
    add("**Courbe de conversion** — part vendue selon les mois écoulés depuis le dépôt :")
    add("")
    months = list(range(len(stats["curve"])))
    add("| Mois | " + " | ".join(str(m) for m in months) + " |")
    add("|---|" + "---:|" * len(months))
    add("| Cumul vendu | " + " | ".join(percent(v) for v in stats["curve"]) + " |")
    add("")
    add(
        f"La colonne « chance de vente sous {parameters.horizon_months} mois » se lit sur cette "
        "courbe : part de la cohorte vendue entre l'âge du candidat et cet horizon, parmi celles "
        "encore invendues à cet âge. L'horizon est **arbitraire et déclaré**, comme les fenêtres. "
        "Au-delà de la portée de la courbe, la valeur manque — elle n'est pas extrapolée."
    )
    add("")
    add("**Par étiquette** — taux à douze mois, même cohorte :")
    add("")
    add("| Étiquette | Parcelles | Vendues dans les 12 mois |")
    add("|---|---:|---:|")
    for label, (size, value) in stats["labels"].items():
        add(f"| {label} | {thousands(size)} | {percent(value)} |")
    add("")
    add(
        "Âge et étiquette sont deux lectures **indépendantes** de la même cohorte. Elles ne se "
        "combinent pas : les combiner serait un modèle, et rien n'établit leur indépendance."
    )
    add("")
    add("## Candidats")
    add("")
    add(
        "L'origine — signal ou baseline — est dans "
        f"`{data['key_file']}`, que le relecteur ne voit pas."
    )
    add("")
    add(
        "| Réf. | Parcelle | Adresse du DPE | DPE déposé | Âge (mois) | "
        f"Chance de vente sous {parameters.horizon_months} mois (âge) | Étiquette | "
        "Taux 12 mois (étiquette) | Surface hab. | Année | Parcelle m² | Zone | "
        "Dernière mutation |"
    )
    add("|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---|---|")
    for row in rows:
        mutation = row["last_mutation"].isoformat() if row["last_mutation"] else "aucune"
        add(
            f"| {row['reference']} | `{row['cadastral_id']}` | "
            f"{row.get('dpe_address') or 'absente — non déclarée sur le diagnostic'} | "
            f"{row['dpe_deposited_at'].isoformat()} | {row['dpe_age_months']} | "
            f"{percent(row['residual_probability'], 'non mesurée — hors courbe')} | "
            f"{row['energy_label'] or 'absente'} | "
            f"{percent(row['label_rate'], 'absent — étiquette absente')} | "
            f"{row['living_area_m2'] or 'absente'} | {row['built_year'] or 'inconnue'} | "
            f"{cell(row, 'parcel_area_m2')} | {row['zone'] or 'absente'} | {mutation} |"
        )
    add("")
    add(
        "La revue et les hypothèses mesurées sont dans "
        "[E9](../backlog/E9-test-terrain-deux-professionnels.md), qui départage cette promesse et "
        "celle de [E8](../backlog/E8-liste-exploratoire-terrain.md)."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Likely-on-market candidates for one commune")
    parser.add_argument("--commune", required=True, help="Code INSEE, par exemple 35051")
    parser.add_argument("--size", type=int, default=20, help="Candidats retenus par cohorte")
    parser.add_argument("--seed", type=int, default=20260915, help="Graine du mélange")
    defaults = Parameters()
    parser.add_argument("--fresh-months", type=int, default=defaults.fresh_months)
    parser.add_argument("--stale-months", type=int, default=defaults.stale_months)
    parser.add_argument("--output-dir", type=Path, default=None)
    arguments = parser.parse_args()

    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        connection.execute("SET LOCAL statement_timeout = '600s'")
        parameters = Parameters(
            fresh_months=arguments.fresh_months, stale_months=arguments.stale_months
        )
        reference = reference_date(connection)
        rows, funnel = eligible(population(connection, arguments.commune), parameters)
        signal, baseline = cohorts(rows, parameters, reference)
        if not signal:
            print(f"Aucun diagnostic frais sur {arguments.commune} — entonnoir : {funnel}")
            return 1
        blind_rows, key_rows = blind(
            signal[: arguments.size], baseline[: arguments.size], arguments.seed
        )
        locate(connection, blind_rows)
        latest_mutation = dvf_end(connection)
        year = reference_cohort_year(latest_mutation)
        department = arguments.commune[:2]
        reference_rows = cohort(connection, department, year)
        curve = conversion_curve(reference_rows, parameters.curve_months)
        labels = label_rates(reference_rows, parameters.curve_months)
        annotate(blind_rows, curve, labels, reference, parameters)
        size, overall = rate(reference_rows, parameters.curve_months)
        commune_size, commune_rate = rate(
            [row for row in reference_rows if row.commune_code == arguments.commune],
            parameters.curve_months,
        )
        statistics = {
            "year": year,
            "department": department,
            "dvf_end": latest_mutation.isoformat(),
            "size": size,
            "rate": overall,
            "commune_size": commune_size,
            "commune_rate": commune_rate,
            "curve": curve,
            "labels": labels,
        }

    root = arguments.output_dir or (Path(__file__).resolve().parents[2] / "docs" / "data")
    directory = root / "biens-en-vente" / arguments.commune
    directory.mkdir(parents=True, exist_ok=True)
    blind_file = directory / "liste-aveugle.csv"
    key_file = directory / "correspondance.csv"
    write_csv(
        blind_file,
        blind_rows,
        [
            "reference",
            "cadastral_id",
            "dpe_deposited_at",
            "dpe_age_months",
            "residual_probability",
            "energy_label",
            "label_rate",
            "living_area_m2",
            "built_year",
            "parcel_area_m2",
            "zone",
            "last_mutation",
            "diagnostics",
            "dpe_address",
            "latitude",
            "longitude",
            "map_url",
            "position_missing",
        ],
    )
    write_csv(key_file, key_rows, ["reference", "property_unit_id", "cadastral_id", "origine"])

    report = root / f"biens-en-vente-{arguments.commune}.md"
    report.write_text(
        render(
            {
                "commune": arguments.commune,
                "parameters": parameters,
                "funnel": funnel,
                "blind": blind_rows,
                "seed": arguments.seed,
                "reference": reference.isoformat(),
                "signal_total": len(signal),
                "baseline_total": len(baseline),
                "statistics": statistics,
                "key_file": f"docs/data/biens-en-vente/{arguments.commune}/correspondance.csv",
            },
            date.today().isoformat(),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {report}, {blind_file}, {key_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
