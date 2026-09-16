"""Le baromètre du marché — H1, mesures BAR-001 à BAR-009.

Cohortes, supports et mesures sont des fonctions pures : elles se testent sans base, comme
`test_market_listing_candidates.py`. Ce qui porte sur le SQL est vérifié sur son texte, faute de
banc PostgreSQL dans `make check`.

Deux cas comptent plus que les autres, et le ticket les demande nommément : une cellule **sous le
support déclaré** ne rend pas de valeur mais rend son effectif et son motif ; une **cohorte dont
les douze mois ne sont pas couverts par DVF** n'entre dans aucun taux à douze mois.
"""

import importlib.util
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "pipelines" / "scripts" / "market_barometer.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("market_barometer", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()
DEPARTMENT = "35"


def territories(mapping: dict[str, str] | None = None) -> Any:
    epci_of = {"35001": "240000001", "35002": "240000001", "35003": "240000002"}
    if mapping is not None:
        epci_of = mapping
    communes_of: dict[str, list[str]] = {}
    for commune, epci in sorted(epci_of.items()):
        communes_of.setdefault(epci, []).append(commune)
    return MODULE.Territories(epci_of=epci_of, communes_of=communes_of, names={})


def sale(commune: str, day: date, price: float, surface: float, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "parcel_id": f"{commune}-{day.isoformat()}-{price:.0f}",
        "commune_code": commune,
        "mutation_date": day,
        "property_type": "Maison",
        "price_eur": price,
        "surface_m2": surface,
    }
    fields.update(overrides)
    return MODULE.Sale(**fields)


def diagnostic(parcel: str, day: date, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "dpe_number": f"D-{parcel}-{day.isoformat()}",
        "parcel_id": parcel,
        "commune_code": "35001",
        "deposited_on": day,
        "label": "D",
        "building_type": "maison",
        "from_immeuble": False,
    }
    fields.update(overrides)
    return MODULE.Diagnostic(**fields)


# --- statistique ----------------------------------------------------------------------------


def test_quantile_interpolates_like_percentile_cont() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert MODULE.quantile(values, 0.5) == 2.5
    assert MODULE.quantile(values, 0.25) == 1.75
    assert MODULE.quantile(values, 0.75) == 3.25
    assert MODULE.quantile([7.0], 0.5) == 7.0


def test_quantile_of_nothing_is_absent_not_zero() -> None:
    assert MODULE.quantile([], 0.5) is None
    assert MODULE.median([]) is None


def test_missing_support_names_the_effectif_and_the_threshold() -> None:
    assert MODULE.missing_support(30, 30) is None
    motif = MODULE.missing_support(12, 15)
    assert motif is not None
    assert "12" in motif and "15" in motif


# --- cohortes -------------------------------------------------------------------------------


def test_first_diagnostic_is_the_earliest_deposit_ties_broken_by_number() -> None:
    rows = [
        diagnostic("p1", date(2024, 5, 1), dpe_number="B"),
        diagnostic("p1", date(2023, 5, 1)),
        diagnostic("p1", date(2023, 5, 1), dpe_number="A"),
    ]
    first = MODULE.first_diagnostics(rows)
    assert first["p1"].deposited_on == date(2023, 5, 1)
    assert first["p1"].dpe_number == "A"


def test_cohort_year_ceiling_refuses_a_cohort_dvf_does_not_cover() -> None:
    assert MODULE.cohort_year_ceiling(date(2025, 12, 31)) == 2024
    assert MODULE.cohort_year_ceiling(date(2025, 6, 30)) == 2023
    assert MODULE.cohort_year_ceiling(date(2026, 12, 31)) == 2025


def test_build_cohort_excludes_immeuble_generated_diagnostics_and_counts_them() -> None:
    first = MODULE.first_diagnostics(
        [
            diagnostic("p1", date(2024, 3, 1)),
            diagnostic("p2", date(2024, 4, 1), from_immeuble=True),
            diagnostic("p3", date(2023, 4, 1)),
        ]
    )
    cohort = MODULE.build_cohort(first, {}, 2024)
    assert [row.parcel_id for row in cohort] == ["p1"]
    assert MODULE.count_excluded_from_immeuble(first, 2024) == 1


