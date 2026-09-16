#!/usr/bin/env python3
"""Mesure ce que chaque signal de regroupement ferait des parcelles du 35 — BUG-11.

Une unité foncière, ce sont des parcelles contiguës d'un même propriétaire. Le propriétaire est
hors d'atteinte ; la contiguïté seule chaîne un quartier entier. Ce rapport mesure les signaux
qui restent, **sans en choisir un** : le choix est une décision, écrite ailleurs.

Pour chaque signal, trois lectures :

- **ce qu'il regroupe** : unités de plus d'une parcelle, tailles, part des parcelles du 35 ;
- **s'il chaîne** : une grappe de mille parcelles n'est pas un bien, quel que soit le signal ;
- **s'il est corroboré** : parmi les paires qu'il relie et dont les deux parcelles ont été
  vendues, la part vendue dans un même acte. Un acte est une disposition unique ; y figurer
  ensemble est l'indice le plus proche d'une propriété commune que les données autorisées
  donnent. La ligne de base est celle des paires contiguës quelconques.

Le seuil du bâti partagé n'est pas choisi ici : BUG-09 le renvoie à E1. Le rapport balaie des
valeurs déclarées et montre ce que chacune change.
"""

import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg

from immo_pipelines.cadastre.settings import CadastreSettings

TRANSFORMATION_VERSION = "property-unit-signals-v1"
# Tolérance de contact entre deux parcelles, en mètres : celle de la mesure de contiguïté
# publiée dans BUG-11.
CONTACT_TOLERANCE_M = 0.01
# Parts d'emprise balayées pour le bâti partagé. Paramètres déclarés, aucun n'est retenu.
SHARED_BUILDING_SHARES = (0.05, 0.10, 0.25, 0.40)
# Communes de la mesure de contiguïté de BUG-11 : Dinard, Rennes, Saint-Malo.
BASELINE_COMMUNES = ("35093", "35238", "35288")
SIZE_BUCKETS = ((2, "2"), (5, "3 à 5"), (10, "6 à 10"), (50, "11 à 50"), (500, "51 à 500"))
LARGEST_BUCKET = "plus de 500"

REFERENCE_CASES = {
    "cas 90": ("parcel:cadastre:35288000DA0321", "parcel:cadastre:35288000DA0322"),
    "cas 55": ("parcel:cadastre:35033000ZS0089", "parcel:cadastre:35033000ZS0091"),
}


class DisjointSet:
    """Union-find sur des identifiants de parcelle."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        parent = self.parent
        parent.setdefault(item, item)
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[left_root] = right_root

    def groups(self) -> list[list[str]]:
        by_root: dict[str, list[str]] = {}
        for item in self.parent:
            by_root.setdefault(self.find(item), []).append(item)
        return [sorted(group) for group in by_root.values() if len(group) > 1]


def chain(groups: Iterable[Sequence[str]]) -> list[list[str]]:
    """Unités obtenues en fusionnant tous les groupes qui partagent une parcelle."""
    sets = DisjointSet()
    for group in groups:
        for other in group[1:]:
            sets.union(group[0], other)
    return sets.groups()


def pairs_of(groups: Iterable[Sequence[str]]) -> set[tuple[str, str]]:
    return {pair for group in groups for pair in combinations(sorted(set(group)), 2)}


def size_bucket(size: int) -> str:
    for bound, label in SIZE_BUCKETS:
        if size <= bound:
            return label
    return LARGEST_BUCKET


def describe(units: Sequence[Sequence[str]], parcel_total: int) -> dict[str, Any]:
    sizes = sorted((len(unit) for unit in units), reverse=True)
    covered = sum(sizes)
    members = [set(unit) for unit in units]
    return {
        "units": len(sizes),
        "parcels": covered,
        "share": covered / parcel_total if parcel_total else None,
        "largest": sizes[:3],
        "buckets": Counter(size_bucket(size) for size in sizes),
        "cases": {
            name: any(set(case) <= unit for unit in members)
            for name, case in REFERENCE_CASES.items()
        },
    }


def corroboration(
    pairs: Iterable[tuple[str, str]], acts_by_parcel: Mapping[str, set[str]]
) -> dict[str, Any]:
    """Part des paires, parmi celles dont les deux parcelles ont été vendues, vendues ensemble.

    Une paire dont une parcelle n'a jamais été vendue n'est ni pour ni contre : elle est exclue
    du dénominateur, et son effectif est publié à côté.
    """
    total = both_sold = together = 0
    for left, right in pairs:
        total += 1
        left_acts, right_acts = acts_by_parcel.get(left), acts_by_parcel.get(right)
        if left_acts and right_acts:
            both_sold += 1
            together += bool(left_acts & right_acts)
    return {
        "pairs": total,
        "both_sold": both_sold,
        "together": together,
        "rate": together / both_sold if both_sold else None,
    }


def contiguous_within(
    acts: Mapping[str, Sequence[str]], touching: Iterable[tuple[str, str, str]]
) -> tuple[list[list[str]], int]:
    """Dans chaque acte, les parcelles reliées par contact, et les actes d'un seul tenant."""
    per_act: dict[str, DisjointSet] = {}
    for act, left, right in touching:
        per_act.setdefault(act, DisjointSet()).union(left, right)
    groups: list[list[str]] = []
    whole = 0
    for act, sets in per_act.items():
        act_groups = sets.groups()
        groups.extend(act_groups)
        if len(act_groups) == 1 and len(act_groups[0]) == len(set(acts[act])):
            whole += 1
    return groups, whole


