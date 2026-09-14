#!/usr/bin/env python3
"""Archiver et importer une release geo-dvf départementale — D1, DS-06.

Le moteur de comparables est livré et testé sur fixtures ; ce script lui apporte la donnée
réelle.

## Qualifier les mutations complexes est notre travail, pas celui de la source

DVF+ du Cerema pré-qualifie les mutations ; `geo-dvf` ne le fait pas, et le contrat DS-06 a été
amendé en disant pourquoi — DVF+ n'est distribué que par un dossier Box authentifié, donc ni
archivable ni checksumable.

La conséquence est que la règle vit ici, sous test, plutôt que dans une boîte noire. Une
mutation dont le prix n'est pas allouable à un bien **ne doit jamais** produire un prix au m².
`geo-dvf` répète la `valeur_fonciere` à l'identique sur chaque ligne d'une même mutation :
diviser ce montant par la surface d'un seul lot fabriquerait un prix faux et crédible.

Trois situations rendent un prix non allouable, et chacune porte son motif :

| Motif | Situation |
|---|---|
| `multiple_parcels` | la mutation porte sur plusieurs parcelles |
| `multiple_local_types` | elle mêle plusieurs types de local |
| `price_missing` | la valeur foncière est absente |

C'est la quarantaine par attribut de BUG-03 appliquée ici : la transaction est **conservée**,
c'est son prix unitaire qui devient inutilisable, avec la raison écrite.

## Idempotence

La clé d'idempotence et l'identifiant de run portent la version de transformation. Sans elle, un
correctif de code n'atteindrait jamais les données — constaté sur BUG-09.
"""

import argparse
import csv
import gzip
import json
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import load_release_manifest, resolve_asset
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.progress import Progress

# 1 : premier import geo-dvf, qualification des mutations complexes dans ce script.
# 2 : le prix ne va plus qu au lot auquel il se rapporte. En version 1, une vente de
# maison avec terrain donnait le montant entier a chacun des deux lots — 5 410
# mutations et 13 303 lots concernes sur le 35, soit 8,3 % des mutations simples.
# 3 : la surface d'un lot bati ne peut plus emprunter celle du terrain.
DVF_TRANSFORMATION_VERSION = "3"

# La version entre dans l'identifiant de chaque ligne, et pas seulement dans une constante. Sans
# cela, `ON CONFLICT DO NOTHING` conserve les lignes de la version precedente et un correctif de
# code n'atteint jamais les donnees : c'est exactement ce qui s'est produit sur BUG-09, ou la
# regle du rang etait ecrite, testee, et 1 240 355 relations fautives restaient en base.

SIMPLE_ALLOCATION = "single_property_full_price"

# Une ligne sans `type_local` n'est pas une ligne dont le type manque : c'est un lot de terrain.
# `geo-dvf` decrit le bati par `type_local` et le non-bati par `nature_culture` et
# `surface_terrain`. Nommer ce cas plutot que d'ecrire NULL dit ce que la source dit.
LAND_PROPERTY_TYPE = "Terrain"


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
        """Les lots auxquels le prix peut se rapporter.

        Une vente de maison comporte le lot bâti **et** ses lots de terrain. Le prix au m² d'une
        maison se rapporte par convention à la surface bâtie, le terrain venant avec : les lots
        de terrain d'une vente bâtie ne reçoivent donc pas de prix, ils ne sont pas ignorés pour
        autant — ils restent enregistrés avec leur surface et leur nature de culture.

        S'il n'y a aucun lot bâti, la mutation est une vente de terrain et le prix se rapporte
        au terrain.
        """
        built = [row for row in self.rows if row["type_local"]]
        return built if built else [row for row in self.rows if _surface(row) is not None]

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

        priced = {id(row) for row in mutation.priced_lots()} if reason is None else set()
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive and import one geo-dvf department release"
    )
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--year", default=None, help="limiter à un millésime, pour vérifier")
    arguments = parser.parse_args()

    manifest = load_release_manifest("DS-06", arguments.release, arguments.department)
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    totals: dict[str, int] = defaultdict(int)

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        catalog = DatasetCatalog(connection)
        catalog.register_release(
            release_id=manifest.release_id,
            release_key=manifest.release_key,
            published_on=date.fromisoformat(manifest.source_published_on),
            schema_fingerprint="ds-06-geo-dvf-v1",
            department_code=manifest.department,
            data_source_id="DS-06",
            source_srid=4326,
        )
        connection.execute("SET ROLE pipeline_rw")
        with tempfile.TemporaryDirectory(prefix="immo-dvf-") as temporary:
            wanted = [
                asset
                for asset in manifest.assets
                if not arguments.year or asset.layer.removeprefix("mutations-") == arguments.year
            ]
            progress = Progress(len(wanted), "DS-06")
            for asset in wanted:
                year = asset.layer.removeprefix("mutations-")
                destination = Path(temporary) / f"{year}.csv.gz"
                # `resolve_asset` verifie l'empreinte, quel que soit le chemin emprunte :
                # archive en base, copie nommee au manifeste, ou amont. Un fichier qui aurait
                # change fait echouer l'import ici, avant toute ecriture.
                resolved = resolve_asset(
                    catalog=catalog,
                    object_store=object_store,
                    manifest=manifest,
                    asset=asset,
                    destination=destination,
                )
                counters = import_year(
                    connection,
                    release_id=manifest.release_id,
                    raw_asset_id=resolved.raw_asset_id,
                    department=manifest.department,
                    path=destination,
                )
                connection.commit()
                for key, value in counters.items():
                    totals[key] += value
                progress.advance(detail=f"{totals['mutations']} mutations")
                print(
                    f"{year} ({resolved.origin}) : {counters['mutations']} mutations, "
                    f"{counters['properties']} biens",
                    flush=True,
                )

    print(json.dumps(dict(sorted(totals.items())), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
