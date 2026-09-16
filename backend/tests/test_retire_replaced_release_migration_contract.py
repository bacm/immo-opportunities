"""Retrait d'une release remplacée — BUG-08, ADR-022.

Test sur le texte et sur les constantes de la migration, faute de banc PostgreSQL dans
`make check`. L'exécution réelle est consignée dans le ticket BUG-08.
"""

import importlib.util
from pathlib import Path
from typing import Any

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "20260917_0026_retire_replaced_release.py"


def migration() -> Any:
    spec = importlib.util.spec_from_file_location("retire_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chains_onto_the_new_build_dpe_source() -> None:
    module = migration()
    assert module.revision == "20260917_0026"
    assert module.down_revision == "20260916_0025"


def test_la_purge_couvre_les_tables_spatiales_et_metier_pas_seulement_le_cadastre() -> None:
    """Le défaut de BUG-08 : seules les tables DS-01 étaient purgées."""
    purged = set(migration().PURGED_TABLES)
    for table in (
        "meta.entity_source_observation",
        "observation.transaction",
        "observation.energy_assessment",
        "observation.urban_document",
        "observation.risk_observation",
        "observation.road_segment",
        "meta.attribute_quarantine",
        "reference.cadastral_parcel",
        "meta.import_run",
    ):
        assert table in purged
    # La purge des runs vient en dernier : d'autres lignes les référencent.
    assert migration().PURGED_TABLES[-1] == "meta.import_run"


def test_ce_qui_doit_rester_n_est_jamais_purge() -> None:
    """Fichiers bruts, identités de source, décisions d'appariement, historique de publication."""
    function = migration().PURGE_FUNCTION
    for kept in (
        "meta.raw_asset",
        "meta.entity_source_identifier",
        "meta.entity_match ",
        "meta.publication_event",
        "meta.dataset_release ",
    ):
        assert f"DELETE FROM {kept}" not in function


def test_le_rollback_des_releases_non_publiees_reutilise_la_purge_complete() -> None:
    rollback = migration().ROLLBACK_FUNCTION
    assert "PERFORM meta.purge_dataset_release_rows(p_release_id)" in rollback
    assert "has publication history and cannot be purged" in rollback


def test_le_retrait_porte_les_garde_fous_d_adr_022() -> None:
    retire = migration().RETIRE_FUNCTION
    for guard in (
        "requires an actor and a written reason",
        "is already retired",
        "is not a distinct existing release",
        "belongs to %, not to %",
        "is itself retired",
        "is active and cannot be retired",
        "belongs to a regional bundle",
        "is not imported on",
    ):
        assert guard in retire
    # Une release publiée puis remplacée est retirable : aucune garde sur publication_event.
    assert "publication_event" not in retire
    # La trace est écrite, et la ligne de release n'est jamais supprimée.
    assert "Retired on %s by %s, replaced by %s: %s" in retire
    assert "DELETE FROM meta.dataset_release" not in retire
