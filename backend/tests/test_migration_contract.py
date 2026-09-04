import importlib.util
from pathlib import Path
from types import ModuleType


def load_foundation_revision() -> ModuleType:
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260804_0001_foundation.py"
    spec = importlib.util.spec_from_file_location("foundation_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_foundation_revision_declares_all_architecture_schemas() -> None:
    revision = load_foundation_revision()

    assert set(revision.SCHEMAS) == {
        "meta",
        "reference",
        "observation",
        "feature",
        "scoring",
        "market",
        "app",
        "tiles",
        "audit",
    }


def test_foundation_revision_does_not_define_premature_domain_tables() -> None:
    revision = load_foundation_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")

    assert "create_table" not in source
