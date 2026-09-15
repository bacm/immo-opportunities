"""Le plafond doit attraper le débordement, et le document réel doit s'y tenir.

Le second test est le seul qui protège vraiment : un contrôle qui passe parce que
personne ne l'exécute sur la vraie arborescence ne protège rien.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_signale_le_depassement(doc_budget):
    breaches = doc_budget.check({"A.md": 100}, {"A.md": 142})
    assert len(breaches) == 1
    assert "142 lignes" in breaches[0] and "42 de trop" in breaches[0]


def test_ne_signale_ni_en_dessous_ni_a_egalite(doc_budget):
    assert doc_budget.check({"A.md": 100}, {"A.md": 99}) == []
    assert doc_budget.check({"A.md": 100}, {"A.md": 100}) == []


def test_les_documents_du_depot_tiennent_dans_leur_plafond(doc_budget):
    measured = doc_budget.sizes(ROOT, doc_budget.BUDGETS)
    assert doc_budget.check(doc_budget.BUDGETS, measured) == []
