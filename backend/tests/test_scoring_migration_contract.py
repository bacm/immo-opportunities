import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType


def load_revision() -> ModuleType:
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260807_0012_scoring.py"
    spec = importlib.util.spec_from_file_location("scoring_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scoring_models_cover_definitions_snapshots_evidence_and_validation() -> None:
    revision = load_revision()
    assert set(revision.SCORING_TABLES) == {
        "strategy",
        "score_definition",
        "score_definition_component",
        "score_definition_feature",
        "score_eligibility_rule",
        "active_score_definition",
        "score_definition_publication_event",
        "estimate_scenario",
        "opportunity_snapshot",
        "score_component",
        "score_evidence",
        "published_opportunity",
        "opportunity_publication_event",
        "backtest_run",
        "backtest_metric",
        "ablation_result",
    }
    assert {item[0] for item in revision.FINANCIAL_FEATURES} == {
        "FIN-001",
        "FIN-002",
        *(f"FIN-{number:03d}" for number in range(101, 107)),
    }


def test_score_rules_are_unique_and_component_weights_are_fixed() -> None:
    revision = load_revision()
    by_definition: dict[str, list[tuple[object, ...]]] = {}
    for rule in revision.SCORE_RULES:
        by_definition.setdefault(rule[0], []).append(rule)
    for rules in by_definition.values():
        codes = [rule[1] for rule in rules]
        assert len(codes) == len(set(codes))
        for component in {rule[2] for rule in rules if rule[2] is not None}:
            assert sum(rule[3] for rule in rules if rule[2] == component) == 1


def test_migration_guards_immutability_time_and_atomic_publication() -> None:
    revision = load_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")
    assert "reject_immutable_change" in source
    assert "opportunity_snapshot_time_guard" in source
    assert "score_evidence_time_guard" in source
    assert "source_release_ids <@ target_snapshot.release_ids" in source
    assert "publish_score_definition" in source
    assert "publish_opportunity_snapshot" in source
    assert "withdraw_opportunity_snapshot" in source
    assert "definition_not_publication_eligible" not in source


def test_scoring_contract_digests_and_draft_status_are_truthful() -> None:
    revision = load_revision()
    root = Path(__file__).parents[2]
    definitions = {item["id"]: item for item in revision.SCORE_DEFINITIONS}
    for definition_id, filename in (
        ("division-extension-v0.1", "division-extension-v1.json"),
        ("renovation-resale-v0.1", "renovation-resale-v1.json"),
    ):
        path = root / "contracts" / "scoring" / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert payload["definition_id"] == definition_id
        assert payload["status"] == "draft"
        assert not payload["publication_eligible"]
        assert definitions[definition_id]["contract_digest"] == digest

    registry = json.loads((root / "contracts" / "scoring" / "feature-registry-v1.json").read_text())
    assert registry["policies"]["optional"].startswith("missing value receives the fixed neutral")
    assert registry["policies"]["confidence_only"].startswith("never changes ranking score")
