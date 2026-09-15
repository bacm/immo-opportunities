#!/usr/bin/env python3
"""Liste exploratoire de candidats, confrontable à un professionnel — E8.

Ce script **ne publie rien**. Il ne touche pas `scoring.*`, ne crée aucun
`OpportunitySnapshot` et ne modifie aucun `publication_eligible` : il lit la base et écrit
des fichiers. C'est ce qui l'autorise à exister alors que BUG-11 laisse toutes les unités en
`entity_resolution_incomplete`.

## Les paramètres du filtre sont arbitraires, et le rapport le dit

Ils ne viennent d'aucun profiling et n'anticipent pas E1. Ils servent à ramener une population
de taille raisonnable sur une commune, pas à définir ce qu'est un bon candidat. Le professionnel
est invité à les contester — c'est une des informations recherchées.

## Deux listes, parce que H1 compare deux ordres

La baseline est le tri cadastral simple que le produit prétend battre : surface décroissante. Le
classement ordonne **la même population** sur les signaux morphologiques disponibles. Filtrer
identiquement les deux isole la question posée : l'ordre, pas l'éligibilité.

## Le rang moyen n'additionne que les signaux présents

Une unité privée de `LAND-007` est classée sur trois signaux au lieu de quatre, et le rapport
publie combien d'unités sont dans ce cas. Remplacer l'absent par zéro la ferait remonter ou
descendre pour une raison qui n'existe pas.
"""

import argparse
import json
from dataclasses import asdict, dataclass
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
    mean_rank,
    use_populations,
    write_csv,
    zone_type,
)

# Seuils arbitraires. Aucun profiling ne les fonde ; ils bornent une population de travail.
# invariant-ok: paramètres exploratoires déclarés, hors moteur de score — voir E8


@dataclass(frozen=True)
class Parameters:
    max_parcel_area_m2: float = 3000.0
    max_footprint_ratio: float = 0.20
    min_width_m: float = 15.0
    min_building_count: int = 1
    zone_type: str = "U"
    max_dwellings_per_building: int = 2
    setback_m: float = 3.0
    # Le seul seuil de sens métier, et le seul qu'un professionnel puisse fixer. Il suppose un
    # retrait obligatoire par rapport aux limites séparatives : construire en limite changerait
    # la réponse, et cette règle est dans le règlement du PLU — profils D2b, non livrés.
    min_lot_width_m: float = 12.0

    @property
    def min_free_radius_m(self) -> float:
        return self.min_lot_width_m / 2


# Les signaux du classement, et le sens qui les ordonne. Tous morphologiques : sur une commune
# unique, les signaux de marché sont constants et ne séparent rien.
# `boundary_distance_m` est la distance **minimale** du bâti à la limite parcellaire : un bâti
# collé à une limite laisse un côté libre, un bâti loin de toute limite est centré. L'ordonner en
# décroissant remontait donc les maisons les moins divisibles — défaut corrigé par E8c.
# L'âge est un signal de **classement**, jamais un filtre : un pavillon récent n'est pas
# disqualifié, il passe derrière. Une longère de 1950 plantée au milieu de son terrain intéresse
# davantage qu'une maison de 2015 bien excentrée — E8e.
RANK_SIGNALS: tuple[tuple[str, bool], ...] = (
    ("built_year", False),
    ("free_radius_m", True),
    ("footprint_ratio", False),
    ("width_m", True),
    ("boundary_distance_m", False),
)

# Valeur publiée par BD TOPO. La liste des usages non résidentiels n'est pas énumérée :
# c'est « résidentiel » qui est exigé, et tout le reste — y compris l'inconnu — en est distinct.
FEATURES = {
    "parcel_area_m2": ("LAND-001", "numeric"),
    "footprint_ratio": ("LAND-003", "numeric"),
    "unbuilt_area_m2": ("LAND-004", "numeric"),
    "width_m": ("LAND-006", "numeric"),
    "boundary_distance_m": ("LAND-007", "numeric"),
    "building_count": ("LAND-009", "numeric"),
    "zone": ("URB-001", "text"),
    "constraints": ("URB-003", "json"),
}


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


