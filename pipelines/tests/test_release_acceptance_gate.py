"""La barrière d'acceptation doit valoir pour toute source, pas seulement DS-01.

Le contrôle de complétude par couches (`communes`, `parcelles`, `batiments`) décrit le
cadastre et rien d'autre. Appliqué sans distinction, il rendait inacceptable n'importe
quelle release non cadastrale : DS-05 BAN, qui ne publie que la couche `addresses`,
échouait sur « Release requires all three archived and imported layers ». Le déclencheur
SQL `meta.guard_active_dataset_release` scope déjà ce contrôle à DS-01 ; c'est le code
Python qui avait gardé la règle du seul cadastre.
"""

from typing import Any, cast

import pytest
from psycopg import Connection

from immo_pipelines.cadastre.catalog import DatasetCatalog


class _Result:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class FakeConnection:
    """Connexion scriptée : retient les requêtes et répond selon leur contenu.

    Le but est d'observer *quelles* barrières sont interrogées, pas de simuler
    PostgreSQL. Une requête inattendue reste visible dans `statements`.
    """

    def __init__(
        self,
        *,
        data_source_id: str | None = "DS-05",
        successful_import: bool = True,
    ) -> None:
        self.data_source_id = data_source_id
        self.successful_import = successful_import
        self.statements: list[str] = []
        self.commits = 0

    def execute(self, statement: str, parameters: Any = None) -> _Result:
        self.statements.append(statement)
        # Du plus spécifique au plus général : la requête de complétude cadastrale
        # contient elle aussi `FROM meta.import_run`, elle doit donc être reconnue
        # avant la barrière générique d'import réussi.
        if "release_assets AS (" in statement:
            # Complétude cadastrale satisfaite : 3 couches, 332 communes, 996 métriques.
            return _Result((3, 3, 332, 996))
        if "SELECT data_source_id FROM meta.dataset_release" in statement:
            return _Result(None if self.data_source_id is None else (self.data_source_id,))
        if "FROM meta.import_run" in statement and "status = 'succeeded'" in statement:
            return _Result((1,) if self.successful_import else None)
        return _Result(None)

    def commit(self) -> None:
        self.commits += 1

    @property
    def layer_gate_was_queried(self) -> bool:
        return any("release_assets AS (" in statement for statement in self.statements)


def catalog_for(connection: FakeConnection) -> DatasetCatalog:
    return DatasetCatalog(cast(Connection[Any], connection))


def test_a_ban_release_is_acceptable_without_the_three_cadastral_layers() -> None:
    connection = FakeConnection(data_source_id="DS-05")

    catalog_for(connection).set_acceptance("DS-05@2026-06-17", "accepted")

    assert not connection.layer_gate_was_queried
    assert connection.commits == 1


def test_the_layer_gate_still_guards_ds01() -> None:
    """Retirer la règle pour DS-05 ne doit pas la retirer pour le cadastre."""
    connection = FakeConnection(data_source_id="DS-01")

    catalog_for(connection).set_acceptance("DS-01@2026-06-01", "accepted")

    assert connection.layer_gate_was_queried


def test_no_source_is_acceptable_without_a_successful_import() -> None:
    """Sans cette barrière générique, écarter le contrôle par couches laisserait une
    release non cadastrale acceptable alors que rien n'a jamais été importé."""
    connection = FakeConnection(data_source_id="DS-05", successful_import=False)

    with pytest.raises(RuntimeError, match="successful import run"):
        catalog_for(connection).set_acceptance("DS-05@2026-06-17", "accepted")

    assert connection.commits == 0


def test_rejecting_a_release_needs_no_gate_at_all() -> None:
    connection = FakeConnection(data_source_id="DS-05", successful_import=False)

    catalog_for(connection).set_acceptance("DS-05@2026-06-17", "rejected")

    assert not connection.layer_gate_was_queried
    assert connection.commits == 1


def test_publication_names_the_source_of_the_release_it_publishes() -> None:
    """`meta.publish_dataset_release` cherche la release par (id, data_source_id) en
    SELECT STRICT : un 'DS-01' codé en dur rendait toute release non cadastrale
    impubliable, DS-05 comprise."""
    connection = FakeConnection(data_source_id="DS-05")

    catalog_for(connection).publish(
        "DS-05@2026-06-17", "35", actor="bruno@manty.eu", reason="audit B1"
    )

    published = [s for s in connection.statements if "publish_dataset_release" in s]
    assert published, "aucun appel de publication"
    assert "'DS-01'" not in published[0]


def test_an_unknown_release_is_never_accepted_silently() -> None:
    connection = FakeConnection(data_source_id=None)

    with pytest.raises(RuntimeError, match="Unknown release"):
        catalog_for(connection).set_acceptance("DS-05@1970-01-01", "accepted")

    assert connection.commits == 0
