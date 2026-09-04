import importlib.util
from pathlib import Path
from types import ModuleType


def load_revision() -> ModuleType:
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260807_0013_connected_mvp.py"
    spec = importlib.util.spec_from_file_location("connected_mvp_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_private_models_cover_mvp_workflow() -> None:
    revision = load_revision()
    assert set(revision.APP_TABLES) == {
        "organization",
        "app_user",
        "organization_membership",
        "candidate_state",
        "candidate_status_history",
        "note",
        "candidate_review",
        "candidate_scenario",
        "saved_search",
    }
    assert {"retained", "rejected", "acquired", "ignored"} < set(revision.STATUSES)
    assert "other" in revision.REJECTION_REASONS


def test_rls_immutable_history_and_audit_are_explicit() -> None:
    revision = load_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "for table in TENANT_TABLES" in source
    assert "app.current_organization_id" in source
    assert "app.current_subject" in source
    assert "reject_immutable_private_event" in source
    assert "audit.sensitive_access_event" in source
