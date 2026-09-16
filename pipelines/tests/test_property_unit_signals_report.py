"""Mesure des signaux de regroupement des parcelles — BUG-11.

Les regroupements et le rendu sont des fonctions pures : ils se testent sans base. Le cas 90 de
la revue B4 — `35288000DA0321` et sa dépendance `DA0322` — sert de cas de référence, comme le
ticket l'exige.
"""

from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "property_unit_signals_report.py"

DA0321 = "parcel:cadastre:35288000DA0321"
DA0322 = "parcel:cadastre:35288000DA0322"
DA0323 = "parcel:cadastre:35288000DA0323"


def load_generator() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("property_unit_signals_report", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_le_chainage_fusionne_les_groupes_qui_partagent_une_parcelle() -> None:
    module = load_generator()
    units = module.chain([["a", "b"], ["b", "c"], ["x", "y"], ["z"]])
    assert sorted(units) == [["a", "b", "c"], ["x", "y"]]


def test_une_parcelle_seule_n_est_pas_une_unite_regroupee() -> None:
    module = load_generator()
    described = module.describe(module.chain([["a"], ["b"]]), parcel_total=2)
    assert described["units"] == 0
    assert described["parcels"] == 0


def test_le_cas_90_n_est_reuni_que_si_ses_deux_parcelles_sont_dans_la_meme_unite() -> None:
    module = load_generator()
    # Ce que DVF observe réellement : la 321 est vendue avec la 323, jamais avec la 322.
    observed = module.describe(module.chain([[DA0321, DA0323]]), parcel_total=3)
    assert observed["cases"]["cas 90"] is False
    # Ce que le relecteur supposait.
    supposed = module.describe(module.chain([[DA0321, DA0322]]), parcel_total=3)
    assert supposed["cases"]["cas 90"] is True
    assert supposed["share"] == 2 / 3


def test_une_paire_dont_une_parcelle_n_a_jamais_ete_vendue_sort_du_denominateur() -> None:
    module = load_generator()
    acts = {DA0321: {"acte-2018"}, DA0323: {"acte-2018"}, "p:autre": {"acte-2020"}}
    measured = module.corroboration([(DA0321, DA0322), (DA0321, DA0323), (DA0321, "p:autre")], acts)
    assert measured == {"pairs": 3, "both_sold": 2, "together": 1, "rate": 0.5}


def test_sans_paire_vendue_le_taux_reste_absent_et_non_nul() -> None:
    module = load_generator()
    measured = module.corroboration([(DA0321, DA0322)], {})
    assert measured["rate"] is None
    assert module.percent(measured["rate"]) == "—"


def test_un_acte_d_un_seul_tenant_se_distingue_d_un_acte_disperse() -> None:
    module = load_generator()
    acts = {"contigu": ["a", "b", "c"], "disperse": ["x", "y", "z"]}
    touching = [("contigu", "a", "b"), ("contigu", "b", "c"), ("disperse", "x", "y")]
    groups, whole = module.contiguous_within(acts, touching)
    assert whole == 1
    assert sorted(groups) == [["a", "b", "c"], ["x", "y"]]


def test_les_tailles_se_rangent_dans_des_classes_fermees() -> None:
    module = load_generator()
    assert [module.size_bucket(n) for n in (2, 3, 10, 11, 500, 501)] == [
        "2",
        "3 à 5",
        "6 à 10",
        "11 à 50",
        "51 à 500",
        "plus de 500",
    ]


def test_le_rapport_ne_choisit_aucun_signal_et_se_declare_non_recompte() -> None:
    module = load_generator()
    described = module.describe(module.chain([[DA0321, DA0323]]), parcel_total=1_333_327)
    corroborated = module.corroboration([(DA0321, DA0323)], {DA0321: {"t"}, DA0323: {"t"}})
    data = {
        "department": "35",
        "parcel_total": 1_333_327,
        "releases": [("DS-06", "DS-06@2019-04-archive", "pending")],
        "period": (date(2014, 1, 2), date(2025, 12, 31)),
        "acts_by_release": {"DS-06@2019-04-archive": 1},
        "multi_acts": 1,
        "multi_act_parcels": 2,
        "whole_acts": 1,
        "acts_with_contact": 1,
        "sold_parcels": 2,
        "declared_acts": 1,
        "partial_acts": 1,
        "lost_multi_acts": 0,
        "signals": {"DVF, même acte, chaîné": (described, corroborated)},
        "baseline": {"35288": {"pairs": 0, "both_sold": 0, "together": 0, "rate": None}},
        "case_acts": {DA0321: ["t"], DA0322: []},
        "case_partners": {DA0321: [DA0323], DA0322: []},
    }
    text = module.render(data, date(2026, 9, 16))
    assert "**Non recompté.**" in text
    assert "Il n'en choisit aucun" in text
    # La release en attente d'acceptation est nommée avec son statut, pas tue.
    assert "`DS-06@2019-04-archive` (DS-06, `pending`), 1 actes" in text
    assert "| `35288000DA0322` | 0 | — |" in text
    assert "| `35288000DA0321` | 1 | `35288000DA0323` |" in text
    assert "1\N{NO-BREAK SPACE}333\N{NO-BREAK SPACE}327" in text
    # Un rattachement perdu depuis la vente est compté, pas ignoré.
    assert "1 actes portent moins de parcelles distinctes\n  rattachées" in text
    # Le signal bâti dit sur quoi il repose.
    assert "entièrement sur les relations secondaires" in text


def test_la_mention_de_recompte_n_apparait_que_si_elle_est_passee() -> None:
    module = load_generator()
    data = {
        "department": "35",
        "parcel_total": 1,
        "releases": [],
        "period": (date(2014, 1, 2), date(2025, 12, 31)),
        "acts_by_release": {},
        "multi_acts": 0,
        "multi_act_parcels": 0,
        "whole_acts": 0,
        "acts_with_contact": 0,
        "sold_parcels": 0,
        "declared_acts": 0,
        "partial_acts": 0,
        "lost_multi_acts": 0,
        "signals": {},
        "baseline": {},
        "case_acts": {},
        "case_partners": {},
    }
    assert "**Non recompté.**" in module.render(data, date(2026, 9, 16))
    recounted = module.render(data, date(2026, 9, 16), date(2026, 9, 16))
    assert "**Recompté le 2026-09-16**" in recounted
    assert "Non recompté" not in recounted


def test_le_seuil_du_bati_partage_est_balaye_et_non_choisi() -> None:
    module = load_generator()
    assert len(module.SHARED_BUILDING_SHARES) > 1
    source = GENERATOR.read_text(encoding="utf-8")
    assert "E1" in source
