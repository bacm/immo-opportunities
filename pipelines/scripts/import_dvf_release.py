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
import hashlib
import json
import sys
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import load_release_manifest, resolve_asset
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.dvf import (
    DVF_TRANSFORMATION_VERSION,
    import_year,
)
from immo_pipelines.market_data.dvf_archive import convert
from immo_pipelines.progress import Progress


# 1 : premier import geo-dvf, qualification des mutations complexes dans ce script.
# 2 : le prix ne va plus qu au lot auquel il se rapporte. En version 1, une vente de
# maison avec terrain donnait le montant entier a chacun des deux lots — 5 410
# mutations et 13 303 lots concernes sur le 35, soit 8,3 % des mutations simples.
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
            schema_fingerprint=(
                "ds-06-dgfip-raw-v1"
                if any(a.layer.startswith("mutations-raw-") for a in manifest.assets)
                else "ds-06-geo-dvf-v1"
            ),
            department_code=manifest.department,
            data_source_id="DS-06",
            source_srid=4326,
        )
        connection.execute("SET ROLE pipeline_rw")
        # L'empreinte porte sur les **cinq millesimes** epingles, et non sur un seul : c'est
        # l'ensemble qui fait la release.
        assets_digest = hashlib.sha256(
            "".join(sorted(asset.sha256 or "" for asset in manifest.assets)).encode()
        ).hexdigest()
        idempotency_key = (
            f"{manifest.release_id}:{manifest.department}:mutations:"
            f"{assets_digest}:{DVF_TRANSFORMATION_VERSION}"
        )
        import_run_id = (
            f"dvf:{manifest.release_key}:{manifest.department}:{DVF_TRANSFORMATION_VERSION}"
        )
        existing = connection.execute(
            "SELECT id, status FROM meta.import_run WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
        if existing is not None and existing[1] == "succeeded" and not arguments.year:
            print(f"déjà importé par {existing[0]}, rien à faire")
            return 0
        if existing is not None:
            connection.execute("DELETE FROM meta.import_run WHERE id = %s", (existing[0],))
        connection.execute(
            """
            INSERT INTO meta.import_run (
                id, release_id, territory_type, territory_code, idempotency_key,
                status, runner_metadata
            ) VALUES (%s, %s, 'department', %s, %s, 'running',
                      jsonb_build_object('layer', 'mutations', 'years', %s::int))
            """,
            (
                import_run_id,
                manifest.release_id,
                manifest.department,
                idempotency_key,
                len(manifest.assets),
            ),
        )
        # Purger les versions de transformation precedentes de cette release.
        #
        # Les avoir laissees coexister etait une erreur : la comparaison entre deux versions se
        # fait une fois, et le doublon reste ensuite. L'ecran de verification de D6a l'a montre
        # aussitot — quatre lignes pour deux mutations, une par version.
        #
        # La version vit dans l'identifiant precisement pour qu'un correctif atteigne les
        # donnees ; elle ne doit pas pour autant faire s'accumuler les etats successifs.
        connection.execute(
            """
            DELETE FROM observation.transaction
             WHERE release_id = %(release_id)s
               AND source_identifier NOT LIKE %(prefix)s
            """,
            {
                "release_id": manifest.release_id,
                "prefix": f"v{DVF_TRANSFORMATION_VERSION}:%",
            },
        )
        connection.commit()
        with tempfile.TemporaryDirectory(prefix="immo-dvf-") as temporary:
            wanted = [
                asset
                for asset in manifest.assets
                if not arguments.year
                or asset.layer.removeprefix("mutations-raw-").removeprefix("mutations-")
                == arguments.year
            ]
            progress = Progress(len(wanted), "DS-06")
            for asset in wanted:
                # Une release archivée porte le format DGFiP brut : fichier national, séparateur
                # « | », sans identifiant de parcelle ni de mutation. Le marqueur est le nom de
                # couche, pour ne pas faire dépendre le manifeste d'un champ de plus.
                raw = asset.layer.startswith("mutations-raw-")
                year = asset.layer.removeprefix("mutations-raw-").removeprefix("mutations-")
                destination = Path(temporary) / (f"{year}.txt" if raw else f"{year}.csv.gz")
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
                if raw:
                    # La conversion écrit la forme que `import_year` consomme déjà : la règle
                    # métier ne doit rien savoir du format d'entrée.
                    converted = Path(temporary) / f"{year}.csv.gz"
                    conversion = convert(destination, converted, manifest.department)
                    print(
                        f"{year} : {conversion['lines']} lignes converties, "
                        f"{conversion['without_parcel']} sans parcelle, "
                        f"{conversion['without_date']} sans date",
                        flush=True,
                    )
                    destination.unlink()
                    destination = converted
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

        connection.execute(
            """
            UPDATE meta.import_run SET
                status = 'succeeded', completed_at = now(),
                source_row_count = %(mutations)s, normalized_row_count = %(properties)s,
                quarantined_row_count = %(complex)s,
                runner_metadata = runner_metadata || %(detail)s::jsonb
             WHERE id = %(id)s
            """,
            {
                "id": import_run_id,
                "mutations": totals["mutations"],
                "properties": totals["properties"],
                # Une mutation dont le prix n'est pas allouable n'est pas rejetee : elle est
                # conservee avec son motif. Le compte est celui des prix inutilisables, pas des
                # transactions perdues.
                "complex": totals["mutations"] - totals.get("reason_allocatable", 0),
                "detail": json.dumps(dict(totals), sort_keys=True),
            },
        )
        connection.commit()

    print(json.dumps(dict(sorted(totals.items())), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
