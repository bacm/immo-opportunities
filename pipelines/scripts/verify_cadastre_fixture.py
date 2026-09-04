"""Exercise DS-01 persistence on a real PostGIS/MinIO stack without publishing fixtures."""

import gzip
import json
import shutil
import tempfile
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore, archive_asset
from immo_pipelines.cadastre.catalog import DatasetCatalog, RawAssetRegistration
from immo_pipelines.cadastre.contract import load_contract, sha256_file
from immo_pipelines.cadastre.importer import CadastreImporter
from immo_pipelines.cadastre.processor import CadastreFeatureProcessor
from immo_pipelines.cadastre.settings import CadastreSettings


def _compress(source: Path, destination: Path) -> None:
    with source.open("rb") as input_stream, gzip.open(destination, "wb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture_root = root / "pipelines" / "tests" / "fixtures" / "cadastre"
    suffix = uuid.uuid4().hex[:12]
    release_id = f"DS-01@fixture-{suffix}"
    contract = load_contract()
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
    )
    evidence: dict[str, Any] = {"release_id": release_id}

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
            release_key=f"fixture-{suffix}",
            published_on=date(2026, 6, 1),
            schema_fingerprint=contract.schema_fingerprint(),
            department_code="35",
        )
        importer = CadastreImporter(connection, CadastreFeatureProcessor(contract))

        with tempfile.TemporaryDirectory(prefix="immo-fixture-") as temp_dir:
            outcomes = []
            fixtures = (
                ("parcelles-minimal.geojson", "parcelles"),
                ("parcelles-invalid.geojson", "parcelles"),
                ("batiments-reprojection-invalid.geojson", "batiments"),
            )
            for fixture_name, layer in fixtures:
                source = fixture_root / fixture_name
                compressed = Path(temp_dir) / f"{fixture_name}.gz"
                _compress(source, compressed)
                checksum = sha256_file(compressed)
                object_key = f"fixtures/{release_id}/{fixture_name}-{checksum}.gz"
                etag = archive_asset(
                    object_store,
                    compressed,
                    object_key=object_key,
                    sha256=checksum,
                    source_url=f"fixture://{fixture_name}",
                    release_id=release_id,
                )
                raw_asset_id = catalog.register_raw_asset(
                    RawAssetRegistration(
                        release_id=release_id,
                        layer=layer,
                        territory_code="35",
                        source_url=f"fixture://{fixture_name}",
                        object_key=object_key,
                        byte_size=compressed.stat().st_size,
                        sha256=checksum,
                        etag=etag,
                    )
                )
                archived_asset = catalog.find_raw_asset(
                    release_id=release_id,
                    layer=layer,
                    territory_code="35",
                    source_url=f"fixture://{fixture_name}",
                )
                if archived_asset is None or archived_asset.id != raw_asset_id:
                    raise AssertionError("Archived raw asset could not be recovered from catalog")
                restored = Path(temp_dir) / f"restored-{fixture_name}.gz"
                object_store.get_file(archived_asset.object_key, restored)
                sha256_file(restored, archived_asset.sha256)
                catalog.record_asset_checks(
                    release_id=release_id,
                    department_code="35",
                    layer=layer,
                    checksum_valid=True,
                    schema_valid=True,
                    schema_fingerprint=contract.schema_fingerprint(),
                )
                key = f"{release_id}:{fixture_name}:{checksum}"
                outcome = importer.import_file(
                    import_run_id=f"fixture:{suffix}:{len(outcomes)}",
                    release_id=release_id,
                    department_code="35",
                    layer=layer,
                    raw_asset_id=raw_asset_id,
                    source_path=compressed,
                    idempotency_key=key,
                )
                outcomes.append(outcome)

                if fixture_name == "parcelles-minimal.geojson":
                    repeated = importer.import_file(
                        import_run_id=f"fixture:{suffix}:repeat",
                        release_id=release_id,
                        department_code="35",
                        layer="parcelles",
                        raw_asset_id=raw_asset_id,
                        source_path=compressed,
                        idempotency_key=key,
                    )
                    if not repeated.skipped_as_idempotent:
                        raise AssertionError("Repeated import was not idempotent")
                    evidence["idempotent_skip"] = True

            evidence["valid_rows"] = outcomes[0].normalized_rows
            evidence["quarantined_rows"] = outcomes[1].quarantined_rows
            evidence["canonical_reprojection_repairs"] = outcomes[2].normalized_rows
            evidence["exact_duplicates_deduplicated"] = outcomes[2].deduplicated_rows
            evidence["archive_resume_verified"] = True
            if (
                evidence["valid_rows"] != 3
                or evidence["quarantined_rows"] != 1
                or evidence["canonical_reprojection_repairs"] != 1
                or evidence["exact_duplicates_deduplicated"] != 1
            ):
                raise AssertionError("Unexpected fixture import counts")

        try:
            catalog.set_acceptance(release_id, "accepted")
        except RuntimeError:
            evidence["incomplete_release_blocked"] = True
        else:
            raise AssertionError("An incomplete fixture release passed the acceptance gate")

        catalog.rollback_unpublished(
            release_id,
            actor="fixture-verification",
            reason="Automated rollback test",
        )
        remaining_assets = connection.execute(
            "SELECT count(*) FROM meta.raw_asset WHERE release_id = %s", (release_id,)
        ).fetchone()
        remaining_rows = connection.execute(
            """
            SELECT
                (SELECT count(*) FROM reference.cadastral_parcel WHERE release_id = %s),
                (SELECT count(*) FROM reference.cadastral_building WHERE release_id = %s)
            """,
            (release_id, release_id),
        ).fetchone()
        evidence["raw_assets_retained"] = int(remaining_assets[0]) if remaining_assets else 0
        evidence["normalized_rows_after_rollback"] = (
            sum(int(value) for value in remaining_rows) if remaining_rows else -1
        )
        if evidence["raw_assets_retained"] != 3 or evidence["normalized_rows_after_rollback"] != 0:
            raise AssertionError("Unpublished rollback did not preserve raw lineage correctly")

    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