def _pivot() -> str:
    """Valeur **et** motif d'absence pour chaque feature : une absence reste une absence."""
    columns = []
    for name, (code, kind) in FEATURES.items():
        column = {"numeric": "fv.numeric_value", "text": "fv.text_value", "json": "fv.json_value"}[
            kind
        ]
        # `jsonb` n'a pas d'agrégat `max` : on prend le premier élément du tableau agrégé.
        value = (
            f"(array_agg({column}) FILTER (WHERE fv.feature_code = '{code}'))[1]"
            if kind == "json"
            else f"max({column}) FILTER (WHERE fv.feature_code = '{code}')"
        )
        columns.append(f"{value} AS {name}")
        columns.append(
            f"max(fv.missing_reason) FILTER (WHERE fv.feature_code = '{code}') AS {name}_missing"
        )
    return ",\n               ".join(columns)


def population(connection: psycopg.Connection[Any], commune: str) -> list[dict[str, Any]]:
    return fetch(
        connection,
        f"""
        WITH bdtopo AS (
            SELECT unnest(string_to_array(properties->>'identifiants_rnb', '/')) AS rnb_id,
                   properties->>'usage_1' AS use,
                   properties->>'nature' AS nature,
                   nullif(left(properties->>'date_d_apparition', 4), '')::int AS built_year,
                   nullif(properties->>'nombre_de_logements', '')::int AS dwellings
              FROM meta.entity_source_observation
             WHERE source_entity_type = 'bdtopo_building'
               AND properties->>'identifiants_rnb' IS NOT NULL
        ),
        unit AS (
            SELECT pu.id, member.entity_id AS parcel_id
              FROM reference.property_unit AS pu
              JOIN reference.property_unit_member AS member
                ON member.property_unit_id = pu.id
               AND member.entity_type = 'parcel'
               AND member.member_role = 'primary'
             WHERE pu.commune_code = %(commune)s
        ),
        use AS (
            SELECT link.parcel_id,
                   string_agg(DISTINCT bdtopo.use, ' · ') AS uses,
                   string_agg(DISTINCT bdtopo.nature, ' · ') AS natures,
                   max(bdtopo.dwellings) AS max_dwellings,
                   min(bdtopo.built_year) AS built_year
              FROM unit
              JOIN reference.building_parcel AS link
                ON link.parcel_id = unit.parcel_id
               AND link.relation_status = 'certain'
              JOIN bdtopo ON 'building:rnb:' || bdtopo.rnb_id = link.building_id
             GROUP BY link.parcel_id
        )
        SELECT unit.id AS property_unit_id, parcel.cadastral_id,
               min(use.uses) AS uses, min(use.natures) AS natures,
               min(use.max_dwellings) AS max_dwellings, min(use.built_year) AS built_year,
               {_pivot()}
          FROM unit
          JOIN reference.parcel AS parcel ON parcel.id = unit.parcel_id
          LEFT JOIN use ON use.parcel_id = unit.parcel_id
          LEFT JOIN feature.feature_value AS fv ON fv.property_unit_id = unit.id
         GROUP BY unit.id, parcel.cadastral_id
        """,
        commune=commune,
    )


