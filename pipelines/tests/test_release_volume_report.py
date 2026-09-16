"""Volume par release — BUG-08, ADR-022."""

import importlib.util
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
NBSP = "\N{NO-BREAK SPACE}"


def load(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_le_rapport_compte_exactement_les_tables_que_le_retrait_purge() -> None:
    """Deux listes, une vérité : un écart ferait annoncer un volume que le retrait n'enlève pas."""
    report = load(REPO / "pipelines" / "scripts" / "release_volume_report.py")
    migration = load(
        REPO / "backend" / "migrations" / "versions" / "20260917_0026_retire_replaced_release.py"
    )
    assert report.COUNTED_TABLES == migration.PURGED_TABLES


def test_une_release_active_ou_groupee_est_dite_non_retirable() -> None:
    report = load(REPO / "pipelines" / "scripts" / "release_volume_report.py")
    data = {
        "database_size": "29 GB",
        "releases": [
            ("DS-01", "DS-01@a", "validated", "accepted", True, False, True),
            ("DS-02", "DS-02@a", "discovered", "pending", False, False, False),
            ("DS-02", "DS-02@b", "retired", "accepted", False, False, False),
            ("DS-09", "DS-09@a", "validated", "display_only", False, True, False),
        ],
        "rows": {"DS-01@a": {"reference.cadastral_parcel": 1_333_327}},
    }
    text = report.render(data, date(2026, 9, 17))
    rows = f"1{NBSP}333{NBSP}327"
    assert (
        f"| DS-01 | `DS-01@a` | validated | accepted | oui | {rows} | active — non retirable |"
        in (text)
    )
    assert "| 0 | retirable si remplacée |" in text
    assert "déjà retirée" in text
    assert "membre d'un bundle — non retirable" in text
    # Aucune release n'est désignée comme remplacée par le rapport : c'est un jugement.
    assert "« Retirable » ne" in text
