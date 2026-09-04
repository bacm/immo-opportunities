from pathlib import Path

MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20260904_0018_match_reference_indexes.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_chains_onto_the_analysis_scope_head() -> None:
    source = migration_source()

    assert 'revision: str = "20260904_0018"' in source
    assert 'down_revision: str | None = "20260904_0017"' in source


def test_every_foreign_key_to_entity_match_is_indexed() -> None:
    """Une clé étrangère NO ACTION non indexée rend la suppression quadratique : retirer
    les relations d'un seul département n'aboutissait pas en dix minutes."""
    source = migration_source()

    for table in ("property_unit_member", "building_parcel"):
        assert f"ON reference.{table} (match_id)" in source


def test_the_self_reference_is_indexed_too() -> None:
    """`supersedes_match_id` pointe vers la table elle-même : sans index, la supprimer
    la balaye intégralement pour chaque ligne retirée. C'est la référence décisive, et
    la plus facile à oublier puisqu'elle ne traverse aucune autre table."""
    assert "ON meta.entity_match (supersedes_match_id)" in migration_source()


def test_the_indexes_are_dropped_on_downgrade() -> None:
    source = migration_source()

    assert "DROP INDEX IF EXISTS reference.property_unit_member_match_idx" in source
    assert "DROP INDEX IF EXISTS reference.building_parcel_match_idx" in source
    assert "DROP INDEX IF EXISTS meta.entity_match_supersedes_idx" in source
