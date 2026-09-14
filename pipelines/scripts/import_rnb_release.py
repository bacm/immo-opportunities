import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import (
    load_release_manifest,
    project_root,
    resolve_asset,
)
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.importer import RnbImporter


def contract_fingerprint() -> str:
    path = project_root() / "contracts" / "datasets" / "DS-02" / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Version de la transformation, incluse dans la cle d'idempotence.
#
# Sans elle, une release deja importee est rejouee a vide : le garde d'idempotence voit un
# `import_run` reussi pour la meme cle et retourne sans rien faire. Un correctif de code ne
# peut alors jamais atteindre les donnees, ce qui s'est produit avec BUG-09 — la regle du rang
# etait ecrite, testee, et les 1 240 355 relations fautives restaient en base.
#
# Le script BD TOPO le faisait deja ; celui-ci l'avait oublie.
#
# 2 : BUG-09, la relation batiment <-> parcelle cesse d'etre certaine par defaut.
RNB_TRANSFORMATION_VERSION = "2"


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive and import one RNB department release")
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    manifest = load_release_manifest("DS-02", arguments.release, arguments.department)
    asset = manifest.asset("buildings")
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
        catalog = DatasetCatalog(connection)
        catalog.register_release(
            release_id=manifest.release_id,
            release_key=manifest.release_key,
            published_on=date.fromisoformat(manifest.source_published_on),
            schema_fingerprint=contract_fingerprint(),
            department_code=manifest.department,
            data_source_id="DS-02",
            source_srid=4326,
        )
        with tempfile.TemporaryDirectory(prefix="immo-rnb-") as temporary_directory:
            local_path = Path(temporary_directory) / "rnb.csv.zip"
            resolved = resolve_asset(
                catalog=catalog,
                object_store=object_store,
                manifest=manifest,
                asset=asset,
                destination=local_path,
            )
            importer = RnbImporter(connection)
            outcome = importer.import_archive(
                # La version entre aussi dans l'identifiant du run, et pas seulement dans la
                # cle d'idempotence : sans cela la nouvelle cle cree bien un run, qui entre
                # aussitot en collision de cle primaire avec l'ancien. BD TOPO le faisait deja.
                import_run_id=(
                    f"rnb:{manifest.release_key}:{manifest.department}:{RNB_TRANSFORMATION_VERSION}"
                ),
                release_id=manifest.release_id,
                department_code=manifest.department,
                raw_asset_id=resolved.raw_asset_id,
                source_path=local_path,
                idempotency_key=(
                    f"{manifest.release_id}:{manifest.department}:buildings:"
                    f"{resolved.sha256}:{RNB_TRANSFORMATION_VERSION}"
                ),
            )
            importer.refresh_match_metrics(manifest.release_id, manifest.department)
    print(json.dumps({**asdict(outcome), "asset_origin": resolved.origin}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
