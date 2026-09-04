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
        # Nombre de commits deja effectues au moment de chaque requete, index par index :
        # c'est ce qui permet d'observer si une requete tombe dans la transaction courante.
        self.commits_before: list[int] = []
        self.commits = 0

    def execute(self, statement: str, parameters: Any = None) -> _Result:
        self.statements.append(statement)
        self.commits_before.append(self.commits)
        if "refresh_cadastre_spatial_reference" in statement:
            return _Result((332, 1_333_327, 1_333_327))
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

    def index_of(self, needle: str) -> int:
        for index, statement in enumerate(self.statements):
            if needle in statement:
                return index
        raise AssertionError(f"aucune requete ne contient {needle!r}")

    @property
    def propagation_was_queried(self) -> bool:
        return any("refresh_cadastre_spatial_reference" in s for s in self.statements)


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


def test_publishing_a_cadastre_release_propagates_the_spatial_reference() -> None:
    """Publier DS-01 doit aligner les identités canoniques, pas seulement le pointeur.

    `reference.refresh_cadastre_spatial_reference` n'avait aucun appelant applicatif :
    déplacer `meta.active_dataset_release` laissait `reference.parcel`,
    `reference.area` et `reference.property_unit` sur la release précédente jusqu'à
    ce qu'un opérateur pense à lancer la fonction à la main.
    """
    connection = FakeConnection(data_source_id="DS-01")

    counts = catalog_for(connection).publish(
        "DS-01@2026-06-01", "35", actor="bruno@manty.eu", reason="verdict B1"
    )

    assert connection.propagation_was_queried
    assert counts is not None
    assert (counts.area_count, counts.parcel_count, counts.property_unit_count) == (
        332,
        1_333_327,
        1_333_327,
    )


def test_propagation_runs_inside_the_publication_transaction_as_pipeline_rw() -> None:
    """Deux propriétés indissociables de la correction.

    La fonction lit `meta.active_dataset_release`, donc elle doit suivre le
    déplacement du pointeur ; et elle doit rester dans la même transaction, sinon un
    échec de propagation laisserait une release active dont le référentiel canonique
    décrit une autre release. `EXECUTE` n'étant accordé qu'à `pipeline_rw`, l'appel
    doit aussi tomber entre le `SET LOCAL ROLE` et le `RESET ROLE`.
    """
    connection = FakeConnection(data_source_id="DS-01")

    catalog_for(connection).publish(
        "DS-01@2026-06-01", "35", actor="bruno@manty.eu", reason="verdict B1"
    )

    propagation = connection.index_of("refresh_cadastre_spatial_reference")
    assert connection.index_of("SET LOCAL ROLE pipeline_rw") < propagation
    assert connection.index_of("publish_dataset_release") < propagation
    assert propagation < connection.index_of("RESET ROLE")
    assert connection.commits_before[propagation] == 0
    assert connection.commits == 1


def test_publishing_a_non_cadastre_release_propagates_nothing() -> None:
    """La fonction ne connaît que le cadastre : elle lit `DS-01` en dur et alimente les
    identités parcellaires. Publier DS-05 ne doit rien y déclencher."""
    connection = FakeConnection(data_source_id="DS-05")

    counts = catalog_for(connection).publish(
        "DS-05@2026-06-17", "35", actor="bruno@manty.eu", reason="verdict B1"
    )

    assert not connection.propagation_was_queried
    assert counts is None


def test_a_rollback_publication_realigns_the_spatial_reference_too() -> None:
    """Un retour arrière déplace le pointeur autant qu'une publication : le référentiel
    doit suivre dans les deux sens, sans quoi il décrirait la release retirée."""
    connection = FakeConnection(data_source_id="DS-01")

    catalog_for(connection).publish(
        "DS-01@2026-05-01",
        "35",
        actor="bruno@manty.eu",
        reason="retour arrière",
        action="rollback",
    )

    assert connection.propagation_was_queried
