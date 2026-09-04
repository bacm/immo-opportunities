import hashlib
import json
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import psycopg
from dagster import (
    AssetExecutionContext,
    DynamicPartitionsDefinition,
    MaterializeResult,
    MetadataValue,
    MultiPartitionKey,
    MultiPartitionsDefinition,
    StaticPartitionsDefinition,
    asset,
)

from immo_pipelines.cadastre.archive import (
    MinioObjectStore,
    archive_asset,
    download_asset,
)
from immo_pipelines.cadastre.catalog import DatasetCatalog, RawAssetRegistration
from immo_pipelines.cadastre.contract import SchemaChangeError, load_contract, sha256_file
from immo_pipelines.cadastre.importer import CadastreImporter
from immo_pipelines.cadastre.processor import CadastreFeatureProcessor
from immo_pipelines.cadastre.settings import CadastreSettings

cadastre_release_partitions = DynamicPartitionsDefinition(name="cadastre_releases")
cadastre_department_partitions = StaticPartitionsDefinition(["22", "29", "35", "56"])
cadastre_partitions = MultiPartitionsDefinition(
    {
        "department": cadastre_department_partitions,
        "release": cadastre_release_partitions,
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _partition(context: AssetExecutionContext) -> tuple[str, str]:
    key = context.partition_key
    if not isinstance(key, MultiPartitionKey):
        raise TypeError("Cadastre assets require release x department partitions")
    return key.keys_by_dimension["release"], key.keys_by_dimension["department"]


def _json_compatible(value: object) -> object:
    """Convert PostgreSQL-native scalar values at the Dagster metadata boundary."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return {str(key): _json_compatible(item) for key, item in mapping.items()}
    if isinstance(value, (list, tuple)):
        items = cast(list[object] | tuple[object, ...], value)
        return [_json_compatible(item) for item in items]
    return value


@asset(
    group_name="cadastre",
    partitions_def=cadastre_partitions,
    description="Archive and normalize one immutable DS-01 release x department partition.",
)
def cadastre_department_release(context: AssetExecutionContext) -> MaterializeResult[Any]:
    release_key, department_code = _partition(context)
    manifest_path = (
        _project_root()
        / "contracts"
        / "datasets"
        / "DS-01"
        / "releases"
        / f"{release_key}-{department_code}.json"
    )
    manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = cast(dict[str, Any], manifest_value)
    release_id = str(manifest["release_id"])
    contract = load_contract()
    processor = CadastreFeatureProcessor(contract)
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
    )

    outcomes: dict[str, dict[str, int | bool]] = {}
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
            release_key=release_key,
            published_on=date.fromisoformat(str(manifest["source_published_on"])),
            schema_fingerprint=contract.schema_fingerprint(),
            department_code=department_code,
        )
        importer = CadastreImporter(connection, processor)
        with tempfile.TemporaryDirectory(prefix="immo-cadastre-") as temp_directory:
            temporary_root = Path(temp_directory)
            for asset_manifest_value in cast(list[dict[str, Any]], manifest["assets"]):
                layer = str(asset_manifest_value["layer"])
                source_url = str(asset_manifest_value["url"])
                expected_checksum_value = asset_manifest_value.get("sha256")
                expected_checksum = (
                    str(expected_checksum_value) if expected_checksum_value is not None else None
                )
                local_path = temporary_root / f"{layer}.json.gz"
                archived_asset = catalog.find_raw_asset(
                    release_id=release_id,
                    layer=layer,
                    territory_code=department_code,
                    source_url=source_url,
                )
                if archived_asset is not None:
                    context.log.info(
                        "Restoring %s from immutable archive %s",
                        layer,
                        archived_asset.object_key,
                    )
                    object_store.get_file(archived_asset.object_key, local_path)
                    checksum = sha256_file(local_path, archived_asset.sha256)
                    raw_asset_id = archived_asset.id
                else:
                    checksum = download_asset(source_url, local_path, expected_checksum)
                    object_key = (
                        f"DS-01/{release_key}/department/{department_code}/"
                        f"{layer}/{checksum}.json.gz"
                    )
                    etag = archive_asset(
                        object_store,
                        local_path,
                        object_key=object_key,
                        sha256=checksum,
                        source_url=source_url,
                        release_id=release_id,
                    )
                    raw_asset_id = catalog.register_raw_asset(
                        RawAssetRegistration(
                            release_id=release_id,
                            layer=layer,
                            territory_code=department_code,
                            source_url=source_url,
                            object_key=object_key,
                            byte_size=local_path.stat().st_size,
                            sha256=checksum,
                            etag=etag,
                        )
                    )
                catalog.record_asset_check(
                    release_id=release_id,
                    department_code=department_code,
                    layer=layer,
                    check_code="checksum",
                    valid=True,
                    details={"sha256": checksum},
                )
                key_material = f"{release_id}:{department_code}:{layer}:{checksum}"
                run_suffix = hashlib.sha256(key_material.encode()).hexdigest()[:20]
                try:
                    outcome = importer.import_file(
                        import_run_id=f"cadastre:{run_suffix}",
                        release_id=release_id,
                        department_code=department_code,
                        layer=layer,
                        raw_asset_id=raw_asset_id,
                        source_path=local_path,
                        idempotency_key=key_material,
                    )
                except SchemaChangeError as exc:
                    catalog.record_asset_check(
                        release_id=release_id,
                        department_code=department_code,
                        layer=layer,
                        check_code="schema",
                        valid=False,
                        details={
                            "schema_fingerprint": contract.schema_fingerprint(),
                            "error": str(exc),
                        },
                    )
                    raise
                catalog.record_asset_check(
                    release_id=release_id,
                    department_code=department_code,
                    layer=layer,
                    check_code="schema",
                    valid=True,
                    details={"schema_fingerprint": contract.schema_fingerprint()},
                )
                outcomes[layer] = {
                    "source": outcome.source_rows,
                    "normalized": outcome.normalized_rows,
                    "quarantined": outcome.quarantined_rows,
                    "deduplicated": outcome.deduplicated_rows,
                    "idempotent_skip": outcome.skipped_as_idempotent,
                }
        catalog.refresh_commune_quality(release_id, department_code)
        report = catalog.quality_report(release_id)

    return MaterializeResult(
        metadata={
            "release_id": release_id,
            "department": department_code,
            "layers": MetadataValue.json(outcomes),
            "quality_report": MetadataValue.json(cast(dict[str, Any], _json_compatible(report))),
            "publication": "pending explicit acceptance",
        }
    )