def test_the_excluded_cohort_is_measured_rather_than_postulated() -> None:
    """Ce que l'exclusion des DPE d'immeuble retire se mesure, sinon on hérite d'un chiffre."""
    first = MODULE.first_diagnostics(
        [
            diagnostic("p1", date(2024, 3, 1)),
            diagnostic("p2", date(2024, 4, 1), from_immeuble=True),
            diagnostic("p3", date(2023, 4, 1), from_immeuble=True),
        ]
    )
    excluded = MODULE.build_excluded_cohort(first, {}, [2023, 2024])
    assert {row.parcel_id for row in excluded} == {"p2", "p3"}
    assert MODULE.build_excluded_cohort(first, {}, [2024])[0].parcel_id == "p2"


def test_build_pairs_breaks_same_day_ties_by_price_then_surface() -> None:
    """Sans règle de départage, « la vente suivante » n'est pas déterminée — et les bandes de
    BAR-003 bougent selon le tri."""
    parameters = MODULE.Parameters()
    same_day = date(2020, 1, 1)
    rows = [
        sale("35001", same_day, 300000, 100, parcel_id="p1"),
        sale("35001", same_day, 200000, 90, parcel_id="p1"),
        sale("35001", date(2023, 1, 1), 400000, 100, parcel_id="p1"),
    ]
    pairs = MODULE.build_pairs(rows, parameters)
    assert len(pairs) == 1
    # La paire retenue part de la vente du même jour la plus chère : c'est la dernière du tri.
    assert pairs[0].entry_price_eur == 300000


def test_same_day_ties_and_all_combinations_are_counted_not_written() -> None:
    """H7 : ces deux chiffres étaient écrits à la main et n'avaient pas suivi les données."""
    parameters = MODULE.Parameters()
    same_day = date(2020, 1, 1)
    rows = [
        sale("35001", same_day, 300000, 100, parcel_id="p1"),
        sale("35001", same_day, 200000, 90, parcel_id="p1"),
        sale("35001", date(2023, 1, 1), 400000, 100, parcel_id="p1"),
        sale("35001", date(2021, 1, 1), 150000, 80, parcel_id="p2"),
    ]
    assert MODULE.same_day_ties(rows) == 1
    # p1 : deux ventes du même jour avec celle de 2023, et aucune entre elles (zéro jour).
    assert MODULE.all_combinations(rows, parameters) == 2


def test_first_sale_after_is_strictly_posterior() -> None:
    dates = [date(2024, 1, 1), date(2024, 6, 1)]
    assert MODULE.first_sale_after(dates, date(2024, 1, 1)) == date(2024, 6, 1)
    assert MODULE.first_sale_after(dates, date(2024, 6, 1)) is None


def test_build_pairs_ignores_two_sales_too_close_together() -> None:
    parameters = MODULE.Parameters()
    rows = [
        sale("35001", date(2020, 1, 1), 200000, 100, parcel_id="p1"),
        sale("35001", date(2020, 3, 1), 210000, 100, parcel_id="p1"),
        sale("35001", date(2023, 1, 1), 300000, 100, parcel_id="p1"),
    ]
    pairs = MODULE.build_pairs(rows, parameters)
    assert len(pairs) == 1
    assert pairs[0].bought_on == date(2020, 3, 1)
    assert pairs[0].sold_on == date(2023, 1, 1)


# --- BAR-001 et BAR-002 ---------------------------------------------------------------------


def test_volumes_absent_below_support_but_effectif_always_present() -> None:
    parameters = MODULE.Parameters(sales_per_cell=15)
    rows = [sale("35001", date(2024, 6, 1), 200000 + index, 100) for index in range(3)]
    output = MODULE.volumes_and_prices(rows, territories(), DEPARTMENT, parameters)
    commune = [row for row in output if row["scope_type"] == "commune"]
    assert len(commune) == 1
    assert commune[0]["sales"] == 3
    assert commune[0]["median_eur_m2"] is None
    assert "support insuffisant" in commune[0]["reason"]


def test_volumes_reported_above_support_at_every_level() -> None:
    parameters = MODULE.Parameters(sales_per_cell=3)
    rows = [
        sale("35001", date(2024, 6, 1), 200000, 100),
        sale("35001", date(2024, 7, 1), 300000, 100),
        sale("35002", date(2024, 8, 1), 400000, 100),
    ]
    output = MODULE.volumes_and_prices(rows, territories(), DEPARTMENT, parameters)
    department = [row for row in output if row["scope_type"] == "departement"]
    assert department[0]["sales"] == 3
    assert department[0]["median_eur_m2"] == 3000
    assert department[0]["reason"] is None
    epci = [row for row in output if row["scope_type"] == "epci"]
    assert epci[0]["scope_code"] == "240000001"


