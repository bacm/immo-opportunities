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
import csv
import json
import random
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings

# Seuils arbitraires. Aucun profiling ne les fonde ; ils bornent une population de travail.
# invariant-ok: paramètres exploratoires déclarés, hors moteur de score — voir E8


@dataclass(frozen=True)
class Parameters:
    min_parcel_area_m2: float = 800.0
    max_parcel_area_m2: float = 3000.0
    max_footprint_ratio: float = 0.20
    min_width_m: float = 15.0
    min_building_count: int = 1
    zone_type: str = "U"
    max_dwellings_per_building: int = 2


# Les signaux du classement, et le sens qui les ordonne. Tous morphologiques : sur une commune
# unique, les signaux de marché sont constants et ne séparent rien.
RANK_SIGNALS: tuple[tuple[str, bool], ...] = (
    ("unbuilt_area_m2", True),
    ("footprint_ratio", False),
    ("width_m", True),
    ("boundary_distance_m", True),
)

# Valeur publiée par BD TOPO. La liste des usages non résidentiels n'est pas énumérée :
# c'est « résidentiel » qui est exigé, et tout le reste — y compris l'inconnu — en est distinct.
RESIDENTIAL_USE = "Résidentiel"
UNKNOWN_USE = "Indifférencié"

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
                   max(bdtopo.dwellings) AS max_dwellings
              FROM unit
              JOIN reference.building_parcel AS link
                ON link.parcel_id = unit.parcel_id
               AND link.relation_status = 'certain'
              JOIN bdtopo ON 'building:rnb:' || bdtopo.rnb_id = link.building_id
             GROUP BY link.parcel_id
        )
        SELECT unit.id AS property_unit_id, parcel.cadastral_id,
               min(use.uses) AS uses, min(use.max_dwellings) AS max_dwellings,
               {_pivot()}
          FROM unit
          JOIN reference.parcel AS parcel ON parcel.id = unit.parcel_id
          LEFT JOIN use ON use.parcel_id = unit.parcel_id
          LEFT JOIN feature.feature_value AS fv ON fv.property_unit_id = unit.id
         GROUP BY unit.id, parcel.cadastral_id
        """,
        commune=commune,
    )


def zone_type(zone: str | None) -> str | None:
    """`U|UE2c(d)` — le type CNIG précède la barre, le libellé local la suit."""
    return zone.split("|", 1)[0] if zone else None


def uses(row: dict[str, Any]) -> list[str]:
    return [use for use in (row.get("uses") or "").split(" · ") if use]


def is_residential(row: dict[str, Any]) -> bool:
    """Au moins un bâtiment que BD TOPO déclare résidentiel.

    `Indifférencié` n'est pas « non résidentiel » : c'est un inconnu, et il est compté comme tel
    par `use_populations`. Exiger le résidentiel connu écarte donc aussi l'inconnu — la liste est
    un échantillon à contester, pas un inventaire, et ce qu'elle perd est publié.
    """
    return RESIDENTIAL_USE in uses(row)


def use_populations(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Trois populations distinctes, jamais fondues en un seul taux d'absence."""
    known = [row for row in rows if uses(row)]
    return {
        "usage résidentiel connu": sum(1 for row in known if is_residential(row)),
        "usage non résidentiel connu": sum(
            1 for row in known if not is_residential(row) and uses(row) != [UNKNOWN_USE]
        ),
        "usage indifférencié": sum(1 for row in known if uses(row) == [UNKNOWN_USE]),
        "aucun bâtiment BD TOPO rattaché": len(rows) - len(known),
    }


