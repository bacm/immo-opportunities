"""Le diff d'un ticket se reconstitue depuis la convention de commit du dépôt."""

import pytest


@pytest.mark.parametrize(
    "tid,subject,attendu",
    [
        ("D5", "D5 — Rapports qualité métier : ce qui se voit en croisant les sources", True),
        ("D1", "D1, D6a — Un bien décrit deux fois ne fait pas deux lots", True),
        ("D6a", "D1, D6a — Un bien décrit deux fois ne fait pas deux lots", True),
        ("BUG-12", "BUG-12 — Compter des enregistrements n'est pas compter des bâtiments", True),
        ("D1", "D5 — Rapports qualité métier", False),
        # `D6` ne doit pas capter les commits de `D6a`.
        ("D6", "D6a — Une fiche ne doit pas garder les mutations", False),
        ("D2", "Pipelines — Un lot interactif n'est pas un lot de production", False),
        ("D2", "D2 sans tiret cadratin", False),
    ],
)
def test_sujet_de_commit(ticket_dod, tid, subject, attendu):
    assert ticket_dod.subject_matches(tid, subject) is attendu


@pytest.mark.parametrize(
    "path,attendu",
    [
        ("backend/tests/test_spatial.py", True),
        ("apps/web/tests/e2e/real-map.spec.ts", True),
        ("pipelines/src/immo_pipelines/spatial/importer.py", False),
    ],
)
def test_chemin_de_test(ticket_dod, path, attendu):
    assert ticket_dod.is_test(path) is attendu


def test_le_ticket_courant_est_lisible(ticket_dod):
    """Le script lit les tickets par le parseur de `backlog-status`, sans le dupliquer."""
    tickets = ticket_dod.load_backlog().load()
    assert "A3" in tickets
