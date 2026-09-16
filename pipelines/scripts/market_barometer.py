#!/usr/bin/env python3
"""Baromètre du marché du 35 — les mesures BAR-001 à BAR-009, reproductibles — H1.

Ce script **ne publie rien** et ne touche aucune table : il lit la base et écrit des fichiers,
comme `market_listing_candidates.py`. Aucune parcelle, aucune adresse, aucune mutation
individuelle ne sort d'ici : toutes les sorties sont agrégées par commune, EPCI ou département.

## Ce qui rend une mesure reproductible

Trois règles, héritées de l'écart 14 532 / 9 754 de `dpe-signal-vente-35.md` :

1. **Le filtre de chaque cohorte est écrit dans la sortie**, en clair, avec son effectif.
2. **Un taux ne paraît jamais sans son effectif.** Sous le support déclaré, la valeur est
   absente *avec son motif* — jamais repliée sur une moyenne, jamais convertie en zéro.
3. **Les supports sont des paramètres**, affichés et contestables, pas des seuils de sens
   métier. Ils viennent de `SPEC.md` §13.4.

## Le référentiel EPCI vient de DS-03

Aucune source du contrat ne porte le découpage intercommunal comme tel. Le seul rattachement
commune → EPCI disponible en base est l'attribut `code_epci_insee` des groupes de bâtiments de
DS-03 BDNB : 332 communes, chacune rattachée à un et un seul EPCI, 18 EPCI. Il est utilisé ici
comme **clé géographique**, jamais comme attribut classant d'un bien, et sa provenance est
écrite dans le rapport. DS-03 ne porte pas le **nom** des EPCI : les pages sont identifiées par
le SIREN de l'EPCI et la liste de ses communes. Nommer les EPCI demande un référentiel que le
dépôt n'a pas ; c'est une limite déclarée, à trancher par H2.

## La réforme DPE du 1er janvier 2026 ne peut pas contaminer ces mesures

L'extrait DPE va jusqu'en septembre 2026, donc il contient des diagnostics postérieurs à la
réforme. Mais DVF s'arrête au 31 décembre 2025 : aucune mesure qui croise un DPE et une vente ne
peut atteindre un diagnostic de 2026. La rupture de série est donc hors du champ mesuré, et le
rapport le dit plutôt que de le supposer.
"""

import argparse
import bisect
import csv
import hashlib
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.dvf import DVF_TRANSFORMATION_VERSION
from immo_pipelines.market_data.exploratory import write_csv

CROSS = "\u00d7"  # « commune x année », rendu tel quel dans le rapport

DEPARTMENT_SCOPE = "departement"
EPCI_SCOPE = "epci"
COMMUNE_SCOPE = "commune"
SCOPE_ORDER = {DEPARTMENT_SCOPE: 0, EPCI_SCOPE: 1, COMMUNE_SCOPE: 2}


@dataclass(frozen=True)
class Parameters:
    """Supports et fenêtres, tous déclarés et tous affichés dans la sortie.

    Les quatre premiers sont les supports minimaux de `SPEC.md` §13.4. Les suivants sont les
    conventions de construction reprises des sondages de `pistes-analyse-marche-35.md` §5.
    """

    # Supports minimaux — SPEC §13.4
    sales_per_cell: int = 15  # BAR-001, BAR-002, et toute médiane commune x année de référence
    repeat_pairs: int = 30  # BAR-003, BAR-008
    label_sales: int = 30  # BAR-004
    dpe_cohort_parcels: int = 200  # BAR-005, BAR-006, BAR-007

    # Conventions de construction
    conversion_days: int = 365
    curve_month_days: int = 30
    curve_months: tuple[int, ...] = (1, 2, 3, 6, 9, 12)
    label_lookback_days: int = 730
    label_from_year: int = 2022
    repeat_min_days: int = 181
    repeat_max_days: int = 1095
    entry_bands: tuple[float, ...] = (0.6, 0.8, 1.0)
    excess_threshold: float = 1.2


@dataclass(frozen=True)
class Sale:
    """Une vente exploitable : prix alloué à un seul bien, surface connue, parcelle rattachée."""

    parcel_id: str
    commune_code: str
    mutation_date: date
    property_type: str
    price_eur: float
    surface_m2: float

    @property
    def price_per_m2(self) -> float:
        return self.price_eur / self.surface_m2

    @property
    def year(self) -> int:
        return self.mutation_date.year


@dataclass(frozen=True)
class Diagnostic:
    """Un DPE rattaché à une parcelle par une relation bâtiment ↔ parcelle `certain`."""

    dpe_number: str
    parcel_id: str
    commune_code: str
    deposited_on: date
    label: str | None
    building_type: str | None
    from_immeuble: bool


@dataclass(frozen=True)
class Pair:
    """Deux ventes successives de la même parcelle, la première servant de prix d'entrée."""

    parcel_id: str
    commune_code: str
    bought_on: date
    sold_on: date
    entry_price_eur: float
    exit_price_eur: float
    entry_surface_m2: float
    exit_surface_m2: float

    @property
    def days(self) -> int:
        return (self.sold_on - self.bought_on).days

    @property
    def price_ratio(self) -> float:
        return self.exit_price_eur / self.entry_price_eur

    @property
    def price_per_m2_ratio(self) -> float:
        return (self.exit_price_eur / self.exit_surface_m2) / (
            self.entry_price_eur / self.entry_surface_m2
        )


@dataclass(frozen=True)
class Territories:
    """Le rattachement commune → EPCI, et rien d'autre."""

    epci_of: dict[str, str]
    communes_of: dict[str, list[str]]
    names: dict[str, str]

    def scopes(self, commune_code: str, department: str) -> list[tuple[str, str]]:
        keys = [(DEPARTMENT_SCOPE, department)]
        epci = self.epci_of.get(commune_code)
        if epci is not None:
            keys.append((EPCI_SCOPE, epci))
        keys.append((COMMUNE_SCOPE, commune_code))
        return keys


# --------------------------------------------------------------------------------------------
# Statistique élémentaire — même définition que `percentile_cont` de PostgreSQL, pour qu'un
# recompte en SQL tombe sur la même valeur.
# --------------------------------------------------------------------------------------------


def quantile(values: Sequence[float], fraction: float) -> float | None:
    """Interpolation linéaire entre statistiques d'ordre, comme `percentile_cont`."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def median(values: Sequence[float]) -> float | None:
    return quantile(values, 0.5)


def missing_support(count: int, minimum: int) -> str | None:
    """Le motif d'absence, ou `None` quand le support est atteint. Jamais un zéro."""
    if count >= minimum:
        return None
    return f"support insuffisant : {count} < {minimum}"


