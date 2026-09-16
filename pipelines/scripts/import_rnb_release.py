"""Archiver et importer une release départementale RNB — entrée en ligne de commande.

La logique vit dans `immo_pipelines.spatial.release_import`, partagée avec l'asset Dagster
`ds02_rnb_release` (BUG-02).
"""

import argparse
import json
from dataclasses import asdict

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.release_import import RNB, import_department_release


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive and import one RNB department release")
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        result = import_department_release(
            RNB,
            arguments.release,
            arguments.department,
            connection=connection,
            object_store=object_store,
        )
    print(
        json.dumps({**asdict(result.outcome), "asset_origin": result.asset_origin}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