# --- Lecture de la base ---------------------------------------------------------------------


def scalar_row(
    connection: psycopg.Connection[Any], sql: LiteralString, *parameters: Any
) -> tuple[Any, ...]:
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise SystemExit(f"Requête sans résultat : {sql}")
    return cast(tuple[Any, ...], row)


def fetch_measures(connection: psycopg.Connection[Any], department: str) -> dict[str, Any]:
    parcel_total = cast(
        int,
        scalar_row(
            connection,
            "SELECT count(*) FROM reference.parcel WHERE department_code = %s",
            department,
        )[0],
    )
    releases = connection.execute(
        """
        SELECT data_source_id, id, acceptance_status FROM meta.dataset_release
         WHERE id IN (SELECT DISTINCT release_id FROM observation.transaction
                       WHERE department_code = %(d)s
                      UNION SELECT DISTINCT release_id FROM reference.cadastral_parcel
                       WHERE department_code = %(d)s
                      UNION SELECT DISTINCT jsonb_array_elements_text(release_ids)
                        FROM meta.entity_match
                       WHERE right_entity_type = 'parcel'
                         AND left_entity_type IN ('address', 'building'))
         ORDER BY 1, 2
        """,
        {"d": department},
    ).fetchall()
    acts_by_release = dict(
        connection.execute(
            "SELECT release_id, count(*) FROM observation.transaction"
            " WHERE department_code = %s GROUP BY 1",
            (department,),
        ).fetchall()
    )
    period = scalar_row(
        connection,
        "SELECT min(mutation_date), max(mutation_date) FROM observation.transaction"
        " WHERE department_code = %s",
        department,
    )

    acts_by_parcel: dict[str, set[str]] = {}
    for act, parcel in connection.execute(
        """
        SELECT DISTINCT tp.transaction_id, tp.parcel_id
          FROM observation.transaction_property AS tp
          JOIN observation.transaction AS t ON t.id = tp.transaction_id
         WHERE tp.parcel_id IS NOT NULL AND t.department_code = %s
        """,
        (department,),
    ):
        acts_by_parcel.setdefault(parcel, set()).add(act)
    acts: dict[str, list[str]] = {}
    for parcel, parcel_acts in acts_by_parcel.items():
        for act in parcel_acts:
            acts.setdefault(act, []).append(parcel)
    multi_acts = {act: sorted(parcels) for act, parcels in acts.items() if len(parcels) > 1}
    # L'import rattache une parcelle DVF au cadastre courant par jointure : une parcelle
    # renumérotée ou divisée depuis la vente perd son rattachement. La source déclare combien
    # l'acte en portait ; l'écart est ce que tout regroupement par acte ne verra pas.
    declared = connection.execute(
        """
        SELECT id, (properties->>'parcel_count')::int FROM observation.transaction
         WHERE department_code = %s AND properties ? 'parcel_count'
        """,
        (department,),
    ).fetchall()
    partial_acts = sum(1 for act, count in declared if count > len(acts.get(act, ())))
    lost_multi_acts = sum(1 for act, count in declared if count > 1 >= len(acts.get(act, ())))

    touching = connection.execute(
        """
        WITH members AS (
          SELECT DISTINCT tp.transaction_id, tp.parcel_id, cp.geom
            FROM observation.transaction_property AS tp
            JOIN observation.transaction AS t ON t.id = tp.transaction_id
            JOIN reference.parcel AS p ON p.id = tp.parcel_id
            JOIN reference.cadastral_parcel AS cp ON cp.cadastral_id = p.cadastral_id
           WHERE t.department_code = %(d)s AND tp.transaction_id = ANY(%(acts)s))
        SELECT a.transaction_id, a.parcel_id, b.parcel_id
          FROM members AS a
          JOIN members AS b ON a.transaction_id = b.transaction_id
                           AND a.parcel_id < b.parcel_id
                           AND ST_DWithin(a.geom, b.geom, %(tolerance)s)
        """,
        {"d": department, "acts": list(multi_acts), "tolerance": CONTACT_TOLERANCE_M},
    ).fetchall()
    contiguous_groups, whole_acts = contiguous_within(multi_acts, touching)

    address_groups: list[list[str]] = [
        cast(list[str], row[0])
        for row in connection.execute(
            """
            SELECT array_agg(DISTINCT m.right_entity_id ORDER BY m.right_entity_id)
              FROM meta.entity_match AS m
              JOIN reference.parcel AS p ON p.id = m.right_entity_id
             WHERE m.left_entity_type = 'address' AND m.right_entity_type = 'parcel'
               AND m.decision = 'certain' AND p.department_code = %s
             GROUP BY m.left_entity_id
            HAVING count(DISTINCT m.right_entity_id) > 1
            """,
            (department,),
        )
    ]

    building_groups: dict[float, list[list[str]]] = {}
    for share in SHARED_BUILDING_SHARES:
        building_groups[share] = [
            cast(list[str], row[0])
            for row in connection.execute(
                """
                SELECT array_agg(bp.parcel_id ORDER BY bp.parcel_id)
                  FROM reference.building_parcel AS bp
                  JOIN reference.parcel AS p ON p.id = bp.parcel_id
                 WHERE bp.building_overlap_ratio >= %s AND p.department_code = %s
                 GROUP BY bp.building_id
                HAVING count(*) > 1
                """,
                (share, department),
            )
        ]

    baseline: dict[str, dict[str, Any]] = {}
    for commune in BASELINE_COMMUNES:
        rows = connection.execute(
            """
            SELECT 'parcel:cadastre:' || a.cadastral_id, 'parcel:cadastre:' || b.cadastral_id
              FROM reference.cadastral_parcel AS a
              JOIN reference.cadastral_parcel AS b
                ON b.commune_code = a.commune_code AND a.cadastral_id < b.cadastral_id
               AND ST_DWithin(a.geom, b.geom, %s)
             WHERE a.commune_code = %s
            """,
            (CONTACT_TOLERANCE_M, commune),
        ).fetchall()
        baseline[commune] = corroboration(((a, b) for a, b in rows), acts_by_parcel)

    case_parcels = sorted({parcel for case in REFERENCE_CASES.values() for parcel in case})
    case_acts = {parcel: sorted(acts_by_parcel.get(parcel, ())) for parcel in case_parcels}
    case_partners = {
        parcel: sorted({other for act in acts for other in multi_acts.get(act, ())} - {parcel})
        for parcel, acts in case_acts.items()
    }

    signals = {
        "DVF, même acte, chaîné": (
            describe(chain(multi_acts.values()), parcel_total),
            corroboration(pairs_of(multi_acts.values()), acts_by_parcel),
        ),
        "DVF, même acte, parcelles contiguës, chaîné": (
            describe(chain(contiguous_groups), parcel_total),
            None,
        ),
        "Adresse BAN commune, chaîné": (
            describe(chain(address_groups), parcel_total),
            corroboration(pairs_of(address_groups), acts_by_parcel),
        ),
    }
    for share, groups in building_groups.items():
        signals[f"Bâti partagé, au moins {share * 100:.0f} % de l'emprise sur chaque parcelle"] = (
            describe(chain(groups), parcel_total),
            corroboration(pairs_of(groups), acts_by_parcel),
        )

    return {
        "department": department,
        "parcel_total": parcel_total,
        "releases": releases,
        "period": period,
        "acts_by_release": acts_by_release,
        "multi_acts": len(multi_acts),
        "multi_act_parcels": len({p for parcels in multi_acts.values() for p in parcels}),
        "whole_acts": whole_acts,
        "acts_with_contact": len({row[0] for row in touching}),
        "sold_parcels": len(acts_by_parcel),
        "declared_acts": len(declared),
        "partial_acts": partial_acts,
        "lost_multi_acts": lost_multi_acts,
        "signals": signals,
        "baseline": baseline,
        "case_acts": case_acts,
        "case_partners": case_partners,
    }


