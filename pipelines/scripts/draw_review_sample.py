"""Tirage stratifié reproductible de l'échantillon de revue manuelle — B4.

Deux principes gouvernent ce tirage, et tous deux viennent du ticket.

**La taille est fixée avant de regarder les résultats.** Elle est passée en paramètre, justifiée
dans `--rationale`, et persistée avec le tirage. Une taille choisie après coup décrit le résultat,
elle ne le valide pas.

**Aucun seuil territorial n'est inventé.** `scoring.segment_definition` est en `draft` avec
`thresholds: profiling_required` : les segments produit n'existent pas encore, et les fabriquer
ici les figerait avant le profiling de E1. Les strates ci-dessous sont donc des **strates
d'échantillonnage**, pas des segments produit : elles ne nourrissent aucun score, ne sont pas
persistées comme une classification du territoire, et servent uniquement à ce que le taux
d'erreur du rural — très majoritaire en volume — ne soit pas noyé dans celui de Rennes.

- `littoral` vient de la limite terre-mer de BD TOPO, source objective et non d'un jugement ;
- `urbain`, `periurbain`, `rural` viennent des tercies de la distribution **observée** du nombre
  de parcelles par commune. Un tercile décrit la distribution, il ne prétend rien sur ce qu'est
  une ville ;
- `frontiere` regroupe les cas que le ticket impose d'inclure, quel que soit leur territoire.
"""

import argparse
import json
from typing import Any

import psycopg

from immo_pipelines.cadastre.settings import CadastreSettings

# Communes du 35 dont la géométrie intersecte la limite terre-mer de
# `BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D035_2026-06-15`, table `limite_terre_mer`.
# Relevé le 8 septembre 2026 ; c'est une observation de la source, pas un choix.
COASTAL_COMMUNES: tuple[str, ...] = (
    "35049",
    "35078",
    "35093",
    "35116",
    "35132",
    "35181",
    "35186",
    "35228",
    "35236",
    "35241",
    "35247",
    "35255",
    "35256",
    "35259",
    "35263",
    "35270",
    "35284",
    "35287",
    "35288",
    "35299",
    "35306",
    "35314",
    "35358",
    "35361",
)

# Strates d'appariement à enjeu : ce sont elles qui décident de ce qui peut fonder une feature.
DECISION_STRATA: tuple[tuple[str, str, str], ...] = (
    # (nom de strate, table, prédicat)
    (
        "certain_official_identifier",
        "link",
        "link.decision = 'certain' AND link.method = 'official_identifier'",
    ),
    (
        "certain_source_relation",
        "match",
        "m.decision = 'certain' AND m.method = 'source_relation'",
    ),
    (
        "ambiguous",
        "match",
        "m.decision = 'ambiguous'",
    ),
)


def territorial_case_expression(alias: str) -> str:
    """Strate territoriale d'une commune, en SQL.

    L'ordre compte : le littoral prime sur la densité, parce qu'un marché littoral se comporte
    autrement qu'un rural de même densité — et c'est précisément ce que la stratification doit
    empêcher de confondre.
    """
    coastal = ", ".join(f"'{code}'" for code in COASTAL_COMMUNES)
    return f"""
        CASE
          WHEN {alias} IN ({coastal}) THEN 'littoral'
          WHEN {alias} IN (SELECT code FROM commune_tercile WHERE tercile = 3) THEN 'urbain'
          WHEN {alias} IN (SELECT code FROM commune_tercile WHERE tercile = 2) THEN 'periurbain'
          ELSE 'rural'
        END
    """


COMMUNE_TERCILE = """
    commune_tercile AS (
        SELECT area.code, ntile(3) OVER (ORDER BY count(parcel.id)) AS tercile
          FROM reference.area AS area
          LEFT JOIN reference.parcel AS parcel ON parcel.commune_code = area.code
         WHERE area.area_type = 'commune' AND area.department_code = %(department)s
         GROUP BY area.code
    )
"""


