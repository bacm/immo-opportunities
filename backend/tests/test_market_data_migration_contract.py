import importlib.util
import json
from pathlib import Path
from types import ModuleType


def load_revision() -> ModuleType:
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260806_0011_market_data.py"
    spec = importlib.util.spec_from_file_location("market_data_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_market_data_models_and_feature_definitions_are_complete() -> None:
    revision = load_revision()
    assert set(revision.OBSERVATION_TABLES) == {
        "transaction",
        "transaction_property",
        "energy_assessment",
        "urban_document",
        "urban_zone",
        "urban_constraint",
        "risk_observation",
    }
    assert set(revision.MARKET_TABLES) == {
        "market_area",
        "comparable_selection",
        "market_metric",
    }
    assert {item["code"] for item in revision.FEATURE_DEFINITIONS} == {
        *(f"MKT-{number:03d}" for number in range(1, 6)),
        *(f"MKT-{number:03d}" for number in range(101, 106)),
        *(f"REN-{number:03d}" for number in range(1, 9)),
        *(f"URB-{number:03d}" for number in range(1, 6)),
        *(f"RISK-{number:03d}" for number in range(1, 5)),
        "RISK-101",
    }


def test_migration_enforces_provenance_snapshot_and_granularity_guards() -> None:
    revision = load_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")

    assert "complex_mutation_not_decomposable" not in source
    assert "transaction_property_allocation" in source
    assert "comparable_selection_snapshot" in source
    assert "energy_assessment_observed_only" in source
    assert "rule_profile_validated_at" in source
    assert "risk_observation_granularity" in source
    assert "dataset_coverage_metric" in source
    assert "USING gist" in source


def test_market_dataset_and_feature_contracts_are_versioned() -> None:
    root = Path(__file__).parents[2] / "contracts"
    for dataset_id in ("DS-06", "DS-07", "DS-08", "DS-09"):
        contract = json.loads((root / "datasets" / dataset_id / "v1.json").read_text())
        assert contract["contract_id"] == dataset_id
        assert contract["contract_version"] == 1
        assert contract["release"]["latest_alias_forbidden_for_reproducible_imports"]
        assert contract["publication"]["acceptance_report_required"]

    catalog = json.loads((root / "features" / "market-data-v1.json").read_text())
    codes = {item["code"] for item in catalog["features"]}
    assert codes == {item["code"] for item in load_revision().FEATURE_DEFINITIONS}
    assert all("missing_value" in item for item in catalog["features"])
    assert "communal risk converted to parcel exposure" in catalog["global_policies"]["forbidden"]
