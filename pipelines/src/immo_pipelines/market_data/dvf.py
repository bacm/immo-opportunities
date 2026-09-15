"""La transformation DVF, partagée par l'import geo-dvf et l'import d'archive — D1 et D8.

Extraite de `pipelines/scripts/import_dvf_release.py` quand un second consommateur réel est
apparu : les millésimes 2014 à 2020, que geo-dvf ne publie plus et qui n'existent qu'au format
DGFiP brut. Rien ici n'est anticipé pour un troisième.

La règle de qualification des mutations complexes, le choix de la surface et la déduplication des
lots ne dépendent pas du format d'entrée : elles portent sur des lignes déjà mises à la forme
geo-dvf. C'est le lecteur d'archive qui a la charge de cette mise en forme — voir
`dvf_archive.py`.
"""

import csv
import gzip
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

# 4 : un bien decrit plusieurs fois par la source ne compte plus pour plusieurs lots.
DVF_TRANSFORMATION_VERSION = "4"

# La version entre dans l'identifiant de chaque ligne, et pas seulement dans une constante. Sans
# cela, `ON CONFLICT DO NOTHING` conserve les lignes de la version precedente et un correctif de
# code n'atteint jamais les donnees : c'est exactement ce qui s'est produit sur BUG-09, ou la
# regle du rang etait ecrite, testee, et 1 240 355 relations fautives restaient en base.

SIMPLE_ALLOCATION = "single_property_full_price"

# Une ligne sans `type_local` n'est pas une ligne dont le type manque : c'est un lot de terrain.
# `geo-dvf` decrit le bati par `type_local` et le non-bati par `nature_culture` et
# `surface_terrain`. Nommer ce cas plutot que d'ecrire NULL dit ce que la source dit.
LAND_PROPERTY_TYPE = "Terrain"


