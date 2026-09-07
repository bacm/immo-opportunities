# pyright: reportUnknownMemberType=false
import hashlib
import shutil
import subprocess
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from immo_pipelines.cadastre.contract import (
    ChecksumMismatchError,
    SchemaChangeError,
    sha256_file,
)


class ArchivedObjectMissingError(RuntimeError):
    """L'objet n'est pas (ou pas encore) dans l'object store.

    Distinct d'une panne d'acces : c'est le cas normal d'une cle d'archive nommee par un
    manifeste avant le premier archivage.
    """


class ObjectStore(Protocol):
    def put_file(self, source: Path, object_key: str, metadata: Mapping[str, str]) -> str: ...


class MinioObjectStore:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        *,
        secure: bool = False,
        bucket: str = "raw-sources",
    ) -> None:
        minio_class = import_module("minio").Minio
        self._client: Any = minio_class(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )
        self._bucket = bucket

    def put_file(self, source: Path, object_key: str, metadata: Mapping[str, str]) -> str:
        content_type = metadata.get("content-type", "application/geo+json")
        object_metadata = {key: value for key, value in metadata.items() if key != "content-type"}
        result = self._client.fput_object(
            self._bucket,
            object_key,
            str(source),
            metadata=object_metadata,
            content_type=content_type,
        )
        return str(result.etag)

    def get_file(self, object_key: str, destination: Path) -> None:
        s3_error: Any = import_module("minio.error").S3Error
        try:
            self._client.fget_object(self._bucket, object_key, str(destination))
        except s3_error as exc:
            # Ne traduire que l'absence : une erreur d'acces ou de configuration doit
            # remonter telle quelle, jamais etre confondue avec « pas encore archive ».
            if getattr(exc, "code", None) in {"NoSuchKey", "NoSuchBucket"}:
                raise ArchivedObjectMissingError(object_key) from exc
            raise


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _download_asset_httpx(
    source_url: str, destination: Path, expected_sha256: str | None = None
) -> str:
    digest = hashlib.sha256()
    headers = {
        "Accept": "application/octet-stream,*/*",
        "User-Agent": "ImmoOpportunitiesDataPipeline/0.1 (+https://github.com/)",
    }
    with httpx.stream(
        "GET", source_url, headers=headers, follow_redirects=True, timeout=120
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as target:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                digest.update(chunk)
                target.write(chunk)
    actual = digest.hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        destination.unlink(missing_ok=True)
        raise ChecksumMismatchError(f"Expected sha256 {expected_sha256}, got {actual}")
    return actual


def _download_asset_curl(source_url: str, destination: Path, expected_sha256: str | None) -> str:
    curl = shutil.which("curl")
    if curl is None:
        raise RuntimeError("curl fallback is not installed")
    destination.unlink(missing_ok=True)
    try:
        subprocess.run(
            [
                curl,
                "--fail",
                "--location",
                "--retry",
                "3",
                "--silent",
                "--show-error",
                "--output",
                str(destination),
                source_url,
            ],
            check=True,
            timeout=600,
        )
    except (subprocess.SubprocessError, OSError):
        destination.unlink(missing_ok=True)
        raise
    actual = sha256_file(destination)
    if expected_sha256 is not None and actual != expected_sha256:
        destination.unlink(missing_ok=True)
        raise ChecksumMismatchError(f"Expected sha256 {expected_sha256}, got {actual}")
    return actual


def download_asset(
    source_url: str,
    destination: Path,
    expected_sha256: str | None = None,
    *,
    prefer_curl: bool = False,
) -> str:
    if prefer_curl:
        return _download_asset_curl(source_url, destination, expected_sha256)
    try:
        return _download_asset_httpx(source_url, destination, expected_sha256)
    except (httpx.TransportError, httpx.HTTPStatusError):
        return _download_asset_curl(source_url, destination, expected_sha256)


def extract_seven_zip_member(archive_path: Path, member_path: str, destination_dir: Path) -> Path:
    """Extraire un membre nomme d'une archive `7z` et renvoyer son chemin.

    DS-04 est la seule source distribuee en `7z`, et son GeoPackage de 3,1 Go doit atterrir
    sur disque : `sqlite3` a besoin d'un fichier reel, pas d'un flux. Le membre est celui que
    le manifeste epingle (`member_path`), jamais devine dans l'archive.
    """
    seven_zip_file: Any = import_module("py7zr").SevenZipFile
    with seven_zip_file(archive_path, "r") as archive:
        names = cast(list[str], archive.getnames())
        if member_path not in names:
            raise SchemaChangeError(f"Archive {archive_path.name} has no member {member_path}")
        archive.extract(path=str(destination_dir), targets=[member_path])
    extracted = destination_dir / member_path
    if not extracted.is_file():
        raise RuntimeError(f"Extraction produced no file at {extracted}")
    return extracted


def archive_asset(
    object_store: ObjectStore,
    local_path: Path,
    *,
    object_key: str,
    sha256: str,
    source_url: str,
    release_id: str,
    content_type: str = "application/geo+json",
) -> str:
    return object_store.put_file(
        local_path,
        object_key,
        {
            "sha256": sha256,
            "source-url": source_url,
            "release-id": release_id,
            "immutable": "true",
            "content-type": content_type,
        },
    )
