"""Rapport de distribution des appariements — B3.

Le rendu est une fonction pure : il se teste sans base. Les invariants qui portent sur le SQL
sont vérifiés sur son texte, faute de banc PostgreSQL dans `make check` — même convention que
`test_ban_parcel_relations.py`.
"""

import re
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "spatial_matching_report.py"
REFRESH = REPO / "pipelines" / "scripts" / "refresh_spatial_matching.py"
IMPORTER = REPO / "pipelines" / "src" / "immo_pipelines" / "spatial" / "importer.py"


def load_generator() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("matching_report", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def relation_row(
    relation_type: str,
    certain: int,
    ambiguous: int,
    rejected: int,
    unmatched: int,
    not_covered: int = 0,
    communes: int = 332,
) -> dict[str, Any]:
    return {
        "relation_type": relation_type,
        "release_id": f"DS-XX@{relation_type}",
        "algorithm_code": "algo",
        "communes": communes,
        "certain": certain,
        "ambiguous": ambiguous,
        "rejected": rejected,
        "unmatched": unmatched,
        "communes_not_covered": not_covered,
    }


def minimal_data(relations: list[dict[str, Any]]) -> dict[str, Any]:
    module = load_generator()
    return {
        "commune_count": 332,
        "relations": relations,
        "methods": [],
        "confidences": {"shapes": [], "exact": [], "buckets": []},
        "cardinality": [],
        "reasons": [],
        "largest": {relation: [] for relation, _ in module.RELATIONS},
        "worst": {relation: [] for relation, _ in module.RELATIONS},
    }


def test_the_four_classes_sum_to_the_relation_total() -> None:
    """Le total affiché est la somme des quatre classes, jamais un compte parallèle."""
    module = load_generator()
    rendered = module.render(
        minimal_data([relation_row("building_parcel", 737353, 0, 0, 4010)]),
        "35",
        "2026-09-08",
    )
    # 737 353 + 4 010 = 741 363, rendu avec l'espace comme séparateur de milliers.
    assert "741 363" in rendered
    assert "737 353" in rendered


def test_unmatched_and_rejected_are_never_added_together() -> None:
    """Une absence de décision et une décision motivée restent deux colonnes."""
    module = load_generator()
    rendered = module.render(
        minimal_data([relation_row("address_parcel", 100, 20, 7, 300)]),
        "35",
        "2026-09-08",
    )
    row = next(line for line in rendered.splitlines() if "Adresse ↔ Parcelle" in line)
    cells = [cell.strip() for cell in row.split("|")]
    # certain, ambigu, rejeté, non apparié, total : cinq colonnes distinctes.
    assert cells[2:7] == ["100", "20", "7", "300", "427"]
    assert "307" not in row


def test_a_relation_with_no_metric_is_declared_absent_not_zero() -> None:
    """Une relation jamais calculée ne doit pas se lire comme un taux nul."""
    module = load_generator()
    rendered = module.render(minimal_data([]), "35", "2026-09-08")
    row = next(line for line in rendered.splitlines() if "Adresse ↔ Bâtiment" in line)
    assert "relation absente" in row
    assert "| 0 |" not in row


def test_communes_without_source_data_are_counted_apart() -> None:
    """« Non couvert » est une colonne, pas un taux de zéro."""
    module = load_generator()
    rendered = module.render(
        minimal_data([relation_row("bdnb_group_rnb", 10, 0, 0, 0, not_covered=17)]),
        "35",
        "2026-09-08",
    )
    assert "communes non couvertes" in rendered
    row = next(line for line in rendered.splitlines() if "Groupe BDNB" in line)
    assert row.rstrip().endswith("| 17 |")


def test_the_not_covered_rule_is_the_four_classes_at_zero() -> None:
    """La règle qui identifie l'absence de couverture, dans le SQL du rapport."""
    source = GENERATOR.read_text(encoding="utf-8")
    assert "communes_not_covered" in source
    assert re.search(
        r"certain_count \+ metric\.ambiguous_count\s*\+ metric\.rejected_count "
        r"\+ metric\.unmatched_count = 0",
        source,
    )


def test_every_expected_relation_is_reported() -> None:
    """Les cinq relations du ticket, dans l'ordre où il les attend."""
    module = load_generator()
    assert [relation for relation, _ in module.RELATIONS] == [
        "building_parcel",
        "address_parcel",
        "address_building",
        "bdtopo_building_rnb",
        "bdnb_group_rnb",
    ]


def test_no_rate_is_published_without_its_volume() -> None:
    """Un taux seul n'a pas de sens : Rennes et une commune de 800 ne se comparent pas."""
    source = GENERATOR.read_text(encoding="utf-8")
    for query in ("largest_communes", "extreme_communes"):
        block = source[source.index(f"def {query}") : source.index(f"def {query}") + 2000]
        assert "certain_rate" in block
        assert "AS total" in block or "total_count" in block or "AS total," in block


def test_the_report_declares_its_own_regeneration_command() -> None:
    module = load_generator()
    rendered = module.render(minimal_data([]), "35", "2026-09-08")
    assert "make matching-report DEPARTMENT=35" in rendered
    assert "**généré**" in rendered


def test_the_regeneration_command_exists_in_the_makefile() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "\nmatching-report:" in makefile
    assert "\nmatching-refresh:" in makefile
    # Le rapport recalcule avant de rendre : il ne peut pas décrire un état périmé.
    assert "matching-report: matching-refresh" in makefile


def test_metrics_are_recomputable_in_place() -> None:
    """Recalculables et stables après réimport : chaque écriture est un upsert."""
    source = IMPORTER.read_text(encoding="utf-8")
    inserts = [
        block
        for block in re.findall(r'"""([\s\S]*?)"""', source)
        if "INSERT INTO meta.entity_match_metric" in block
    ]
    assert len(inserts) == 5, f"expected five metric writers, found {len(inserts)}"
    for block in inserts:
        assert "DO UPDATE SET" in block
        assert "measured_at = clock_timestamp()" in block


def test_the_address_building_relation_no_longer_depends_on_import_order() -> None:
    """Elle était calculée pendant l'import BAN, donc vide si le RNB venait après."""
    source = IMPORTER.read_text(encoding="utf-8")
    assert "def refresh_address_building_relations" in source
    assert "def refresh_address_building_metrics" in source
    block = source[source.index("def refresh_address_building_relations") :][:4000]
    assert "recomputed_independently_of_import_order" in block
    assert "ON CONFLICT" in block


def test_statistics_are_refreshed_before_the_metrics_are_planned() -> None:
    """4 h 44 sans aboutir contre 2,2 s : le planificateur ignorait les lignes insérées."""
    source = REFRESH.read_text(encoding="utf-8")
    assert "def analyze_hot_tables" in source
    assert "meta.entity_match" in source
    # Appelé avant la métrique qui lit les relations fraîchement insérées.
    relations_at = source.index("refresh_address_building_relations(")
    metrics_at = source.index("refresh_address_building_metrics(")
    analyze_between = source.index("analyze_hot_tables(connection)", relations_at)
    assert relations_at < analyze_between < metrics_at


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "0"), (1234, "1 234"), (741363, "741 363"), (None, "—")],
)
def test_thousands_separator_matches_the_documents(value: object, expected: str) -> None:
    module = load_generator()
    assert module.thousands(value) == expected
