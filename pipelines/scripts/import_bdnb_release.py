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
from immo_pipelines.spatial.bdnb import BDNB_TRANSFORMATION_VERSION
from immo_pipelines.spatial.importer import BdnbImporter


def contract_fingerprint() -> str:
    path = project_root() / "contracts" / "datasets" / "DS-03" / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_zip_member(archive_path: Path, member_path: str, destination_dir: Path) -> Path:
    import zipfile

    with zipfile.ZipFile(archive_path) as archive:
        if member_path not in archive.namelist():
            raise RuntimeError(f"Archive has no member {member_path}")
        archive.extract(member_path, path=destination_dir)
    extracted = destination_dir / member_path
    if not extracted.is_file():
        raise RuntimeError(f"Extraction produced no file at {extracted}")
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive and import one BDNB department release")
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    manifest = load_release_manifest("DS-03", arguments.release, arguments.department)
    asset = manifest.asset("bdnb")
    if asset.member_path is None:
        raise RuntimeError("DS-03 manifest must name the GeoPackage member inside the archive")
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
            data_source_id="DS-03",
            source_srid=2154,
        )
        with tempfile.TemporaryDirectory(prefix="immo-bdnb-") as temporary_directory:
            working = Path(temporary_directory)
            archive_path = working / "bdnb.zip"
            resolved = resolve_asset(
                catalog=catalog,
                object_store=object_store,
                manifest=manifest,
                asset=asset,
                destination=archive_path,
            )
            geopackage = extract_zip_member(archive_path, asset.member_path, working)
            # L'archive de 805 Mo n'a plus d'utilite une fois le GeoPackage de 2,7 Go extrait.
            archive_path.unlink(missing_ok=True)

            importer = BdnbImporter(connection)
            outcome = importer.import_archive(
                import_run_id=(
                    f"bdnb:{manifest.release_key}:{manifest.department}"
                    f":{BDNB_TRANSFORMATION_VERSION}"
                ),
                release_id=manifest.release_id,
                department_code=manifest.department,
                raw_asset_id=resolved.raw_asset_id,
                source_path=geopackage,
                idempotency_key=(
                    f"{manifest.release_id}:{manifest.department}:bdnb:"
                    f"{resolved.sha256}:{BDNB_TRANSFORMATION_VERSION}"
                ),
            )
            importer.refresh_match_metrics(manifest.release_id, manifest.department)
            report = importer.report(manifest.release_id)
    print(
        json.dumps(
            {**asdict(outcome), "asset_origin": resolved.origin, "report": report},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
