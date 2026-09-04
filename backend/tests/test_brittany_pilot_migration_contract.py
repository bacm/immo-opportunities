import importlib.util
from pathlib import Path
from types import ModuleType


def load_revision() -> ModuleType:
    path = Path(__file__).parents[1] / "migrations" / "versions" / "20260810_0015_brittany_pilot.py"
    spec = importlib.util.spec_from_file_location("brittany_pilot_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_regional_contract_covers_every_department_source_and_segment() -> None:
    revision = load_revision()
    assert revision.down_revision == "20260807_0014"
    assert revision.BRITTANY_DEPARTMENTS == ("22", "29", "35", "56")
    assert len(revision.BRITTANY_DATASETS) == 9
    assert {"metropolitan", "medium_city", "periurban", "coastal", "rural"} == set(
        revision.PILOT_SEGMENTS
    )


def test_publication_review_and_rollback_guards_are_explicit() -> None:
    revision = load_revision()
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text(encoding="utf-8")
    assert "brittany_release_readiness" in source
    assert "Regional bundle must contain DS-01 to DS-09 for four departments" in source
    assert "Both score strategies must be profiled and active" in source
    assert "INSERT INTO meta.active_dataset_release" in source
    assert "Published candidates must cover four departments and five pilot segments" in source
    assert "DELETE FROM meta.active_dataset_release AS active" in source
    assert "CROSS JOIN meta.active_regional_release AS regional" in source
    assert "candidate_review_outcome" in source
    assert "reviewer_pseudonym" in source
    assert "p_action NOT IN ('publish', 'rollback')" in source
