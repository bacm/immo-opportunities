"""La liste exploratoire — E8.

Filtre, classement et mise en aveugle sont des fonctions pures : elles se testent sans base.
Les invariants qui portent sur le SQL sont vérifiés sur son texte, faute de banc PostgreSQL dans
`make check` — même convention que `test_market_data_quality_report.py`.
"""

import importlib.util
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "exploratory_candidates.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("exploratory_candidates", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit(identifier: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "property_unit_id": f"property-unit:{identifier}",
        "cadastral_id": identifier,
        "parcel_area_m2": 1500.0,
        "parcel_area_m2_missing": None,
        "footprint_ratio": 0.10,
        "footprint_ratio_missing": None,
        "unbuilt_area_m2": 1350.0,
        "unbuilt_area_m2_missing": None,
        "width_m": 30.0,
        "width_m_missing": None,
        "boundary_distance_m": 5.0,
        "boundary_distance_m_missing": None,
        "building_count": 1.0,
        "building_count_missing": None,
        "zone": "U|UE2c",
        "zone_missing": None,
        "constraints": [],
        "constraints_missing": None,
        "uses": "Résidentiel",
        "max_dwellings": 1,
    }
    row.update(overrides)
    return row


def test_le_type_de_zone_se_lit_avant_la_barre() -> None:
    module = load()
    assert module.zone_type("U|UE2c(d)") == "U"
    assert module.zone_type("AUc|1AUO1") == "AUc"
    assert module.zone_type(None) is None


def test_une_valeur_absente_exclut_et_se_compte_sans_valoir_zero() -> None:
    """Le mode d'échec à écarter : `None` traité comme 0 passerait le plafond d'emprise."""
    module = load()
    kept, funnel = module.eligible(
        [unit("A"), unit("B", footprint_ratio=None, footprint_ratio_missing="ambiguous_match")],
        module.Parameters(),
    )
    assert [row["cadastral_id"] for row in kept] == ["A"]
    assert funnel["emprise connue"] == 1
    assert funnel["emprise faible"] == 1


def test_le_plafond_de_surface_ecarte_le_foncier_d_activite() -> None:
    module = load()
    kept, funnel = module.eligible(
        [unit("A"), unit("grand", parcel_area_m2=266_895.0, unbuilt_area_m2=262_996.0)],
        module.Parameters(),
    )
    assert [row["cadastral_id"] for row in kept] == ["A"]
    assert funnel["surface plafonnée"] == 1


def test_seule_la_zone_de_type_u_est_retenue() -> None:
    module = load()
    kept, _ = module.eligible([unit("A"), unit("agricole", zone="A|A")], module.Parameters())
    assert [row["cadastral_id"] for row in kept] == ["A"]


def test_le_rang_moyen_n_additionne_que_les_signaux_presents() -> None:
    module = load()
    rows = [
        unit("A"),
        unit("B", boundary_distance_m=None, boundary_distance_m_missing="not_applicable"),
    ]
    ranks = module.mean_rank(rows)
    assert ranks["property-unit:A"][1] == len(module.RANK_SIGNALS)
    assert ranks["property-unit:B"][1] == len(module.RANK_SIGNALS) - 1


def test_un_candidat_present_dans_les_deux_ordres_n_apparait_qu_une_fois() -> None:
    """Le dupliquer donnerait deux verdicts sur le même bien et fausserait la comparaison."""
    module = load()
    commun, propre_baseline, propre_classement = unit("commun"), unit("B"), unit("C")
    blind_rows, key_rows = module.blind([commun, propre_baseline], [commun, propre_classement], 7)
    assert len(blind_rows) == 3
    origines = {row["cadastral_id"]: row["origine"] for row in key_rows}
    assert origines["commun"] == "baseline+classement"
    assert origines["B"] == "baseline"
    assert origines["C"] == "classement"


def test_la_mise_en_aveugle_est_reproductible_depuis_la_graine() -> None:
    module = load()
    rows = [unit(str(index)) for index in range(12)]
    premier, _ = module.blind(rows[:6], rows[6:], 42)
    second, _ = module.blind(rows[:6], rows[6:], 42)
    autre, _ = module.blind(rows[:6], rows[6:], 43)
    assert [row["cadastral_id"] for row in premier] == [row["cadastral_id"] for row in second]
    assert [row["cadastral_id"] for row in premier] != [row["cadastral_id"] for row in autre]


def test_la_reference_remise_ne_trahit_pas_l_origine() -> None:
    """`C001` doit être muet : une référence ordonnée par liste annulerait l'aveugle."""
    module = load()
    baseline = [unit(f"b{index}") for index in range(5)]
    ranked = [unit(f"r{index}") for index in range(5)]
    blind_rows, key_rows = module.blind(baseline, ranked, 11)
    origines = {row["reference"]: row["origine"] for row in key_rows}
    premiers = [origines[row["reference"]] for row in blind_rows[:5]]
    assert len(set(premiers)) > 1


def test_les_contraintes_sont_comptees_par_type_jamais_traduites() -> None:
    module = load()
    resume = module.constraint_summary(
        [
            {"constraint_type": "prescription", "constraint_code": "05", "intersection_m2": 1.0},
            {"constraint_type": "prescription", "constraint_code": "25", "intersection_m2": 0.0},
            {"constraint_type": "information", "constraint_code": "18", "intersection_m2": 2.0},
        ]
    )
    assert resume == "1 information, 2 prescription"
    assert module.constraint_summary(None) == "aucune"


def test_une_absence_s_affiche_avec_son_motif() -> None:
    module = load()
    row = unit("A", width_m=None, width_m_missing="source_value_missing")
    assert module.cell(row, "width_m", 1) == "absent — source_value_missing"
    assert module.cell(row, "parcel_area_m2") == "1 500"


