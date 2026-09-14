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

# 1 : premier import geo-dvf, qualification des mutations complexes dans ce script.
DVF_TRANSFORMATION_VERSION = "1"

SIMPLE_ALLOCATION = "single_property_full_price"

# Une ligne sans `type_local` n'est pas une ligne dont le type manque : c'est un lot de terrain.
# `geo-dvf` decrit le bati par `type_local` et le non-bati par `nature_culture` et
# `surface_terrain`. Nommer ce cas plutot que d'ecrire NULL dit ce que la source dit.
LAND_PROPERTY_TYPE = "Terrain"


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
        if len(self.local_types) > 1:
            return "multiple_local_types"
        return None


def read_mutations(path: Path) -> dict[str, Mutation]:
    """Regrouper les lignes par mutation. Une ligne = un lot, une mutation = un acte."""
    mutations: dict[str, Mutation] = defaultdict(lambda: Mutation(rows=[]))
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mutations[row["id_mutation"]].rows.append(row)
    return dict(mutations)


def _surface(row: dict[str, str]) -> float | None:
    """La surface du lot : bâtie si le lot est un local, foncière sinon.

    Une surface absente reste absente. La contrainte de schéma refuse une surface nulle ou
    négative, ce qui est la bonne garde : une surface de zéro n'est pas une surface.
    """
    for column in ("surface_reelle_bati", "surface_terrain"):
        raw = row.get(column) or ""
        if raw:
            value = float(raw)
            if value > 0:
                return value
    return None


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
                f"transaction:dvf:{release_id}:{mutation_id}",
                release_id,
                raw_asset_id,
                mutation_id,
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

        for index, row in enumerate(mutation.rows):
            surface = _surface(row)
            allocatable = reason is None and surface is not None
            properties.append(
                (
                    f"transaction-property:dvf:{release_id}:{mutation_id}:{index}",
                    f"transaction:dvf:{release_id}:{mutation_id}",
                    f"{mutation_id}:{index}",
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
        [
            (row[1], row[2], row[4], row[5], row[6], row[7], row[8], row[3])
            for row in properties
        ],
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
            for asset in manifest.assets:
                year = asset.layer.removeprefix("mutations-")
                if arguments.year and year != arguments.year:
                    continue
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
                print(
                    f"{year} ({resolved.origin}) : {counters['mutations']} mutations, "
                    f"{counters['properties']} biens",
                    flush=True,
                )

    print(json.dumps(dict(sorted(totals.items())), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
