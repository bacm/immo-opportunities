"""Une relation `cad_parcelles` non résoluble doit être rejetée avec motif, jamais perdue.

L'appariement adresse ↔ parcelle joignait `reference.parcel` en jointure interne : une
référence cadastrale que le référentiel actif ne contient pas ne produisait aucune ligne.
La perte était totale et muette — et `meta.entity_match_metric.rejected_count`, alimenté
depuis `decision = 'rejected'`, valait structurellement zéro puisque aucun chemin de code
ne produisait cette décision.

Ces tests portent sur le SQL de l'importeur, faute de banc PostgreSQL dans `make check`.
La vérification sur données réelles est consignée dans `docs/data/`.
"""

import re
from pathlib import Path

IMPORTER = Path(__file__).parents[1] / "src" / "immo_pipelines" / "spatial" / "importer.py"


def importer_source() -> str:
    return IMPORTER.read_text(encoding="utf-8")


def parcel_relation_block() -> str:
    """Le seul INSERT de relations adresse ↔ parcelle issu de `cad_parcelles`."""
    source = importer_source()
    blocks = re.findall(
        r"WITH candidates AS MATERIALIZED \([\s\S]*?\) DO NOTHING",
        source,
    )
    matching = [block for block in blocks if "ban-cad-parcelles" in block]
    assert len(matching) == 1, f"{len(matching)} bloc(s) ban-cad-parcelles, attendu 1"
    return matching[0]


def test_an_unknown_cadastral_reference_survives_the_join() -> None:
    """En jointure interne, la référence inconnue disparaissait sans trace."""
    block = parcel_relation_block()

    assert "LEFT JOIN reference.parcel AS parcel" in block
    assert "LEFT JOIN reference.parcel_geometry AS geometry" in block
    assert "JOIN reference.parcel AS parcel ON" not in block


def test_the_two_failure_modes_are_distinguished() -> None:
    """« Parcelle inconnue » et « géométrie non publiée » n'appellent pas le même examen :
    la première met en cause la référence source, la seconde l'état de publication."""
    block = parcel_relation_block()

    assert "'unresolved_cadastral_reference'" in block
    assert "'unpublished_parcel_geometry'" in block
    assert "AS resolution" in block


def test_an_unresolvable_reference_is_rejected_with_zero_confidence() -> None:
    block = parcel_relation_block()

    assert "WHEN candidate.resolution <> 'resolved' THEN 'rejected'" in block
    assert "WHEN candidate.resolution <> 'resolved' THEN 0" in block


def test_a_rejected_relation_never_claims_to_block_publication() -> None:
    """`entity_match_blocking_consistency` n'autorise `blocks_publication` que sur une
    décision `ambiguous`. Un rejet qui prétendrait bloquer violerait la contrainte et
    ferait échouer l'import entier."""
    block = parcel_relation_block()

    assert "candidate.resolution = 'resolved' AND NOT candidate.within_ten_meters" in block


def test_the_motive_is_carried_by_the_row_itself() -> None:
    """« Rejetée avec motif » : le motif doit voyager avec la relation, pas rester dans un
    journal. La reprise d'audit lit `meta.entity_match`, pas les logs d'import."""
    block = parcel_relation_block()

    assert "'resolution', candidate.resolution" in block
    assert "'source_cadastral_id', candidate.cadastral_id" in block
    assert "does not contain" in block


def test_an_address_without_a_position_enters_no_spatial_relation() -> None:
    """Décision BUG-03 : une position contradictoire rend l'attribut manquant. Sans
    position, aucun test spatial n'a de sens et aucune relation ne doit être inventée."""
    block = parcel_relation_block()

    assert "AND stage.geometry_wkt IS NOT NULL" in block


def test_rejections_are_counted_so_the_loss_is_never_silent() -> None:
    """Une relation rejetée enfouie dans une table de 300 000 lignes reste invisible :
    le rapport d'import doit en porter le compte."""
    source = importer_source()

    assert "def _publish_stage_and_count_rejections(" in source
    assert "'unresolved_cadastral_reference', '1'," in source
    assert "unresolved_reference_relation_count" in source
    assert "'addresses_concerned'" in source


def test_the_confidence_tiers_stay_where_a_measure_can_replace_them() -> None:
    """Les paliers 0,99 / 0,95 / 0,80 restent à justifier par la distribution observée
    (B1 §3). Ce test fige leur emplacement pour que leur recalibrage soit un changement
    visible, pas un ajustement silencieux."""
    block = parcel_relation_block()

    assert "WHEN candidate.point_covered THEN 0.99" in block
    assert "WHEN candidate.within_ten_meters THEN 0.95" in block
    assert "ELSE 0.8 END" in block
