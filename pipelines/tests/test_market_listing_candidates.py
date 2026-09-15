"""La liste des biens probablement en vente — E8f.

Cohortes, fenêtres et rendu sont des fonctions pures : elles se testent sans base. Les invariants
qui portent sur le SQL sont vérifiés sur son texte, faute de banc PostgreSQL dans `make check` —
même convention que `test_exploratory_candidates.py`.
"""

import importlib.util
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "market_listing_candidates.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("market_listing_candidates", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit(identifier: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "property_unit_id": f"parcel:{identifier}",
        "cadastral_id": identifier,
        "uses": "Résidentiel",
        "natures": "Indifférenciée",
        "max_dwellings": 1,
        "built_year": 1975,
        "dpe_deposited_at": date(2026, 6, 1),
        "energy_label": "D",
        "living_area_m2": "110.0",
        "diagnostics": 1,
        "last_mutation": None,
        "zone": "U|UE2c",
        "parcel_area_m2": 600.0,
        "parcel_area_m2_missing": None,
    }
    row.update(overrides)
    return row


REFERENCE = date(2026, 9, 7)


def test_la_fenetre_se_compte_depuis_l_extrait_pas_depuis_l_horloge() -> None:
    """Sinon la liste se vide toute seule à mesure que l'extrait vieillit, sans le signaler."""
    module = load()
    assert module.months_before(REFERENCE, 6) == date(2026, 3, 7)
    assert module.months_before(REFERENCE, 24) == date(2024, 9, 7)
    assert module.months_before(date(2026, 1, 31), 1) == date(2025, 12, 31)


def test_une_mutation_posterieure_au_diagnostic_ecarte_la_parcelle() -> None:
    """Le bien a déjà changé de mains : le diagnostic ne dit plus rien du marché."""
    module = load()
    vendue = unit("vendue", last_mutation=date(2026, 7, 1))
    encore = unit("encore", last_mutation=date(2020, 1, 1))
    kept, funnel = module.eligible([vendue, encore, unit("jamais")], module.Parameters())
    assert {row["cadastral_id"] for row in kept} == {"encore", "jamais"}
    assert funnel["pas de mutation depuis le diagnostic"] == 2


def test_les_deux_cohortes_sortent_de_la_meme_population() -> None:
    module = load()
    parameters = module.Parameters()
    rows = [
        unit("frais", dpe_deposited_at=date(2026, 8, 1)),
        unit("ancien", dpe_deposited_at=date(2021, 1, 1)),
        unit("entre-deux", dpe_deposited_at=date(2025, 6, 1)),
    ]
    signal, baseline = module.cohorts(rows, parameters, REFERENCE)
    assert [row["cadastral_id"] for row in signal] == ["frais"]
    assert [row["cadastral_id"] for row in baseline] == ["ancien"]


def test_la_cohorte_signal_est_ordonnee_du_plus_recent_au_plus_ancien() -> None:
    module = load()
    rows = [
        unit("juin", dpe_deposited_at=date(2026, 6, 1)),
        unit("aout", dpe_deposited_at=date(2026, 8, 1)),
        unit("juillet", dpe_deposited_at=date(2026, 7, 1)),
    ]
    signal, _ = module.cohorts(rows, module.Parameters(), REFERENCE)
    assert [row["cadastral_id"] for row in signal] == ["aout", "juillet", "juin"]


def test_un_usage_non_residentiel_ou_collectif_est_ecarte() -> None:
    module = load()
    kept, _ = module.eligible(
        [
            unit("maison"),
            unit("commerce", uses="Commercial et services"),
            unit("atelier", natures="Industriel, agricole ou commercial"),
            unit("immeuble", max_dwellings=7),
            unit("agricole", zone="A|A"),
        ],
        module.Parameters(),
    )
    assert [row["cadastral_id"] for row in kept] == ["maison"]


def test_une_parcelle_sans_diagnostic_n_entre_dans_aucune_cohorte() -> None:
    """La jointure est interne sur le diagnostic : une parcelle sans DPE n'est pas une candidate."""
    source = GENERATOR.read_text(encoding="utf-8")
    assert "JOIN diagnostic ON diagnostic.parcel_id = parcel.id" in source
    assert "LEFT JOIN diagnostic" not in source


def test_le_diagnostic_retenu_est_le_plus_recent_de_la_parcelle() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    assert "max(coalesce(assessment.deposited_at, assessment.assessment_date))" in source


def test_le_rattachement_n_utilise_que_des_relations_certaines() -> None:
    """BUG-09 : une relation bâtiment ↔ parcelle ambiguë ne prouve pas que le DPE porte ici."""
    source = GENERATOR.read_text(encoding="utf-8")
    assert source.count("link.relation_status = 'certain'") >= 2


def test_le_script_ne_publie_rien() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    for verbe in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ", "ALTER "):
        assert verbe not in source.upper(), f"le script contient {verbe.strip()}"


def _data(module: Any) -> dict[str, Any]:
    signal, baseline = module.cohorts(
        [unit("a"), unit("b", dpe_deposited_at=date(2021, 1, 1))],
        module.Parameters(),
        REFERENCE,
    )
    from immo_pipelines.market_data.exploratory import blind

    blind_rows, _ = blind(signal, baseline, 3)
    return {
        "commune": "35051",
        "parameters": module.Parameters(),
        "funnel": {"parcelles avec diagnostic": 728},
        "blind": blind_rows,
        "seed": 3,
        "reference": REFERENCE.isoformat(),
        "signal_total": len(signal),
        "baseline_total": len(baseline),
        "key_file": "docs/data/listing-candidates/35051/correspondance.csv",
    }


def test_le_rapport_dit_que_deux_tiers_ne_mutent_pas() -> None:
    """La promesse doit porter sa propre limite, pas seulement son lift."""
    module = load()
    rendu = module.render(_data(module), "2026-09-15")
    assert "Deux tiers" in rendu
    assert "35,65 %" in rendu
    assert "3,03 %" in rendu


def test_le_rapport_nomme_les_quatre_limites() -> None:
    module = load()
    rendu = module.render(_data(module), "2026-09-15")
    assert "location" in rendu
    assert "31 décembre 2025" in rendu
    assert "59 %" in rendu
    assert "un seul département" in rendu.lower()


def test_le_rapport_justifie_la_baseline() -> None:
    module = load()
    rendu = module.render(_data(module), "2026-09-15")
    assert "même population" in rendu
    assert "fraîcheur du dépôt" in rendu