def _render_data(module: Any, **overrides: Any) -> dict[str, Any]:
    rows = [unit("A"), unit("B")]
    module.orderings(rows, 2)
    blind_rows, _ = module.blind(rows, rows, 3)
    for row in blind_rows:
        row.update(
            last_mutation=None, mutations=0, dpe_count=0, dpe_label=None, dpe_note="", risks=""
        )
    data: dict[str, Any] = {
        "commune": "35051",
        "parameters": module.Parameters(),
        "funnel": {"population": 10, "habitat individuel": 2},
        "use_populations": {"usage résidentiel connu": 2},
        "blind": blind_rows,
        "seed": 3,
        "size": 2,
        "shared": 2,
        "only_baseline": 0,
        "only_ranked": 0,
        "partial_signals": 0,
        "blind_file": "docs/data/exploratory-candidates/35051/liste-aveugle.csv",
        "key_file": "docs/data/exploratory-candidates/35051/correspondance.csv",
    }
    data.update(overrides)
    return data


def test_le_rapport_dit_qu_il_ne_publie_rien_et_que_l_objet_est_une_parcelle() -> None:
    module = load()
    rendu = module.render(_render_data(module), "2026-09-15")
    assert "n'est pas un score publié" in rendu
    assert "parcelle, pas un bien" in rendu
    assert "BUG-11" in rendu


def test_le_rapport_signale_deux_ordres_identiques_comme_une_mesure_impossible() -> None:
    """Faire juger deux fois la même liste produirait un lift nul par construction."""
    module = load()
    rendu = module.render(_render_data(module), "2026-09-15")
    assert "H1 n'est pas mesurable" in rendu


def test_le_rapport_declare_les_parametres_arbitraires() -> None:
    module = load()
    rendu = module.render(_render_data(module), "2026-09-15")
    assert "arbitraires" in rendu
    assert "max_parcel_area_m2" in rendu


def test_le_script_ne_peut_rien_publier() -> None:
    """Critère d'acceptation de E8 : la lecture seule est vérifiable sur le texte du script."""
    source = GENERATOR.read_text(encoding="utf-8")
    for verbe in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ", "CREATE ", "ALTER "):
        assert verbe not in source.upper(), f"le script contient {verbe.strip()}"
    for cible in ("publication_eligible", "opportunity_snapshot", "published_opportunity"):
        assert f"SET {cible}" not in source and f"INTO {cible}" not in source


def test_les_diagnostics_ne_viennent_que_de_relations_certaines() -> None:
    """BUG-09 : une relation bâtiment ↔ parcelle ambiguë ne prouve pas que le DPE porte ici."""
    source = GENERATOR.read_text(encoding="utf-8")
    assert "link.relation_status = 'certain'" in source


def test_les_risques_communaux_ne_sont_pas_presentes_comme_parcellaires() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    assert "observation.granularity <> 'commune'" in source


def test_un_usage_non_residentiel_connu_ecarte_la_parcelle() -> None:
    """Les parcelles industrielles et commerciales de la première liste venaient de là."""
    module = load()
    kept, funnel = module.eligible(
        [unit("A"), unit("commerce", uses="Commercial et services")], module.Parameters()
    )
    assert [row["cadastral_id"] for row in kept] == ["A"]
    assert funnel["usage résidentiel connu"] == 1


def test_un_usage_inconnu_n_est_pas_compte_comme_non_residentiel() -> None:
    """`Indifférencié` et « aucun bâtiment rattaché » sont deux inconnus, pas deux refus."""
    module = load()
    populations = module.use_populations(
        [
            unit("residentiel"),
            unit("commerce", uses="Commercial et services"),
            unit("indifferencie", uses="Indifférencié"),
            unit("sans", uses=None),
        ]
    )
    assert populations["usage résidentiel connu"] == 1
    assert populations["usage non résidentiel connu"] == 1
    assert populations["usage indifférencié"] == 1
    assert populations["aucun bâtiment BD TOPO rattaché"] == 1


def test_une_parcelle_melant_residentiel_et_annexe_est_retenue() -> None:
    module = load()
    kept, _ = module.eligible([unit("A", uses="Annexe · Résidentiel")], module.Parameters())
    assert [row["cadastral_id"] for row in kept] == ["A"]


def test_un_immeuble_est_ecarte_par_le_nombre_de_logements() -> None:
    module = load()
    kept, funnel = module.eligible(
        [unit("A"), unit("immeuble", max_dwellings=7)], module.Parameters()
    )
    assert [row["cadastral_id"] for row in kept] == ["A"]
    assert funnel["habitat individuel"] == 1


def test_un_nombre_de_logements_inconnu_ne_disqualifie_pas() -> None:
    """Une absence n'est pas un immeuble : elle reste une absence."""
    module = load()
    kept, _ = module.eligible([unit("A", max_dwellings=None)], module.Parameters())
    assert [row["cadastral_id"] for row in kept] == ["A"]


def test_l_usage_se_rattache_par_identifiant_declare_et_multivalue() -> None:
    """`identifiants_rnb` est multivalué par `/` sur 29 236 bâtiments : sans le découpage,
    ces bâtiments sont perdus."""
    source = GENERATOR.read_text(encoding="utf-8")
    assert "string_to_array(properties->>'identifiants_rnb', '/')" in source
    assert "ST_Intersects" not in source.split("def enrich")[0]


def test_le_rapport_dit_que_l_usage_vient_d_une_release_display_only() -> None:
    module = load()
    data = _render_data(module)
    data["use_populations"] = {"usage résidentiel connu": 4291}
    rendu = module.render(data, "2026-09-15")
    assert "display_only" in rendu
    assert "identifiants_rnb" in rendu
