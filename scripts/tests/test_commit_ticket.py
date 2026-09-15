"""Un commit qui touche le code sans ticket doit être vu, et lui seul.

Le dernier test est le seul qui protège vraiment : les autres éprouvent la règle sur
des cas fabriqués, celui-là l'applique à l'historique réel du dépôt.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Le commit qui précède l'écriture de la règle. Au-delà, tout commit touchant autre
# chose que `docs/` porte son ticket ou justifie son absence.
DEPUIS = "96f12f4"


def commit(subject: str, paths: list[str], body: str = "") -> dict:
    return {"sha": "abc1234", "subject": subject, "body": body, "paths": paths}


@pytest.mark.parametrize(
    "sujet,attendu",
    [
        ("D5 — Rapports qualité métier", {"D5"}),
        ("D1, D6a — Un bien décrit deux fois", {"D1", "D6a"}),
        ("BUG-12 — Compter des enregistrements", {"BUG-12"}),
        # Le tiret cadratin délimite : sans lui, aucun identifiant n'est déclaré.
        ("D5 Rapports qualité métier", set()),
        ("Pipelines — Annoncer l'avancement d'un lot long", set()),
        # L'identifiant vient avant le tiret, pas dans la description.
        ("v0.3 — BUG-05, B2b et B2a importées", set()),
    ],
)
def test_identifiants_du_sujet(commit_ticket, sujet, attendu):
    assert commit_ticket.subject_ids(sujet) == attendu


def test_les_identifiants_connus_viennent_du_backlog(commit_ticket):
    known = commit_ticket.known_ids(ROOT)
    assert {"A5", "BUG-12", "D6a"} <= known
    assert "A9" not in known


def test_docs_seul_ne_demande_pas_de_ticket(commit_ticket):
    entries = [commit("Roadmap — Découpler D3 et D4", ["docs/backlog/README.md"])]
    assert commit_ticket.check(entries, {"D5"}) == []


def test_le_code_sans_identifiant_est_signale(commit_ticket):
    entries = [commit("Pipelines — Annoncer l'avancement", ["pipelines/src/a.py"])]
    findings = commit_ticket.check(entries, {"D5"})
    assert len(findings) == 1
    assert "aucun identifiant" in findings[0]


def test_un_identifiant_absent_du_backlog_est_refuse(commit_ticket):
    """Sans quoi « A9 — … » suffirait à passer le contrôle."""
    entries = [commit("A9 — Un ticket qui n'existe pas", ["backend/src/immo/a.py"])]
    findings = commit_ticket.check(entries, {"D5"})
    assert len(findings) == 1
    assert "inconnu du backlog" in findings[0]


def test_l_echappatoire_est_reconnue_dans_le_corps(commit_ticket):
    entries = [
        commit(
            "Conformer deux fichiers de tests à ruff format",
            ["backend/tests/test_a.py"],
            body="ticket-ok: reformatage seul, aucun comportement modifié.",
        )
    ]
    assert commit_ticket.check(entries, {"D5"}) == []


def test_l_echappatoire_ne_vaut_pas_depuis_le_sujet(commit_ticket):
    """Une échappatoire doit être motivée, donc écrite là où il y a la place de le faire."""
    entries = [commit("ticket-ok: pas le temps", ["backend/src/immo/a.py"])]
    assert len(commit_ticket.check(entries, {"D5"})) == 1


def test_l_historique_depuis_la_regle_est_rattache(commit_ticket):
    entries = commit_ticket.commits(DEPUIS, "HEAD")
    # Un clone superficiel ne verrait aucun commit et le test passerait sans rien lire.
    assert entries, f"aucun commit lu depuis {DEPUIS} — historique tronqué ?"
    assert commit_ticket.check(entries, commit_ticket.known_ids(ROOT)) == []
