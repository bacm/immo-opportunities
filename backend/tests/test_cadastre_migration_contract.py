import importlib.util
from pathlib import Path
from types import ModuleType


def load_cadastre_revision() -> ModuleType:
    path = (
        Path(__file__).parents[1] / "migrations" / "versions" / "20260804_0002_cadastre_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("cadastre_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cadastre_revision_keeps_catalog_generic_and_source_entities_explicit() -> None:
    revision = load_cadastre_revision()

    assert "data_source" in revision.DATASET_TABLES
    assert "dataset_release" in revision.DATASET_TABLES
    assert "cadastral_building" in revision.REFERENCE_TABLES
    assert "building" not in revision.REFERENCE_TABLES


def test_cadastre_revision_has_atomic_publication_provenance_and_spatial_indexes() -> None:
    revision = load_cadastre_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")

    assert "publish_dataset_release" in source
    assert "rollback_unpublished_dataset_release" in source
    assert "raw_asset_id" in source
    assert "source_row_number" in source
    assert "USING gist (geom)" in source
    assert "geometry(MultiPolygon, 2154)" in source
    assert "active_cadastral_parcel" in source


def test_publication_guard_requires_assets_imports_and_commune_metrics() -> None:
    path = (
        Path(__file__).parents[1] / "migrations" / "versions" / "20260804_0003_publication_guard.py"
    )
    source = path.read_text(encoding="utf-8")

    assert "active_dataset_release_guard" in source
    assert "asset_layer_count <> 3" in source
    assert "import_layer_count <> 3" in source
    assert "commune_metric_count <> commune_count * 3" in source


def test_exact_duplicates_are_accounted_without_hiding_conflicts() -> None:
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260804_0004_exact_duplicate_accounting.py"
    )
    source = path.read_text(encoding="utf-8")

    assert "deduplicated_row_count" in source
    assert "exact_duplicate_record" in source
    assert "conflicting_duplicate_source_id" in source
    assert "identical_record_checksum" in source
