"""Un paramètre optionnel comparé à NULL doit être typé — BUG-07.

`(:param IS NULL OR colonne = :param)` échoue avec `AmbiguousParameter` dès que la valeur est
`NULL` : PostgreSQL ne peut pas déduire le type d'un paramètre qui n'apparaît que comparé à NULL
et à une colonne. Le motif correct est un `CAST` explicite.

Ce défaut avait rendu la recherche d'adresse — FR-001, le premier geste de l'utilisateur —
inutilisable dans son cas d'usage principal, et la route le traduisait en 503 « Spatial reference
is unavailable », ce qui désigne une panne d'infrastructure et non une erreur de programmation.

Ces tests portent sur le texte des requêtes, faute de banc PostgreSQL dans `make check`.
"""

import re
from pathlib import Path

import pytest

SOURCES = (
    Path(__file__).resolve().parents[1] / "src" / "immo" / "spatial.py",
    Path(__file__).resolve().parents[1] / "src" / "immo" / "connected_mvp.py",
    Path(__file__).resolve().parents[1] / "src" / "immo" / "scoring.py",
    Path(__file__).resolve().parents[1] / "src" / "immo" / "market_data.py",
)

# `:nom IS NULL` sans CAST autour du paramètre.
UNTYPED_OPTIONAL = re.compile(r"\(\s*:(\w+)\s+IS\s+NULL", re.IGNORECASE)


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: p.name)
def test_no_optional_parameter_is_compared_to_null_without_a_cast(source: Path) -> None:
    offenders = UNTYPED_OPTIONAL.findall(source.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{source.name}: paramètres optionnels sans CAST — {sorted(set(offenders))}. "
        "PostgreSQL lève AmbiguousParameter dès que la valeur est NULL ; "
        "écrire CAST(:param AS text) IS NULL."
    )


def test_the_address_search_types_its_optional_commune() -> None:
    """Le cas qui a réellement cassé : recherche sans filtre de commune."""
    source = (Path(__file__).resolve().parents[1] / "src" / "immo" / "spatial.py").read_text(
        encoding="utf-8"
    )
    assert "CAST(:commune_code AS text) IS NULL" in source


def test_the_match_metrics_endpoint_types_both_optional_filters() -> None:
    """Écrit la veille en B3, il portait le même défaut."""
    source = (Path(__file__).resolve().parents[1] / "src" / "immo" / "connected_mvp.py").read_text(
        encoding="utf-8"
    )
    assert "CAST(:relation_type AS text) IS NULL" in source
    assert "CAST(:commune_code AS text) IS NULL" in source
