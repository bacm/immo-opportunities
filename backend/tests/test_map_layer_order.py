"""Les fonds de carte ne se montent ni ne se démontent — ils se masquent.

Une source MapLibre ajoutée après coup se place en **fin** de pile, donc au-dessus de tout ce
qui existait déjà. En rendant le fond conditionnellement, le remplissage des parcelles passait
par-dessus les géométries du cas de revue : il n'en restait visible que la part débordant du
parcellaire, soit un mince trait sur un bord. Le relecteur voyait un trait là où il y avait un
bâtiment de 91 m².

Le même piège attend l'orthophoto de l'Explorer, qui recouvrirait parcelles et bâtiments.

L'invariant tenable est simple : toute source est déclarée une fois, inconditionnellement, et
l'ordre du JSX fixe l'ordre de la pile une bonne fois pour toutes. Ce qui varie est la
`visibility` des couches — MapLibre ne télécharge alors aucune tuile et retire l'attribution.

Ce test lit le source faute de banc WebGL dans `make check`.
"""

import re
from pathlib import Path

import pytest

WEB_SOURCES = (
    Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "review" / "ReviewMap.tsx",
    Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "RealMap.tsx",
)

# `{orthophoto && <Source` ou `{orthophoto ? <Source` — un fond dont le montage est conditionnel.
CONDITIONAL_SOURCE = re.compile(r"[?&]{1,2}\s*<Source\b")
# Les commentaires citent le motif interdit pour l'expliquer : les retirer avant de chercher.
COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


def _code(source: Path) -> str:
    return COMMENT.sub("", source.read_text(encoding="utf-8"))


# Une couche de fond, raster ou parcellaire, dont l'affichage depend du mode choisi.
BASE_LAYER = re.compile(
    r"<Layer\b[^>]*id=\"(ign-background|review-base-layer|review-parcels-[a-z]+)\"[^>]*>"
)


@pytest.mark.parametrize("source", WEB_SOURCES, ids=lambda path: path.name)
def test_aucune_source_montee_conditionnellement(source: Path) -> None:
    assert not CONDITIONAL_SOURCE.search(_code(source)), (
        f"{source.name} monte une <Source> conditionnellement. Une source ajoutée après coup "
        "passe au-dessus des couches déjà présentes : déclarer la source une fois et basculer "
        "`layout.visibility` sur ses couches."
    )


@pytest.mark.parametrize("source", WEB_SOURCES, ids=lambda path: path.name)
def test_les_couches_de_fond_basculent_par_visibility(source: Path) -> None:
    text = _code(source)
    layers = BASE_LAYER.findall(text)
    assert layers, f"{source.name} ne déclare plus de couche de fond identifiable."
    for match in BASE_LAYER.finditer(text):
        assert "visibility:" in match.group(0), (
            f"La couche de fond {match.group(1)} de {source.name} ne porte pas de "
            "`layout.visibility` : elle resterait affichée dans les deux modes."
        )


@pytest.mark.parametrize("source", WEB_SOURCES, ids=lambda path: path.name)
def test_le_plan_ign_reste_hors_de_la_pile(source: Path) -> None:
    """PLANIGNV2 est généralisé et déplacé pour la lisibilité : il décale visiblement le fond."""
    text = source.read_text(encoding="utf-8")
    assert "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2" not in text, (
        f"{source.name} réintroduit le Plan IGN. C'est un produit cartographique, pas une "
        "référence géométrique : superposé à nos géométries il montre une translation qui "
        "n'existe pas dans les données."
    )