def eligible(
    rows: list[dict[str, Any]], parameters: Parameters
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Filtre et entonnoir. Une valeur absente exclut et se compte — elle ne vaut pas zéro."""
    funnel = {"population": len(rows)}
    steps: tuple[tuple[str, Any], ...] = (
        ("bâtie", lambda r: (r["building_count"] or 0) >= parameters.min_building_count),
        ("surface connue", lambda r: r["parcel_area_m2"] is not None),
        ("surface suffisante", lambda r: r["parcel_area_m2"] >= parameters.min_parcel_area_m2),
        ("surface plafonnée", lambda r: r["parcel_area_m2"] <= parameters.max_parcel_area_m2),
        ("emprise connue", lambda r: r["footprint_ratio"] is not None),
        ("emprise faible", lambda r: r["footprint_ratio"] <= parameters.max_footprint_ratio),
        ("largeur connue", lambda r: r["width_m"] is not None),
        ("largeur suffisante", lambda r: r["width_m"] >= parameters.min_width_m),
        ("zone connue", lambda r: r["zone"] is not None),
        ("zone constructible", lambda r: zone_type(r["zone"]) == parameters.zone_type),
        ("usage résidentiel connu", is_residential),
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


def mean_rank(rows: list[dict[str, Any]]) -> dict[str, tuple[float, int]]:
    """Rang moyen sur les seuls signaux présents, et leur nombre."""
    totals: dict[str, list[float]] = {row["property_unit_id"]: [] for row in rows}
    for signal, descending in RANK_SIGNALS:
        present = [row for row in rows if row[signal] is not None]
        present.sort(key=lambda row: row[signal], reverse=descending)
        for position, row in enumerate(present, start=1):
            totals[row["property_unit_id"]].append(position / len(present))
    return {
        unit: (sum(ranks) / len(ranks) if ranks else 1.0, len(ranks))
        for unit, ranks in totals.items()
    }


def orderings(
    rows: list[dict[str, Any]], size: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline = sorted(rows, key=lambda row: -row["parcel_area_m2"])[:size]
    ranks = mean_rank(rows)
    ranked = sorted(rows, key=lambda row: ranks[row["property_unit_id"]][0])[:size]
    for row in rows:
        row["rank_score"], row["rank_signals"] = ranks[row["property_unit_id"]]
    return baseline, ranked


def blind(
    baseline: list[dict[str, Any]], ranked: list[dict[str, Any]], seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mélange les deux listes et retourne (liste aveugle, correspondance).

    Un candidat présent dans les deux ordres n'apparaît qu'une fois et porte les deux origines :
    le dupliquer donnerait deux verdicts sur le même bien et fausserait la comparaison.
    """
    origins: dict[str, set[str]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for label, rows in (("baseline", baseline), ("classement", ranked)):
        for row in rows:
            origins.setdefault(row["property_unit_id"], set()).add(label)
            by_id[row["property_unit_id"]] = row

    units = sorted(by_id)
    random.Random(seed).shuffle(units)
    blind_rows, key_rows = [], []
    for position, unit in enumerate(units, start=1):
        reference = f"C{position:03d}"
        blind_rows.append({"reference": reference, **by_id[unit]})
        key_rows.append(
            {
                "reference": reference,
                "property_unit_id": unit,
                "cadastral_id": by_id[unit]["cadastral_id"],
                "origine": "+".join(sorted(origins[unit])),
            }
        )
    return blind_rows, key_rows


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


def cell(row: dict[str, Any], name: str, digits: int = 0) -> str:
    """Une valeur absente s'affiche absente, avec son motif."""
    value = row.get(name)
    if value is None:
        return f"absent — {row.get(f'{name}_missing') or 'non calculé'}"
    return f"{float(value):,.{digits}f}".replace(",", " ") if digits >= 0 else str(value)


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
        "| Réf. | Parcelle | Surface m² | Emprise | Libre m² | Largeur m | Recul m | Bât. | "
        "Usage | Log. | Zone | Contraintes | Dernière mutation | DPE | Risques fins |"
    )
    add("|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|---|---|")
    for row in rows:
        dpe = row["dpe_label"] or (row["dpe_note"] or "aucun")
        mutation = row["last_mutation"].isoformat() if row["last_mutation"] else "aucune"
        add(
            f"| {row['reference']} | `{row['cadastral_id']}` | {cell(row, 'parcel_area_m2')} | "
            f"{cell(row, 'footprint_ratio', 3)} | {cell(row, 'unbuilt_area_m2')} | "
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


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploratory candidate list for a single commune")
    parser.add_argument("--commune", required=True, help="Code INSEE, par exemple 35051")
    parser.add_argument("--size", type=int, default=20, help="Candidats retenus par ordre")
    parser.add_argument("--seed", type=int, default=20260915, help="Graine du mélange")
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
        parameters = Parameters()
        units = population(connection, arguments.commune)
        populations = use_populations(units)
        rows, funnel = eligible(units, parameters)
        if not rows:
            print(f"Aucune unité éligible sur {arguments.commune} — entonnoir : {funnel}")
            return 1
        baseline, ranked = orderings(rows, arguments.size)
        blind_rows, key_rows = blind(baseline, ranked, arguments.seed)
        enrich(connection, blind_rows)

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
