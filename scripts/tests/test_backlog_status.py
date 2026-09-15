"""Le verrou humain est une propriété déclarée du ticket, jamais une appréciation."""

import pytest

HUMAN = "**Nature :** revue humaine · **Preuve :** docs/data/exists.md"


def ticket(**over) -> dict:
    base = {
        "id": "X1",
        "file": "X1.md",
        "title": "t",
        "version": "v",
        "size": "S",
        "state": "À faire",
        "nature": "implémentation",
        "proof": "",
        "deps": [],
        "writes": ["a.py"],
    }
    return base | over


def test_entete_bornee_au_premier_titre(backlog_status):
    """`Preuve :` réapparaît en conclusion des tickets : seul l'en-tête fait foi."""
    text = "# X — t\n\n**État :** À faire\n\n## Conclusion\n\n**Preuve :** docs/data/ailleurs.md\n"
    assert backlog_status.field(text, "État") == "À faire"
    assert backlog_status.field(text, "Preuve") is None


def test_lien_markdown_reduit_au_chemin(backlog_status):
    assert backlog_status.strip_link("[`a.md`](../data/a.md)") == "../data/a.md"
    assert backlog_status.strip_link("docs/data/a.md") == "docs/data/a.md"


@pytest.mark.parametrize(
    "nature,attendu",
    [
        ("implémentation", "**prêt**"),
        ("revue humaine", "**verrou humain**"),
        ("décision humaine", "**verrou humain**"),
    ],
)
def test_un_ticket_humain_n_est_jamais_pret(backlog_status, nature, attendu):
    t = ticket(nature=nature, proof="docs/data/a.md")
    assert backlog_status.availability(t, {"X1": t}) == attendu


def test_un_verrou_ne_masque_pas_une_dependance_non_tenue(backlog_status):
    dep = ticket(id="X0", state="À faire")
    t = ticket(nature="revue humaine", proof="docs/data/a.md", deps=["X0"])
    assert backlog_status.availability(t, {"X0": dep, "X1": t}) == "attend X0"


def test_un_verrou_sort_des_lots_menables_de_front(backlog_status):
    libre = ticket(id="X1", writes=["a.py"])
    verrou = ticket(id="X2", nature="revue humaine", proof="docs/data/a.md", writes=["b.py"])
    batches, _ = backlog_status.parallel_batches({"X1": libre, "X2": verrou})
    assert batches == [["X1"]]


def test_verrou_sans_preuve_declaree_est_une_erreur(backlog_status):
    t = ticket(nature="revue humaine")
    errors = backlog_status.check_integrity({"X1": t})
    assert any("sans `**Preuve :**`" in e for e in errors)


def test_verrou_termine_sans_preuve_sur_disque_est_une_erreur(backlog_status):
    t = ticket(nature="revue humaine", state="Terminé", proof="docs/data/absente.md")
    errors = backlog_status.check_integrity({"X1": t})
    assert any("n'existe pas" in e for e in errors)


def test_verrou_termine_avec_sa_preuve_passe(backlog_status):
    t = ticket(
        nature="revue humaine",
        state="Terminé",
        proof="docs/data/spatial-matching-manual-review-35.md",
    )
    assert backlog_status.check_integrity({"X1": t}) == []


def test_nature_hors_nomenclature_est_une_erreur(backlog_status):
    errors = backlog_status.check_integrity({"X1": ticket(nature="peut-être")})
    assert any("hors nomenclature" in e for e in errors)


def test_le_backlog_reel_est_coherent(backlog_status):
    assert backlog_status.check_integrity(backlog_status.load()) == []


def test_deux_fichiers_de_meme_identifiant_sont_signales(backlog_status, tmp_path, monkeypatch):
    """La collision faisait disparaître un ticket du tableau sans bruit — BUG-15."""
    for name in ("A4-premier.md", "A4-second.md", "A5-seul.md", "README.md"):
        (tmp_path / name).write_text("# X — t\n\n**État :** À faire\n", encoding="utf-8")
    monkeypatch.setattr(backlog_status, "BACKLOG", tmp_path)

    errors = backlog_status.duplicate_ids()

    assert len(errors) == 1
    assert "A4-premier.md" in errors[0] and "A4-second.md" in errors[0]


def test_le_backlog_reel_n_a_pas_de_doublon(backlog_status):
    assert backlog_status.duplicate_ids() == []