def eligible(
    rows: list[dict[str, Any]], parameters: Parameters
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Filtre et entonnoir. Une valeur absente exclut et se compte — elle ne vaut pas zéro."""
    funnel = {"population": len(rows)}
    steps: tuple[tuple[str, Any], ...] = (
        ("bâtie", lambda r: (r["building_count"] or 0) >= parameters.min_building_count),
        ("surface connue", lambda r: r["parcel_area_m2"] is not None),
        ("surface plafonnée", lambda r: r["parcel_area_m2"] <= parameters.max_parcel_area_m2),
        ("emprise connue", lambda r: r["footprint_ratio"] is not None),
        ("emprise faible", lambda r: r["footprint_ratio"] <= parameters.max_footprint_ratio),
        ("largeur connue", lambda r: r["width_m"] is not None),
        ("largeur suffisante", lambda r: r["width_m"] >= parameters.min_width_m),
        ("zone connue", lambda r: r["zone"] is not None),
        ("zone constructible", lambda r: zone_type(r["zone"]) == parameters.zone_type),
        ("usage résidentiel connu", is_residential),
        ("nature résidentielle", lambda r: not has_non_residential_nature(r)),
        (
            "habitat individuel",
            lambda r: (
                r["max_dwellings"] is None
                or r["max_dwellings"] <= parameters.max_dwellings_per_building
            ),
        ),
    )
    kept = rows
    for label, predicate in steps:
        kept = [row for row in kept if predicate(row)]
        funnel[label] = len(kept)
    return kept, funnel


def orderings(
    rows: list[dict[str, Any]], size: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline = sorted(rows, key=lambda row: -row["parcel_area_m2"])[:size]
    ranks = mean_rank(rows, RANK_SIGNALS)
    ranked = sorted(rows, key=lambda row: ranks[row["property_unit_id"]][0])[:size]
    for row in rows:
        row["rank_score"], row["rank_signals"] = ranks[row["property_unit_id"]]
    return baseline, ranked


SURFACE_BANDS: tuple[tuple[str, float, float], ...] = (
    ("moins de 400 m²", 0.0, 400.0),
    ("400 à 600 m²", 400.0, 600.0),
    ("600 à 800 m²", 600.0, 800.0),
    ("800 à 1 000 m²", 800.0, 1000.0),
    ("1 000 à 1 500 m²", 1000.0, 1500.0),
    ("plus de 1 500 m²", 1500.0, float("inf")),
)


def surface_bands(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Bornes semi-ouvertes : chaque unité tombe dans une tranche et une seule."""
    return {
        label: sum(1 for row in rows if low <= row["parcel_area_m2"] < high)
        for label, low, high in SURFACE_BANDS
    }


def divisibility(
    connection: psycopg.Connection[Any], rows: list[dict[str, Any]], parameters: Parameters
) -> None:
    """Rayon du plus grand cercle inscriptible dans la partie libre, et accès à la voirie.

    La **surface** libre ne dit rien de la divisibilité : une maison centrée laisse un anneau
    connexe de grande aire et inutilisable — 75 % à 91 % de la parcelle sur l'échantillon relu,
    rejetées et retenues confondues. C'est une mesure de forme qu'il faut.

    Calculé sur le seul vivier éligible : `ST_MaximumInscribedCircle` par composante est trop cher
    pour une commune entière, et sans objet sur les unités déjà écartées.
    """
    measures = {
        record["cadastral_id"]: record
        for record in fetch(
            connection,
            """
            WITH built AS (
                SELECT link.parcel_id, ST_Union(building.geom) AS geom
                  FROM reference.building_parcel AS link
                  JOIN reference.building AS building ON building.id = link.building_id
                 WHERE link.relation_status = 'certain'
                   AND link.parcel_id IN (
                       SELECT id FROM reference.parcel
                        WHERE cadastral_id = ANY(%(parcels)s::text[]))
                 GROUP BY link.parcel_id
            ),
            free AS (
                SELECT parcel.cadastral_id,
                       (ST_Dump(ST_Difference(parcel.geom,
                                              ST_Buffer(built.geom, %(setback)s)))).geom AS geom
                  FROM reference.parcel_geometry AS parcel
                  JOIN built ON built.parcel_id = parcel.id
                 WHERE parcel.cadastral_id = ANY(%(parcels)s::text[])
            ),
            ranked AS (
                SELECT cadastral_id, geom,
                       (ST_MaximumInscribedCircle(geom)).radius AS radius,
                       row_number() OVER (
                           PARTITION BY cadastral_id
                               ORDER BY (ST_MaximumInscribedCircle(geom)).radius DESC) AS rank
                  FROM free
            )
            SELECT ranked.cadastral_id, ranked.radius AS free_radius_m,
                   min(ST_Distance(ranked.geom, road.geom)) AS road_distance_m
              FROM ranked
              LEFT JOIN observation.road_segment AS road
                ON ST_DWithin(ranked.geom, road.geom, 50)
             WHERE ranked.rank = 1
             GROUP BY ranked.cadastral_id, ranked.radius
            """,
            parcels=[row["cadastral_id"] for row in rows],
            setback=parameters.setback_m,
        )
    }
    for row in rows:
        measure = measures.get(row["cadastral_id"])
        row["free_radius_m"] = measure["free_radius_m"] if measure else None
        # Une géométrie absente reste absente : elle ne vaut pas un rayon nul.
        row["free_radius_m_missing"] = None if measure else "invalid_geometry"
        row["road_distance_m"] = measure["road_distance_m"] if measure else None


def divisible(
    rows: list[dict[str, Any]], parameters: Parameters, funnel: dict[str, int]
) -> list[dict[str, Any]]:
    """Second étage du filtre, après la mesure géométrique."""
    funnel["forme mesurée"] = sum(1 for row in rows if row["free_radius_m"] is not None)
    kept = [
        row
        for row in rows
        if row["free_radius_m"] is not None and row["free_radius_m"] >= parameters.min_free_radius_m
    ]
    funnel["lot inscriptible"] = len(kept)
    return kept


def enrich(connection: psycopg.Connection[Any], rows: list[dict[str, Any]]) -> None:
    """Mutations, DPE et risques fins des seuls candidats retenus."""
    parcels = [row["cadastral_id"] for row in rows]
    mutations = {
        record["cadastral_id"]: record
        for record in fetch(
            connection,
            """
            SELECT parcel.cadastral_id,
                   max(mutation.mutation_date) AS last_mutation,
                   count(*) AS mutations
              FROM observation.transaction_property AS property
              JOIN observation.transaction AS mutation ON mutation.id = property.transaction_id
              JOIN reference.parcel AS parcel ON parcel.id = property.parcel_id
             WHERE parcel.cadastral_id = ANY(%(parcels)s::text[])
             GROUP BY parcel.cadastral_id
            """,
            parcels=parcels,
        )
    }
    diagnostics: dict[str, list[dict[str, Any]]] = {}
    for record in fetch(
        connection,
        """
        SELECT parcel.cadastral_id, assessment.energy_label, assessment.assessment_date
          FROM reference.parcel AS parcel
          JOIN reference.building_parcel AS link ON link.parcel_id = parcel.id
           AND link.relation_status = 'certain'
          JOIN observation.energy_assessment AS assessment
            ON assessment.building_id = link.building_id
         WHERE parcel.cadastral_id = ANY(%(parcels)s::text[])
        """,
        parcels=parcels,
    ):
        diagnostics.setdefault(record["cadastral_id"], []).append(record)
    risks: dict[str, list[str]] = {}
    for record in fetch(
        connection,
        """
        SELECT DISTINCT parcel.cadastral_id, observation.risk_type
          FROM reference.parcel_geometry AS parcel
          JOIN observation.risk_observation AS observation
            ON observation.granularity <> 'commune'
           AND observation.geom IS NOT NULL
           AND ST_Intersects(observation.geom, parcel.geom)
         WHERE parcel.cadastral_id = ANY(%(parcels)s::text[])
        """,
        parcels=parcels,
    ):
        risks.setdefault(record["cadastral_id"], []).append(record["risk_type"])

    for row in rows:
        mutation = mutations.get(row["cadastral_id"], {})
        row["last_mutation"] = mutation.get("last_mutation")
        row["mutations"] = mutation.get("mutations", 0)
        labels = diagnostics.get(row["cadastral_id"], [])
        row["dpe_count"] = len(labels)
        row["dpe_label"] = labels[0]["energy_label"] if len(labels) == 1 else None
        row["dpe_note"] = "plusieurs diagnostics — appariement ambigu" if len(labels) > 1 else ""
        row["risks"] = ", ".join(sorted(set(risks.get(row["cadastral_id"], [])))) or ""


def constraint_summary(value: Any) -> str:
    """Compté par type, pas traduit : interpréter un code CNIG est le refus explicite de D2.

    Le détail code par code reste dans le CSV ; une quinzaine de codes par ligne rendait le
    tableau illisible sans rien apprendre au relecteur.
    """
    if not value:
        return "aucune"
    entries = value if isinstance(value, list) else json.loads(value)
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["constraint_type"]] = counts.get(entry["constraint_type"], 0) + 1
    return ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))


