import gzip
import json
from pathlib import Path
from typing import Any

import pytest
from shapely import from_wkt

from immo_pipelines.cadastre.archive import archive_asset
from immo_pipelines.cadastre.contract import (
    ChecksumMismatchError,
    SchemaChangeError,
    load_contract,
    sha256_file,
)
from immo_pipelines.cadastre.geojson import iter_features
from immo_pipelines.cadastre.processor import (
    CadastreFeatureProcessor,
    NormalizedFeature,
    QuarantinedFeature,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cadastre"
PROJECT_ROOT = Path(__file__).parents[2]


def test_ds01_contract_is_versioned_and_scalable() -> None:
    contract = load_contract()

    assert contract.contract_id == "DS-01"
    assert contract.source_srid == 4326
    assert contract.canonical_srid == 2154
    assert set(contract.layers) == {"communes", "parcelles", "batiments"}
    assert len(contract.schema_fingerprint()) == 64


def test_release_manifest_uses_pinned_urls_not_latest() -> None:
    manifest_path = PROJECT_ROOT / "contracts/datasets/DS-01/releases/2026-06-01-35.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["release_id"] == "DS-01@2026-06-01"
    assert all("/2026-06-01/" in asset["url"] for asset in manifest["assets"])
    assert all("/latest/" not in asset["url"] for asset in manifest["assets"])


def test_wrong_checksum_is_detected(tmp_path: Path) -> None:
    source = tmp_path / "asset.geojson"
    source.write_text("{}", encoding="utf-8")

    with pytest.raises(ChecksumMismatchError):
        sha256_file(source, "0" * 64)


def test_schema_change_is_detected_before_geometry_processing() -> None:
    processor = CadastreFeatureProcessor(load_contract())
    feature: dict[str, Any] = {
        "type": "Feature",
        "properties": {"id": "x", "commune": "35238"},
        "geometry": {"type": "Polygon", "coordinates": []},
    }

    with pytest.raises(SchemaChangeError, match="prefixe"):
        processor.process("parcelles", 1, feature)


def test_minimal_fixture_normalizes_three_territory_profiles_to_lambert93() -> None:
    processor = CadastreFeatureProcessor(load_contract())
    results = [
        processor.process("parcelles", index, feature)
        for index, feature in enumerate(iter_features(FIXTURES / "parcelles-minimal.geojson"), 1)
    ]

    assert len(results) == 3
    assert all(isinstance(result, NormalizedFeature) for result in results)
    normalized = [result for result in results if isinstance(result, NormalizedFeature)]
    assert {result.properties["commune"] for result in normalized} == {"35238", "35210", "35346"}
    assert "contenance" not in normalized[2].properties
    assert all(from_wkt(result.geometry_wkt).is_valid for result in normalized)
    assert all(from_wkt(result.geometry_wkt).bounds[0] > 100_000 for result in normalized)


def test_unrepairable_geometry_is_quarantined_with_source_payload() -> None:
    processor = CadastreFeatureProcessor(load_contract())
    feature = next(iter_features(FIXTURES / "parcelles-invalid.geojson"))

    result = processor.process("parcelles", 1, feature)

    assert isinstance(result, QuarantinedFeature)
    assert result.reason_code == "unrepairable_geometry"
    assert result.repair_attempted
    assert result.source_geometry is not None


def test_geometry_made_invalid_by_reprojection_is_repaired_in_target_srid() -> None:
    processor = CadastreFeatureProcessor(load_contract())
    feature: dict[str, Any] = {
        "type": "Feature",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [-1.802795, 48.1056742],
                        [-1.8027709, 48.1056144],
                        [-1.8027069, 48.1056257],
                        [-1.8027027, 48.105615],
                        [-1.8026807, 48.105619],
                        [-1.8027676, 48.1056032],
                        [-1.8027438, 48.1055443],
                        [-1.8025513, 48.1055792],
                        [-1.8026036, 48.1057087],
                        [-1.802795, 48.1056742],
                    ]
                ]
            ],
        },
        "properties": {
            "type": "01",
            "nom": None,
            "commune": "35240",
            "created": "2022-04-26",
            "updated": "2022-05-04",
        },
    }

    result = processor.process("batiments", 755378, feature)

    assert isinstance(result, NormalizedFeature)
    assert result.was_repaired
    assert result.repair_method == processor.contract.repair_version
    assert from_wkt(result.geometry_wkt).is_valid


def test_streaming_reader_accepts_real_gzip_container(tmp_path: Path) -> None:
    source = FIXTURES / "parcelles-minimal.geojson"
    compressed = tmp_path / "parcelles.json.gz"
    with source.open("rb") as input_stream, gzip.open(compressed, "wb") as output_stream:
        output_stream.write(input_stream.read())

    assert len(list(iter_features(compressed))) == 3


def test_archive_records_checksum_release_and_source(tmp_path: Path) -> None:
    class MemoryObjectStore:
        def __init__(self) -> None:
            self.metadata: dict[str, str] = {}

        def put_file(self, source: Path, object_key: str, metadata: dict[str, str]) -> str:
            assert source.exists()
            assert object_key.startswith("DS-01/")
            self.metadata = metadata
            return "fixture-etag"

    path = tmp_path / "source.json.gz"
    path.write_bytes(b"immutable source bytes")
    store = MemoryObjectStore()

    etag = archive_asset(
        store,
        path,
        object_key="DS-01/2026-06-01/department/35/parcelles/test.json.gz",
        sha256="a" * 64,
        source_url="https://cadastre.data.gouv.fr/source.json.gz",
        release_id="DS-01@2026-06-01",
    )

    assert etag == "fixture-etag"
    assert store.metadata["immutable"] == "true"
    assert store.metadata["release-id"] == "DS-01@2026-06-01"
