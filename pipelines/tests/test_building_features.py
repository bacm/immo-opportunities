"""Features de bâtiment sur le bâtiment physique — BUG-13, ADR-024.

La migration se teste sur son texte, faute de banc PostgreSQL dans `make check` ; l'exécution
réelle, upgrade et downgrade, est consignée dans le ticket.
"""

import importlib.util
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipelines" / "scripts" / "compute_building_features.py"
MIGRATION = (
    REPO
    / "backend"
    / "migrations"
    / "versions"
    / "20260917_0028_physical_building_feature_subject.py"
)


def load(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migration_text(function: str) -> str:
    source = MIGRATION.read_text(encoding="utf-8")
    start = source.index(f"def {function}()")
    end = source.find("\ndef ", start + 1)
    return source[start:] if end < 0 else source[start:end]


def test_la_migration_suit_celle_des_indicateurs_territoriaux() -> None:
    module = load(MIGRATION)
    assert module.revision == "20260917_0028"
    assert module.down_revision == "20260917_0027"


def test_le_sujet_reste_une_exclusion_stricte_a_trois_colonnes() -> None:
    module = load(MIGRATION)
    assert module.SUBJECT_COLUMNS == ("property_unit_id", "building_id", "physical_building_id")
    upgrade = migration_text("upgrade")
    assert "num_nonnulls({" in upgrade
    assert ") = 1)" in upgrade
    assert "REFERENCES reference.physical_building(id) ON DELETE CASCADE" in upgrade
    assert "UNIQUE NULLS NOT DISTINCT ({" in upgrade


def test_une_feature_de_batiment_ne_peut_pas_s_ecrire_sur_un_enregistrement() -> None:
    module = load(MIGRATION)
    upgrade = migration_text("upgrade")
    assert "building_id IS NULL OR feature_code !~" in upgrade
    assert module.BUILDING_FAMILIES_PATTERN == "^(BLD|REN)-"
    for code in load(SCRIPT).FEATURE_CODES:
        assert code.startswith(("BLD-", "REN-"))


def test_le_downgrade_retablit_le_schema_sans_toucher_aux_unites_foncieres() -> None:
    downgrade = migration_text("downgrade")
    assert "DELETE FROM feature.feature_value WHERE physical_building_id IS NOT NULL" in downgrade
    assert "property_unit_id IS NOT NULL" not in downgrade
    assert "num_nonnulls(property_unit_id, building_id) = 1" in downgrade
    assert "(property_unit_id, building_id, feature_code, feature_version)" in downgrade
    assert "DROP COLUMN physical_building_id" in downgrade


def test_les_ecritures_existantes_visent_la_nouvelle_identite() -> None:
    """Un ON CONFLICT sur l'ancienne identité échouerait une fois la contrainte remplacée."""
    target = "ON CONFLICT (property_unit_id, building_id, physical_building_id, feature_code,"
    for name in ("compute_morphology_features.py", "compute_urban_features.py"):
        text = (REPO / "pipelines" / "scripts" / name).read_text(encoding="utf-8")
        assert target in text
        assert "ON CONFLICT (property_unit_id, building_id, feature_code" not in text
    assert "physical_building_id, feature_code, feature_version)" in load(SCRIPT).UPSERT


def test_le_sujet_ecrit_est_le_regroupement_rnb() -> None:
    script = load(SCRIPT)
    assert script.GROUPING_SOURCE == "rnb"
    assert "building.source = %(grouping)s" in script.UPSERT
    codes = ("BLD-001", "BLD-002", "BLD-003", *(f"REN-00{i}" for i in range(1, 9)))
    assert tuple(script.FEATURE_CODES) == codes


def test_l_absence_n_est_jamais_une_valeur() -> None:
    script = load(SCRIPT)
    assert script.MISSING_REASON == "source_not_accepted"
    assert "numeric_value = NULL" in script.UPSERT
    assert "text_value = NULL" in script.UPSERT
    assert "json_value = NULL" in script.UPSERT


def test_une_release_acceptee_bloque_l_ecriture() -> None:
    script = load(SCRIPT)
    assert script.refusal({}) is None
    reason = script.refusal({"DS-07": ["DS-07@2026-10-01"]})
    assert reason is not None
    assert "DS-07@2026-10-01" in reason


def test_les_releases_citees_suivent_le_contrat_et_ignorent_les_sources_sans_release() -> None:
    script = load(SCRIPT)
    latest = {"DS-03": "DS-03@2026-02-a", "DS-07": "DS-07@2026-09-14-extract"}
    assert script.cited_releases(["DS-03", "DS-05", "DS-07"], latest) == [
        "DS-03@2026-02-a",
        "DS-07@2026-09-14-extract",
    ]


def test_le_rapport_dit_le_sujet_et_les_lignes_hors_famille() -> None:
    script = load(SCRIPT)
    data = {
        "groupings": [("cadastre", 3, 4), ("rnb", 2, 5)],
        "by_feature": [("BLD-001", "source_not_accepted", '["DS-03@x", "DS-04@y"]', 2)],
        "subjects": (10, 0, 2, 0),
    }
    text = script.render("35", data, date(2026, 9, 17))
    assert "| `rnb` | 2 | 5 |" in text
    assert "| BLD-001 | `source_not_accepted` | `DS-03@x`, `DS-04@y` | 2 |" in text
    assert "| bâtiment physique, feature hors `BLD`/`REN` | 0 |" in text