def render(data: dict[str, Any], today: str) -> str:
    parameters: Parameters = data["parameters"]
    funnel: dict[str, int] = data["funnel"]
    rows: list[dict[str, Any]] = data["blind"]
    lines: list[str] = []
    add = lines.append

    add(f"# Liste exploratoire de candidats — commune {data['commune']}")
    add("")
    add(
        f"**Généré le :** {today} · **Ticket :** [E8](../backlog/E8-liste-exploratoire-terrain.md)"
        f" · **Graine :** `{data['seed']}`"
    )
    add("")
    add("Ce fichier est **régénéré** par `make exploratory-candidates`. Ne pas l'éditer à la main.")
    add("")
    add("## Ce que cette liste est, et n'est pas")
    add("")
    add(
        "Elle **n'est pas un score publié**. Aucun `OpportunitySnapshot` n'a été créé, aucune "
        "unité "
        "n'est devenue publiable, et les 1 333 327 unités du 35 restent en "
        "`entity_resolution_incomplete`. C'est une requête de lecture, destinée à être montrée à "
        "un "
        "professionnel par [E9](../backlog/E9-test-terrain-deux-professionnels.md)."
    )
    add("")
    add(
        "**Chaque ligne désigne une parcelle, pas un bien.** "
        "[BUG-11](../backlog/BUG-11-unite-fonciere-degeneree.md) mesure cette limite : l'unité "
        "foncière au sens juridique suppose le propriétaire, hors périmètre, et la contiguïté "
        "seule "
        "produit des grappes de plusieurs milliers de parcelles. Un garage sur parcelle propre "
        "apparaît donc ici comme un candidat distinct de la maison voisine. Savoir si cette limite "
        "est rédhibitoire fait partie de ce que la revue doit établir."
    )
    add("")
    add("## Ce que la forme du terrain libre mesure, et ce qu'aucune source ne mesure")
    add("")
    add(
        "Seconde relecture, motif devenu unique : « la maison est trop centrée pour "
        "déparcelliser ». La **surface** libre n'en dit rien — une maison centrée laisse un anneau "
        "connexe couvrant 75 % à 91 % de la parcelle, rejetées et retenues confondues. Le "
        "classement porte donc désormais sur le rayon du plus grand cercle inscriptible dans la "
        "partie libre, bâti tamponné de "
        f"{parameters.setback_m:.0f} m, et `LAND-007` a repris son sens : un bâti **proche** d'une "
        "limite laisse un côté libre, et c'est lui qu'on remonte."
    )
    add("")
    add(
        "Deux motifs de rejet relevés n'ont **aucune source dans le dépôt**, "
        "et rien ici ne les voit :"
    )
    add("")
    add("| Motif | Source qui le porterait | État |")
    add("|---|---|---|")
    add(
        "| « c'est déjà goudronné » | couverture du sol, OCS GE | "
        "cité `SPEC.md` §27, non importé, sans contrat DS-* |"
    )
    add(
        "| « il y a une piscine » | constructions surfaciques BD TOPO | "
        "seule la couche bâtiment est importée |"
    )
    add("")
    add(
        "**Cas manqué consigné :** `35051000ZS0176` — rayon inscriptible 11,5 m, usage et nature "
        "résidentiels, un logement — a été rejetée à la relecture pour une maison « trop grande et "
        "en plein milieu ». Aucune source disponible ne porte ce jugement. Elle est "
        "consignée telle quelle plutôt qu'écartée par un seuil taillé sur elle."
    )
    add("")
    add("## L'âge du bâti, et ce qu'il vaut")
    add("")
    add(
        "Une maison de 1950 plantée au milieu de son terrain intéresse davantage un marchand "
        "qu'une maison de 2015 bien excentrée. L'âge est donc entré dans le classement — **en "
        "signal, jamais en filtre** : un bien récent n'est pas écarté, il passe derrière."
    )
    add("")
    add(
        "La source est `date_d_apparition` de BD TOPO, **renseignée sur 44,6 %** des bâtiments et "
        "**approximative pour l'ancien** : les valeurs se concentrent sur 1800, 1850, 1870, 1880 "
        "et 1900, signature d'une datation historique arrondie. C'est une période, pas une date "
        "d'acte, et une unité sans année reste classée sur les autres signaux."
    )
    add("")
    add(
        "BDNB porte la même information mieux : `ffo_bat_annee_construction`, renseignée à "
        "**68,9 %** et distribuée sur toutes les périodes. Elle est hors de portée faute de "
        "rattachement — aucun identifiant RNB, seul un appariement géométrique y mènerait. "
        "Entrée de plus pour [BUG-13](../backlog/BUG-13-sujet-des-features-batiment.md)."
    )
    add("")
    add("## L'usage du bâti, et la source d'où il vient")
    add("")
    add(
        "Dix candidats de la première liste relus à la main : **deux d'intérêt**, les autres des "
        "délaissés de voirie, des parcelles industrielles, des espaces verts et des immeubles. La "
        "cause est nommée dans [E8b](../backlog/E8b-usage-du-bati.md) : « grande parcelle, petit "
        "bâtiment » décrit aussi bien un jardin de maison qu'un espace vert communal. Le filtre "
        "exige désormais un usage **résidentiel** et un habitat **individuel**."
    )
    add("")
    add(
        "**L'usage vient de DS-04 BD TOPO, release `display_only`.** Ce n'est acceptable que parce "
        "que cette liste ne publie rien et sert à être contestée. Un score publié ne pourrait pas "
        "s'appuyer dessus. Le rattachement se fait par `identifiants_rnb`, déclaré par le "
        "producteur — aucun appariement géométrique, donc aucune des erreurs mesurées par "
        "[B4](../backlog/B4-revue-manuelle-appariements.md)."
    )
    add("")
    add("| Population avant filtre d'usage | Unités |")
    add("|---|---:|")
    for label, count in data["use_populations"].items():
        add(f"| {label} | {count:,} |".replace(",", " "))
    add("")
    add(
        "`Indifférencié` n'est pas « non résidentiel » : c'est un inconnu. Exiger le résidentiel "
        "connu écarte donc aussi l'inconnu, et le volume perdu est publié ci-dessus plutôt que "
        "fondu dans un taux unique."
    )
    add("")
    add("## Ce que le zonage ne permet pas de faire")
    add("")
    add(
        "Le filtre ne retient que le **type CNIG** `U`. Le libellé local — `UI1a`, `UG2b`, "
        "`UE2c(d)` — n'est pas interprétable sans le règlement du document, et "
        "[D2](../backlog/D2-import-gpu-ds08.md) a explicitement refusé de le recoder au jugé. "
        "Les profils de règles qui le permettraient sont "
        "[D2b](../backlog/D2b-profils-de-regles.md), non livré."
    )
    add("")
    add(
        "Conséquence directe, constatée au premier passage : sans plafond de surface, la liste se "
        "remplit de foncier d'activité — parcelles de plusieurs hectares en zone `UI` ou `UG`, "
        "jusqu'à 31 bâtiments — qui ne relève pas de la promesse produit. Le plafond ci-dessous "
        "l'écarte grossièrement, faute de pouvoir écarter la zone. C'est une limite à signaler au "
        "relecteur, pas un réglage à défendre."
    )
    add("")
    add("## Le plancher de surface a été supprimé")
    add("")
    add(
        "Il valait 800 m² et faisait doublon : proxy grossier d'une divisibilité que le rayon "
        "inscriptible mesure directement depuis "
        "[E8c](../backlog/E8c-divisibilite-geometrique.md). Il écartait **348 parcelles pourtant "
        "divisibles** — 262 entre 600 et 800 m², 86 entre 400 et 600 — pour un vivier retenu de "
        "357. Un seul critère décide désormais : le lot est-il inscriptible ? Voir "
        "[E8d](../backlog/E8d-seuils-parametrables.md)."
    )
    add("")
    add("| Tranche de surface | Unités du vivier |")
    add("|---|---:|")
    for label, count in data["surface_bands"].items():
        add(f"| {label} | {count:,} |".replace(",", " "))
    add("")
    add(
        f"**La largeur minimale du lot vaut {parameters.min_lot_width_m:.0f} m** — soit un rayon "
        f"inscriptible de {parameters.min_free_radius_m:.1f} m — et se règle par "
        "`make exploratory-candidates COMMUNE=… LOT_WIDTH=…`. C'est le seul seuil de sens métier "
        "de ce rapport."
    )
    add("")
    add(
        "**Cette valeur suppose un retrait obligatoire par rapport aux limites "
        "séparatives.** Là où le règlement autorise la construction en limite, un lot plus "
        "étroit reste constructible et la question change. Cette règle est dans le "
        "règlement du PLU, que "
        "[D2b](../backlog/D2b-profils-de-regles.md) doit rendre lisible et qui n'est pas livré : "
        "`URB-001` ne donne que le code de zone, jamais ce qu'il autorise. La valeur "
        "retenue est donc une hypothèse de travail, pas une contrainte physique."
    )
    add("")
    add("## Paramètres — arbitraires, et c'est délibéré")
    add("")
    add(
        "Aucun profiling ne les fonde. Ils bornent une population de travail sur une commune ; ils "
        "ne définissent pas ce qu'est un bon candidat et n'anticipent pas "
        "[E1](../backlog/E1-profiling-distributions.md). Les contester fait partie de la revue."
    )
    add("")
    add("| Paramètre | Valeur |")
    add("|---|---:|")
    for name, value in asdict(parameters).items():
        add(f"| `{name}` | {value} |")
    add("")
    add("## Entonnoir")
    add("")
    add("| Étape | Unités restantes |")
    add("|---|---:|")
    for label, count in funnel.items():
        add(f"| {label} | {count:,} |".replace(",", " "))
    add("")
    add(
        f"**{funnel[list(funnel)[-1]]:,} unités éligibles**, dont {data['size']} retenues par "
        f"chaque "
        "ordre.".replace(",", " ")
    )
    add("")
    add("## Les deux ordres, et leur recouvrement")
    add("")
    add(
        "La baseline est le tri cadastral simple que H1 demande de battre : surface décroissante. "
        "Le "
        "classement ordonne **la même population** par le rang moyen des signaux morphologiques "
        f"disponibles — {', '.join(f'`{name}`' for name, _ in RANK_SIGNALS)}."
    )
    add("")
    add("| | |")
    add("|---|---:|")
    add(f"| Candidats issus de la baseline seule | {data['only_baseline']} |")
    add(f"| Candidats issus du classement seul | {data['only_ranked']} |")
    add(f"| Communs aux deux ordres | {data['shared']} |")
    add(f"| **Total remis au relecteur** | **{len(rows)}** |")
    add("")
    if data["shared"] == data["size"]:
        add(
            "> **Les deux ordres sont identiques.** H1 n'est pas mesurable sur cette commune avec "
            "ces "
            "paramètres : il n'y a rien à comparer. Le signaler avant la session vaut mieux que de "
            "faire juger deux fois la même liste."
        )
    else:
        add(
            f"Les deux ordres diffèrent sur {data['only_baseline'] + data['only_ranked']} "
            f"candidats. "
            "C'est cet écart que la revue en aveugle départage."
        )
    add("")
    add(
        f"{data['partial_signals']} candidats sont classés sur moins de {len(RANK_SIGNALS)} "
        f"signaux, "
        "un signal absent n'étant pas remplacé par zéro."
    )
    add("")
    add("## Candidats")
    add("")
    add(
        "L'origine de chaque candidat — baseline ou classement — n'est **pas** dans ce tableau : "
        "elle "
        f"est dans `{data['key_file']}`, que le relecteur ne voit pas. La liste remise est "
        f"`{data['blind_file']}`."
    )
    add("")
    add(
        "| Réf. | Parcelle | Année | Surface m² | Emprise | Rayon libre m | Voirie m | "
        "Largeur m | Recul m | Bât. | Usage | Log. | Zone | Contraintes | Mutation | DPE | "
        "Risques fins |"
    )
    add("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|---|---|")
    for row in rows:
        dpe = row["dpe_label"] or (row["dpe_note"] or "aucun")
        mutation = row["last_mutation"].isoformat() if row["last_mutation"] else "aucune"
        add(
            f"| {row['reference']} | `{row['cadastral_id']}` | "
            f"{row['built_year'] or 'inconnue'} | {cell(row, 'parcel_area_m2')} | "
            f"{cell(row, 'footprint_ratio', 3)} | {cell(row, 'free_radius_m', 1)} | "
            f"{cell(row, 'road_distance_m', 1)} | "
            f"{cell(row, 'width_m', 1)} | {cell(row, 'boundary_distance_m', 1)} | "
            f"{cell(row, 'building_count')} | {row['uses'] or 'inconnu'} | "
            f"{row['max_dwellings'] if row['max_dwellings'] is not None else 'inconnu'} | "
            f"{row['zone'] or 'absent'} | "
            f"{constraint_summary(row['constraints'])} | {mutation} | {dpe} | "
            f"{row['risks'] or 'aucun'} |"
        )
    add("")
    add("## Ce que la revue doit produire")
    add("")
    add(
        "Un verdict par candidat — pertinent / non pertinent / indécidable — avec son motif, sans "
        "que le relecteur connaisse l'origine. Le protocole, les hypothèses mesurées et la "
        "conclusion attendue sont dans "
        "[E9](../backlog/E9-test-terrain-deux-professionnels.md)."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploratory candidate list for a single commune")
    parser.add_argument("--commune", required=True, help="Code INSEE, par exemple 35051")
    parser.add_argument("--size", type=int, default=20, help="Candidats retenus par ordre")
    parser.add_argument("--seed", type=int, default=20260915, help="Graine du mélange")
    defaults = Parameters()
    parser.add_argument(
        "--lot-width",
        type=float,
        default=defaults.min_lot_width_m,
        help="Largeur minimale du lot à détacher, en mètres",
    )
    parser.add_argument("--max-area", type=float, default=defaults.max_parcel_area_m2)
    parser.add_argument("--max-footprint-ratio", type=float, default=defaults.max_footprint_ratio)
    parser.add_argument("--min-width", type=float, default=defaults.min_width_m)
    parser.add_argument("--setback", type=float, default=defaults.setback_m)
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
            max_parcel_area_m2=arguments.max_area,
            max_footprint_ratio=arguments.max_footprint_ratio,
            min_width_m=arguments.min_width,
            setback_m=arguments.setback,
            min_lot_width_m=arguments.lot_width,
        )
        units = population(connection, arguments.commune)
        populations = use_populations(units)
        rows, funnel = eligible(units, parameters)
        if not rows:
            print(f"Aucune unité éligible sur {arguments.commune} — entonnoir : {funnel}")
            return 1
        divisibility(connection, rows, parameters)
        rows = divisible(rows, parameters, funnel)
        if not rows:
            print(f"Aucun lot inscriptible sur {arguments.commune} — entonnoir : {funnel}")
            return 1
        baseline, ranked = orderings(rows, arguments.size)
        blind_rows, key_rows = blind(baseline, ranked, arguments.seed)
        enrich(connection, blind_rows)
        locate(connection, blind_rows)

    root = arguments.output_dir or (Path(__file__).resolve().parents[2] / "docs" / "data")
    directory = root / "exploratory-candidates" / arguments.commune
    directory.mkdir(parents=True, exist_ok=True)
    blind_file = directory / "liste-aveugle.csv"
    key_file = directory / "correspondance.csv"
    write_csv(
        blind_file,
        blind_rows,
        [
            "reference",
            "cadastral_id",
            "built_year",
            "parcel_area_m2",
            "footprint_ratio",
            "unbuilt_area_m2",
            "width_m",
            "boundary_distance_m",
            "building_count",
            "zone",
            "last_mutation",
            "dpe_label",
            "dpe_note",
            "risks",
            "latitude",
            "longitude",
            "map_url",
            "position_missing",
        ],
    )
    write_csv(key_file, key_rows, ["reference", "property_unit_id", "cadastral_id", "origine"])

    baseline_ids = {row["property_unit_id"] for row in baseline}
    ranked_ids = {row["property_unit_id"] for row in ranked}
    report = root / f"exploratory-candidates-{arguments.commune}.md"
    report.write_text(
        render(
            {
                "commune": arguments.commune,
                "parameters": parameters,
                "funnel": funnel,
                "use_populations": populations,
                "surface_bands": surface_bands(rows),
                "blind": blind_rows,
                "seed": arguments.seed,
                "size": arguments.size,
                "shared": len(baseline_ids & ranked_ids),
                "only_baseline": len(baseline_ids - ranked_ids),
                "only_ranked": len(ranked_ids - baseline_ids),
                "partial_signals": sum(
                    1
                    for row in blind_rows
                    if row.get("rank_signals", len(RANK_SIGNALS)) < len(RANK_SIGNALS)
                ),
                "blind_file": blind_file.relative_to(root.parent.parent)
                if root.is_absolute()
                else blind_file,
                "key_file": key_file.relative_to(root.parent.parent)
                if root.is_absolute()
                else key_file,
            },
            date.today().isoformat(),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {report}, {blind_file}, {key_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
