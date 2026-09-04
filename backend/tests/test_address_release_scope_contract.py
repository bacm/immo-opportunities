"""Aucune adresse ne sort de l'API sans release DS-05 activée.

Les tests d'API monkeypatchent la couche de données : le filtrage par release active
n'est donc couvert par aucun test de comportement. Il l'est ici sur le SQL lui-même,
faute de banc PostgreSQL dans `make check`.

L'invariant vaut pour *toute* requête lisant `reference.address` : la table conserve les
adresses de toute release importée, activée ou non. Une requête qui oublierait la clause
d'activation exposerait des adresses d'une release au verdict encore inconnu.
"""

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[1] / "src" / "immo"
MODULES = ("spatial.py", "explorer.py")


def sql_literals(module: str) -> list[str]:
    """Tous les littéraux de chaîne du module, y compris ceux passés à `text()`."""
    tree = ast.parse((SOURCE_ROOT / module).read_text(encoding="utf-8"))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def address_queries() -> list[tuple[str, str]]:
    found = [
        (module, literal)
        for module in MODULES
        for literal in sql_literals(module)
        if "FROM reference.address" in literal
    ]
    assert found, "aucune requête sur reference.address trouvée"
    return found


def test_every_address_query_requires_an_activated_ds05_release() -> None:
    for module, query in address_queries():
        assert "meta.active_dataset_release" in query, module
        assert "data_source_id = 'DS-05'" in query, module


def test_activation_is_scoped_to_the_department_of_the_address() -> None:
    """Une release activée sur le 35 ne doit pas exposer les adresses du 29 : sans le
    scope, la première activation départementale ouvrirait toute la table."""
    for module, query in address_queries():
        assert "active.scope_type = 'department'" in query, module
        assert "active.scope_code = address.department_code" in query, module


def test_the_activation_clause_binds_the_release_that_last_carried_the_address() -> None:
    """`last_release_id` et non `first_release_id` : une adresse disparue d'une release
    ultérieure ne doit pas rester visible au titre de sa première apparition."""
    for module, query in address_queries():
        assert "active.release_id = identifier.last_release_id" in query, module


def test_address_queries_never_widen_to_the_analysis_scope() -> None:
    """La recherche et la carte acceptent `display_only` : elles lisent le pointeur de
    publication, jamais la vue restreinte aux releases analysables — sinon une release
    acceptée pour le seul affichage cesserait d'alimenter la carte."""
    for module, query in address_queries():
        assert "meta.analysis_dataset_release" not in query, module
