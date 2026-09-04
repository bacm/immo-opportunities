from pathlib import Path

MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20260904_0017_analysis_release_scope.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_revision_chains_onto_the_attribute_quarantine_head() -> None:
    source = migration_source()

    assert 'revision: str = "20260904_0017"' in source
    assert 'down_revision: str | None = "20260904_0016"' in source


def test_analysis_scope_excludes_display_only_releases() -> None:
    """Sans ce filtre, `display_only` resterait une étiquette sans effet : une release
    acceptée pour le seul affichage pourrait fonder une feature entrant dans un score."""
    source = migration_source()

    assert "CREATE VIEW meta.analysis_dataset_release" in source
    assert "FROM meta.active_dataset_release" in source
    assert "WHERE publication_mode = 'accepted'" in source


def test_analysis_scope_is_a_view_and_never_a_second_copy_of_the_pointer() -> None:
    """La publication déplace un pointeur unique. Une table séparée pourrait diverger de
    meta.active_dataset_release et faire vivre deux vérités sur la release active."""
    source = migration_source()

    assert "CREATE TABLE" not in source
    assert "INSERT INTO" not in source
    assert "DROP VIEW meta.analysis_dataset_release" in source


def test_no_data_source_is_named_in_the_scope() -> None:
    """La frontière vaut pour DS-01 à DS-09 : y inscrire une source la rendrait fausse
    dès l'import suivant."""
    assert "DS-" not in migration_source()