def _distinct_lots(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Dédupliquer les lignes qui décrivent le même bien.

    `geo-dvf` publie **une ligne par (bien, nature de culture du terrain)**. Une maison vendue
    avec un terrain en « terres » et un en « sols » apparaît donc deux fois, identique à
    l'identique — même type, même surface bâtie, même nombre de pièces, même parcelle.

    Sans déduplication, cette maison compte pour deux lots chiffrables et la mutation devient
    complexe : son prix est écarté alors qu'il est parfaitement allouable. Mesuré sur les cinq
    millésimes du 35 : **4 666 mutations sur 49 838**, soit 9,4 % de celles à plusieurs lignes
    bâties, sont un seul bien répété.

    La clé de déduplication est volontairement stricte. Deux appartements identiques du même
    immeuble ne s'y distinguent pas — mais ils partagent alors leur numéro de lot ou leur
    parcelle, et l'ambiguïté est réelle, pas fabriquée par nous : la source ne permet pas de
    trancher, et une mutation ambiguë doit le rester.
    """
    seen: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = (
            row.get("type_local") or "",
            row.get("surface_reelle_bati") or "",
            row.get("nombre_pieces_principales") or "",
            row.get("lot1_numero") or "",
            row.get("id_parcelle") or "",
        )
        seen.setdefault(key, row)
    return list(seen.values())


def _surface(row: dict[str, str]) -> float | None:
    """La surface du lot : **bâtie** pour un local, **foncière** pour un terrain, jamais l'autre.

    La première version prenait la surface bâtie puis retombait sur la surface de terrain. Ce
    repli conflait deux grandeurs sans rapport : un lot déclaré `Dépendance` sans surface bâtie
    ressortait avec les 382 m² de sa parcelle, comme si la dépendance faisait 382 m². Relevé sur
    **30 816 lots bâtis — 17,2 %** — dont 367 portaient un prix alloué, donc un prix au m² faux
    d'un ordre de grandeur.

    Un lot bâti sans surface bâtie garde donc une surface **absente**. C'est la règle du projet :
    une valeur manquante reste manquante, elle n'emprunte pas celle du voisin.
    """
    column = "surface_terrain" if not row.get("type_local") else "surface_reelle_bati"
    raw = row.get(column) or ""
    if not raw:
        return None
    value = float(raw)
    # La contrainte de schema refuse une surface nulle ou negative, et c'est la bonne garde :
    # une surface de zero n'est pas une surface.
    return value if value > 0 else None


@dataclass
class Mutation:
    """Les lignes d'une même mutation, avant toute décision."""

    rows: list[dict[str, str]]

    @property
    def parcels(self) -> set[str]:
        return {row["id_parcelle"] for row in self.rows if row["id_parcelle"]}

    @property
    def local_types(self) -> set[str]:
        return {row["type_local"] for row in self.rows if row["type_local"]}

    def priced_lots(self) -> list[dict[str, str]]:
        """Les lots **distincts** auxquels le prix peut se rapporter.

        Une vente de maison comporte le lot bâti **et** ses lots de terrain. Le prix au m² d'une
        maison se rapporte par convention à la surface bâtie, le terrain venant avec : les lots
        de terrain d'une vente bâtie ne reçoivent donc pas de prix, ils ne sont pas ignorés pour
        autant — ils restent enregistrés avec leur surface et leur nature de culture.

        S'il n'y a aucun lot bâti, la mutation est une vente de terrain et le prix se rapporte
        au terrain.
        """
        built = _distinct_lots([row for row in self.rows if row["type_local"]])
        if built:
            return built
        return _distinct_lots([row for row in self.rows if _surface(row) is not None])

    @property
    def price(self) -> float | None:
        values = {row["valeur_fonciere"] for row in self.rows if row["valeur_fonciere"]}
        if len(values) != 1:
            # Plusieurs montants pour une meme mutation : la source se contredit, le prix
            # n'est pas exploitable. Ce n'est pas un rejet de la transaction.
            return None
        return float(values.pop())

    def complexity(self) -> str | None:
        """Le motif rendant le prix non allouable, ou `None` si le prix l'est."""
        if self.price is None:
            return "price_missing"
        if len(self.parcels) > 1:
            return "multiple_parcels"
        lots = self.priced_lots()
        if len(lots) != 1:
            # Zero lot chiffrable : rien a quoi rapporter le prix. Plusieurs : le montant
            # couvre l'ensemble sans dire ce qui revient a chacun, et l'attribuer entierement
            # a l'un d'eux fabriquerait un prix au m2 faux et credible. Une maison avec son
            # garage tombe ici, et c'est voulu.
            return "no_priced_lot" if not lots else "multiple_priced_lots"
        if _surface(lots[0]) is None:
            return "surface_missing"
        return None


def read_mutations(path: Path) -> dict[str, Mutation]:
    """Regrouper les lignes par mutation. Une ligne = un lot, une mutation = un acte."""
    mutations: dict[str, Mutation] = defaultdict(lambda: Mutation(rows=[]))
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mutations[row["id_mutation"]].rows.append(row)
    return dict(mutations)


def import_year(
    connection: psycopg.Connection[Any],
    *,
    release_id: str,
    raw_asset_id: int,
    department: str,
    path: Path,
) -> dict[str, int]:
    mutations = read_mutations(path)
    counters: dict[str, int] = defaultdict(int)
    transactions: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []

    for mutation_id, mutation in mutations.items():
        head = mutation.rows[0]
        reason = mutation.complexity()
        counters["mutations"] += 1
        counters[f"reason_{reason or 'allocatable'}"] += 1

        transactions.append(
            (
                f"transaction:dvf:{release_id}:v{DVF_TRANSFORMATION_VERSION}:{mutation_id}",
                release_id,
                raw_asset_id,
                f"v{DVF_TRANSFORMATION_VERSION}:{mutation_id}",
                head["date_mutation"] or None,
                head["nature_mutation"] or None,
                mutation.price,
                reason is not None,
                reason,
                head["code_commune"] or None,
                department,
                json.dumps(
                    {
                        "parcel_count": len(mutation.parcels),
                        "local_types": sorted(mutation.local_types),
                        "row_count": len(mutation.rows),
                    }
                ),
            )
        )

        priced: set[int] = {id(row) for row in mutation.priced_lots()} if reason is None else set()
        for index, row in enumerate(mutation.rows):
            surface = _surface(row)
            # Le prix ne va qu'au lot auquel il se rapporte, jamais a chaque lot de la mutation.
            allocatable = id(row) in priced and surface is not None
            properties.append(
                (
                    f"transaction-property:dvf:{release_id}:{mutation_id}:{index}",
                    f"transaction:dvf:{release_id}:v{DVF_TRANSFORMATION_VERSION}:{mutation_id}",
                    f"v{DVF_TRANSFORMATION_VERSION}:{mutation_id}:{index}",
                    row["id_parcelle"] or None,
                    row["type_local"] or LAND_PROPERTY_TYPE,
                    surface,
                    mutation.price if allocatable else None,
                    SIMPLE_ALLOCATION if allocatable else None,
                    json.dumps(
                        {
                            "type_local": row["type_local"] or None,
                            "nature_culture": row.get("nature_culture") or None,
                            "surface_terrain": row.get("surface_terrain") or None,
                            "surface_reelle_bati": row.get("surface_reelle_bati") or None,
                            "nombre_pieces_principales": row.get("nombre_pieces_principales")
                            or None,
                        }
                    ),
                )
            )
            if allocatable:
                counters["properties_with_price"] += 1
            counters["properties"] += 1

    cursor = connection.cursor()
    cursor.executemany(
        """
        INSERT INTO observation.transaction (
            id, release_id, raw_asset_id, source_identifier, mutation_date, mutation_nature,
            price_eur, is_complex, complex_reason, commune_code, department_code, properties
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (release_id, source_identifier) DO NOTHING
        """,
        transactions,
    )
    cursor.executemany(
        """
        -- `id` est une identite generee : ne pas la fournir. L'unicite metier est
        -- (transaction_id, source_identifier), et c'est elle qui porte l'idempotence.
        INSERT INTO observation.transaction_property (
            transaction_id, source_identifier, parcel_id, property_type, surface_m2,
            allocated_price_eur, allocation_method, properties
        )
        SELECT %s, %s, parcel.id, %s, %s, %s, %s, %s::jsonb
          FROM (SELECT 1) AS anchor
          LEFT JOIN reference.parcel AS parcel ON parcel.cadastral_id = %s
        ON CONFLICT (transaction_id, source_identifier) DO NOTHING
        """,
        [(row[1], row[2], row[4], row[5], row[6], row[7], row[8], row[3]) for row in properties],
    )
    return dict(counters)
