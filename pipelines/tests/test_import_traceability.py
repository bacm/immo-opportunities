"""Un verdict ne se prononce pas sans import traçable — BUG-14.

Le défaut trouvé par [D5] ne se lit pas dans un rapport par source : il se lit en comptant les
runs d'import. `DS-08@2026-09-14` est resté `pending` parce que la porte d'acceptation refusait —
correctement — une release sans run. `DS-06@2026-09-13` portait `display_only` **sans qu'aucun
run ne l'appuie**.

Les invariants qui portent sur le SQL sont vérifiés sur le texte des scripts, faute de banc
PostgreSQL dans `make check` — même convention que `test_dpe.py`.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "pipelines" / "scripts"
CATALOG = REPO / "pipelines" / "src" / "immo_pipelines" / "cadastre" / "catalog.py"

# Tout import d'une release metier doit laisser une trace. La liste est explicite : un script
# ajoute sans run passerait sinon inapercu, ce qui est exactement ce qui s'est produit.
IMPORTERS = (
    "import_dvf_release.py",
    "import_gpu_release.py",
    "import_dpe_release.py",
    "import_georisques_release.py",
    "import_territorial_release.py",
)


@pytest.mark.parametrize("script", IMPORTERS)
def test_every_market_importer_records_an_import_run(script: str) -> None:
    source = (SCRIPTS / script).read_text(encoding="utf-8")
    assert "INSERT INTO meta.import_run" in source, f"{script} n'écrit aucun run d'import"
    assert "UPDATE meta.import_run SET" in source, f"{script} ne clôt jamais son run"


@pytest.mark.parametrize("script", IMPORTERS)
def test_every_idempotency_key_carries_the_transformation_version(script: str) -> None:
    """Sans elle, un correctif de code n'atteint jamais les données — leçon de BUG-09."""
    source = (SCRIPTS / script).read_text(encoding="utf-8")
    block = source[source.index("idempotency_key = (") :][:400]
    assert "TRANSFORMATION_VERSION" in block, f"{script} : clé sans version de transformation"


def test_the_acceptance_gate_requires_a_successful_import() -> None:
    """La garde qui a refusé DS-08, et qui avait raison."""
    source = CATALOG.read_text(encoding="utf-8")
    gate = source[source.index("def set_acceptance") :][:900]
    assert "_require_successful_import" in gate


def test_an_interrupted_gpu_import_does_not_claim_success() -> None:
    """Un lot interrompu reste `running` : c'est ce qui empêche un verdict prématuré."""
    source = (SCRIPTS / "import_gpu_release.py").read_text(encoding="utf-8")
    closing = source[source.index("UPDATE meta.import_run SET") :][:400]
    assert "CASE WHEN %(transient)s::int > 0 THEN 'running' ELSE 'succeeded' END" in closing


def test_a_fresh_gpu_run_reimports_instead_of_resuming() -> None:
    """Un run doit dire ce qu'il a fait, pas ce qu'il a trouvé.

    La reprise existe parce qu'un import départemental demande plus d'une heure. Mais reprendre
    sans run ferait attester « 184 documents » par un run qui n'en a lu aucun.
    """
    source = (SCRIPTS / "import_gpu_release.py").read_text(encoding="utf-8")
    assert 'resuming = existing is not None and existing[1] == "running"' in source
    assert "if not resuming:" in source
    purge = source[source.index("if not resuming:") :][:300]
    assert "DELETE FROM observation.urban_document" in purge


def test_urban_features_refuse_an_unaccepted_release() -> None:
    """554 714 valeurs sont entrées en base sur une release `pending`. Plus maintenant."""
    source = (SCRIPTS / "compute_urban_features.py").read_text(encoding="utf-8")
    assert 'USABLE_ACCEPTANCE = ("accepted", "display_only")' in source
    assert "if acceptance not in USABLE_ACCEPTANCE:" in source
    guard = source[source.index("acceptance = acceptance_of(") :][:600]
    assert "return 1" in guard


def test_out_of_document_is_not_an_unaccepted_source() -> None:
    """Deux motifs d'absence, deux décisions différentes pour E1.

    « Aucune zone opposable ne couvre cette parcelle » est une valeur absente ; « la release n'a
    pas de verdict » est une source à ignorer en bloc. Les confondre rendait E1 impossible à
    conduire correctement : 776 499 absences `URB-001` se lisaient « DS-08 inutilisable » alors
    que 554 714 parcelles portaient une valeur réelle.
    """
    source = (SCRIPTS / "compute_urban_features.py").read_text(encoding="utf-8")
    computed = source[source.index("def commune_rows") : source.index("USABLE_ACCEPTANCE")]
    # Le motif ne sert plus qu'a son sens propre, et il est decide en amont de la boucle.
    assert "source_not_accepted" not in computed.replace("`source_not_accepted`", "")
    assert computed.count('"source_value_missing"') >= 2