def test_a_commune_without_epci_is_never_attached_by_default() -> None:
    parameters = MODULE.Parameters(sales_per_cell=1)
    rows = [sale("35999", date(2024, 6, 1), 200000, 100)]
    output = MODULE.volumes_and_prices(rows, territories(), DEPARTMENT, parameters)
    assert {row["scope_type"] for row in output} == {"departement", "commune"}


# --- BAR-003 --------------------------------------------------------------------------------


def margin_context(count: int) -> tuple[list[Any], dict[tuple[str, int], tuple[float, int]]]:
    pairs = [
        MODULE.Pair(
            parcel_id=f"p{index}",
            commune_code="35001",
            bought_on=date(2021, 1, 1),
            sold_on=date(2022, 6, 1),
            entry_price_eur=100000,
            exit_price_eur=200000,
            entry_surface_m2=100,
            exit_surface_m2=100,
        )
        for index in range(count)
    ]
    references = {("35001", 2021): (1000.0, 40), ("35001", 2022): (1000.0, 40)}
    return pairs, references


def test_margin_absent_below_support_with_its_effectif() -> None:
    parameters = MODULE.Parameters(repeat_pairs=30)
    pairs, references = margin_context(5)
    rows, _ = MODULE.net_margin_by_entry_price(
        pairs, references, territories(), DEPARTMENT, parameters
    )
    band = [row for row in rows if row["scope_type"] == "departement" and row["pairs"] == 5]
    assert band and band[0]["median_excess"] is None
    assert "support insuffisant" in band[0]["reason"]


def test_margin_reads_the_entry_price_relative_to_the_commune() -> None:
    parameters = MODULE.Parameters(repeat_pairs=2)
    pairs, references = margin_context(3)
    rows, _ = MODULE.net_margin_by_entry_price(
        pairs, references, territories(), DEPARTMENT, parameters
    )
    filled = [row for row in rows if row["scope_type"] == "departement" and row["pairs"] == 3]
    # Entrée à 1 000 €/m² contre une médiane de 1 000 € : bande « 100 % et plus ».
    assert filled[0]["entry_band"].startswith("100")
    assert filled[0]["median_excess"] == 2.0
    assert filled[0]["share_above_threshold_pct"] == 100.0


def test_margin_drops_a_pair_whose_commune_lacks_a_reference_median() -> None:
    parameters = MODULE.Parameters(repeat_pairs=1)
    pairs, _ = margin_context(2)
    rows, _ = MODULE.net_margin_by_entry_price(pairs, {}, territories(), DEPARTMENT, parameters)
    assert all(row["pairs"] == 0 for row in rows)


def test_margin_drops_a_pair_whose_surface_changed() -> None:
    parameters = MODULE.Parameters(repeat_pairs=1)
    pairs, references = margin_context(1)
    widened = [
        MODULE.Pair(
            parcel_id=pairs[0].parcel_id,
            commune_code=pairs[0].commune_code,
            bought_on=pairs[0].bought_on,
            sold_on=pairs[0].sold_on,
            entry_price_eur=pairs[0].entry_price_eur,
            exit_price_eur=pairs[0].exit_price_eur,
            entry_surface_m2=100,
            exit_surface_m2=140,
        )
    ]
    rows, _ = MODULE.net_margin_by_entry_price(
        widened, references, territories(), DEPARTMENT, MODULE.Parameters(repeat_pairs=1)
    )
    assert all(row["pairs"] == 0 for row in rows)
    assert parameters.repeat_pairs == 1


# --- BAR-004 --------------------------------------------------------------------------------


def test_label_of_sale_takes_the_latest_diagnostic_inside_the_window() -> None:
    parameters = MODULE.Parameters()
    target = sale("35001", date(2024, 6, 1), 200000, 100, parcel_id="p1")
    rows = [
        diagnostic("p1", date(2023, 1, 1), label="G"),
        diagnostic("p1", date(2024, 1, 1), label="E"),
        diagnostic("p1", date(2024, 9, 1), label="A"),
    ]
    assert MODULE.label_of_sale(target, rows, parameters) == "E"


