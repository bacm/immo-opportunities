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
               diagnostic.living_area_m2, diagnostic.diagnostics,
               mutation.last_mutation, zone.zone, zone.parcel_area_m2
          FROM parcel
          JOIN use ON use.parcel_id = parcel.id
          JOIN diagnostic ON diagnostic.parcel_id = parcel.id
          LEFT JOIN mutation ON mutation.parcel_id = parcel.id
          LEFT JOIN zone ON zone.parcel_id = parcel.id
        """,
        commune=commune,
    )


def months_before(reference: date, months: int) -> date:
    """Recul en mois, sans dépendance externe — le jour est conservé quand il existe."""
    year, month = divmod((reference.year * 12 + reference.month - 1) - months, 12)
    day = min(
        reference.day,
        [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month],
    )
    return date(year, month + 1, day)


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
    lines: list[str] = []
    add = lines.append

    add(f"# Biens probablement en vente — commune {data['commune']}")
    add("")
    add(
        f"**Généré le :** {today} · **Ticket :** [E8f](../backlog/E8f-liste-biens-en-vente.md)"
        f" · **Graine :** `{data['seed']}` · **Extrait DPE au :** {data['reference']}"
    )
    add("")
    add("Ce fichier est **régénéré** par `make listing-candidates`. Ne pas l'éditer à la main.")
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
    add("**Un seul département, une seule cohorte annuelle** fondent le lift.")
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
    add("## Candidats")
    add("")
    add(
        "L'origine — signal ou baseline — est dans "
        f"`{data['key_file']}`, que le relecteur ne voit pas."
    )
    add("")
    add(
        "| Réf. | Parcelle | DPE déposé | Étiquette | Surface hab. | Année | Parcelle m² | Zone | "
        "Dernière mutation |"
    )
    add("|---|---|---|---|---:|---:|---:|---|---|")
    for row in rows:
        mutation = row["last_mutation"].isoformat() if row["last_mutation"] else "aucune"
        add(
            f"| {row['reference']} | `{row['cadastral_id']}` | "
            f"{row['dpe_deposited_at'].isoformat()} | {row['energy_label'] or 'absente'} | "
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

    root = arguments.output_dir or (Path(__file__).resolve().parents[2] / "docs" / "data")
    directory = root / "listing-candidates" / arguments.commune
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
            "energy_label",
            "living_area_m2",
            "built_year",
            "parcel_area_m2",
            "zone",
            "last_mutation",
            "diagnostics",
        ],
    )
    write_csv(key_file, key_rows, ["reference", "property_unit_id", "cadastral_id", "origine"])

    report = root / f"listing-candidates-{arguments.commune}.md"
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
                "key_file": f"docs/data/listing-candidates/{arguments.commune}/correspondance.csv",
            },
            date.today().isoformat(),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {report}, {blind_file}, {key_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