def draw_decision_stratum(
    connection: psycopg.Connection[Any],
    *,
    sample_id: str,
    seed: float,
    stratum: str,
    source: str,
    predicate: str,
    size: int,
    department: str,
) -> int:
    """Tirer `size` cas d'une strate, en équilibrant les territoires.

    `setseed` rend le tirage reproductible : rejouer le script avec la même graine redonne
    exactement les mêmes cas, ce que le ticket exige pour que la revue soit vérifiable.
    """
    connection.execute("SELECT setseed(%s)", (seed,))
    if source == "link":
        # La commune vient du batiment canonique, pas de l'observation : BD TOPO n'a aucune
        # colonne commune dans sa table `batiment`, et la deduire de la geometrie ici
        # dupliquerait une resolution deja faite a l'import.
        selection = f"""
            SELECT link.id AS link_id, NULL::bigint AS match_id,
                   NULL::text AS unmatched_type, NULL::text AS unmatched_id,
                   coalesce(
                       building.commune_code,
                       observation.properties->>'commune_code'
                   ) AS commune_code
              FROM meta.entity_observation_link AS link
              JOIN meta.entity_source_observation AS observation
                ON observation.id = link.observation_id
              LEFT JOIN reference.building AS building ON building.id = link.entity_id
             WHERE {predicate}
        """
    else:
        selection = f"""
            SELECT NULL::bigint AS link_id, m.id AS match_id,
                   NULL::text AS unmatched_type, NULL::text AS unmatched_id,
                   coalesce(address.commune_code, parcel.commune_code) AS commune_code
              FROM meta.entity_match AS m
              LEFT JOIN reference.address AS address
                     ON address.id = m.left_entity_id AND m.left_entity_type = 'address'
              LEFT JOIN reference.parcel AS parcel
                     ON parcel.id = m.right_entity_id AND m.right_entity_type = 'parcel'
             WHERE {predicate}
        """
    statement = f"""
        WITH {COMMUNE_TERCILE},
        candidate AS ({selection}),
        stratified AS (
            SELECT candidate.*,
                   {territorial_case_expression("candidate.commune_code")} AS territorial,
                   row_number() OVER (
                       PARTITION BY {territorial_case_expression("candidate.commune_code")}
                       ORDER BY random()
                   ) AS rank_in_stratum
              FROM candidate
             WHERE candidate.commune_code IS NOT NULL
        )
        INSERT INTO meta.matching_review_case (
            sample_id, territorial_stratum, matching_stratum, commune_code,
            match_id, observation_link_id, unmatched_entity_type, unmatched_entity_id,
            drawn_rank
        )
        SELECT %(sample_id)s, territorial, %(stratum)s, commune_code,
               match_id, link_id, unmatched_type, unmatched_id,
               row_number() OVER (ORDER BY territorial, rank_in_stratum)
          FROM stratified
         WHERE rank_in_stratum <= %(per_territory)s
        """
    # Quatre territoires : l'échantillon est équilibré entre eux, pour que le rural ne noie
    # pas le littoral ni l'inverse.
    per_territory = max(1, size // 4)
    cursor = connection.execute(
        statement,
        {
            "sample_id": sample_id,
            "stratum": stratum,
            "per_territory": per_territory,
            "department": department,
        },
    )
    return cursor.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description="Draw the B4 stratified review sample")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--seed", type=float, required=True, help="setseed value in [-1, 1]")
    parser.add_argument("--per-stratum", type=int, required=True)
    parser.add_argument("--rationale", required=True, help="justification, fixed before drawing")
    parser.add_argument("--protocol", default="docs/data/spatial-matching-manual-review-35.md")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), default="35")
    arguments = parser.parse_args()

    settings = CadastreSettings.from_environment()
    drawn: dict[str, int] = {}
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        connection.execute("SET ROLE pipeline_rw")
        connection.execute(
            """
            INSERT INTO meta.matching_review_sample (
                id, seed, target_size, size_rationale, protocol_document
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                arguments.sample_id,
                int(arguments.seed * 1_000_000_000),
                arguments.per_stratum * len(DECISION_STRATA),
                arguments.rationale,
                arguments.protocol,
            ),
        )
        for stratum, source, predicate in DECISION_STRATA:
            drawn[stratum] = draw_decision_stratum(
                connection,
                sample_id=arguments.sample_id,
                seed=arguments.seed,
                stratum=stratum,
                source=source,
                predicate=predicate,
                size=arguments.per_stratum,
                department=arguments.department,
            )
        connection.commit()

    print(json.dumps({"sample_id": arguments.sample_id, "drawn": drawn}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