def test_label_of_sale_ignores_a_diagnostic_older_than_the_window() -> None:
    parameters = MODULE.Parameters()
    target = sale("35001", date(2024, 6, 1), 200000, 100, parcel_id="p1")
    assert MODULE.label_of_sale(target, [diagnostic("p1", date(2020, 1, 1))], parameters) is None


def test_label_premium_publishes_every_label_with_its_effectif() -> None:
    parameters = MODULE.Parameters(label_sales=2, sales_per_cell=1)
    sales = [
        sale("35001", date(2024, 6, 1), 180000, 100, parcel_id="p1"),
        sale("35001", date(2024, 7, 1), 220000, 100, parcel_id="p2"),
    ]
    diagnostics = {
        "p1": [diagnostic("p1", date(2024, 1, 1), label="F")],
        "p2": [diagnostic("p2", date(2024, 1, 1), label="F")],
    }
    references = MODULE.reference_medians(sales, parameters)
    rows = MODULE.label_premium(
        sales, diagnostics, references, territories(), DEPARTMENT, parameters
    )
    published = {row["energy_label"]: row for row in rows if row["scope_type"] == "departement"}
    assert set(published) == set("ABCDEFG")
    assert published["F"]["sales"] == 2
    assert published["F"]["median_ratio"] == 1.0
    assert published["A"]["sales"] == 0
    assert published["A"]["median_ratio"] is None
    assert "support insuffisant" in published["A"]["reason"]


# --- BAR-005, BAR-006, BAR-007 --------------------------------------------------------------


def cohort_of(size: int, sold: int) -> list[Any]:
    rows = []
    for index in range(size):
        deposited = date(2024, 1, 1)
        rows.append(
            MODULE.CohortParcel(
                parcel_id=f"p{index}",
                commune_code="35001",
                deposited_on=deposited,
                label="D",
                first_sale=date(2024, 7, 1) if index < sold else None,
            )
        )
    return rows


def test_conversion_rate_absent_below_support_but_counts_are_published() -> None:
    parameters = MODULE.Parameters(dpe_cohort_parcels=200)
    rows = MODULE.conversion_rate(cohort_of(10, 4), 2024, territories(), DEPARTMENT, parameters)
    department = next(row for row in rows if row["scope_type"] == "departement")
    assert department["cohort_parcels"] == 10
    assert department["sold_within_12_months"] == 4
    assert department["rate_pct"] is None
    assert "support insuffisant" in department["reason"]


def test_conversion_rate_published_above_support() -> None:
    parameters = MODULE.Parameters(dpe_cohort_parcels=10)
    rows = MODULE.conversion_rate(cohort_of(10, 4), 2024, territories(), DEPARTMENT, parameters)
    department = next(row for row in rows if row["scope_type"] == "departement")
    assert department["rate_pct"] == 40.0
    assert department["reason"] is None


def test_a_sale_beyond_twelve_months_does_not_count_as_a_conversion() -> None:
    parameters = MODULE.Parameters(dpe_cohort_parcels=1)
    late = [
        MODULE.CohortParcel(
            parcel_id="p1",
            commune_code="35001",
            deposited_on=date(2024, 1, 1),
            label="D",
            first_sale=date(2025, 6, 1),
        )
    ]
    rows = MODULE.conversion_rate(late, 2024, territories(), DEPARTMENT, parameters)
    department = next(row for row in rows if row["scope_type"] == "departement")
    assert department["sold_within_12_months"] == 0
    assert department["rate_pct"] == 0.0


def test_deed_delay_quartiles_rest_on_the_sold_subset() -> None:
    parameters = MODULE.Parameters(dpe_cohort_parcels=4)
    rows = MODULE.deed_delay(cohort_of(10, 4), territories(), DEPARTMENT, parameters)
    department = next(row for row in rows if row["scope_type"] == "departement")
    assert department["cohort_parcels"] == 10
    assert department["sold_within_window"] == 4
    assert department["median_days"] == 182


def test_conversion_curve_is_cumulative_and_carries_its_effectif() -> None:
    parameters = MODULE.Parameters(dpe_cohort_parcels=1)
    rows = MODULE.conversion_curve(cohort_of(10, 4), 2024, territories(), DEPARTMENT, parameters)
    department = [row for row in rows if row["scope_type"] == "departement"]
    values = [row["cumulative_pct"] for row in department]
    assert values == sorted(values)
    assert all(row["cohort_parcels"] == 10 for row in department)
    assert department[-1]["cumulative_pct"] == 40.0


