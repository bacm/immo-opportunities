from pathlib import Path

MIGRATION = (
    Path(__file__).parents[1] / "migrations" / "versions" / "20260904_0016_attribute_quarantine.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_chains_onto_the_brittany_pilot_head() -> None:
    source = migration_source()

    assert 'revision: str = "20260904_0016"' in source
    assert 'down_revision: str | None = "20260810_0015"' in source


def test_attribute_quarantine_is_generic_and_not_ban_specific() -> None:
    """Le mécanisme doit servir DS-06 à DS-09 autant que DS-05 : aucune colonne, aucune
    contrainte ne peut présumer d'une adresse ni d'une source particulière."""
    source = migration_source()

    assert "CREATE TABLE meta.attribute_quarantine" in source
    for column in ("entity_type", "entity_id", "attribute", "reason_code", "evidence"):
        assert column in source
    for ban_specific in ("ban_id", "DS-05", "address_id"):
        assert ban_specific not in source


def test_one_quarantine_row_per_attribute_and_release() -> None:
    source = migration_source()

    assert "CONSTRAINT attribute_quarantine_identity" in source
    assert "UNIQUE (release_id, entity_type, entity_id, attribute)" in source


def test_address_position_becomes_optional() -> None:
    """Une position contradictoire rend l'attribut manquant : la colonne doit l'accepter,
    sans quoi l'import devrait choisir arbitrairement l'une des variantes."""
    source = migration_source()

    assert "ALTER TABLE reference.address ALTER COLUMN geom DROP NOT NULL" in source


def test_downgrade_restores_the_previous_guarantee() -> None:
    source = migration_source()
    downgrade = source[source.index("def downgrade()") :]

    assert "ALTER COLUMN geom SET NOT NULL" in downgrade
    assert "DELETE FROM reference.address WHERE geom IS NULL" in downgrade
    assert "DROP TABLE meta.attribute_quarantine" in downgrade


def test_migration_runs_as_migration_owner() -> None:
    source = migration_source()

    assert source.count('op.execute("SET LOCAL ROLE migration_owner")') == 2
    assert source.count('op.execute("RESET ROLE")') == 2
