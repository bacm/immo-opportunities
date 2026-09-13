"""Regrouper les enregistrements contigus en bâtiments physiques — BUG-12.

Le comptage naïf surestime de 44 % sur le 35 : 741 379 enregistrements RNB pour 514 859 bâtiments
réels. Les contrats `LAND-002` et `LAND-009` demandaient des bâtiments physiques dédupliqués
depuis le début ; c'est l'implémentation qui manquait.

Ces tests portent sur le texte du script, faute de banc PostGIS dans `make check`. Les
vérifications de fond — convergence entre deux levés indépendants, effet sur les features — sont
dans `docs/data/physical-building-grouping-35.md`.
"""

from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_physical_buildings.py"
TEXT = SCRIPT.read_text(encoding="utf-8")


def test_aucune_donnee_source_n_est_modifiee() -> None:
    """Le regroupement est une entité de plus, pas une réécriture du bâti importé."""
    for table in ("reference.building", "reference.active_cadastral_building"):
        for verbe in ("UPDATE " + table, "DELETE FROM " + table, "INSERT INTO " + table):
            assert verbe not in TEXT, (
                f"`{verbe}` touche la donnée source. Le regroupement doit être dérivé et "
                "réversible : chaque identifiant source reste atteignable."
            )


def test_l_identifiant_du_groupe_est_deterministe() -> None:
    """Sinon une reconstruction produirait d'autres identifiants pour les mêmes bâtiments."""
    assert "min(clustered.building_id) OVER" in TEXT, (
        "L'identifiant doit dériver du plus petit membre. L'indice de grappe rendu par "
        "ST_ClusterDBSCAN dépend de l'ordre de lecture et n'est pas reproductible."
    )


def test_la_version_de_regroupement_entre_dans_l_identifiant() -> None:
    """Leçon de BUG-09 : une clé sans version rend un changement de méthode inapplicable."""
    assert "GROUPING_VERSION" in TEXT
    assert "'physical:' || %(source)s || ':' || %(version)s" in TEXT


def test_la_reconstruction_efface_la_version_precedente() -> None:
    """Sans cela, deux regroupements coexisteraient et le comptage verrait double."""
    assert "DELETE FROM reference.physical_building" in TEXT
    assert "AND grouping_version = %s" in TEXT


def test_le_seuil_de_contiguite_est_explicite_et_justifie() -> None:
    """Un paramètre géométrique muet est un seuil inventé qui ne dit pas son nom."""
    assert "EPSILON_METRES = 0.01" in TEXT
    assert "mur" in TEXT, "le choix de 1 cm doit porter sa justification en commentaire"


@pytest.mark.parametrize("source", ["rnb", "cadastre"])
def test_les_deux_sources_sont_regroupables(source: str) -> None:
    """La convergence entre deux levés indépendants est la validation du critère."""
    assert f'"{source}"' in TEXT
