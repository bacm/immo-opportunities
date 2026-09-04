import importlib.util
import json
from pathlib import Path
from types import ModuleType


def load_spatial_revision() -> ModuleType:
    path = (
        Path(__file__).parents[1] / "migrations" / "versions" / "20260805_0005_spatial_reference.py"
    )
    spec = importlib.util.spec_from_file_location("spatial_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_spatial_revision_models_canonical_entities_without_replacing_source_tables() -> None:
    revision = load_spatial_revision()

    assert set(revision.REFERENCE_TABLES) == {
        "area",
        "address",
        "parcel",
        "building",
        "building_parcel",
        "property_unit",
        "property_unit_member",
    }
    assert "entity_source_identifier" in revision.MATCH_TABLES
    assert "entity_match_review" in revision.MATCH_TABLES


def test_spatial_revision_keeps_ambiguity_provenance_and_spatial_indexes() -> None:
    revision = load_spatial_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")

    assert "decision IN ('certain', 'ambiguous', 'rejected')" in source
    assert "blocks_publication" in source
    assert "algorithm_version" in source
    assert "rationale text NOT NULL" in source
    assert "USING gist (geom)" in source
    assert "address_label_trgm" in source
    assert "refresh_cadastre_spatial_reference" in source


def test_all_spatial_dataset_and_morphology_contracts_are_versioned_json() -> None:
    contract_root = Path(__file__).parents[2] / "contracts"
    for dataset_id in ("DS-02", "DS-03", "DS-04", "DS-05"):
        contract = json.loads((contract_root / "datasets" / dataset_id / "v1.json").read_text())
        assert contract["contract_id"] == dataset_id
        assert contract["contract_version"] == 1
        assert contract["release"]["latest_alias_forbidden_for_reproducible_imports"]

    feature_catalog = json.loads((contract_root / "features" / "morphology-v1.json").read_text())
    assert {feature["code"] for feature in feature_catalog["features"]} == {
        *(f"LAND-{number:03d}" for number in range(1, 11)),
        *(f"BLD-{number:03d}" for number in range(1, 4)),
    }
    assert all("missing_value" in feature for feature in feature_catalog["features"])


def test_spatial_storage_does_not_copy_every_parcel_geometry_into_each_unit() -> None:
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260805_0006_spatial_storage_and_features.py"
    )
    source = path.read_text(encoding="utf-8")

    assert "DROP COLUMN geom" in source
    assert "CREATE VIEW reference.parcel_geometry" in source
    assert "CREATE VIEW reference.property_unit_geometry" in source
    assert "FEATURE_DEFINITIONS" in source


def test_spatial_revision_allows_rnb_identity_before_polygon_resolution() -> None:
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260805_0007_partial_building_identity.py"
    )
    source = path.read_text(encoding="utf-8")

    assert "ALTER COLUMN geom DROP NOT NULL" in source
    assert "geom IS NULL OR ST_IsValid(geom)" in source
    assert "review_entity_match" in source
