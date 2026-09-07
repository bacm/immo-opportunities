import hashlib
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

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.contract import SchemaChangeError, load_contract
from immo_pipelines.cadastre.importer import CadastreImporter
from immo_pipelines.cadastre.manifest import (
    load_release_manifest,
    require_reproducible,
    resolve_asset,
)
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
    manifest = load_release_manifest("DS-01", release_key, department_code)
    release_id = manifest.release_id
    # Refuser avant tout telechargement un asset qu'on ne saurait pas retrouver. DS-01
    # portait `"sha256": null` sur ses trois couches : le reimport telechargeait donc des
    # octets qu'aucun checksum ne contraignait. Voir BUG-05.
    for manifest_asset in manifest.assets:
        require_reproducible(release_id, manifest_asset)
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
            published_on=date.fromisoformat(manifest.source_published_on),
            schema_fingerprint=contract.schema_fingerprint(),
            department_code=department_code,
        )
        importer = CadastreImporter(connection, processor)
        with tempfile.TemporaryDirectory(prefix="immo-cadastre-") as temp_directory:
            temporary_root = Path(temp_directory)
            for manifest_asset in manifest.assets:
                layer = manifest_asset.layer
                local_path = temporary_root / f"{layer}.json.gz"
                resolved = resolve_asset(
                    catalog=catalog,
                    object_store=object_store,
                    manifest=manifest,
                    asset=manifest_asset,
                    destination=local_path,
                )
                context.log.info("Resolved %s from %s", layer, resolved.origin)
                checksum = resolved.sha256
                raw_asset_id = resolved.raw_asset_id
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