# --- BAR-008 et BAR-009 ---------------------------------------------------------------------


def test_extension_effect_needs_its_pairs() -> None:
    parameters = MODULE.Parameters(repeat_pairs=30)
    rows = MODULE.extension_effect([], DEPARTMENT, parameters)
    assert [row["pairs"] for row in rows] == [0, 0]
    assert rows[0]["median_price_ratio"] is None
    assert "support insuffisant" in rows[0]["reason"]


def test_extension_effect_publishes_both_windows() -> None:
    """La conclusion dépend de la fenêtre : les deux paraissent, ou aucune ne vaut."""
    parameters = MODULE.Parameters(repeat_pairs=1)
    inside = MODULE.Pair(
        parcel_id="p1",
        commune_code="35001",
        bought_on=date(2021, 1, 1),
        sold_on=date(2022, 6, 1),
        entry_price_eur=100000,
        exit_price_eur=200000,
        entry_surface_m2=100,
        exit_surface_m2=150,
    )
    outside = MODULE.Pair(
        parcel_id="p2",
        commune_code="35001",
        bought_on=date(2014, 1, 1),
        sold_on=date(2024, 1, 1),
        entry_price_eur=100000,
        exit_price_eur=400000,
        entry_surface_m2=100,
        exit_surface_m2=150,
    )
    rows = MODULE.extension_effect([inside, outside], DEPARTMENT, parameters)
    assert [row["window"] for row in rows] == [
        f"revente en {parameters.repeat_max_days} jours au plus",
        f"toutes durées au-delà de {parameters.repeat_min_days - 1} jours",
    ]
    assert [row["pairs"] for row in rows] == [1, 2]


def test_margin_funnel_accounts_for_every_pair() -> None:
    """Paires retenues plus paires écartées valent le total : un entonnoir qui ne boucle pas
    est un fil à tirer, pas un détail de présentation."""
    parameters = MODULE.Parameters(repeat_pairs=1)
    pairs, references = margin_context(3)
    _, funnel = MODULE.net_margin_by_entry_price(
        pairs, references, territories(), DEPARTMENT, parameters
    )
    assert funnel["paires successives"] == 3
    assert (
        funnel["au-delà de la fenêtre"]
        + funnel["surface modifiée entre les deux ventes"]
        + funnel["sans médiane de référence des deux côtés"]
        + funnel["retenues"]
        == funnel["paires successives"]
    )


def test_coverage_never_divides_by_an_empty_denominator() -> None:
    rows = MODULE.coverage_gaps(
        [
            {
                "commune_code": "35001",
                "mutations": 100,
                "unallocatable": 65,
                "diagnostics": 200,
                "unattached": 80,
            },
            {
                "commune_code": "35002",
                "mutations": 0,
                "unallocatable": 0,
                "diagnostics": 0,
                "unattached": 0,
            },
        ]
    )
    assert rows[0]["share_without_allocatable_price_pct"] == 65.0
    assert rows[0]["share_without_building_pct"] == 40.0
    assert rows[1]["share_without_allocatable_price_pct"] is None
    assert rows[1]["reason"] == "aucune observation"


# --- invariants de sortie -------------------------------------------------------------------


FORBIDDEN_TOKENS = ("parcel_id", "address", "adresse", "cadastral", "dpe_number")


def test_no_output_column_carries_a_parcel_or_an_address() -> None:
    for _, filename, columns in MODULE.CSV_TABLES:
        for column in columns:
            assert not any(token in column for token in FORBIDDEN_TOKENS), (filename, column)


def test_no_measured_value_carries_a_parcel_identifier() -> None:
    """Le périmètre d'une ligne est un territoire, jamais un bien — SPEC §7.2."""
    parameters = MODULE.Parameters(sales_per_cell=1)
    rows = [sale("35001", date(2024, 6, 1), 200000, 100, parcel_id="350010000AB0001")]
    output = MODULE.volumes_and_prices(rows, territories(), DEPARTMENT, parameters)
    values = {str(value) for row in output for value in row.values()}
    assert "350010000AB0001" not in values
    assert {row["scope_code"] for row in output} == {"35", "240000001", "35001"}


