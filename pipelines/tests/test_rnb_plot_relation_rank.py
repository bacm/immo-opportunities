"""La relation bâtiment ↔ parcelle ne se déclare plus certaine par défaut — BUG-09.

Le défaut tenait en une ligne : `greatest(0.9, …)` plancherisait la confiance, si bien qu'un
contact à 0,27 % ressortait avec la même décision et presque la même confiance qu'un bâtiment
entièrement posé sur sa parcelle. La revue manuelle du 13 septembre 2026 a jugé fausses 15 des
40 relations tirées, et **toutes** portaient une confiance de 0,90000 pile, c'est-à-dire le
plancher.

Le correctif ne calcule rien de neuf. Le RNB publie lui-même la part occupée sur chaque parcelle,
et le moteur la stockait déjà : il suffit de cesser de l'écraser, et de réserver `certain` à la
parcelle qui porte la plus grande part du bâtiment.

C'est un **rang**, pas un seuil — ce qui importe parce qu'aucun seuil territorial ne peut être
inventé avant le profiling. Le relecteur a d'ailleurs jugé fausse une relation à 12,4 % de
recouvrement et juste une autre à 15,6 % : aucun seuil ne reproduit ces deux verdicts, le rang
les reproduit tous les deux.

Ces tests portent sur le texte de la requête, faute de banc PostgreSQL dans `make check`. La
logique a été validée à part contre les 35 verdicts humains : 34 accords.
"""

import re
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "immo_pipelines" / "spatial" / "importer.py"
TEXT = SOURCE.read_text(encoding="utf-8")
# Le bloc complet, depuis la CTE de rang jusqu'au ON CONFLICT : couper sur le nom de
# l'algorithme laisserait la CTE dehors, elle le precede.
PLOT_RELATION = TEXT.split("WITH plot_relation AS")[1].split("ON CONFLICT")[0]


def test_le_plancher_de_confiance_a_disparu() -> None:
    """`greatest(0.9, …)` transformait un contact marginal en certitude."""
    assert "greatest(0.9" not in TEXT, (
        "Le plancher de confiance est de retour. Il rendait indiscernables un bâtiment posé sur "
        "sa parcelle et un contact de bord, et 50,3 % des relations en sortaient à 0,90000 pile."
    )


def test_certain_est_reserve_au_rang_un() -> None:
    assert "cover_rank = 1" in PLOT_RELATION
    assert "'certain'" in PLOT_RELATION


def test_une_egalite_parfaite_ne_produit_aucune_certitude() -> None:
    """À 50 % / 50 %, le rang tranche mais la réalité non : aucune des deux n'est *la* parcelle."""
    assert "rank() OVER" in PLOT_RELATION, "row_number() choisirait arbitrairement un gagnant"
    assert "ties = 1" in PLOT_RELATION


def test_un_recouvrement_nul_ou_absent_n_est_jamais_certain() -> None:
    assert "cover_ratio IS NULL OR ranked.cover_ratio = 0" in PLOT_RELATION


def test_un_recouvrement_absent_reste_absent_avec_son_motif() -> None:
    """Règle non négociable : une valeur manquante ne devient pas zéro sans motif écrit."""
    assert "missing_reason" in PLOT_RELATION
    assert "bdg_cover_ratio absent from the RNB plot entry" in PLOT_RELATION


def test_la_version_d_algorithme_est_incrementee() -> None:
    """Sans cela, `ON CONFLICT DO NOTHING` laisserait les relations fautives en place."""
    assert "'rnb-plot-relation', '2'" in TEXT
    assert "algorithm_version = '2'" in TEXT, (
        "La table `reference.building_parcel` lirait encore la version 1."
    )


@pytest.mark.parametrize(
    "expected",
    [
        "Parcel carrying the largest share of this RNB building",
        "Tied for the largest share: no parcel can be called certain",
        "Secondary parcel: another one carries a larger share",
    ],
)
def test_chaque_decision_porte_sa_justification(expected: str) -> None:
    """Une décision sans motif lisible est invérifiable en revue."""
    assert expected in PLOT_RELATION


def test_le_rang_est_conserve_en_preuve() -> None:
    """Le rang doit être relisible sans refaire le calcul, pour E1 comme pour une revue."""
    assert re.search(r"'cover_rank',\s*ranked\.cover_rank", PLOT_RELATION)