# --- Rendu ------------------------------------------------------------------------------------

NBSP = "\N{NO-BREAK SPACE}"
BUG11 = "[BUG-11](../backlog/BUG-11-unite-fonciere-degeneree.md)"


def number(value: int) -> str:
    return f"{value:,}".replace(",", NBSP)


def percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}{NBSP}%".replace(".", ",")


def short(parcel: str) -> str:
    return f"`{parcel.removeprefix('parcel:cadastre:')}`"


def signal_rows(signals: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    for name, (described, _) in signals.items():
        cases = described["cases"]
        cells = [
            name,
            number(described["units"]),
            number(described["parcels"]),
            percent(described["share"]),
            ", ".join(number(size) for size in described["largest"]),
            "oui" if cases["cas 90"] else "non",
            "oui" if cases["cas 55"] else "non",
        ]
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def bucket_rows(signals: Mapping[str, Any], labels: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for name, (described, _) in signals.items():
        counts = [number(described["buckets"].get(label, 0)) for label in labels]
        rows.append("| " + " | ".join([name, *counts]) + " |")
    return rows


def corroboration_row(name: str, measured: Mapping[str, Any]) -> str:
    cells = [
        name,
        number(measured["pairs"]),
        number(measured["both_sold"]),
        number(measured["together"]),
        percent(measured["rate"]),
    ]
    return "| " + " | ".join(cells) + " |"


def render(data: Mapping[str, Any], generated_on: date, recounted_on: date | None = None) -> str:
    department = data["department"]
    multi_acts = data["multi_acts"]
    whole_share = data["whole_acts"] / multi_acts if multi_acts else None
    first_sale, last_sale = data["period"]
    labels = [label for _, label in SIZE_BUCKETS] + [LARGEST_BUCKET]
    lines = [
        f"# Unités foncières du {department} — ce que chaque signal regrouperait",
        "",
        f"**Généré le** {generated_on.isoformat()} par `make property-unit-report`",
        f"(`{TRANSFORMATION_VERSION}`) — ticket {BUG11}.",
        (
            f"**Recompté le {recounted_on.isoformat()}** par `recompte-preuve`, en isolement du"
            " code : aucune divergence. Une régénération efface cette mention."
            if recounted_on
            else "**Non recompté.** Aucun chiffre ne sort de ce fichier sans `recompte-preuve`."
        ),
        "",
        "Une unité foncière, ce sont des parcelles contiguës d'un même propriétaire ;",
        "le propriétaire est hors d'atteinte. Ce rapport mesure les signaux qui restent.",
        "**Il n'en choisit aucun** : le choix est une décision.",
        "",
        "## Sources et filtres",
        "",
        f"- Parcelles du {department} : **{number(data['parcel_total'])}**,",
        "  une unité `single_parcel` chacune aujourd'hui.",
        f"- Mutations DVF du {first_sale} au {last_sale} : {number(data['declared_acts'])} actes,",
        f"  {number(data['sold_parcels'])} parcelles distinctes rattachées au cadastre courant.",
        f"- {number(data['partial_acts'])} actes portent moins de parcelles distinctes",
        "  rattachées que la source n'en déclare : une parcelle renumérotée ou divisée",
        "  depuis la vente perd son rattachement.",
        f"  {number(data['lost_multi_acts'])} actes à plusieurs parcelles n'en",
        "  gardent qu'une ou aucune, et échappent à tout regroupement par acte.",
        "- Releases lues :",
        *(
            f"  - `{release}` ({source}, `{status}`)"
            + (
                f", {number(data['acts_by_release'][release])} actes"
                if release in data["acts_by_release"]
                else ""
            )
            for source, release, status in data["releases"]
        ),
        "- Une release `pending` n'est pas acceptée : les actes qui en viennent comptent ici",
        "  comme observation, pas comme donnée validée.",
        "- Adresse : appariements adresse → parcelle `certain` seulement.",
        "- Bâti : `reference.building_parcel`, part de l'emprise du bâtiment sur la parcelle,",
        "  relations `certain` et `ambiguous` confondues. Depuis BUG-09, un bâtiment n'a qu'une",
        "  relation `certain`, celle de la parcelle qui en porte le plus : **le signal repose",
        "  donc entièrement sur les relations secondaires**, dont BUG-09 renvoie le seuil à E1.",
        f"- Contact : deux parcelles à moins de {CONTACT_TOLERANCE_M * 100:.0f} cm.",
        "- **Chaîné** : deux groupes qui partagent une parcelle fusionnent. C'est ce qui",
        "  produit une partition — et ce qui peut faire d'un quartier une seule unité.",
        "",
        "## Actes DVF portant plusieurs parcelles",
        "",
        f"- **{number(multi_acts)}** actes,",
        f"  **{number(data['multi_act_parcels'])}** parcelles distinctes.",
        f"- {number(data['acts_with_contact'])} actes ont au moins deux parcelles qui se",
        f"  touchent ; {number(data['whole_acts'])} sont d'un seul tenant, soit",
        f"  {percent(whole_share)} des {number(multi_acts)} actes à plusieurs parcelles.",
        "- Un acte qui n'est pas d'un seul tenant vend ensemble des parcelles éloignées :",
        "  même vendeur, mais pas une unité foncière au sens de la contiguïté.",
        "",
        "## Ce que chaque signal regrouperait",
        "",
        "| Signal | Unités de plus d'une parcelle | Parcelles regroupées | Part du "
        + department
        + " | Trois plus grandes | Cas 90 réuni | Cas 55 réuni |",
        "|---|---:|---:|---:|---|:---:|:---:|",
        *signal_rows(data["signals"]),
        "",
        "### Taille des unités",
        "",
        "| Signal | " + " | ".join(labels) + " |",
        "|---|" + "---:|" * len(labels),
        *bucket_rows(data["signals"], labels),
        "",
        "## Corroboration par les ventes",
        "",
        "Unité : la paire distincte de parcelles prise **dans un même groupe** — même acte,",
        "même adresse, même bâtiment —, sans chaînage. Parmi ces paires, celles dont les deux",
        "parcelles ont été vendues, et la part vendue dans un même acte. Une paire dont une",
        "parcelle n'a jamais été vendue est exclue du dénominateur. Le signal DVF vaut 100 %",
        "par construction : sa ligne ne donne que ses effectifs. La ligne de base ne compte que",
        "les paires internes à la commune.",
        "",
        "| Signal | Paires | Deux parcelles vendues | Vendues ensemble | Taux |",
        "|---|---:|---:|---:|---:|",
        *(
            corroboration_row(name.removesuffix(", chaîné"), measured)
            for name, (_, measured) in data["signals"].items()
            if measured is not None
        ),
        *(
            corroboration_row(f"Ligne de base : parcelles contiguës, commune {commune}", measured)
            for commune, measured in data["baseline"].items()
        ),
        "",
        "Vendues ensemble ne veut pas dire « même propriétaire » : c'est l'indice le plus",
        "proche que les données autorisées donnent. Un signal au niveau de la ligne de base",
        "n'apporte rien de plus que la contiguïté, déjà disqualifiée.",
        "",
        "## Cas de référence",
        "",
        "| Parcelle | Actes DVF | Vendue avec |",
        "|---|---:|---|",
        *(
            f"| {short(parcel)} | {len(acts)} | "
            + (", ".join(short(p) for p in data["case_partners"][parcel]) or "—")
            + " |"
            for parcel, acts in data["case_acts"].items()
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", default="35")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--recounted-on",
        type=date.fromisoformat,
        help="date du recompte adversarial, à ne passer qu'après un recompte sans divergence",
    )
    arguments = parser.parse_args()
    department: str = arguments.department
    output: Path = arguments.output or Path(f"docs/data/property-unit-{department}.md")

    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        data = fetch_measures(connection, department)
    output.write_text(render(data, date.today(), arguments.recounted_on), encoding="utf-8")
    print(f"Rapport écrit : {output}")


if __name__ == "__main__":
    main()