def test_every_measured_row_carries_an_effectif() -> None:
    counters = {
        "bar-001-002-volumes-prix.csv": "sales",
        "bar-003-plus-value-prix-entree.csv": "pairs",
        "bar-004-etiquette.csv": "sales",
        "bar-005-delai-dpe-acte.csv": "cohort_parcels",
        "bar-006-taux-mutation-12-mois.csv": "cohort_parcels",
        "bar-007-courbe-conversion.csv": "cohort_parcels",
        "bar-008-extension-surface.csv": "pairs",
        "bar-009-couverture.csv": "mutations",
    }
    for _, filename, columns in MODULE.CSV_TABLES:
        assert counters[filename] in columns


def test_the_dpe_cohort_sql_keeps_only_certain_relations() -> None:
    assert "relation_status = 'certain'" in MODULE.DIAGNOSTICS_SQL
    assert "cancelled_at IS NULL" in MODULE.DIAGNOSTICS_SQL


def test_the_cohort_commune_is_read_on_the_parcel_not_on_the_diagnostic() -> None:
    """Un DPE déclare parfois une commune que le cadastre ne porte plus ; sa parcelle, jamais."""
    assert "parcel.commune_code" in MODULE.DIAGNOSTICS_SQL
    assert "JOIN reference.parcel parcel" in MODULE.DIAGNOSTICS_SQL


def test_the_releases_table_declares_the_building_identity_dataset() -> None:
    """Tout lien DPE ↔ parcelle passe par un bâtiment du RNB : DS-02 est dans le chemin."""
    assert "'DS-02'" in MODULE.RELEASES_SQL


def test_the_releases_table_lists_only_what_was_imported() -> None:
    """Une release découverte mais jamais importée n'a rien été lu."""
    assert "meta.import_run" in MODULE.RELEASES_SQL


def test_the_strict_conversion_event_requires_a_dwelling_lot() -> None:
    assert "property_type IN ('Maison', 'Appartement')" in MODULE.DWELLING_SALE_DATES_SQL
    assert "property_type" not in MODULE.SALE_DATES_SQL


def test_the_sales_sql_states_its_closed_filter() -> None:
    assert "mutation_nature = 'Vente'" in MODULE.SALES_SQL
    assert "allocation_method = 'single_property_full_price'" in MODULE.SALES_SQL


# --- BR-007 : la mention de recompte ne peut pas mentir ------------------------------------


def test_the_fingerprint_changes_when_a_measure_changes(tmp_path: Path) -> None:
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    first.write_text("scope_type,sales\ndepartement,10\n", encoding="utf-8")
    second.write_text("scope_type,pairs\ndepartement,3\n", encoding="utf-8")
    before = MODULE.fingerprint_files([first, second])
    assert before == MODULE.fingerprint_files([first, second])
    first.write_text("scope_type,sales\ndepartement,11\n", encoding="utf-8")
    assert MODULE.fingerprint_files([first, second]) != before


def test_an_attestation_applies_only_to_the_measures_it_recounted() -> None:
    rows = [
        {"recounted_on": "2026-09-01", "fingerprint": "ancienne", "note": ""},
        {"recounted_on": "2026-09-16", "fingerprint": "actuelle", "note": "deux passes"},
    ]
    assert MODULE.find_attestation(rows, "actuelle")["recounted_on"] == "2026-09-16"
    assert MODULE.find_attestation(rows, "autre") is None


def test_without_attestation_the_report_says_it_must_not_be_published() -> None:
    mention = MODULE.recount_mention(None)
    assert "Non recompté" in mention
    assert "BR-007" in mention
    dated = MODULE.recount_mention(
        {"recounted_on": "2026-09-16", "fingerprint": "x", "note": "deux passes"}
    )
    assert dated.startswith("**Recompté le 2026-09-16**")
    assert "deux passes" in dated


def test_a_missing_attestation_file_is_no_attestation(tmp_path: Path) -> None:
    assert MODULE.read_attestations(tmp_path / "recompte.csv") == []


def test_a_malformed_attestation_stops_the_run(tmp_path: Path) -> None:
    """Une empreinte suivie d'un retour chariot coupe la ligne en deux : la note disparaît et
    une ligne fantôme apparaît. Cela doit arrêter la génération, pas l'autoriser."""
    path = tmp_path / "recompte.csv"
    path.write_bytes(b'recounted_on,fingerprint,note\n2026-09-16,abc\r,"deux passes"\n')
    try:
        MODULE.read_attestations(path)
    except SystemExit as stop:
        assert "mal formée" in str(stop)
    else:
        raise AssertionError("une attestation mal formée a été acceptée")
