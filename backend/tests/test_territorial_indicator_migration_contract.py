"""Variables communales DS-14 à DS-16 — D7, ADR-023.

Test sur le texte et sur les constantes de la migration, faute de banc PostgreSQL dans
`make check`. L'exécution réelle (montée, descente, remontée) est consignée dans le ticket D7.
"""

import importlib.util
import re
from pathlib import Path
from typing import Any

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
ROOT = Path(__file__).parents[2]


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, VERSIONS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migration() -> Any:
    return load("20260917_0027_territorial_indicator")


def test_revision_chains_onto_the_release_retirement() -> None:
    module = migration()
    assert module.revision == "20260917_0027"
    assert module.down_revision == "20260917_0026"


def test_the_purge_of_adr_022_covers_the_new_table() -> None:
    """Sans elle, retirer une release DS-14 laisserait ses lignes et la clé étrangère refuserait."""
    module = migration()
    assert "observation.territorial_indicator" in module.PURGED_TABLES
    assert "DELETE FROM observation.territorial_indicator" in module.PURGE_FUNCTION
    assert module.PURGED_TABLES[-1] == "meta.import_run"


def test_the_downgrade_restores_exactly_the_previous_purge() -> None:
    previous = load("20260917_0026_retire_replaced_release")
    assert migration().PREVIOUS_PURGED_TABLES == previous.PURGED_TABLES


def test_a_row_carries_one_value_or_one_reason() -> None:
    table = migration().TABLE
    assert "num_nonnulls(numeric_value, text_value, missing_reason) = 1" in table
    assert "UNIQUE (release_id, commune_code, indicator_code)" in table


def test_missing_reasons_are_the_spec_vocabulary() -> None:
    """`SPEC.md` §13.7 fixe le vocabulaire ; la table n'en invente pas."""
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    section = spec[spec.index("### 13.7") : spec.index("### 13.8")]
    declared = set(re.findall(r"`([a-z_]+)`", section))
    assert set(migration().MISSING_REASONS) == declared


def test_the_three_sources_are_declared_with_their_contracts() -> None:
    sql = migration().DATA_SOURCES
    for source in ("DS-14", "DS-15", "DS-16"):
        assert f"('{source}'" in sql
        assert (ROOT / "contracts" / "datasets" / source / "v1.json").exists()
    # DS-10 à DS-12 restent réservés (SPEC §13.1).
    for reserved in ("DS-10", "DS-11", "DS-12"):
        assert reserved not in sql
