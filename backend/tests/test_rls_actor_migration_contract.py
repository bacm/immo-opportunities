import importlib.util
from pathlib import Path
from types import ModuleType


def load_revision() -> ModuleType:
    path = (
        Path(__file__).parents[1] / "migrations" / "versions" / "20260807_0014_rls_actor_context.py"
    )
    spec = importlib.util.spec_from_file_location("rls_actor_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_actor_context_has_no_recursive_policy_and_snapshots_author_names() -> None:
    revision = load_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")
    assert revision.down_revision == "20260807_0013"
    assert "organization_membership_current_user" in source
    assert "app.current_user_id" in source
    assert "ADD COLUMN author_name" in source
