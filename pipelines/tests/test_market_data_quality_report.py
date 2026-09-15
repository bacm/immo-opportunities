"""Le rapport qualité métier — D5.

Le rendu est une fonction pure : il se teste sans base. Les invariants qui portent sur le SQL
sont vérifiés sur son texte, faute de banc PostgreSQL dans `make check` — même convention que
`test_spatial_matching_report.py`.
"""

import importlib.util
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "market_data_quality_report.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("quality_report", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _data(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "verdicts": [
            {
                "data_source_id": "DS-06",
                "name": "DVF+",
                "releases": 1,
                "accepted": 0,
                "display_only": 1,
                "pending": 0,
                "import_runs": 0,
            }
        ],
        "volumes": [
            {
                "data_source_id": "DS-06",
                "unit": "transactions",
                "records": 133066,
                "communes": 333,
                "freshest": "2025-12-31",
            }
        ],
        "completeness": [
            {
                "feature_code": "URB-001",
                "total": 100,
                "present": 40,
                "not_accepted": 50,
                "value_missing": 0,
                "not_applicable": 0,
                "ambiguous": 10,
                "invalid_geometry": 0,
                "calculation_error": 0,
            }
        ],
        "distributions": [
            {
                "feature_code": "LAND-001",
                "observed": 10,
                "minimum": 1,
                "q1": 2,
                "median": 3,
                "q3": 4,
                "maximum": 5,
            }
        ],
        "worst": [
            {
                "commune_code": "35001",
                "commune_name": "ACIGNE",
                "units": 10,
                "present": 1,
                "feature_rows": 50,
            }
        ],
        "vocabulary": {
            "clay_zone_communes": 332,
            "gaspar_labels": [
                {"risk_type": "Tassements différentiels", "communes": 76},
                {"risk_type": "flood", "communes": 96},
            ],
        },
    }
    base.update(overrides)
    return base


def test_the_reason_breakdown_sums_to_the_total() -> None:
    """L'invariant central de D5 : présentes + absences par motif = volume, par feature."""
    rendered = load().render(_data(), "35", "2026-09-15")
    assert "| `URB-001` | 100 | 40 | 50 | 0 | 0 | 10 | oui |" in rendered


def test_a_missing_reason_that_does_not_add_up_is_announced() -> None:
    """Un motif d'absence non prévu ne doit pas se perdre dans un arrondi."""
    broken = _data(
        completeness=[
            {
                "feature_code": "URB-001",
                "total": 100,
                "present": 40,
                "not_accepted": 0,
                "value_missing": 0,
                "not_applicable": 0,
                "ambiguous": 0,
                "invalid_geometry": 0,
                "calculation_error": 0,
            }
        ]
    )
    assert "**NON**" in load().render(broken, "35", "2026-09-15")


def test_no_share_is_published_without_its_volume() -> None:
    rendered = load().render(_data(), "35", "2026-09-15")
    # La commune defavorable publie son compte d'unites et de lignes, pas seulement une part.
    assert "| ACIGNE (35001) | 10 | 1 | 50 | 2,00 % |" in rendered


def test_a_source_without_an_import_run_is_named() -> None:
    """Un verdict sans import traçable derrière lui est une anomalie, pas un détail."""
    rendered = load().render(_data(), "35", "2026-09-15")
    # invariant-ok: assertion-supprimee — le libellé fixe « sans qu'aucun run ne l'appuie »
    # est remplacé par un libellé dérivé du tableau, qui nomme la source ; l'assertion suit.
    assert "DS-06 n'en a aucun" in rendered
    assert "BUG-14" in rendered


def test_the_traceability_verdict_is_derived_and_not_hardcoded() -> None:
    """Un rapport généré ne doit pas affirmer un défaut corrigé.

    La première version écrivait le constat en dur : après BUG-14, le tableau disait que les
    quatre sources avaient un run et le paragraphe en dessous soutenait le contraire.
    """
    traced = _data(
        verdicts=[
            {
                "data_source_id": "DS-06",
                "name": "DVF+",
                "releases": 1,
                "accepted": 0,
                "display_only": 1,
                "pending": 0,
                "import_runs": 1,
            }
        ]
    )
    rendered = load().render(traced, "35", "2026-09-15")
    assert "Chaque release porte au moins un run d'import réussi" in rendered
    assert "n'en a aucun" not in rendered


def test_the_vocabulary_gap_is_measured_and_not_arbitrated() -> None:
    """Deux libellés ne sont pas déclarés équivalents sans source qui le dise."""
    rendered = load().render(_data(), "35", "2026-09-15")
    assert "`Tassements différentiels` | 76" in rendered
    assert "serait une interprétation que le contrat DS-09 ne porte pas" in rendered


def test_unmaterialised_families_state_their_obstacle() -> None:
    rendered = load().render(_data(), "35", "2026-09-15")
    for family in ("MKT-001..005", "REN-001..008", "RISK-001..004", "BLD-001..003"):
        assert family in rendered
    assert "BUG-13" in rendered


def test_the_report_is_regenerated_by_one_command() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "market-data-quality:" in makefile
    assert "market_data_quality_report.py" in makefile