def round_or_none(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


# --------------------------------------------------------------------------------------------
# Cohortes — fonctions pures, testées sans base
# --------------------------------------------------------------------------------------------


def first_diagnostics(rows: Iterable[Diagnostic]) -> dict[str, Diagnostic]:
    """Le premier DPE de chaque parcelle.

    Départage par `dpe_number` à date égale, pour que deux exécutions donnent la même cohorte.
    """
    first: dict[str, Diagnostic] = {}
    for row in rows:
        held = first.get(row.parcel_id)
        if held is None or (row.deposited_on, row.dpe_number) < (
            held.deposited_on,
            held.dpe_number,
        ):
            first[row.parcel_id] = row
    return first


def cohort_year_ceiling(last_mutation: date) -> int:
    """La dernière cohorte annuelle dont les douze mois de suivi sont couverts par DVF.

    Dérivée de la donnée, jamais choisie : un dépôt du 31 décembre de l'année Y demande une
    couverture jusqu'au 31 décembre de Y+1.
    """
    if last_mutation >= date(last_mutation.year, 12, 31):
        return last_mutation.year - 1
    return last_mutation.year - 2


def first_sale_after(sale_dates: Sequence[date], moment: date) -> date | None:
    """La première vente strictement postérieure au dépôt, sur une liste déjà triée."""
    index = bisect.bisect_right(sale_dates, moment)
    return sale_dates[index] if index < len(sale_dates) else None


def build_pairs(sales: Iterable[Sale], parameters: Parameters) -> list[Pair]:
    """Les ventes successives d'une même parcelle, écartées de plus de `repeat_min_days`."""
    by_parcel: dict[str, list[Sale]] = defaultdict(list)
    for sale in sales:
        by_parcel[sale.parcel_id].append(sale)
    pairs: list[Pair] = []
    for parcel_id, rows in sorted(by_parcel.items()):
        # Des couples (parcelle, date) portent plusieurs ventes de maison le même jour — leur
        # nombre est publié par `same_day_ties`. Sans règle de départage, « la vente suivante »
        # n'est pas déterminée et les bandes de BAR-003 bougent. Prix croissant puis surface
        # croissante, écrit dans le rapport.
        ordered = sorted(rows, key=lambda row: (row.mutation_date, row.price_eur, row.surface_m2))
        for entry, exit_ in pairwise(ordered):
            if (exit_.mutation_date - entry.mutation_date).days < parameters.repeat_min_days:
                continue
            pairs.append(
                Pair(
                    parcel_id=parcel_id,
                    commune_code=exit_.commune_code,
                    bought_on=entry.mutation_date,
                    sold_on=exit_.mutation_date,
                    entry_price_eur=entry.price_eur,
                    exit_price_eur=exit_.price_eur,
                    entry_surface_m2=entry.surface_m2,
                    exit_surface_m2=exit_.surface_m2,
                )
            )
    return pairs


def same_day_ties(sales: Iterable[Sale]) -> int:
    """Les couples (parcelle, date) qui portent plusieurs ventes, départagés par `build_pairs`."""
    counts = Counter((sale.parcel_id, sale.mutation_date) for sale in sales)
    return sum(1 for count in counts.values() if count > 1)


def all_combinations(sales: Iterable[Sale], parameters: Parameters) -> int:
    """Toutes les combinaisons de deux ventes d'une parcelle assez espacées, rang ou non.

    Publié à côté des paires consécutives pour dire ce que le rang écarte : une parcelle vendue
    trois fois donne deux paires consécutives, mais trois combinaisons.
    """
    by_parcel: dict[str, list[date]] = defaultdict(list)
    for sale in sales:
        by_parcel[sale.parcel_id].append(sale.mutation_date)
    return sum(
        1
        for dates in by_parcel.values()
        for first, second in combinations(sorted(dates), 2)
        if (second - first).days >= parameters.repeat_min_days
    )


def reference_medians(
    sales: Iterable[Sale], parameters: Parameters
) -> dict[tuple[str, int], tuple[float, int]]:
    """Médiane du prix au m² par commune x année, sur les maisons, au-dessus du support.

    C'est le contrôle de marché de BAR-003 et BAR-004 : aucun modèle, aucune pondération.
    """
    cells: dict[tuple[str, int], list[float]] = defaultdict(list)
    for sale in sales:
        if sale.property_type == "Maison":
            cells[(sale.commune_code, sale.year)].append(sale.price_per_m2)
    result: dict[tuple[str, int], tuple[float, int]] = {}
    for key, values in cells.items():
        if len(values) < parameters.sales_per_cell:
            continue
        cell_median = median(values)
        if cell_median is not None:
            result[key] = (cell_median, len(values))
    return result


def group_by_scope(
    rows: Iterable[Any],
    commune_of: Callable[[Any], str],
    territories: Territories,
    department: str,
    levels: Sequence[str],
) -> dict[tuple[str, str], list[Any]]:
    """Réplique chaque ligne dans chacun des niveaux demandés. Une ligne sans EPCI connu n'est
    comptée qu'au département et à sa commune — jamais rattachée par défaut."""
    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for row in rows:
        for scope_type, scope_code in territories.scopes(commune_of(row), department):
            if scope_type in levels:
                grouped[(scope_type, scope_code)].append(row)
    return grouped


def scope_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (SCOPE_ORDER[row["scope_type"]], row["scope_code"])


# --------------------------------------------------------------------------------------------
# Les mesures — BAR-001 à BAR-009
# --------------------------------------------------------------------------------------------


def volumes_and_prices(
    sales: Sequence[Sale], territories: Territories, department: str, parameters: Parameters
) -> list[dict[str, Any]]:
    """BAR-001 et BAR-002 — volumes et prix au m², EPCI x année et commune x année."""
    grouped = group_by_scope(
        sales,
        lambda sale: sale.commune_code,
        territories,
        department,
        (DEPARTMENT_SCOPE, EPCI_SCOPE, COMMUNE_SCOPE),
    )
    rows: list[dict[str, Any]] = []
    for (scope_type, scope_code), scope_sales in grouped.items():
        cells: dict[tuple[int, str], list[float]] = defaultdict(list)
        for sale in scope_sales:
            cells[(sale.year, sale.property_type)].append(sale.price_per_m2)
        for (year, property_type), values in cells.items():
            reason = missing_support(len(values), parameters.sales_per_cell)
            rows.append(
                {
                    "scope_type": scope_type,
                    "scope_code": scope_code,
                    "year": year,
                    "property_type": property_type,
                    "sales": len(values),
                    "median_eur_m2": None if reason else round_or_none(median(values), 0),
                    "q1_eur_m2": None if reason else round_or_none(quantile(values, 0.25), 0),
                    "q3_eur_m2": None if reason else round_or_none(quantile(values, 0.75), 0),
                    "reason": reason,
                }
            )
    return sorted(rows, key=lambda row: (*scope_sort_key(row), row["year"], row["property_type"]))


def share_label(fraction: float) -> str:
    """« 60 % », espace insécable comprise — le rapport est lu par des humains."""
    return f"{round(fraction * 100)}\u00a0%"


def entry_band_label(relative_entry: float, parameters: Parameters) -> str:
    edges = parameters.entry_bands
    if relative_entry < edges[0]:
        return f"< {share_label(edges[0])} de la médiane"
    for low, high in pairwise(edges):
        if relative_entry < high:
            return f"{share_label(low)} à {share_label(high)}"
    return f"{share_label(edges[-1])} et plus"


def band_order(parameters: Parameters) -> list[str]:
    edges = parameters.entry_bands
    bands = [f"< {share_label(edges[0])} de la médiane"]
    bands += [f"{share_label(low)} à {share_label(high)}" for low, high in pairwise(edges)]
    bands.append(f"{share_label(edges[-1])} et plus")
    return bands


def net_margin_by_entry_price(
    pairs: Sequence[Pair],
    references: dict[tuple[str, int], tuple[float, int]],
    territories: Territories,
    department: str,
    parameters: Parameters,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """BAR-003 — plus-value nette de marché selon le prix d'entrée, ventes répétées.

    Nette de marché : le ratio de prix est divisé par l'évolution de la médiane de la commune
    entre les deux années. Surface inchangée, pour ne pas confondre une extension avec une
    plus-value. Les paires dont une des deux années de commune manque de support sont écartées
    et comptées.
    """
    eligible: list[tuple[Pair, str, float]] = []
    dropped_no_reference = 0
    dropped_surface_changed = 0
    dropped_beyond_window = 0
    for pair in pairs:
        if pair.days > parameters.repeat_max_days:
            dropped_beyond_window += 1
            continue
        if pair.entry_surface_m2 != pair.exit_surface_m2:
            dropped_surface_changed += 1
            continue
        entry_cell = references.get((pair.commune_code, pair.bought_on.year))
        exit_cell = references.get((pair.commune_code, pair.sold_on.year))
        if entry_cell is None or exit_cell is None:
            dropped_no_reference += 1
            continue
        market = exit_cell[0] / entry_cell[0]
        excess = pair.price_ratio / market
        relative_entry = (pair.entry_price_eur / pair.entry_surface_m2) / entry_cell[0]
        eligible.append((pair, entry_band_label(relative_entry, parameters), excess))

    grouped = group_by_scope(
        eligible,
        lambda item: item[0].commune_code,
        territories,
        department,
        (DEPARTMENT_SCOPE, EPCI_SCOPE),
    )
    rows: list[dict[str, Any]] = []
    order = band_order(parameters)
    for (scope_type, scope_code), items in grouped.items():
        by_band: dict[str, list[float]] = defaultdict(list)
        for _, band, excess in items:
            by_band[band].append(excess)
        for band in order:
            values = by_band.get(band, [])
            reason = missing_support(len(values), parameters.repeat_pairs)
            above = sum(1 for value in values if value > parameters.excess_threshold)
            rows.append(
                {
                    "scope_type": scope_type,
                    "scope_code": scope_code,
                    "entry_band": band,
                    "pairs": len(values),
                    "median_excess": None if reason else round_or_none(median(values), 2),
                    "q3_excess": None if reason else round_or_none(quantile(values, 0.75), 2),
                    "share_above_threshold_pct": (
                        None if reason else round(100.0 * above / len(values), 1)
                    ),
                    "reason": reason,
                }
            )
    rows.sort(key=lambda row: (*scope_sort_key(row), order.index(row["entry_band"])))
    funnel = {
        "paires successives": len(pairs),
        "au-delà de la fenêtre": dropped_beyond_window,
        "surface modifiée entre les deux ventes": dropped_surface_changed,
        "sans médiane de référence des deux côtés": dropped_no_reference,
        "retenues": len(eligible),
    }
    return rows, funnel


def label_of_sale(
    sale: Sale, diagnostics: Sequence[Diagnostic], parameters: Parameters
) -> str | None:
    """L'étiquette du dernier DPE déposé dans la fenêtre précédant l'acte, ou rien."""
    window_start = sale.mutation_date - timedelta(days=parameters.label_lookback_days)
    candidates = [
        row
        for row in diagnostics
        if row.label is not None and window_start < row.deposited_on <= sale.mutation_date
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda row: (row.deposited_on, row.dpe_number))
    return latest.label


def label_premium(
    sales: Sequence[Sale],
    diagnostics_by_parcel: dict[str, list[Diagnostic]],
    references: dict[tuple[str, int], tuple[float, int]],
    territories: Territories,
    department: str,
    parameters: Parameters,
) -> list[dict[str, Any]]:
    """BAR-004 — décote ou surcote par étiquette, contrôle commune x année.

    Sur les maisons seulement : l'étiquette d'un appartement se lit sur un marché différent et le
    contrôle commune x année est bâti sur les maisons.
    """
    observed: list[tuple[Sale, str, float]] = []
    for sale in sales:
        if sale.property_type != "Maison" or sale.year < parameters.label_from_year:
            continue
        cell = references.get((sale.commune_code, sale.year))
        if cell is None:
            continue
        label = label_of_sale(sale, diagnostics_by_parcel.get(sale.parcel_id, []), parameters)
        if label is None:
            continue
        observed.append((sale, label, sale.price_per_m2 / cell[0]))

    grouped = group_by_scope(
        observed,
        lambda item: item[0].commune_code,
        territories,
        department,
        (DEPARTMENT_SCOPE, EPCI_SCOPE),
    )
    rows: list[dict[str, Any]] = []
    for (scope_type, scope_code), items in grouped.items():
        by_label: dict[str, list[float]] = defaultdict(list)
        for _, label, ratio in items:
            by_label[label].append(ratio)
        for label in "ABCDEFG":
            values = by_label.get(label, [])
            reason = missing_support(len(values), parameters.label_sales)
            rows.append(
                {
                    "scope_type": scope_type,
                    "scope_code": scope_code,
                    "energy_label": label,
                    "sales": len(values),
                    "q1_ratio": None if reason else round_or_none(quantile(values, 0.25), 2),
                    "median_ratio": None if reason else round_or_none(median(values), 2),
                    "q3_ratio": None if reason else round_or_none(quantile(values, 0.75), 2),
                    "reason": reason,
                }
            )
    rows.sort(key=lambda row: (*scope_sort_key(row), row["energy_label"]))
    return rows


@dataclass(frozen=True)
class CohortParcel:
    """Une parcelle de cohorte : son premier DPE, et sa première vente postérieure s'il y en a."""

    parcel_id: str
    commune_code: str
    deposited_on: date
    label: str | None
    first_sale: date | None

    @property
    def days_to_deed(self) -> int | None:
        return None if self.first_sale is None else (self.first_sale - self.deposited_on).days


def cohort_rows(
    diagnostics: Iterable[Diagnostic], sale_dates_by_parcel: dict[str, list[date]]
) -> list[CohortParcel]:
    """Attache à chaque premier DPE sa première vente postérieure, s'il y en a une."""
    return sorted(
        (
            CohortParcel(
                parcel_id=diagnostic.parcel_id,
                commune_code=diagnostic.commune_code,
                deposited_on=diagnostic.deposited_on,
                label=diagnostic.label,
                first_sale=first_sale_after(
                    sale_dates_by_parcel.get(diagnostic.parcel_id, []), diagnostic.deposited_on
                ),
            )
            for diagnostic in diagnostics
        ),
        key=lambda row: (row.deposited_on, row.parcel_id),
    )


def build_cohort(
    first: dict[str, Diagnostic],
    sale_dates_by_parcel: dict[str, list[date]],
    year: int,
) -> list[CohortParcel]:
    """La cohorte d'une année : les premiers DPE déposés cette année-là, hors DPE d'immeuble.

    Les DPE d'appartement générés depuis un DPE d'immeuble sont exclus de toute mesure de
    conversion. L'exclusion est comptée par `count_excluded_from_immeuble`, et ce qu'elle retire
    est mesuré par `build_excluded_cohort` plutôt que postulé.
    """
    return cohort_rows(
        (
            diagnostic
            for diagnostic in first.values()
            if not diagnostic.from_immeuble and diagnostic.deposited_on.year == year
        ),
        sale_dates_by_parcel,
    )


def build_excluded_cohort(
    first: dict[str, Diagnostic],
    sale_dates_by_parcel: dict[str, list[date]],
    years: Sequence[int],
) -> list[CohortParcel]:
    """Ce que l'exclusion retire : les premiers DPE générés depuis un DPE d'immeuble."""
    return cohort_rows(
        (
            diagnostic
            for diagnostic in first.values()
            if diagnostic.from_immeuble and diagnostic.deposited_on.year in years
        ),
        sale_dates_by_parcel,
    )


def count_excluded_from_immeuble(first: dict[str, Diagnostic], year: int) -> int:
    return sum(
        1
        for diagnostic in first.values()
        if diagnostic.from_immeuble and diagnostic.deposited_on.year == year
    )


def deed_delay(
    cohort: Sequence[CohortParcel],
    territories: Territories,
    department: str,
    parameters: Parameters,
) -> list[dict[str, Any]]:
    """BAR-005 — délai dépôt DPE → acte, quartiles, sur les parcelles vendues dans l'année."""
    grouped = group_by_scope(
        cohort,
        lambda row: row.commune_code,
        territories,
        department,
        (DEPARTMENT_SCOPE, EPCI_SCOPE, COMMUNE_SCOPE),
    )
    rows: list[dict[str, Any]] = []
    for (scope_type, scope_code), items in grouped.items():
        reason = missing_support(len(items), parameters.dpe_cohort_parcels)
        delays = [
            float(cast(int, row.days_to_deed))
            for row in items
            if row.days_to_deed is not None and row.days_to_deed <= parameters.conversion_days
        ]
        rows.append(
            {
                "scope_type": scope_type,
                "scope_code": scope_code,
                "cohort_parcels": len(items),
                "sold_within_window": len(delays),
                "q1_days": None if reason else round_or_none(quantile(delays, 0.25), 0),
                "median_days": None if reason else round_or_none(median(delays), 0),
                "q3_days": None if reason else round_or_none(quantile(delays, 0.75), 0),
                "reason": reason,
            }
        )
    return sorted(rows, key=scope_sort_key)


def conversion_rate(
    cohort: Sequence[CohortParcel],
    year: int,
    territories: Territories,
    department: str,
    parameters: Parameters,
) -> list[dict[str, Any]]:
    """BAR-006 — taux de mutation à douze mois après le premier DPE."""
    grouped = group_by_scope(
        cohort,
        lambda row: row.commune_code,
        territories,
        department,
        (DEPARTMENT_SCOPE, EPCI_SCOPE, COMMUNE_SCOPE),
    )
    rows: list[dict[str, Any]] = []
    for (scope_type, scope_code), items in grouped.items():
        reason = missing_support(len(items), parameters.dpe_cohort_parcels)
        sold = sum(
            1
            for row in items
            if row.days_to_deed is not None and row.days_to_deed <= parameters.conversion_days
        )
        rows.append(
            {
                "scope_type": scope_type,
                "scope_code": scope_code,
                "cohort_year": year,
                "cohort_parcels": len(items),
                "sold_within_12_months": sold,
                "rate_pct": None if reason else round(100.0 * sold / len(items), 1),
                "reason": reason,
            }
        )
    return sorted(rows, key=scope_sort_key)


def conversion_curve(
    cohort: Sequence[CohortParcel],
    year: int,
    territories: Territories,
    department: str,
    parameters: Parameters,
) -> list[dict[str, Any]]:
    """BAR-007 — courbe de conversion mensuelle, en mois conventionnels de trente jours."""
    grouped = group_by_scope(
        cohort,
        lambda row: row.commune_code,
        territories,
        department,
        (DEPARTMENT_SCOPE, EPCI_SCOPE),
    )
    rows: list[dict[str, Any]] = []
    for (scope_type, scope_code), items in grouped.items():
        reason = missing_support(len(items), parameters.dpe_cohort_parcels)
        for month in parameters.curve_months:
            horizon = month * parameters.curve_month_days
            sold = sum(
                1 for row in items if row.days_to_deed is not None and row.days_to_deed <= horizon
            )
            rows.append(
                {
                    "scope_type": scope_type,
                    "scope_code": scope_code,
                    "cohort_year": year,
                    "month": month,
                    "cohort_parcels": len(items),
                    "sold_cumulative": sold,
                    "cumulative_pct": None if reason else round(100.0 * sold / len(items), 1),
                    "reason": reason,
                }
            )
    rows.sort(key=lambda row: (*scope_sort_key(row), row["month"]))
    return rows


def extension_effect(
    pairs: Sequence[Pair], department: str, parameters: Parameters
) -> list[dict[str, Any]]:
    """BAR-008 — ce que rapporte un agrandissement, sur les reventes à surface augmentée.

    Deux fenêtres, parce que la conclusion dépend de celle qu'on retient : sous trois ans, les m²
    ajoutés se vendent au prix des m² existants ; sur toutes les durées, ils se vendent plus cher.
    Ne publier que la fenêtre courte ferait dépendre un résultat d'un choix tu.
    """
    windows: tuple[tuple[str, int | None], ...] = (
        (f"revente en {parameters.repeat_max_days} jours au plus", parameters.repeat_max_days),
        (f"toutes durées au-delà de {parameters.repeat_min_days - 1} jours", None),
    )
    rows: list[dict[str, Any]] = []
    for label, ceiling in windows:
        widened = [
            pair
            for pair in pairs
            if pair.days >= parameters.repeat_min_days
            and (ceiling is None or pair.days <= ceiling)
            and pair.exit_surface_m2 > pair.entry_surface_m2
        ]
        reason = missing_support(len(widened), parameters.repeat_pairs)
        rows.append(
            {
                "scope_type": DEPARTMENT_SCOPE,
                "scope_code": department,
                "window": label,
                "pairs": len(widened),
                "median_price_ratio": (
                    None if reason else round_or_none(median([p.price_ratio for p in widened]), 2)
                ),
                "median_price_per_m2_ratio": (
                    None
                    if reason
                    else round_or_none(median([p.price_per_m2_ratio for p in widened]), 2)
                ),
                "reason": reason,
            }
        )
    return rows


def coverage_gaps(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """BAR-009 — ce que le baromètre ne voit pas, commune par commune.

    Aucune part n'est calculée sur un dénominateur nul : elle reste absente avec son motif.
    """
    output: list[dict[str, Any]] = []
    for row in rows:
        mutations = int(row["mutations"])
        diagnostics = int(row["diagnostics"])
        output.append(
            {
                "scope_type": COMMUNE_SCOPE,
                "scope_code": row["commune_code"],
                "mutations": mutations,
                "mutations_without_allocatable_price": int(row["unallocatable"]),
                "share_without_allocatable_price_pct": (
                    round(100.0 * int(row["unallocatable"]) / mutations, 1) if mutations else None
                ),
                "diagnostics": diagnostics,
                "diagnostics_without_building": int(row["unattached"]),
                "share_without_building_pct": (
                    round(100.0 * int(row["unattached"]) / diagnostics, 1) if diagnostics else None
                ),
                "reason": None if mutations and diagnostics else "aucune observation",
            }
        )
    return sorted(output, key=lambda row: row["scope_code"])


# --------------------------------------------------------------------------------------------
# Lecture de la base
# --------------------------------------------------------------------------------------------


def fetch(connection: psycopg.Connection[Any], sql: str, **parameters: Any) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        return cast(list[dict[str, Any]], cursor.execute(sql, parameters).fetchall())


SALES_SQL = """
SELECT tp.parcel_id, t.commune_code, t.mutation_date, tp.property_type,
       tp.allocated_price_eur::float8 AS price_eur, tp.surface_m2::float8 AS surface_m2
  FROM observation.transaction_property tp
  JOIN observation.transaction t ON t.id = tp.transaction_id
 WHERE t.department_code = %(department)s
   AND t.mutation_nature = 'Vente'
   AND tp.property_type IN ('Maison', 'Appartement')
   AND tp.allocation_method = 'single_property_full_price'
   AND tp.parcel_id IS NOT NULL
   AND tp.allocated_price_eur > 0
   AND tp.surface_m2 > 0
"""

DIAGNOSTICS_SQL = """
-- La commune d'une parcelle de cohorte est celle de la **parcelle**, jamais celle déclarée par
-- le DPE : 78 diagnostics rattachés portent une commune que le cadastre ne porte plus, et les
-- rattacher par leur déclaration ferait sortir leur parcelle du découpage EPCI.
SELECT a.dpe_number, link.parcel_id, parcel.commune_code,
       coalesce(a.deposited_at, a.assessment_date) AS deposited_on,
       a.energy_label,
       a.properties->>'type_batiment' AS building_type,
       (a.properties->>'numero_dpe_immeuble_associe') IS NOT NULL AS from_immeuble
  FROM observation.energy_assessment a
  JOIN reference.building_parcel link
    ON link.building_id = a.building_id AND link.relation_status = 'certain'
  JOIN reference.parcel parcel ON parcel.id = link.parcel_id
 WHERE a.department_code = %(department)s
   AND a.cancelled_at IS NULL
   -- DS-07 seulement : un DPE neuf (DS-13) accompagne une livraison, pas une vente (ADR-021).
   AND a.release_id IN (SELECT id FROM meta.dataset_release WHERE data_source_id = 'DS-07')
"""

SALE_DATES_SQL = """
SELECT DISTINCT tp.parcel_id, t.mutation_date
  FROM observation.transaction_property tp
  JOIN observation.transaction t ON t.id = tp.transaction_id
 WHERE t.department_code = %(department)s
   AND tp.parcel_id IS NOT NULL
   AND t.mutation_nature LIKE 'Vente%%'
"""

DWELLING_SALE_DATES_SQL = """
SELECT DISTINCT tp.parcel_id, t.mutation_date
  FROM observation.transaction_property tp
  JOIN observation.transaction t ON t.id = tp.transaction_id
 WHERE t.department_code = %(department)s
   AND tp.parcel_id IS NOT NULL
   AND t.mutation_nature LIKE 'Vente%%'
   AND tp.property_type IN ('Maison', 'Appartement')
"""

TERRITORIES_SQL = """
SELECT observation.properties->>'code_commune_insee' AS commune_code,
       observation.properties->>'code_epci_insee' AS epci_code,
       count(*) AS groups
  FROM meta.entity_source_observation AS observation
 WHERE observation.properties->>'code_departement_insee' = %(department)s
   AND observation.properties ? 'code_epci_insee'
 GROUP BY 1, 2
"""

COMMUNE_NAMES_SQL = """
SELECT DISTINCT ON (code) code AS commune_code, name
  FROM reference.administrative_area
 WHERE area_type = 'commune' AND department_code = %(department)s
 ORDER BY code, release_id DESC
"""

COVERAGE_SQL = """
-- Une commune que DVF connaît mais que l'ADEME ignore a bien zéro diagnostic observé : le zéro
-- est un compte, pas une valeur manquante convertie. La part, elle, reste absente avec son
-- motif dans `coverage_gaps`, jamais calculée sur un dénominateur nul.
WITH m AS (
  SELECT t.commune_code,
         count(*) AS total,
         count(*) FILTER (
           WHERE NOT EXISTS (
             SELECT 1 FROM observation.transaction_property tp
              WHERE tp.transaction_id = t.id AND tp.allocation_method IS NOT NULL)
         ) AS unallocatable
    FROM observation.transaction t
   WHERE t.department_code = %(department)s
   GROUP BY 1),
d AS (
  SELECT a.commune_code,
         count(*) AS total,
         count(*) FILTER (WHERE a.building_id IS NULL) AS unattached
    FROM observation.energy_assessment a
   WHERE a.department_code = %(department)s AND a.cancelled_at IS NULL
     AND a.release_id IN (SELECT id FROM meta.dataset_release WHERE data_source_id = 'DS-07')
   GROUP BY 1)
SELECT coalesce(m.commune_code, d.commune_code) AS commune_code,
       coalesce(m.total, 0) AS mutations,  -- invariant-ok: compte, pas manquant
       coalesce(m.unallocatable, 0) AS unallocatable,  -- invariant-ok: compte, pas manquant
       coalesce(d.total, 0) AS diagnostics,  -- invariant-ok: compte, pas manquant
       coalesce(d.unattached, 0) AS unattached  -- invariant-ok: compte, pas manquant
  FROM m FULL OUTER JOIN d ON d.commune_code = m.commune_code
"""

ATTACHMENT_GAP_SQL = """
SELECT count(*) AS n
  FROM observation.energy_assessment a
 WHERE a.department_code = %(department)s
   AND a.cancelled_at IS NULL
   AND a.release_id IN (SELECT id FROM meta.dataset_release WHERE data_source_id = 'DS-07')
   AND a.building_id IS NOT NULL
   AND NOT EXISTS (
     SELECT 1 FROM reference.building_parcel link
      WHERE link.building_id = a.building_id AND link.relation_status = 'certain')
"""

RELEASES_SQL = """
SELECT data_source_id, id, release_key, lifecycle_status, acceptance_status
  FROM meta.dataset_release
 WHERE data_source_id IN ('DS-01', 'DS-02', 'DS-03', 'DS-06', 'DS-07')
   -- « Ce qui a été lu » : une release découverte mais jamais importée n'a rien fourni.
   AND EXISTS (
     SELECT 1 FROM meta.import_run run WHERE run.release_id = dataset_release.id)
 ORDER BY data_source_id, release_key
"""


def load_sales(connection: psycopg.Connection[Any], department: str) -> list[Sale]:
    return [
        Sale(
            parcel_id=row["parcel_id"],
            commune_code=row["commune_code"],
            mutation_date=row["mutation_date"],
            property_type=row["property_type"],
            price_eur=row["price_eur"],
            surface_m2=row["surface_m2"],
        )
        for row in fetch(connection, SALES_SQL, department=department)
    ]


def load_diagnostics(connection: psycopg.Connection[Any], department: str) -> list[Diagnostic]:
    return [
        Diagnostic(
            dpe_number=row["dpe_number"],
            parcel_id=row["parcel_id"],
            commune_code=row["commune_code"],
            deposited_on=row["deposited_on"],
            label=row["energy_label"],
            building_type=row["building_type"],
            from_immeuble=bool(row["from_immeuble"]),
        )
        for row in fetch(connection, DIAGNOSTICS_SQL, department=department)
    ]


def load_sale_dates(
    connection: psycopg.Connection[Any], department: str, sql: str
) -> dict[str, list[date]]:
    dates: dict[str, list[date]] = defaultdict(list)
    for row in fetch(connection, sql, department=department):
        dates[row["parcel_id"]].append(row["mutation_date"])
    return {parcel: sorted(values) for parcel, values in dates.items()}


def load_territories(connection: psycopg.Connection[Any], department: str) -> Territories:
    """Le rattachement commune → EPCI de DS-03, refusé s'il n'est pas univoque.

    Une commune rattachée à deux EPCI serait un défaut de source, pas une donnée à arbitrer ici.
    """
    epci_of: dict[str, str] = {}
    seen: dict[str, set[str]] = defaultdict(set)
    for row in fetch(connection, TERRITORIES_SQL, department=department):
        seen[row["commune_code"]].add(row["epci_code"])
    ambiguous = sorted(commune for commune, codes in seen.items() if len(codes) > 1)
    if ambiguous:
        raise SystemExit(
            f"Rattachement EPCI non univoque sur {len(ambiguous)} communes : {ambiguous[:5]}"
        )
    for commune, codes in seen.items():
        epci_of[commune] = next(iter(codes))
    communes_of: dict[str, list[str]] = defaultdict(list)
    for commune, epci in sorted(epci_of.items()):
        communes_of[epci].append(commune)
    names = {
        row["commune_code"]: row["name"] or ""
        for row in fetch(connection, COMMUNE_NAMES_SQL, department=department)
    }
    return Territories(epci_of=epci_of, communes_of=dict(communes_of), names=names)


# --------------------------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------------------------


def french(value: float | int | None, digits: int = 0, missing: str = "—") -> str:
    if value is None:
        return missing
    if digits == 0:
        return f"{round(value):,}".replace(",", " ")
    return f"{value:.{digits}f}".replace(".", ",")


def scope_rows(rows: Sequence[dict[str, Any]], scope_type: str, scope_code: str | None = None):
    return [
        row
        for row in rows
        if row["scope_type"] == scope_type
        and (scope_code is None or row["scope_code"] == scope_code)
    ]


def table(header: Sequence[str], lines: Sequence[Sequence[str]]) -> str:
    if not lines:
        return "_Aucune ligne._\n"
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(line) + " |" for line in lines]
    return "\n".join(out) + "\n"


def render(context: dict[str, Any]) -> str:
    parameters: Parameters = context["parameters"]
    department: str = context["department"]
    territories: Territories = context["territories"]
    lines: list[str] = []
    add = lines.append

    add(f"# Baromètre du marché — département {department}")
    add("")
    add(
        f"**Généré le :** {context['generated_on']} · **Mesures :** BAR-001 à BAR-009 de "
        "[`SPEC.md`](../../SPEC.md) §13.4 · **Ticket :** "
        "[H1](../backlog/H1-barometre-marche-35-mesures.md) · **Prix DVF :** transformation "
        f"version {DVF_TRANSFORMATION_VERSION} "
        "([H7](../backlog/H7-mutations-multi-parcelles.md), "
        "[`dvf-quality-35.md`](./dvf-quality-35.md))"
    )
    add("")
    add(recount_mention(context["attestation"]))
    add("")
    add(
        f"Empreinte des mesures : `{context['fingerprint'][:16]}` — une attestation de recompte ne "
        f"vaut que pour cette empreinte, consignée dans `barometre-marche-{department}/"
        f"{ATTESTATION_FILE}`. Elle est le SHA-256 des CSV `bar-*`, pris par ordre de nom, "
        "chacun sous la forme « nom, octet nul, contenu, octet nul »."
    )
    add("")
    add(
        "Toutes les mesures sont agrégées. Aucune parcelle, aucune adresse, aucune mutation "
        "individuelle n'apparaît dans ce document ni dans les CSV qui l'accompagnent. "
        "Régénérer : `make market-barometer DEPARTMENT=" + department + "`."
    )
    add("")
    add("## Ce qui a été lu, et dans quel état")
    add("")
    add(
        table(
            ["Source", "Release", "Cycle de vie", "Acceptation"],
            [
                [
                    row["data_source_id"],
                    row["release_key"],
                    row["lifecycle_status"],
                    row["acceptance_status"],
                ]
                for row in context["releases"]
            ],
        )
    )
    add(
        f"Dernière mutation connue : **{context['last_mutation']}**. Dernier dépôt de DPE de "
        f"l'extrait : **{context['last_deposit']}**."
    )
    add("")
    add(
        "**La réforme DPE du 1er janvier 2026 ne touche aucune mesure de ce rapport.** L'extrait "
        "DPE va au-delà, mais DVF s'arrête au 31 décembre 2025 : aucune mesure croisant un "
        "diagnostic et une vente ne peut atteindre un DPE postérieur à la réforme. La rupture de "
        "série reste à traiter au prochain millésime DVF."
    )
    add("")
    add("## Le filtre de chaque cohorte")
    add("")
    add(
        table(
            ["Cohorte", "Filtre écrit", "Effectif"],
            [
                [
                    "Ventes exploitables",
                    "`mutation_nature = 'Vente'` · type Maison ou Appartement · "
                    "`allocation_method = 'single_property_full_price'` · surface et prix > 0 · "
                    "parcelle rattachée · commune et année de la **mutation DVF**, pas de la "
                    "parcelle",
                    french(context["sales_count"]),
                ],
                [
                    "— dont maisons",
                    "idem, `property_type = 'Maison'`",
                    french(context["house_sales_count"]),
                ],
                [
                    "Ventes écartées par leur nature",
                    "`mutation_nature <> 'Vente'` — vente en l'état futur d'achèvement, terrain à "
                    "bâtir, échange, adjudication, expropriation",
                    french(context["excluded_nature_count"]),
                ],
                [
                    "DPE rattachés à une parcelle",
                    "relation bâtiment ↔ parcelle `certain` · DPE non annulé · commune lue sur "
                    "la parcelle, jamais sur le diagnostic",
                    french(context["diagnostics_count"]),
                ],
                [
                    "— DPE rattachés à un bâtiment mais à aucune parcelle `certain`",
                    "hors de toute mesure de cohorte, motif : leur bâtiment ne porte aucune "
                    "relation à une parcelle — aucune n'est `ambiguous`, elles sont toutes "
                    "absentes",
                    french(context["attachment_gap"]),
                ],
                [
                    "Premiers DPE par parcelle",
                    "le plus ancien dépôt de chaque parcelle, départagé par numéro de DPE",
                    french(context["first_diagnostics_count"]),
                ],
                [
                    f"Cohorte {context['cohort_year']}",
                    "premier DPE déposé dans l'année, hors DPE d'appartement généré depuis un "
                    "DPE d'immeuble",
                    french(context["cohort_size"]),
                ],
                [
                    "— exclusions DPE d'immeuble comptées",
                    "`numero_dpe_immeuble_associe` renseigné",
                    french(context["cohort_excluded"]),
                ],
                [
                    "Paires de ventes successives",
                    f"deux ventes de maison **consécutives** de la même parcelle, rang n → n+1, "
                    f"à plus de {parameters.repeat_min_days - 1} jours d'écart. "
                    f"{french(context['same_day_ties'])} couples (parcelle, date) portent "
                    "plusieurs ventes le même jour : elles sont **départagées par prix croissant, "
                    "puis par surface croissante**, faute de quoi « la vente suivante » n'est pas "
                    "déterminée. Compter toutes les combinaisons de deux ventes de la même "
                    f"parcelle au même écart, consécutives ou non, en donnerait "
                    f"{french(context['all_combinations'])}",
                    french(context["pairs_count"]),
                ],
                [
                    "Parcelles portant au moins une mutation, toutes dates",
                    "`mutation_nature LIKE 'Vente%'` — vente, VEFA et terrain à bâtir compris — "
                    "quel que soit le type de lot : une parcelle qui change de main a muté. "
                    "La vente doit être **strictement postérieure** au dépôt. C'est l'événement "
                    "de BAR-005, BAR-006 et BAR-007",
                    french(context["parcels_with_a_sale"]),
                ],
            ],
        )
    )
    add("")
    add("## L'écart 14 532 / 9 754, tranché")
    add("")
    add(
        "`dpe-signal-vente-35.md` annonce une cohorte 2024 de **14 532 parcelles** sans écrire son "
        "filtre, et E8g n'a pas su la reconstituer. Le filtre écrit ci-dessus donne, pour la même "
        f"année, **{french(context['cohort_before_exclusion'])} parcelles** avant l'exclusion des "
        f"DPE d'immeuble et **{french(context['cohort_size'])}** après. Le 14 532 n'est donc pas "
        "reproductible et ne doit plus être cité : l'effectif de référence est celui de ce "
        "rapport, avec son filtre. Le **taux**, lui, se retrouve — 35,65 % annoncé alors, "
        f"{french(context['reference_rate'], 1)} % ici : c'est la mesure qui tenait, pas son "
        "effectif."
    )
    add("")
    add("## Les supports, déclarés et contestables")
    add("")
    add(
        table(
            ["Mesure", "Support minimal", "Paramètre"],
            [
                [
                    "BAR-001, BAR-002",
                    f"{parameters.sales_per_cell} ventes par cellule",
                    "`--sales-per-cell`",
                ],
                ["BAR-003, BAR-008", f"{parameters.repeat_pairs} paires", "`--repeat-pairs`"],
                ["BAR-004", f"{parameters.label_sales} ventes par étiquette", "`--label-sales`"],
                [
                    f"Médiane de référence commune {CROSS} année, utilisée par BAR-003 et BAR-004",
                    f"{parameters.sales_per_cell} ventes de maison",
                    "`--sales-per-cell`",
                ],
                [
                    "BAR-005, BAR-006, BAR-007",
                    f"{parameters.dpe_cohort_parcels} parcelles de cohorte",
                    "`--dpe-cohort-parcels`",
                ],
                ["BAR-009", "aucun — les manques se comptent toujours", "—"],
            ],
        )
    )
    add(
        "Aucun de ces nombres n'est un seuil de sens métier. Sous le support, la valeur est "
        "**absente avec son motif** : elle n'est jamais repliée sur la valeur départementale."
    )
    add("")
    add("## Le découpage par EPCI")
    add("")
    add(
        f"{len(territories.communes_of)} EPCI, {len(territories.epci_of)} communes rattachées. "
        "Le rattachement vient de l'attribut `code_epci_insee` des groupes de bâtiments de "
        "**DS-03 BDNB**, seule source du dépôt qui le porte ; il est utilisé comme clé "
        "géographique, jamais comme attribut classant. DS-03 ne porte pas le nom des EPCI : "
        "chaque EPCI est désigné par son SIREN, et ses communes sont listées dans "
        "`epci-communes.csv`. Nommer les EPCI demande un référentiel absent du dépôt — limite "
        "déclarée, à trancher par H2."
    )
    add("")

    add("## BAR-001 et BAR-002 — volumes et prix au m²")
    add("")
    volumes = context["volumes"]
    years = sorted({row["year"] for row in volumes if row["scope_type"] == DEPARTMENT_SCOPE})
    for property_type in ("Maison", "Appartement"):
        add(f"### {property_type}s, département {department}")
        add("")
        add(
            table(
                ["Année", "Ventes", "Q1 €/m²", "Médiane €/m²", "Q3 €/m²", "Motif"],
                [
                    [
                        str(row["year"]),
                        french(row["sales"]),
                        french(row["q1_eur_m2"]),
                        f"**{french(row['median_eur_m2'])}**",
                        french(row["q3_eur_m2"]),
                        row["reason"] or "",
                    ]
                    for year in years
                    for row in volumes
                    if row["scope_type"] == DEPARTMENT_SCOPE
                    and row["year"] == year
                    and row["property_type"] == property_type
                ],
            )
        )
        add("")
    add(
        "Le détail par EPCI et par commune est dans `bar-001-002-volumes-prix.csv`, une ligne par "
        "cellule, effectif toujours présent. Dans cette mesure, une cellule sans vente est "
        "**absente**, jamais mise à zéro."
    )
    add("")
    add(
        "**La série mêle deux releases DVF** : les années 2014 à 2020 viennent de l'archive "
        "`DS-06@2019-04-archive`, les années 2021 à 2025 de `DS-06@2026-09-13`. Aucune césure "
        "n'apparaît dans les tableaux. `dvf-quality-35.md` établit que 2014 et 2015 sont les deux "
        "seuls millésimes dont l'incomplétude ne peut pas être corrigée, aucune publication "
        "ultérieure ne les portant : leurs volumes sont des planchers, pas des comptes."
    )
    add("")

    add("## BAR-003 — plus-value nette de marché selon le prix d'entrée")
    add("")
    add(
        f"Reventes de maison en {french(parameters.repeat_max_days)} jours au plus, **surface "
        "inchangée**, ratio de prix divisé par l'évolution de la médiane de la commune entre les "
        "deux années. Le prix d'entrée est rapporté à la médiane de la commune l'année de "
        f"l'achat, et les deux années doivent atteindre {parameters.sales_per_cell} ventes."
    )
    add("")
    add(
        table(
            ["De la paire à la mesure", "Paires"],
            [[label, french(value)] for label, value in context["margin_funnel"].items()],
        )
    )
    add("")
    add(
        table(
            [
                "Prix d'entrée",
                "Paires",
                "Médiane",
                "Q3",
                f"Part > {french(parameters.excess_threshold, 2)}",
                "Motif",
            ],
            [
                [
                    row["entry_band"],
                    french(row["pairs"]),
                    f"**{french(row['median_excess'], 2)}**",
                    french(row["q3_excess"], 2),
                    french(row["share_above_threshold_pct"], 1) + " %"
                    if row["share_above_threshold_pct"] is not None
                    else "—",
                    row["reason"] or "",
                ]
                for row in scope_rows(context["margin"], DEPARTMENT_SCOPE)
            ],
        )
    )
    add(
        "Réserves, inchangées depuis `pistes-analyse-marche-35.md` §5.2 : biais du survivant — "
        "seules les reventes sont vues ; retour à la moyenne ; une surface erronée à l'achat "
        "gonfle mécaniquement le ratio."
    )
    add("")

    add("## BAR-004 — décote ou surcote par étiquette")
    add("")
    add(
        f"Ventes de maison depuis {parameters.label_from_year} portant un DPE de "
        f"`type_batiment = 'maison'` déposé dans les {parameters.label_lookback_days} jours "
        "précédant l'acte, le jour même compris — le dernier de la fenêtre. Prix au m² "
        "rapporté à la médiane commune "
        f"{CROSS} année, laquelle doit atteindre {parameters.sales_per_cell} ventes. Contrôle "
        f"commune {CROSS} année seulement : ni âge, ni surface, ni modèle hédonique."
    )
    add("")
    add(
        table(
            ["Étiquette", "Ventes", "Q1", "Médiane", "Q3", "Motif"],
            [
                [
                    row["energy_label"],
                    french(row["sales"]),
                    french(row["q1_ratio"], 2),
                    f"**{french(row['median_ratio'], 2)}**",
                    french(row["q3_ratio"], 2),
                    row["reason"] or "",
                ]
                for row in scope_rows(context["labels"], DEPARTMENT_SCOPE)
            ],
        )
    )
    add(
        "Les sept étiquettes paraissent pour chaque périmètre, **y compris à effectif nul** : "
        "qu'aucune vente de maison classée A n'ait été observée dans un EPCI est une "
        f"information, alors qu'une cellule année {CROSS} type sans aucune vente n'existe pas et "
        "reste absente de "
        "BAR-001/002. Les deux mesures ne traitent pas l'absence de la même façon, et c'est "
        "délibéré."
    )
    add("")

    add(f"## BAR-005 — délai dépôt DPE → acte, cohorte {context['cohort_year']}")
    add("")
    add(
        table(
            [
                "Périmètre",
                "Parcelles de cohorte",
                "Vendues sous 12 mois",
                "Q1 j",
                "Médiane j",
                "Q3 j",
            ],
            [
                [
                    "Département " + department,
                    french(row["cohort_parcels"]),
                    french(row["sold_within_window"]),
                    french(row["q1_days"]),
                    f"**{french(row['median_days'])}**",
                    french(row["q3_days"]),
                ]
                for row in scope_rows(context["delay"], DEPARTMENT_SCOPE)
            ],
        )
    )
    add("Par EPCI et par commune : `bar-005-delai-dpe-acte.csv`.")
    add("")

    add("## BAR-006 — taux de mutation à douze mois après le premier DPE")
    add("")
    add(
        table(
            ["Cohorte", "Parcelles", "Vendues sous 12 mois", "Taux", "Motif"],
            [
                [
                    str(row["cohort_year"]),
                    french(row["cohort_parcels"]),
                    french(row["sold_within_12_months"]),
                    f"**{french(row['rate_pct'], 1)} %**" if row["rate_pct"] is not None else "—",
                    row["reason"] or "",
                ]
                for row in context["rates"]
                if row["scope_type"] == DEPARTMENT_SCOPE
            ],
        )
    )
    add(
        "**Ce que change la définition de la vente.** Le taux ci-dessus compte toute mutation de "
        f"la parcelle. En exigeant que la mutation porte un lot Maison ou Appartement, la cohorte "
        f"{context['cohort_year']} passe de {french(context['reference_rate'], 1)} % à "
        f"{french(context['dwelling_rate'], 1)} %. L'écart est le fait des parcelles vendues "
        "comme terrain, dépendance ou local. Les deux lectures sont défendables ; c'est la "
        "première qui est publiée, et la seconde qui en donne la marge."
    )
    add("")
    add(
        "La cohorte la plus récente est la dernière dont les douze mois de suivi sont couverts "
        f"par DVF — **{context['cohort_year']}**, dérivée de la dernière mutation connue, jamais "
        "choisie. La cohorte la plus ancienne est tronquée à gauche : l'extrait DPE commence le "
        f"{context['first_deposit']}, donc « premier DPE » y est moins sûr."
    )
    add("")

    add(f"## BAR-007 — courbe de conversion, cohorte {context['cohort_year']}")
    add("")
    curve = [
        row
        for row in context["curve"]
        if row["scope_type"] == DEPARTMENT_SCOPE and row["cohort_year"] == context["cohort_year"]
    ]
    add(
        table(
            ["Mois après dépôt"] + [str(row["month"]) for row in curve],
            [
                ["Cumul vendu"]
                + [
                    french(row["cumulative_pct"], 1) + " %"
                    if row["cumulative_pct"] is not None
                    else "—"
                    for row in curve
                ],
                ["Parcelles"] + [french(row["cohort_parcels"]) for row in curve],
            ],
        )
    )
    add(
        f"Mois conventionnels de {parameters.curve_month_days} jours, déclarés comme tels. La "
        f"courbe porte sur {french(context['cohort_size'])} parcelles. Son douzième mois vaut "
        f"{parameters.curve_months[-1] * parameters.curve_month_days} jours et non "
        f"{parameters.conversion_days} : c'est pourquoi il tombe légèrement sous le taux de "
        "BAR-006, qui est la même mesure sur cinq jours de plus."
    )
    add("")

    add("## BAR-008 — effet d'une extension de surface")
    add("")
    add(
        "Paires de ventes successives de maison, **surface bâtie strictement en hausse** entre "
        f"les deux actes, écart de plus de {parameters.repeat_min_days - 1} jours. Aucune médiane "
        "de référence n'intervient : les deux ratios sont bruts. La ligne « surface modifiée » de "
        "l'entonnoir BAR-003 compte toute surface différente, celle-ci seulement les hausses."
    )
    add("")
    add(
        table(
            ["Fenêtre", "Paires", "Ratio de prix médian", "Ratio au m² médian", "Motif"],
            [
                [
                    row["window"],
                    french(row["pairs"]),
                    french(row["median_price_ratio"], 2),
                    f"**{french(row['median_price_per_m2_ratio'], 2)}**",
                    row["reason"] or "",
                ]
                for row in context["extension"]
            ],
        )
    )
    add("")

    add("## BAR-009 — ce que le baromètre ne voit pas")
    add("")
    coverage = context["coverage"]
    total_mutations = sum(row["mutations"] for row in coverage)
    total_unallocatable = sum(row["mutations_without_allocatable_price"] for row in coverage)
    total_diagnostics = sum(row["diagnostics"] for row in coverage)
    total_unattached = sum(row["diagnostics_without_building"] for row in coverage)
    add(
        table(
            ["Mesure", "Total", "Manquants", "Part"],
            [
                [
                    "Mutations sans prix allouable — toutes natures, tous millésimes",
                    french(total_mutations),
                    french(total_unallocatable),
                    french(100.0 * total_unallocatable / total_mutations, 1) + " %"
                    if total_mutations
                    else "—",
                ],
                [
                    "DPE non rattachés à un bâtiment — extrait entier",
                    french(total_diagnostics),
                    french(total_unattached),
                    french(100.0 * total_unattached / total_diagnostics, 1) + " %"
                    if total_diagnostics
                    else "—",
                ],
            ],
        )
    )
    add(
        f"Commune par commune : `bar-009-couverture.csv`, {len(coverage)} communes — contre "
        f"{len(territories.epci_of)} au référentiel cadastral. L'écart est le phénomène de "
        "communes fusionnées déjà mesuré dans `dvf-quality-35.md` : une commune que DVF ou "
        "l'ADEME connaît encore mais que le cadastre ne porte plus reste comptée ici, sans EPCI, "
        "plutôt que rattachée par défaut. Une part n'est jamais calculée sur un dénominateur "
        "nul : elle reste absente avec son motif."
    )
    add("")

    add("## Ce que ce rapport n'établit pas")
    add("")
    add(
        "- Il ne publie aucune parcelle ni aucune adresse, et n'estime la valeur d'aucun bien non "
        "vendu.\n"
        "- Il ne combine aucune mesure en score : l'étiquette et l'âge d'un DPE restent deux "
        "lectures indépendantes.\n"
        "- Le rattachement d'un DPE à un bâtiment plafonne à ce que mesure BAR-009 ; les "
        "diagnostics rattachés à la seule adresse sont hors de toutes les mesures de cohorte.\n"
        "- Le taux de conversion encaisse la dilution vente / location : le motif d'un "
        "diagnostic n'est pas publié par l'ADEME.\n"
        "- **Le « 0,6 % » hérité ne se reproduit pas.** `SPEC.md` §7.3 et "
        "`pistes-analyse-marche-35.md` §1.4 justifient l'exclusion des DPE d'appartement générés "
        "depuis un DPE d'immeuble par un taux de conversion de 0,6 %, sans filtre écrit. Sous les "
        f"filtres de ce rapport, ces premiers DPE des cohortes {context['cohort_years'][0]} à "
        f"{context['cohort_years'][-1]} sont {french(context['excluded_cohort_size'])}, dont "
        f"{french(context['excluded_cohort_sold'])} "
        f"{'a' if context['excluded_cohort_sold'] <= 1 else 'ont'} muté dans les douze mois, soit "
        f"**{french(context['excluded_cohort_rate'], 1)} %**. Même ordre de grandeur, pas le même "
        "chiffre, et le filtre d'origine reste inconnu. L'exclusion garde sa justification — ce "
        "taux est sans commune mesure avec celui de la cohorte — mais c'est ce chiffre-ci, avec "
        "son effectif et son filtre, qui doit être cité. La réécriture de `SPEC.md` est le "
        "ticket H6.\n"
        "- Les CSV descendent à des effectifs communaux de quelques parcelles. Ce sont des "
        "comptes sans attribut, donc rien de nominatif, mais une commune où la cohorte compte une "
        "parcelle n'a plus grand-chose d'agrégé : ces lignes portent toutes « support "
        "insuffisant » et aucune valeur, et n'ont pas à être publiées telles quelles par H2."
    )
    add("")
    add("Sources : DVF DGFiP / Etalab, DPE ADEME, cadastre Etalab, BDNB CSTB. Licence Ouverte 2.0.")
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# Programme
# --------------------------------------------------------------------------------------------


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    defaults = Parameters()
    parser = argparse.ArgumentParser(description="Baromètre du marché — mesures BAR-001 à BAR-009")
    parser.add_argument("--department", default="35", help="Code département, par exemple 35")
    parser.add_argument("--sales-per-cell", type=int, default=defaults.sales_per_cell)
    parser.add_argument("--repeat-pairs", type=int, default=defaults.repeat_pairs)
    parser.add_argument("--label-sales", type=int, default=defaults.label_sales)
    parser.add_argument("--dpe-cohort-parcels", type=int, default=defaults.dpe_cohort_parcels)
    parser.add_argument(
        "--generated-on", default=None, help="Date de génération, pour une sortie reproductible"
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args(argv)


def collect(connection: psycopg.Connection[Any], department: str, parameters: Parameters):
    """Lit la base et calcule toutes les mesures. Le calcul lui-même reste hors de la base."""
    territories = load_territories(connection, department)
    sales = load_sales(connection, department)
    diagnostics = load_diagnostics(connection, department)
    sale_dates = load_sale_dates(connection, department, SALE_DATES_SQL)
    # La même cohorte, lue avec un événement plus strict : la mutation doit porter un lot de
    # logement. L'écart entre les deux taux est la sensibilité de BAR-006 à sa définition.
    dwelling_sale_dates = load_sale_dates(connection, department, DWELLING_SALE_DATES_SQL)
    coverage = coverage_gaps(fetch(connection, COVERAGE_SQL, department=department))
    attachment_gap = fetch(connection, ATTACHMENT_GAP_SQL, department=department)[0]["n"]
    releases = fetch(connection, RELEASES_SQL)
    excluded_nature = fetch(
        connection,
        "SELECT count(*) AS n FROM observation.transaction"
        " WHERE department_code = %(department)s AND mutation_nature <> 'Vente'",
        department=department,
    )[0]["n"]
    last_mutation = fetch(
        connection,
        "SELECT max(mutation_date) AS last FROM observation.transaction"
        " WHERE department_code = %(department)s",
        department=department,
    )[0]["last"]
    deposits = fetch(
        connection,
        "SELECT min(coalesce(deposited_at, assessment_date)) AS first,"
        " max(coalesce(deposited_at, assessment_date)) AS last"
        " FROM observation.energy_assessment WHERE department_code = %(department)s"
        " AND release_id IN (SELECT id FROM meta.dataset_release WHERE data_source_id = 'DS-07')",
        department=department,
    )[0]

    houses = [sale for sale in sales if sale.property_type == "Maison"]
    pairs = build_pairs(houses, parameters)
    references = reference_medians(sales, parameters)
    first = first_diagnostics(diagnostics)
    by_parcel: dict[str, list[Diagnostic]] = defaultdict(list)
    for diagnostic in diagnostics:
        if diagnostic.building_type == "maison":
            by_parcel[diagnostic.parcel_id].append(diagnostic)

    ceiling = cohort_year_ceiling(last_mutation)
    cohort_years = sorted(
        {
            diagnostic.deposited_on.year
            for diagnostic in first.values()
            if diagnostic.deposited_on.year <= ceiling
        }
    )
    rates: list[dict[str, Any]] = []
    for year in cohort_years:
        cohort = build_cohort(first, sale_dates, year)
        rates += conversion_rate(cohort, year, territories, department, parameters)
    # La cohorte de référence est celle du plafond : la dernière dont les douze mois de suivi
    # sont couverts par DVF. Elle porte la courbe et le délai.
    reference_cohort = build_cohort(first, sale_dates, ceiling)
    curve = conversion_curve(reference_cohort, ceiling, territories, department, parameters)
    excluded = count_excluded_from_immeuble(first, ceiling)
    reference_rate = next(
        row["rate_pct"]
        for row in rates
        if row["scope_type"] == DEPARTMENT_SCOPE and row["cohort_year"] == ceiling
    )
    excluded_cohort = build_excluded_cohort(first, sale_dates, cohort_years)
    excluded_sold = sum(
        1
        for row in excluded_cohort
        if row.days_to_deed is not None and row.days_to_deed <= parameters.conversion_days
    )
    dwelling_cohort = build_cohort(first, dwelling_sale_dates, ceiling)
    dwelling_rate = next(
        row["rate_pct"]
        for row in conversion_rate(dwelling_cohort, ceiling, territories, department, parameters)
        if row["scope_type"] == DEPARTMENT_SCOPE
    )
    margin, margin_funnel = net_margin_by_entry_price(
        pairs, references, territories, department, parameters
    )

    return {
        "department": department,
        "parameters": parameters,
        "territories": territories,
        "releases": releases,
        "last_mutation": last_mutation.isoformat(),
        "first_deposit": deposits["first"].isoformat(),
        "last_deposit": deposits["last"].isoformat(),
        "sales_count": len(sales),
        "house_sales_count": len(houses),
        "excluded_nature_count": int(excluded_nature),
        "diagnostics_count": len(diagnostics),
        "first_diagnostics_count": len(first),
        "cohort_year": ceiling,
        "cohort_size": len(reference_cohort),
        "cohort_excluded": excluded,
        "cohort_before_exclusion": len(reference_cohort) + excluded,
        "cohort_years": cohort_years,
        "excluded_cohort_size": len(excluded_cohort),
        "excluded_cohort_sold": excluded_sold,
        "excluded_cohort_rate": (
            round(100.0 * excluded_sold / len(excluded_cohort), 1) if excluded_cohort else None
        ),
        "reference_rate": reference_rate,
        "dwelling_rate": dwelling_rate,
        "attachment_gap": int(attachment_gap),
        "parcels_with_a_sale": len(sale_dates),
        "pairs_count": len(pairs),
        "same_day_ties": same_day_ties(houses),
        "all_combinations": all_combinations(houses, parameters),
        "margin_funnel": margin_funnel,
        "volumes": volumes_and_prices(sales, territories, department, parameters),
        "margin": margin,
        "labels": label_premium(
            sales, dict(by_parcel), references, territories, department, parameters
        ),
        "delay": deed_delay(reference_cohort, territories, department, parameters),
        "rates": rates,
        "curve": curve,
        "extension": extension_effect(pairs, department, parameters),
        "coverage": coverage,
    }


CSV_TABLES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "volumes",
        "bar-001-002-volumes-prix.csv",
        (
            "scope_type",
            "scope_code",
            "year",
            "property_type",
            "sales",
            "q1_eur_m2",
            "median_eur_m2",
            "q3_eur_m2",
            "reason",
        ),
    ),
    (
        "margin",
        "bar-003-plus-value-prix-entree.csv",
        (
            "scope_type",
            "scope_code",
            "entry_band",
            "pairs",
            "median_excess",
            "q3_excess",
            "share_above_threshold_pct",
            "reason",
        ),
    ),
    (
        "labels",
        "bar-004-etiquette.csv",
        (
            "scope_type",
            "scope_code",
            "energy_label",
            "sales",
            "q1_ratio",
            "median_ratio",
            "q3_ratio",
            "reason",
        ),
    ),
    (
        "delay",
        "bar-005-delai-dpe-acte.csv",
        (
            "scope_type",
            "scope_code",
            "cohort_parcels",
            "sold_within_window",
            "q1_days",
            "median_days",
            "q3_days",
            "reason",
        ),
    ),
    (
        "rates",
        "bar-006-taux-mutation-12-mois.csv",
        (
            "scope_type",
            "scope_code",
            "cohort_year",
            "cohort_parcels",
            "sold_within_12_months",
            "rate_pct",
            "reason",
        ),
    ),
    (
        "curve",
        "bar-007-courbe-conversion.csv",
        (
            "scope_type",
            "scope_code",
            "cohort_year",
            "month",
            "cohort_parcels",
            "sold_cumulative",
            "cumulative_pct",
            "reason",
        ),
    ),
    (
        "extension",
        "bar-008-extension-surface.csv",
        (
            "scope_type",
            "scope_code",
            "window",
            "pairs",
            "median_price_ratio",
            "median_price_per_m2_ratio",
            "reason",
        ),
    ),
    (
        "coverage",
        "bar-009-couverture.csv",
        (
            "scope_type",
            "scope_code",
            "mutations",
            "mutations_without_allocatable_price",
            "share_without_allocatable_price_pct",
            "diagnostics",
            "diagnostics_without_building",
            "share_without_building_pct",
            "reason",
        ),
    ),
)


ATTESTATION_FILE = "recompte.csv"
ATTESTATION_COLUMNS = ("recounted_on", "fingerprint", "note")
METADATA_FILE = "metadonnees.csv"


def fingerprint_files(paths: Sequence[Path]) -> str:
    """L'empreinte des mesures publiées, dans un ordre fixe.

    Une attestation de recompte porte cette empreinte : si une mesure change, l'attestation ne
    s'applique plus, et la mention « recompté » disparaît d'elle-même au lieu de mentir.
    """
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def read_attestations(path: Path) -> list[dict[str, str]]:
    """Les attestations écrites après un recompte. Une ligne incomplète arrête tout.

    Une attestation est ce qui autorise la mention « recompté » : mal formée, elle ne doit ni
    passer en silence ni être ignorée, sinon la mention dépendrait d'un accident de saisie.
    """
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for number, row in enumerate(rows, start=2):
        if any(row.get(column) is None for column in ATTESTATION_COLUMNS) or None in row:
            raise SystemExit(f"{path}, ligne {number} : attestation mal formée — {row}")
    return rows


def find_attestation(rows: Sequence[dict[str, str]], fingerprint: str) -> dict[str, str] | None:
    """La dernière attestation écrite pour exactement ces mesures, ou rien."""
    matching = [row for row in rows if row.get("fingerprint") == fingerprint]
    return matching[-1] if matching else None


def recount_mention(attestation: dict[str, str] | None) -> str:
    """BR-007 : la mention datée en tête du rapport, ou l'avertissement qui la remplace."""
    if attestation is None:
        return (
            "**Non recompté.** Aucune attestation de `recompte-preuve` ne porte l'empreinte de ces "
            "mesures : ce rapport ne se publie pas en l'état (BR-007)."
        )
    note = attestation.get("note", "").strip()
    return f"**Recompté le {attestation['recounted_on']}** par `recompte-preuve`" + (
        f" — {note}." if note else "."
    )


def metadata_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Ce que H2 doit imprimer sur chaque page : millésimes, dates, supports, recompte."""
    parameters: Parameters = context["parameters"]
    attestation = context["attestation"]
    releases = context["releases"]

    def release_keys(source: str) -> str:
        return " + ".join(row["release_key"] for row in releases if row["data_source_id"] == source)

    values = {
        "department": context["department"],
        "generated_on": context["generated_on"],
        "last_mutation": context["last_mutation"],
        "first_deposit": context["first_deposit"],
        "last_deposit": context["last_deposit"],
        "cohort_year": context["cohort_year"],
        "sales_first_year": min(row["year"] for row in context["volumes"]),
        "sales_last_year": max(row["year"] for row in context["volumes"]),
        "label_from_year": parameters.label_from_year,
        "release_ds01": release_keys("DS-01"),
        "release_ds02": release_keys("DS-02"),
        "release_ds03": release_keys("DS-03"),
        "release_ds06": release_keys("DS-06"),
        "release_ds07": release_keys("DS-07"),
        "support_sales_per_cell": parameters.sales_per_cell,
        "support_repeat_pairs": parameters.repeat_pairs,
        "support_label_sales": parameters.label_sales,
        "support_dpe_cohort_parcels": parameters.dpe_cohort_parcels,
        "repeat_max_days": parameters.repeat_max_days,
        "curve_month_days": parameters.curve_month_days,
        "fingerprint": context["fingerprint"],
        "recounted_on": attestation["recounted_on"] if attestation else "",
        "recount_note": attestation.get("note", "") if attestation else "non recompté",
    }
    return [{"key": key, "value": value} for key, value in values.items()]


def write_outputs(context: dict[str, Any], root: Path) -> Path:
    department = context["department"]
    directory = root / f"barometre-marche-{department}"
    directory.mkdir(parents=True, exist_ok=True)
    for key, filename, columns in CSV_TABLES:
        write_csv(directory / filename, context[key], list(columns))
    territories: Territories = context["territories"]
    write_csv(
        directory / "epci-communes.csv",
        [
            {
                "epci_code": epci,
                "commune_code": commune,
                "commune_name": territories.names.get(commune, ""),
            }
            for epci, communes in sorted(territories.communes_of.items())
            for commune in communes
        ],
        ["epci_code", "commune_code", "commune_name"],
    )
    context["fingerprint"] = fingerprint_files(
        [directory / filename for _, filename, _ in CSV_TABLES]
    )
    context["attestation"] = find_attestation(
        read_attestations(directory / ATTESTATION_FILE), context["fingerprint"]
    )
    write_csv(directory / METADATA_FILE, metadata_rows(context), ["key", "value"])
    report = root / f"barometre-marche-{department}.md"
    report.write_text(render(context), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    parameters = replace(
        Parameters(),
        sales_per_cell=arguments.sales_per_cell,
        repeat_pairs=arguments.repeat_pairs,
        label_sales=arguments.label_sales,
        dpe_cohort_parcels=arguments.dpe_cohort_parcels,
    )
    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        connection.execute("SET LOCAL statement_timeout = '1200s'")
        context = collect(connection, arguments.department, parameters)

    context["generated_on"] = arguments.generated_on or date.today().isoformat()
    root = arguments.output_dir or (Path(__file__).resolve().parents[2] / "docs" / "data")
    report = write_outputs(context, root)
    print(f"Baromètre écrit : {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
