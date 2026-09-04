import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, cast

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore, archive_asset, download_asset
from immo_pipelines.cadastre.catalog import DatasetCatalog, RawAssetRegistration
from immo_pipelines.cadastre.contract import sha256_file
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.ban import BAN_TRANSFORMATION_VERSION
from immo_pipelines.spatial.importer import BanImporter


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def contract_fingerprint() -> str:
    path = project_root() / "contracts" / "datasets" / "DS-05" / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive and import one BAN department release")
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()
    manifest_path = (
        project_root()
        / "contracts"
        / "datasets"
        / "DS-05"
        / "releases"
        / f"{arguments.release}-{arguments.department}.json"
    )
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    asset = cast(dict[str, Any], cast(list[object], manifest["assets"])[0])
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    release_id = str(manifest["release_id"])
    source_url = str(asset["url"])
    expected_sha = str(asset["sha256"])

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        catalog = DatasetCatalog(connection)
        catalog.register_release(
            release_id=release_id,
            release_key=str(manifest["release_key"]),
            published_on=date.fromisoformat(str(manifest["source_published_on"])),
            schema_fingerprint=contract_fingerprint(),
            department_code=arguments.department,
            data_source_id="DS-05",
            source_srid=2154,
        )
        archived = catalog.find_raw_asset(
            release_id=release_id,
            layer="addresses",
            territory_code=arguments.department,
            source_url=source_url,
        )
        with tempfile.TemporaryDirectory(prefix="immo-ban-") as temporary_directory:
            local_path = Path(temporary_directory) / "addresses.csv.gz"
            if archived is None:
                actual_sha = download_asset(source_url, local_path, expected_sha, prefer_curl=True)
                object_key = (
                    f"DS-05/{arguments.release}/department/{arguments.department}/addresses.csv.gz"
                )
                etag = archive_asset(
                    object_store,
                    local_path,
                    object_key=object_key,
                    sha256=actual_sha,
                    source_url=source_url,
                    release_id=release_id,
                    content_type="application/gzip",
                )
                raw_asset_id = catalog.register_raw_asset(
                    RawAssetRegistration(
                        release_id=release_id,
                        layer="addresses",
                        territory_code=arguments.department,
                        source_url=source_url,
                        object_key=object_key,
                        byte_size=local_path.stat().st_size,
                        sha256=actual_sha,
                        etag=etag,
                        media_type="text/csv",
                        content_encoding="gzip",
                    )
                )
            else:
                object_store.get_file(archived.object_key, local_path)
                if sha256_file(local_path) != archived.sha256:
                    raise RuntimeError("Archived BAN asset checksum mismatch")
                raw_asset_id = archived.id
                actual_sha = archived.sha256

            importer = BanImporter(connection)
            outcome = importer.import_archive(
                # Deux transformations differentes sont deux imports differents :
                # partager l'identifiant de run les rendrait indiscernables et ferait
                # collisionner la cle primaire de meta.import_run au reimport.
                import_run_id=(
                    f"ban:{arguments.release}:{arguments.department}:{BAN_TRANSFORMATION_VERSION}"
                ),
                release_id=release_id,
                department_code=arguments.department,
                raw_asset_id=raw_asset_id,
                source_path=local_path,
                idempotency_key=(
                    f"{release_id}:{arguments.department}:addresses:"
                    f"{actual_sha}:{BAN_TRANSFORMATION_VERSION}"
                ),
            )
            importer.refresh_match_metrics(release_id, arguments.department)
    print(json.dumps(asdict(outcome), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
