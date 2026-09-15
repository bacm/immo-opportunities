"""Les invariants doivent attraper l'arrangement sans signaler l'usage légitime.

Un contrôle bruyant est un contrôle qu'on désactive : chaque motif est donc éprouvé
dans les deux sens, sur le cas coupable et sur le cas innocent qui lui ressemble.
"""

import pytest


def diff(path: str, added: list[str] | None = None, removed: list[str] | None = None) -> str:
    lines = [f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}", "@@ -10,0 +10,1 @@"]
    lines += [f"-{line}" for line in removed or []]
    lines += [f"+{line}" for line in added or []]
    return "\n".join(lines) + "\n"


def findings(module, text: str) -> list[str]:
    return module.check(*module.parse(text))


def names(module, text: str) -> set[str]:
    return {f.split("[")[1].split("]")[0] for f in findings(module, text)}


@pytest.mark.parametrize(
    "line,attendu",
    [
        ("df = df.fillna(0)", True),
        ("coalesce(ranked.cover_ratio, 0),", True),
        ("const surface = parcel.area ?? 0;", True),
        # Un agrégat sur un ensemble vide vaut légitimement zéro : ce n'est pas une valeur
        # manquante, c'est une absence de lignes.
        ("SELECT coalesce(sum(record_count), 0) AS eligible,", False),
        ("coalesce(count(*), 0)", False),
        ("total_pages = int(payload.get('total_pages') or 0) or 1", False),
    ],
)
def test_valeur_manquante_en_zero(diff_invariants, line, attendu):
    got = "valeur-manquante-en-zero" in names(diff_invariants, diff("pipelines/src/a.py", [line]))
    assert got is attendu


@pytest.mark.parametrize(
    "line,attendu",
    [
        ('RELEASE = "latest"', True),
        ("url = f'{BASE}/latest/file.zip'", True),
        ("latest_release = pinned_release(dataset)", False),
    ],
)
def test_alias_latest(diff_invariants, line, attendu):
    got = "alias-latest" in names(diff_invariants, diff("pipelines/src/a.py", [line]))
    assert got is attendu


@pytest.mark.parametrize(
    "line,attendu",
    [
        ("DIVISION_THRESHOLD = 0.35", True),
        ("percentile_haut = 90", True),
        ("if ratio > 0:", False),
        ("threshold = profile.percentile(feature)", False),
    ],
)
def test_seuil_invente(diff_invariants, line, attendu):
    path = "pipelines/src/immo_pipelines/scoring/engine.py"
    got = "seuil-invente" in names(diff_invariants, diff(path, [line]))
    assert got is attendu


@pytest.mark.parametrize(
    "path,attendu",
    [
        ("pipelines/src/immo_pipelines/market_data/dvf.py", True),
        ("pipelines/tests/test_dvf.py", False),
    ],
)
def test_donnee_simulee_hors_des_tests(diff_invariants, path, attendu):
    line = "rows = [dummy_transaction() for _ in range(10)]"
    got = "donnee-simulee" in names(diff_invariants, diff(path, [line]))
    assert got is attendu


@pytest.mark.parametrize(
    "line,attendu",
    [
        ("@pytest.mark.skip(reason='trop long')", True),
        ("test.skip('publie un score', async ({ page }) => {", True),
        ("    assert True", True),
        # Une garde d'exécution — l'échantillon est épuisé — n'est pas un renoncement.
        ("test.skip(!(await caseAvailable(page)), 'échantillon entièrement jugé')", False),
    ],
)
def test_test_affaibli(diff_invariants, line, attendu):
    got = "test-affaibli" in names(diff_invariants, diff("apps/web/tests/e2e/a.spec.ts", [line]))
    assert got is attendu


def test_assertion_supprimee_dans_un_test(diff_invariants):
    text = diff("backend/tests/test_a.py", removed=["    assert response.status_code == 200"])
    assert "assertion-supprimee" in names(diff_invariants, text)


def test_assertion_supprimee_justifiee_dans_le_meme_fichier(diff_invariants):
    text = diff(
        "backend/tests/test_a.py",
        added=["    # invariant-ok: assertion-supprimee — la route a disparu"],
        removed=["    assert response.status_code == 200"],
    )
    assert findings(diff_invariants, text) == []


def test_echappatoire_sur_la_ligne(diff_invariants):
    line = "df = df.fillna(0)  # invariant-ok: colonne de comptage, pas une mesure"
    assert findings(diff_invariants, diff("pipelines/src/a.py", [line])) == []


def test_le_controle_ne_se_signale_pas_lui_meme(diff_invariants):
    text = diff("scripts/check-diff-invariants", ["r'\\.fillna\\(0'"])
    assert findings(diff_invariants, text) == []


def test_la_documentation_est_hors_perimetre(diff_invariants):
    text = diff("docs/data/a.md", ["ne jamais écrire `fillna(0)` sur une mesure"])
    assert findings(diff_invariants, text) == []
