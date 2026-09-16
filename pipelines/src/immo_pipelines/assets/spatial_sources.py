"""RNB et BAN dans le graphe d'assets, partitionnés release x département — BUG-02.

Même partition que le cadastre ; une dimension release dynamique par source, puisque chaque
source publie ses propres releases.
"""

from typing import Any

import psycopg
from dagster import (
    AssetExecutionContext,
    AssetsDefinition,
    DynamicPartitionsDefinition,
    MaterializeResult,
    MetadataValue,
    MultiPartitionKey,
    MultiPartitionsDefinition,
    asset,
)

from immo_pipelines.assets.cadastre import cadastre_department_partitions
from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.release_import import (
    BAN,
    RNB,
    SourceImport,
    import_department_release,
)


def source_partitions(source: SourceImport) -> MultiPartitionsDefinition:
    return MultiPartitionsDefinition(
        {
            "department": cadastre_department_partitions,
            "release": DynamicPartitionsDefinition(name=f"{source.run_prefix}_releases"),
        }
    )


def partition_keys(context: AssetExecutionContext) -> tuple[str, str]:
    key = context.partition_key
    if not isinstance(key, MultiPartitionKey):
        raise TypeError("Source release assets require release x department partitions")
    return key.keys_by_dimension["release"], key.keys_by_dimension["department"]


def materialize_source(
    source: SourceImport, context: AssetExecutionContext
) -> MaterializeResult[Any]:
    release_key, department_code = partition_keys(context)
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
            source,
            release_key,
            department_code,
            connection=connection,
            object_store=object_store,
        )
    context.log.info("Resolved %s from %s", source.layer, result.asset_origin)
    outcome = result.outcome
    return MaterializeResult(
        metadata={
            "release_id": result.release_id,
            "department": result.department_code,
            "import_run_id": outcome.import_run_id,
            "asset_origin": result.asset_origin,
            "sha256": result.sha256,
            "rows": MetadataValue.json(
                {
                    "source": outcome.source_rows,
                    "normalized": outcome.normalized_rows,
                    "quarantined": outcome.quarantined_rows,
                    "idempotent_skip": outcome.skipped_as_idempotent,
                }
            ),
            "publication": "pending explicit acceptance",
        }
    )


def source_release_asset(name: str, source: SourceImport) -> AssetsDefinition:
    @asset(
        name=name,
        group_name="spatial_sources",
        partitions_def=source_partitions(source),
        description=(
            f"Archive and import one immutable {source.data_source_id} release x department "
            "partition."
        ),
    )
    def _asset(context: AssetExecutionContext) -> MaterializeResult[Any]:
        return materialize_source(source, context)

    return _asset


ds02_rnb_release = source_release_asset("ds02_rnb_release", RNB)
ds05_ban_release = source_release_asset("ds05_ban_release", BAN)
