import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore, extract_seven_zip_member
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import (
    load_release_manifest,
    project_root,
    resolve_asset,
)
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.bdtopo import BDTOPO_TRANSFORMATION_VERSION
from immo_pipelines.spatial.importer import BdtopoImporter


def contract_fingerprint() -> str:
    path = project_root() / "contracts" / "datasets" / "DS-04" / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive and import one BD TOPO department release"
    )
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    manifest = load_release_manifest("DS-04", arguments.release, arguments.department)
    asset = manifest.asset("bdtopo")
    if asset.member_path is None:
        raise RuntimeError("DS-04 manifest must name the GeoPackage member inside the archive")
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
            data_source_id="DS-04",
            source_srid=2154,
        )
        with tempfile.TemporaryDirectory(prefix="immo-bdtopo-") as temporary_directory:
            working = Path(temporary_directory)
            archive_path = working / "bdtopo.7z"
            resolved = resolve_asset(
                catalog=catalog,
                object_store=object_store,
                manifest=manifest,
                asset=asset,
                destination=archive_path,
            )
            geopackage = extract_seven_zip_member(archive_path, asset.member_path, working)
            # L'archive de 529 Mo n'a plus d'utilite une fois le GeoPackage de 3,1 Go extrait,
            # et les deux ensemble saturent inutilement le disque du conteneur.
            archive_path.unlink(missing_ok=True)

            importer = BdtopoImporter(connection)
            outcome = importer.import_archive(
                import_run_id=(
                    f"bdtopo:{manifest.release_key}:{manifest.department}"
                    f":{BDTOPO_TRANSFORMATION_VERSION}"
                ),
                release_id=manifest.release_id,
                department_code=manifest.department,
                raw_asset_id=resolved.raw_asset_id,
                source_path=geopackage,
                idempotency_key=(
                    f"{manifest.release_id}:{manifest.department}:bdtopo:"
                    f"{resolved.sha256}:{BDTOPO_TRANSFORMATION_VERSION}"
                ),
            )
            importer.refresh_match_metrics(manifest.release_id, manifest.department)
            rates = importer.method_rates(manifest.release_id)
    print(
        json.dumps(
            {**asdict(outcome), "asset_origin": resolved.origin, "match_rates": rates},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
