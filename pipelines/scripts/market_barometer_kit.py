#!/usr/bin/env python3
"""Le baromètre mis en forme : une feuille A4 par territoire — H2.

Lit **uniquement** les CSV que H1 écrit dans `docs/data/barometre-marche-<dep>/` et produit, dans
le même dossier, un document HTML autonome par territoire : le département, puis chaque EPCI qui a
du support. Aucune base, aucune dépendance réseau, aucune bibliothèque : les graphiques sont du SVG
écrit à la main. La sortie est une fonction pure des CSV — la date imprimée est celle de la
génération des mesures, lue dans `metadonnees.csv`, jamais l'horloge.

## Une feuille, deux faces

Le **recto** répond aux quatre questions de `SPEC.md` §7.1 — le marché, la marge, l'énergie, le
tempo — avec un chiffre et un graphique chacune. Le **verso** porte les mêmes chiffres en tableaux,
avec leurs effectifs, leurs motifs d'absence et leurs filtres : c'est la vue tableau que tout
graphique doit avoir, et c'est lui qui rend chaque nombre du recto vérifiable.

## Ce qu'une page ne fait jamais

Elle ne remplace pas une valeur sans support par celle du département : elle écrit « support
insuffisant » avec l'effectif (BR-003). Elle ne nomme ni parcelle ni adresse (BR-005). Elle ne se
présente pas comme publiable si les mesures n'ont pas été recomptées (BR-007).
"""

import argparse
import csv
import html
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

DEPARTMENT_SCOPE = "departement"
EPCI_SCOPE = "epci"
NBSP = "\u00a0"
NNBSP = "\u202f"
CROSS = "\u00d7"
MINUS = "\u2212"
EN_DASH = "\u2013"

# Motif qui ne doit jamais apparaître dans un document : un identifiant cadastral.
CADASTRAL_ID = re.compile(r"\d{5}\d{3}[A-Z]{2}\d{4}")

MEASURE_FILES = {
    "volumes": "bar-001-002-volumes-prix.csv",
    "margin": "bar-003-plus-value-prix-entree.csv",
    "labels": "bar-004-etiquette.csv",
    "delay": "bar-005-delai-dpe-acte.csv",
    "rates": "bar-006-taux-mutation-12-mois.csv",
    "curve": "bar-007-courbe-conversion.csv",
    "extension": "bar-008-extension-surface.csv",
}


# --------------------------------------------------------------------------------------------
# Lecture
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Barometer:
    tables: dict[str, list[dict[str, str]]]
    metadata: dict[str, str]
    communes: list[dict[str, str]]

    def rows(self, table: str, scope_type: str, scope_code: str) -> list[dict[str, str]]:
        return [
            row
            for row in self.tables[table]
            if row["scope_type"] == scope_type and row["scope_code"] == scope_code
        ]

    @property
    def department(self) -> str:
        return self.metadata["department"]

    @property
    def recounted(self) -> bool:
        return bool(self.metadata.get("recounted_on"))


@dataclass(frozen=True)
class Territory:
    scope_type: str
    scope_code: str
    communes: tuple[tuple[str, str], ...] = ()

    @property
    def slug(self) -> str:
        return f"{self.scope_type}-{self.scope_code}"

    @property
    def title(self) -> str:
        if self.scope_type == DEPARTMENT_SCOPE:
            return f"Département {self.scope_code}"
        return f"Intercommunalité {self.scope_code}"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"{path} absent — lancer d'abord make market-barometer")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load(directory: Path) -> Barometer:
    tables = {key: read_csv(directory / name) for key, name in MEASURE_FILES.items()}
    metadata = {row["key"]: row["value"] for row in read_csv(directory / "metadonnees.csv")}
    communes = read_csv(directory / "epci-communes.csv")
    return Barometer(tables=tables, metadata=metadata, communes=communes)


def number(raw: str | None) -> float | None:
    """Une cellule vide est une absence, jamais un zéro."""
    if raw is None or raw.strip() == "":
        return None
    return float(raw)


def count(raw: str | None) -> int:
    return int(raw) if raw and raw.strip() else 0


def has_support(row: dict[str, str], value_key: str) -> bool:
    return number(row.get(value_key)) is not None


def territories(barometer: Barometer) -> list[Territory]:
    """Le département, puis chaque EPCI qui a du support sur au moins une mesure."""
    result = [Territory(DEPARTMENT_SCOPE, barometer.department)]
    by_epci: dict[str, list[tuple[str, str]]] = {}
    for row in barometer.communes:
        by_epci.setdefault(row["epci_code"], []).append(
            (row["commune_code"], row["commune_name"] or row["commune_code"])
        )
    value_keys = {
        "volumes": "median_eur_m2",
        "margin": "median_excess",
        "labels": "median_ratio",
        "rates": "rate_pct",
    }
    for epci in sorted(by_epci):
        supported = any(
            has_support(row, value_key)
            for table, value_key in value_keys.items()
            for row in barometer.rows(table, EPCI_SCOPE, epci)
        )
        if supported:
            communes = tuple(sorted(by_epci[epci], key=lambda item: item[1]))
            result.append(Territory(EPCI_SCOPE, epci, communes))
    return result


# --------------------------------------------------------------------------------------------
# Écriture des nombres — à la française, jamais un zéro pour une absence
# --------------------------------------------------------------------------------------------


def grouped(value: float) -> str:
    return f"{round(value):,}".replace(",", NNBSP)


def decimal(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def signed_percent(value: float, digits: int = 0) -> str:
    rounded = round(value, digits)
    sign = "+" if rounded > 0 else (MINUS if rounded < 0 else "")
    return f"{sign}{decimal(abs(rounded), digits)}{NBSP}%"


def percent(value: float, digits: int = 1) -> str:
    return f"{decimal(value, digits)}{NBSP}%"


def euros_m2(value: float) -> str:
    return f"{grouped(value)}{NBSP}€/m²"


def date_fr(iso: str) -> str:
    months = (
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
    )  # fmt: skip
    year, month, day = iso.split("-")
    return f"{int(day)} {months[int(month) - 1]} {year}"


def month_fr(iso: str) -> str:
    months = (
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
    )  # fmt: skip
    year, month, _ = iso.split("-")
    return f"{months[int(month) - 1]} {year}"


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def insufficient(effectif: int, minimum: str, unit: str) -> str:
    return (
        f'<p class="absent"><b>Support insuffisant</b> : {grouped(effectif)} {unit}, '
        f"{minimum} requis. La valeur n'est pas publiée, et n'est pas remplacée par celle du "
        "département.</p>"
    )


# --------------------------------------------------------------------------------------------
# Graphiques SVG
# --------------------------------------------------------------------------------------------


def nice_step(span: float, target_ticks: int = 4) -> float:
    raw = span / max(target_ticks, 1)
    magnitude = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 1
    for multiple in (1, 2, 2.5, 5, 10):
        step = multiple * magnitude
        if step >= raw:
            return step
    return 10 * magnitude


def ticks(low: float, high: float, target: int = 4) -> list[float]:
    if high <= low:
        high = low + 1
    step = nice_step(high - low, target)
    start = (low // step) * step
    values = []
    value = start
    while value <= high + step * 0.001:
        values.append(value)
        value += step
    if values[-1] < high:
        values.append(values[-1] + step)
    return values


@dataclass(frozen=True)
class Series:
    name: str
    token: str
    points: tuple[tuple[int, float | None], ...]


def line_chart(series: Sequence[Series], width: int = 330, height: int = 140) -> str:
    """Prix médian au m² dans le temps. Une année sans support est un trou, pas un zéro."""
    left, right, top, bottom = 44, 70, 10, 22
    plot_w, plot_h = width - left - right, height - top - bottom
    years = sorted({year for item in series for year, _ in item.points})
    values = [value for item in series for _, value in item.points if value is not None]
    if not years or not values:
        return ""
    grid = ticks(min(values), max(values))
    low, high = grid[0], grid[-1]

    def x(year: int) -> float:
        if len(years) == 1:
            return left + plot_w / 2
        return left + (year - years[0]) / (years[-1] - years[0]) * plot_w

    def y(value: float) -> float:
        return top + plot_h - (value - low) / (high - low) * plot_h

    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Prix médian au mètre carré par année">'
    ]
    for tick in grid:
        parts.append(
            f'<line class="grid" x1="{left}" x2="{left + plot_w}" y1="{y(tick):.1f}" '
            f'y2="{y(tick):.1f}"/>'
            f'<text class="tick" x="{left - 6}" y="{y(tick) + 3:.1f}" text-anchor="end">'
            f"{grouped(tick)}</text>"
        )
    for year in (years[0], years[len(years) // 2], years[-1]):
        parts.append(
            f'<text class="tick" x="{x(year):.1f}" y="{height - 6}" text-anchor="middle">'
            f"{year}</text>"
        )
    end_labels: list[tuple[float, str, str]] = []
    for item in series:
        segments: list[list[tuple[int, float]]] = [[]]
        for year, value in item.points:
            if value is None:
                if segments[-1]:
                    segments.append([])
                continue
            segments[-1].append((year, value))
        for segment in segments:
            if len(segment) > 1:
                path = " ".join(
                    f"{'M' if index == 0 else 'L'}{x(year):.1f},{y(value):.1f}"
                    for index, (year, value) in enumerate(segment)
                )
                parts.append(f'<path class="line" style="stroke:var({item.token})" d="{path}"/>')
            for year, value in segment if len(segment) == 1 else ():
                parts.append(
                    f'<circle class="dot" style="fill:var({item.token})" cx="{x(year):.1f}" '
                    f'cy="{y(value):.1f}" r="4"/>'
                )
        for year, value in item.points:
            if value is not None:
                parts.append(
                    f'<circle class="hit" cx="{x(year):.1f}" cy="{y(value):.1f}" r="7">'
                    f"<title>{esc(item.name)} {year} : {euros_m2(value)}</title></circle>"
                )
        last = [(year, value) for year, value in item.points if value is not None]
        if last:
            year, value = last[-1]
            parts.append(
                f'<circle class="dot" style="fill:var({item.token})" cx="{x(year):.1f}" '
                f'cy="{y(value):.1f}" r="4"/>'
            )
            text = grouped(value) if year == years[-1] else f"{grouped(value)} ({year})"
            end_labels.append((y(value), text, item.token))
    # Étiquettes de fin : écartées si elles se chevauchent, sans jamais quitter leur série.
    end_labels.sort()
    placed: list[float] = []
    for position, text, token in end_labels:
        target = position
        if placed and target - placed[-1] < 12:
            target = placed[-1] + 12
        placed.append(target)
        parts.append(
            f'<line class="key" style="stroke:var({token})" x1="{left + plot_w + 8}" '
            f'x2="{left + plot_w + 16}" y1="{target:.1f}" y2="{target:.1f}"/>'
            f'<text class="value" x="{left + plot_w + 20}" y="{target + 3:.1f}">{text}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def rounded_bar(x0: float, x1: float, y0: float, thickness: float) -> str:
    """Une barre horizontale, extrémité de donnée arrondie à 4 px, carrée à la ligne de base."""
    radius = min(4.0, abs(x1 - x0) / 2, thickness / 2)
    top, bottom = y0, y0 + thickness
    if x1 >= x0:
        return (
            f"M{x0:.1f},{top:.1f} H{x1 - radius:.1f} Q{x1:.1f},{top:.1f} {x1:.1f},"
            f"{top + radius:.1f} V{bottom - radius:.1f} Q{x1:.1f},{bottom:.1f} "
            f"{x1 - radius:.1f},{bottom:.1f} H{x0:.1f} Z"
        )
    return (
        f"M{x0:.1f},{top:.1f} H{x1 + radius:.1f} Q{x1:.1f},{top:.1f} {x1:.1f},"
        f"{top + radius:.1f} V{bottom - radius:.1f} Q{x1:.1f},{bottom:.1f} "
        f"{x1 + radius:.1f},{bottom:.1f} H{x0:.1f} Z"
    )


@dataclass(frozen=True)
class Bar:
    label: str
    effectif: str
    value: float | None
    token: str
    note: str = ""


def bar_chart(bars: Sequence[Bar], width: int = 330) -> str:
    """Barres horizontales à partir de zéro ; une barre sans support devient une ligne de texte."""
    row_h, thickness, label_w, value_w = 30, 14, 128, 52
    height = row_h * len(bars) + 4
    plot_w = width - label_w - value_w
    values = [bar.value for bar in bars if bar.value is not None]
    low = min([0.0, *values])
    high = max([0.0, *values]) or 1.0

    def x(value: float) -> float:
        return label_w + (value - low) / (high - low) * plot_w

    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Gain médian au-delà du marché par prix d\'entrée">'
    ]
    parts.append(f'<line class="axis" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="0" y2="{height - 4}"/>')
    for index, bar in enumerate(bars):
        top = index * row_h + 4
        parts.append(
            f'<text class="label" x="0" y="{top + 10}">{esc(bar.label)}</text>'
            f'<text class="muted" x="0" y="{top + 22}">{esc(bar.effectif)}</text>'
        )
        if bar.value is None:
            parts.append(f'<text class="muted" x="{x(0) + 6:.1f}" y="{top + 14}">—</text>')
            continue
        parts.append(
            f'<path style="fill:var({bar.token})" '
            f'd="{rounded_bar(x(0), x(bar.value), top + 3, thickness)}">'
            f"<title>{esc(bar.label)} : {signed_percent(bar.value)} ({esc(bar.effectif)})"
            "</title></path>"
        )
        anchor_x = max(x(bar.value), x(0)) + 6
        parts.append(
            f'<text class="value" x="{anchor_x:.1f}" y="{top + 14}">'
            f"{signed_percent(bar.value)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


@dataclass(frozen=True)
class Range:
    label: str
    effectif: int
    low: float | None
    mid: float | None
    high: float | None


def range_chart(ranges: Sequence[Range], width: int = 330) -> str:
    """Écart au prix de la commune par étiquette : la médiane, et l'intervalle interquartile."""
    row_h, label_w, value_w, top_pad = 19, 70, 46, 16
    height = top_pad + row_h * len(ranges) + 16
    plot_w = width - label_w - value_w
    values = [value for item in ranges for value in (item.low, item.high) if value is not None]
    # Domaine asymétrique, zéro toujours inclus : une étiquette très dispersée d'un côté
    # n'écrase pas les autres sous un axe symétrique trop large.
    grid = ticks(min([-10.0, *values]), max([10.0, *values]))
    low, high = grid[0], grid[-1]

    def x(value: float) -> float:
        return label_w + (value - low) / (high - low) * plot_w

    bottom = top_pad + row_h * len(ranges)
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Écart de prix au mètre carré par étiquette énergétique">'
    ]
    for tick in grid:
        css = "axis" if tick == 0 else "grid"
        parts.append(
            f'<line class="{css}" x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{top_pad - 4}" '
            f'y2="{bottom}"/>'
            f'<text class="tick" x="{x(tick):.1f}" y="{bottom + 12}" text-anchor="middle">'
            f"{signed_percent(tick)}</text>"
        )
    parts.append(
        f'<text class="muted" x="{x(0):.1f}" y="9" text-anchor="middle">prix de la commune</text>'
    )
    for index, item in enumerate(ranges):
        centre = top_pad + index * row_h + row_h / 2
        parts.append(
            f'<text class="label" x="0" y="{centre + 3:.1f}">{esc(item.label)}</text>'
            f'<text class="muted" x="16" y="{centre + 3:.1f}">n{NBSP}{grouped(item.effectif)}'
            "</text>"
        )
        if item.mid is None or item.low is None or item.high is None:
            parts.append(
                f'<text class="muted" x="{width - value_w + 6}" y="{centre + 3:.1f}">—</text>'
            )
            continue
        parts.append(
            f'<line class="range" x1="{x(item.low):.1f}" x2="{x(item.high):.1f}" '
            f'y1="{centre:.1f}" y2="{centre:.1f}"/>'
            f'<circle class="dot" style="fill:var(--series-1)" cx="{x(item.mid):.1f}" '
            f'cy="{centre:.1f}" r="4"><title>{esc(item.label)} : médiane '
            f"{signed_percent(item.mid)}, de {signed_percent(item.low)} à "
            f"{signed_percent(item.high)} ({grouped(item.effectif)} ventes)</title></circle>"
            f'<text class="value" x="{width - value_w + 6}" y="{centre + 3:.1f}">'
            f"{signed_percent(item.mid)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def curve_chart(
    points: Sequence[tuple[int, float]], month_days: str, width: int = 330, height: int = 140
) -> str:
    """La part cumulée des parcelles vendues, mois après mois depuis le dépôt."""
    left, right, top, bottom = 34, 78, 10, 22
    plot_w, plot_h = width - left - right, height - top - bottom
    series = [(0, 0.0), *points]
    grid = ticks(0, max(value for _, value in series))
    high = grid[-1]
    last_month = series[-1][0]

    def x(month: int) -> float:
        return left + month / last_month * plot_w

    def y(value: float) -> float:
        return top + plot_h - value / high * plot_h

    line = " ".join(
        f"{'M' if index == 0 else 'L'}{x(month):.1f},{y(value):.1f}"
        for index, (month, value) in enumerate(series)
    )
    area = f"{line} L{x(last_month):.1f},{y(0):.1f} L{x(0):.1f},{y(0):.1f} Z"
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Part cumulée des parcelles vendues après le dépôt du DPE">'
    ]
    for tick in grid:
        parts.append(
            f'<line class="grid" x1="{left}" x2="{left + plot_w}" y1="{y(tick):.1f}" '
            f'y2="{y(tick):.1f}"/>'
            f'<text class="tick" x="{left - 6}" y="{y(tick) + 3:.1f}" text-anchor="end">'
            f"{decimal(tick, 0)}{NBSP}%</text>"
        )
    for month, _ in series:
        if month in (0, 3, 6, 9, 12):
            parts.append(
                f'<text class="tick" x="{x(month):.1f}" y="{height - 6}" text-anchor="middle">'
                f"{month}</text>"
            )
    parts.append(
        f'<text class="tick" x="{left + plot_w}" y="{height - 6}" text-anchor="end" dx="40">'
        "mois</text>"
    )
    parts.append(f'<path class="wash" d="{area}"/><path class="line" d="{line}"/>')
    for month, value in points:
        parts.append(
            f'<circle class="hit" cx="{x(month):.1f}" cy="{y(value):.1f}" r="7">'
            f"<title>{month} mois ({month} {CROSS} {month_days} jours) : "
            f"{percent(value)} vendues</title></circle>"
        )
    month, value = series[-1]
    parts.append(
        f'<circle class="dot" style="fill:var(--series-1)" cx="{x(month):.1f}" '
        f'cy="{y(value):.1f}" r="4"/>'
        f'<text class="value" x="{x(month) + 8:.1f}" y="{y(value) + 3:.1f}">'
        f"{percent(value)}</text>"
    )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------------------------
# Les quatre rubriques du recto
# --------------------------------------------------------------------------------------------


def latest_supported(rows: Sequence[dict[str, str]], property_type: str) -> dict[str, str] | None:
    supported = [
        row
        for row in rows
        if row["property_type"] == property_type and has_support(row, "median_eur_m2")
    ]
    return max(supported, key=lambda row: int(row["year"])) if supported else None


def market_card(barometer: Barometer, territory: Territory) -> str:
    rows = barometer.rows("volumes", territory.scope_type, territory.scope_code)
    minimum = barometer.metadata["support_sales_per_cell"]
    years = sorted({int(row["year"]) for row in rows})
    series = []
    for property_type, name, token in (
        ("Maison", "Maisons", "--series-1"),
        ("Appartement", "Appartements", "--series-2"),
    ):
        by_year = {int(row["year"]): row for row in rows if row["property_type"] == property_type}
        points = tuple(
            (year, number(by_year[year]["median_eur_m2"]) if year in by_year else None)
            for year in years
        )
        if any(value is not None for _, value in points):
            series.append(Series(name, token, points))
    house = latest_supported(rows, "Maison")
    if house is None:
        houses = sum(count(row["sales"]) for row in rows if row["property_type"] == "Maison")
        figure = insufficient(houses, f"{minimum} ventes par an", "ventes de maison")
    else:
        year = int(house["year"])
        figure = (
            f'<p class="figure">{euros_m2(float(house["median_eur_m2"]))}</p>'
            f'<p class="caption">prix médian d\'une maison en {year}, sur '
            f"{grouped(count(house['sales']))} ventes — la moitié entre "
            f"{euros_m2(float(house['q1_eur_m2']))} et {euros_m2(float(house['q3_eur_m2']))}</p>"
        )
    legend = "".join(
        f'<span class="legend-item"><i style="background:var({item.token})"></i>{item.name}</span>'
        for item in series
    )
    missing = [
        name
        for property_type, name in (("Maison", "maisons"), ("Appartement", "appartements"))
        if not any(item.name.lower() == name for item in series)
    ]
    note = (
        f'<p class="muted-note">{", ".join(missing).capitalize()} : aucune année n\'atteint '
        f"{minimum} ventes.</p>"
        if missing
        else ""
    )
    return f"""<section class="rubric">
  <h2><span class="num">1</span>Le marché</h2>
  {figure}
  <h3>Prix médian au m², ventes de {years[0] if years else "—"} à {years[-1] if years else "—"}</h3>
  <p class="legend">{legend}</p>
  {line_chart(series)}
  {note}
  <p class="source">Ventes simples à prix alloué. Une année sous {minimum} ventes est un trou dans
  la courbe, jamais un zéro.</p>
</section>"""


ENTRY_TOKENS = ("--ordinal-4", "--ordinal-3", "--ordinal-2", "--ordinal-1")


def effectifs_line(pairs: Sequence[tuple[str, int]], unit: str) -> str:
    """Les effectifs d'une mesure non publiée : ce que le lecteur peut encore savoir."""
    items = " · ".join(f"{esc(label)} : {grouped(value)}" for label, value in pairs)
    return f'<p class="effectifs">{unit} — {items}</p>'


ENTRY_BAND = re.compile(
    r"< (?P<high>.+?) de la médiane|(?P<low>.+?) à (?P<top>.+)|(?P<floor>.+?) et plus"
)


def entry_phrase(band: str) -> str:
    """La tranche de prix d'entrée, dite en français : « entre 60 % et 80 % »."""
    matched = ENTRY_BAND.fullmatch(band)
    if matched is None:
        return band
    if matched["high"]:
        return f"à moins de {matched['high']}"
    if matched["low"]:
        return f"entre {matched['low']} et {matched['top']}"
    return f"à {matched['floor']} ou plus"


def margin_card(barometer: Barometer, territory: Territory) -> str:
    rows = barometer.rows("margin", territory.scope_type, territory.scope_code)
    minimum = barometer.metadata["support_repeat_pairs"]
    days = barometer.metadata["repeat_max_days"]
    bars = []
    for index, row in enumerate(rows):
        value = number(row["median_excess"])
        bars.append(
            Bar(
                label=row["entry_band"].replace(" de la médiane", ""),
                effectif=f"{grouped(count(row['pairs']))} reventes",
                value=None if value is None else 100 * (value - 1),
                token=ENTRY_TOKENS[min(index, len(ENTRY_TOKENS) - 1)],
            )
        )
    supported = [row for row in rows if has_support(row, "median_excess")]
    if supported:
        first = supported[0]
        share = number(first["share_above_threshold_pct"])
        band = entry_phrase(first["entry_band"])
        figure = (
            f'<p class="figure">{signed_percent(100 * (float(first["median_excess"]) - 1))}</p>'
            f'<p class="caption">gain médian au-delà du marché, maison achetée {esc(band)} du '
            "prix médian communal et revendue entre six mois et trois ans plus tard — "
            f"{grouped(count(first['pairs']))} reventes"
            + (f", dont {percent(share, 0)} au-delà de +20{NBSP}%" if share is not None else "")
            + "</p>"
        )
        partial = len(supported) < len(rows)
        chart = (
            "<h3>Gain au-delà du marché selon le prix d'achat, rapporté au prix médian de la "
            "commune"
            f"</h3>{bar_chart(bars)}"
            + (
                f'<p class="muted-note">— : moins de {minimum} reventes, valeur non publiée.</p>'
                if partial
                else ""
            )
        )
    else:
        total = sum(count(row["pairs"]) for row in rows)
        figure = insufficient(total, f"{minimum} par tranche", "reventes au total")
        chart = effectifs_line(
            [(bar.label, count(row["pairs"])) for bar, row in zip(bars, rows, strict=True)],
            "Reventes par prix d'achat",
        )
    return f"""<section class="rubric">
  <h2><span class="num">2</span>La marge</h2>
  {figure}
  {chart}
  <p class="source">Même maison, surface inchangée, revendue entre six mois et
  {grouped(float(days))} jours après l'achat. Gain : rapport des deux prix divisé par l'évolution
  du prix médian communal ; frais et travaux inconnus, seules les reventes sont vues.</p>
</section>"""


def energy_card(barometer: Barometer, territory: Territory) -> str:
    rows = barometer.rows("labels", territory.scope_type, territory.scope_code)
    minimum = barometer.metadata["support_label_sales"]
    ranges = []
    for row in rows:
        low, mid, high = (number(row[key]) for key in ("q1_ratio", "median_ratio", "q3_ratio"))
        ranges.append(
            Range(
                label=row["energy_label"],
                effectif=count(row["sales"]),
                low=None if low is None else 100 * (low - 1),
                mid=None if mid is None else 100 * (mid - 1),
                high=None if high is None else 100 * (high - 1),
            )
        )
    by_label = {item.label: item for item in ranges}
    house_f, house_d = by_label.get("F"), by_label.get("D")
    if house_f is not None and house_f.mid is not None:
        context = (
            f" ; classée D : {signed_percent(house_d.mid)}"
            if house_d is not None and house_d.mid is not None
            else ""
        )
        reading = (
            f'<p class="figure">{signed_percent(house_f.mid)}</p>'
            '<p class="caption">écart médian entre le prix au m² d\'une maison classée F et le '
            f"prix médian de sa commune la même année — {grouped(house_f.effectif)} ventes"
            f"{context}</p>"
        )
    else:
        reading = (
            '<p class="absent"><b>Étiquette F non publiée</b> : '
            f"{grouped(house_f.effectif if house_f else 0)} ventes, {minimum} requises. "
            "La valeur n'est pas remplacée par celle du département.</p>"
        )
    supported = [item for item in ranges if item.mid is not None]
    if supported:
        chart = (
            "<h3>Prix au m² selon l'étiquette DPE, écart au prix de la commune la même année</h3>"
            f"{range_chart(ranges)}"
            + (
                f'<p class="muted-note">— : moins de {minimum} ventes, valeur non publiée.</p>'
                if len(supported) < len(ranges)
                else ""
            )
        )
    else:
        chart = effectifs_line(
            [(item.label, item.effectif) for item in ranges], "Ventes par étiquette"
        )
    since = barometer.metadata["label_from_year"]
    return f"""<section class="rubric">
  <h2><span class="num">3</span>L'énergie</h2>
  {reading}
  {chart}
  <p class="source">Maisons vendues depuis {since} avec un DPE déposé dans les deux ans avant
  l'acte. Point : médiane ; trait : la moitié centrale des ventes. Aucun DPE postérieur à la
  réforme du 1<sup>er</sup> janvier 2026 n'entre dans la mesure.</p>
</section>"""


def tempo_card(barometer: Barometer, territory: Territory) -> str:
    year = barometer.metadata["cohort_year"]
    minimum = barometer.metadata["support_dpe_cohort_parcels"]
    rate = next(
        (
            row
            for row in barometer.rows("rates", territory.scope_type, territory.scope_code)
            if row["cohort_year"] == year
        ),
        None,
    )
    delay = next(iter(barometer.rows("delay", territory.scope_type, territory.scope_code)), None)
    curve_rows = [
        row
        for row in barometer.rows("curve", territory.scope_type, territory.scope_code)
        if row["cohort_year"] == year
    ]
    if rate is not None and has_support(rate, "rate_pct"):
        figure = (
            f'<p class="figure">{percent(float(rate["rate_pct"]))}</p>'
            f'<p class="caption">des parcelles dont le premier DPE a été déposé en {year} ont '
            f"changé de main dans les douze mois — {grouped(count(rate['sold_within_12_months']))}"
            f" sur {grouped(count(rate['cohort_parcels']))}</p>"
        )
    else:
        effectif = count(rate["cohort_parcels"]) if rate else 0
        figure = insufficient(effectif, f"{minimum} parcelles", f"parcelles en {year}")
    delay_line = ""
    if delay is not None and has_support(delay, "median_days"):
        delay_line = (
            f'<p class="secondary"><b>{grouped(float(delay["median_days"]))} jours</b> entre le '
            f"dépôt et l'acte, en médiane — la moitié entre "
            f"{grouped(float(delay['q1_days']))} et {grouped(float(delay['q3_days']))} jours, "
            f"sur {grouped(count(delay['sold_within_window']))} parcelles vendues</p>"
        )
    chart = ""
    if curve_rows and all(has_support(row, "cumulative_pct") for row in curve_rows):
        points = [(int(row["month"]), float(row["cumulative_pct"])) for row in curve_rows]
        chart = (
            f"<h3>Part des parcelles vendues, mois après mois depuis le dépôt</h3>"
            f"{curve_chart(points, barometer.metadata['curve_month_days'])}"
        )
    curve_note = (
        f" Mois de {barometer.metadata['curve_month_days']} jours : la courbe finit un peu sous "
        "le taux à douze mois."
        if chart
        else ""
    )
    if not chart and rate is not None:
        chart = effectifs_line(
            [
                (row["cohort_year"], count(row["cohort_parcels"]))
                for row in barometer.rows("rates", territory.scope_type, territory.scope_code)
            ],
            "Parcelles par cohorte",
        )
    return f"""<section class="rubric">
  <h2><span class="num">4</span>Le tempo</h2>
  {figure}
  {delay_line}
  {chart}
  <p class="source">Un DPE est obligatoire pour vendre un logement, mais aussi pour le louer : la
  mesure encaisse les deux. C'est une fréquence observée sur une cohorte, pas la chance d'un bien
  donné.{curve_note}</p>
</section>"""


# --------------------------------------------------------------------------------------------
# Le verso : les chiffres, leurs effectifs, leurs filtres
# --------------------------------------------------------------------------------------------


def cell(value: str | None, render: Callable[[float], str]) -> str:
    parsed = number(value)
    return "—" if parsed is None else render(parsed)


def multiplier(value: float) -> str:
    return f"{CROSS}{decimal(value, 2)}"


SUPPORT_REASON = re.compile(r"support insuffisant : \d+ < (\d+)")
THOUSANDS = re.compile(r"(\d)(\d{3})\b")


def group_digits(text: str) -> str:
    """« 1095 jours » devient « 1 095 jours » dans un libellé venu d'un CSV."""
    return THOUSANDS.sub(rf"\1{NNBSP}\2", text)


def reason_cell(row: dict[str, str]) -> str:
    """Le motif, raccourci : l'effectif est déjà dans sa colonne."""
    reason = (row.get("reason") or "").strip()
    if not reason:
        return "<td></td>"
    matched = SUPPORT_REASON.fullmatch(reason)
    text = f"sous le support de {matched.group(1)}" if matched else reason
    return f'<td class="reason">{esc(text)}</td>'


def html_table(header: Sequence[str], body: Sequence[str], numeric_from: int = 1) -> str:
    head = "".join(
        f'<th class="{"n" if index >= numeric_from else ""}">{esc(title)}</th>'
        for index, title in enumerate(header)
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def annex(barometer: Barometer, territory: Territory) -> str:
    code, scope = territory.scope_code, territory.scope_type
    meta = barometer.metadata
    volumes = barometer.rows("volumes", scope, code)
    volume_lines = []
    for year in sorted({row["year"] for row in volumes}):
        cells = [f"<td>{year}</td>"]
        for property_type in ("Maison", "Appartement"):
            row = next(
                (r for r in volumes if r["year"] == year and r["property_type"] == property_type),
                None,
            )
            if row is None:
                cells += ['<td class="n">—</td>', '<td class="n">—</td>']
                continue
            cells += [
                f'<td class="n">{grouped(count(row["sales"]))}</td>',
                f'<td class="n">{cell(row["median_eur_m2"], grouped)}</td>',
            ]
        volume_lines.append(f"<tr>{''.join(cells)}</tr>")
    market = html_table(["Année", "Maisons", "€/m²", "Appart.", "€/m²"], volume_lines) + (
        '<p class="muted-note">— : aucune vente exploitable, ou moins de '
        f"{meta['support_sales_per_cell']} pour le prix.</p>"
    )

    margin = html_table(
        ["Prix d'entrée", "Reventes", "Médiane", "Q3", "> +20 %", "Motif"],
        [
            f"<tr><td>{esc(row['entry_band'])}</td>"
            f'<td class="n">{grouped(count(row["pairs"]))}</td>'
            f'<td class="n">{cell(row["median_excess"], multiplier)}</td>'
            f'<td class="n">{cell(row["q3_excess"], multiplier)}</td>'
            f'<td class="n">{cell(row["share_above_threshold_pct"], percent)}</td>'
            f"{reason_cell(row)}</tr>"
            for row in barometer.rows("margin", scope, code)
        ],
    )
    labels = html_table(
        ["Étiquette", "Ventes", "Q1", "Médiane", "Q3", "Motif"],
        [
            f"<tr><td>{esc(row['energy_label'])}</td>"
            f'<td class="n">{grouped(count(row["sales"]))}</td>'
            + "".join(
                f'<td class="n">{cell(row[key], lambda v: signed_percent(100 * (v - 1)))}</td>'
                for key in ("q1_ratio", "median_ratio", "q3_ratio")
            )
            + f"{reason_cell(row)}</tr>"
            for row in barometer.rows("labels", scope, code)
        ],
    )
    rates = html_table(
        ["Cohorte", "Parcelles", "Vendues", "Taux", "Motif"],
        [
            f"<tr><td>{esc(row['cohort_year'])}</td>"
            f'<td class="n">{grouped(count(row["cohort_parcels"]))}</td>'
            f'<td class="n">{grouped(count(row["sold_within_12_months"]))}</td>'
            f'<td class="n">{cell(row["rate_pct"], percent)}</td>'
            f"{reason_cell(row)}</tr>"
            for row in barometer.rows("rates", scope, code)
        ],
    )
    curve_rows = [
        row
        for row in barometer.rows("curve", scope, code)
        if row["cohort_year"] == meta["cohort_year"]
    ]
    if curve_rows and all(has_support(row, "cumulative_pct") for row in curve_rows):
        curve = html_table(
            ["Mois", *[row["month"] for row in curve_rows]],
            [
                "<tr><td>Vendues</td>"
                + "".join(
                    f'<td class="n">{cell(row["cumulative_pct"], percent)}</td>'
                    for row in curve_rows
                )
                + "</tr>"
            ],
        )
    else:
        effectif = count(curve_rows[0]["cohort_parcels"]) if curve_rows else 0
        curve = (
            f'<p class="effectifs">Courbe de conversion et délai non publiés : '
            f"{grouped(effectif)} parcelles en {meta['cohort_year']}, "
            f"{meta['support_dpe_cohort_parcels']} requises.</p>"
        )
    delay_rows = [
        row for row in barometer.rows("delay", scope, code) if has_support(row, "median_days")
    ]
    delay = (
        ""
        if not delay_rows
        else html_table(
            ["Délai dépôt → acte", "Parcelles", "Vendues", "Q1", "Médiane", "Q3"],
            [
                f"<tr><td>cohorte {meta['cohort_year']}</td>"
                f'<td class="n">{grouped(count(row["cohort_parcels"]))}</td>'
                f'<td class="n">{grouped(count(row["sold_within_window"]))}</td>'
                + "".join(
                    f'<td class="n">{cell(row[key], lambda v: grouped(v) + NBSP + "j")}</td>'
                    for key in ("q1_days", "median_days", "q3_days")
                )
                + "</tr>"
                for row in delay_rows
            ],
        )
    )
    extension = ""
    if scope == DEPARTMENT_SCOPE:
        extension = "<h3>Effet d'un agrandissement</h3>" + html_table(
            ["Fenêtre", "Reventes", "Prix", "Prix au m²"],
            [
                f"<tr><td>{esc(group_digits(row['window']))}</td>"
                f'<td class="n">{grouped(count(row["pairs"]))}</td>'
                f'<td class="n">{cell(row["median_price_ratio"], multiplier)}</td>'
                f'<td class="n">{cell(row["median_price_per_m2_ratio"], multiplier)}</td></tr>'
                for row in barometer.rows("extension", scope, code)
            ],
        )
    communes = ""
    if territory.communes:
        names = ", ".join(esc(name) for _, name in territory.communes)
        communes = (
            f'<p class="communes"><b>{len(territory.communes)} communes</b> — {names}. '
            "Rattachement lu dans la BDNB (CSTB), attribut <code>code_epci_insee</code>.</p>"
        )
    return f"""<section class="annex">
  <h2>Les chiffres, leurs effectifs et leurs filtres</h2>
  {communes}
  <div class="columns">
    <div>
      <h3>1 — Ventes et prix médian au m²</h3>{market}
      <h3>2 — Gain au-delà du marché, par prix d'entrée</h3>{margin}
    </div>
    <div>
      <h3>3 — Écart de prix par étiquette</h3>{labels}
      <h3>4 — Taux de mutation à douze mois</h3>{rates}
      {curve}
      {delay}
      {extension}
    </div>
  </div>
  <h3>Comment ces chiffres sont construits</h3>
  <ul class="filters">
    <li><b>Ventes</b> : mutations de nature « Vente » uniquement — VEFA, terrain à bâtir,
    échange, adjudication et expropriation écartés ; un seul bien par mutation, pour que le prix
    lui soit attribuable ; surface et prix renseignés.</li>
    <li><b>Médiane de référence</b> : prix médian au m² des maisons de la commune l'année de la
    vente, retenu à partir de {meta["support_sales_per_cell"]} ventes. C'est le seul
    contrôle : ni âge, ni surface, ni modèle.</li>
    <li><b>Reventes</b> : deux ventes successives de la même maison, à plus de six mois
    d'écart ; ventes du même jour départagées par prix puis surface croissants.</li>
    <li><b>Cohorte DPE</b> : premier DPE de chaque parcelle, rattaché par une relation
    bâtiment ↔ parcelle certaine ; DPE d'appartement issus d'un DPE d'immeuble exclus. Une
    parcelle « a muté » si une vente — simple, en l'état futur d'achèvement ou de terrain à
    bâtir, tout type de lot — suit le dépôt ; échange, adjudication et expropriation n'en sont
    pas.</li>
    <li><b>Supports</b> : {meta["support_sales_per_cell"]} ventes par cellule,
    {meta["support_repeat_pairs"]} reventes par tranche, {meta["support_label_sales"]} ventes par
    étiquette, {meta["support_dpe_cohort_parcels"]} parcelles par cohorte. Ce sont des
    paramètres déclarés, pas des seuils de sens. En dessous, la valeur est absente et le motif
    écrit.</li>
  </ul>
</section>"""


# --------------------------------------------------------------------------------------------
# La feuille
# --------------------------------------------------------------------------------------------

STYLE = """
@page{size:A4;margin:11mm 12mm}
:root{color-scheme:light;
  --page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#6f6e69;
  --grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.12);--warn-bg:#fdf1dc;--warn:#7a4b00;
  --series-1:#2a78d6;--series-2:#eb6834;
  --ordinal-1:#86b6ef;--ordinal-2:#5598e7;--ordinal-3:#2a78d6;--ordinal-4:#1c5cab;
  --good:#006300}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;
  --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink-2:#c3c2b7;--muted:#9a9990;
  --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.12);--warn-bg:#3a2a0c;--warn:#fab219;
  --series-1:#3987e5;--series-2:#d95926;
  --ordinal-1:#184f95;--ordinal-2:#256abf;--ordinal-3:#3987e5;--ordinal-4:#6da7ec;
  --good:#0ca30c}}
:root[data-theme="dark"]{color-scheme:dark;
  --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink-2:#c3c2b7;--muted:#9a9990;
  --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.12);--warn-bg:#3a2a0c;--warn:#fab219;
  --series-1:#3987e5;--series-2:#d95926;
  --ordinal-1:#184f95;--ordinal-2:#256abf;--ordinal-3:#3987e5;--ordinal-4:#6da7ec;
  --good:#0ca30c}
*{box-sizing:border-box}
html{background:var(--page)}
body{margin:0;background:var(--page);color:var(--ink);
  font:9pt/1.38 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.sheet{width:210mm;min-height:297mm;margin:12px auto;padding:11mm 12mm;background:var(--surface);
  box-shadow:0 0 0 1px var(--border);display:flex;flex-direction:column}
header.masthead{border-bottom:1px solid var(--axis);padding-bottom:2.5mm;margin-bottom:3mm}
.eyebrow{margin:0;color:var(--ink-2);font-size:8pt;letter-spacing:.06em;text-transform:uppercase}
h1{margin:1mm 0 1mm;font-size:20pt;line-height:1.1;font-weight:650}
.scope{margin:0;color:var(--ink-2);font-size:8.5pt}
.meta{margin:1.5mm 0 0;color:var(--muted);font-size:7.8pt}
.recount{display:inline-block;margin-top:1.5mm;padding:1px 6px;border-radius:3px;font-size:7.8pt;
  border:1px solid var(--border)}
.recount.missing{background:var(--warn-bg);color:var(--warn);font-weight:600}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:3mm 7mm;flex:1}
.rubric{display:flex;flex-direction:column;min-width:0}
.rubric h2{margin:0 0 1.5mm;font-size:11pt;font-weight:650;display:flex;align-items:center;gap:2mm}
.num{display:inline-grid;place-items:center;width:5mm;height:5mm;border-radius:50%;
  background:var(--ink);color:var(--surface);font-size:7.5pt}
.figure{margin:0;font-size:21pt;font-weight:600;line-height:1.1}
.muted-figure{color:var(--muted)}
.delta{margin-left:2.5mm;font-size:8.5pt;font-weight:500;color:var(--ink-2)}
.caption{margin:.8mm 0 2.5mm;color:var(--ink-2);font-size:8pt}
.secondary{margin:0 0 2mm;font-size:8.3pt;color:var(--ink-2)}
.secondary b{color:var(--ink)}
.rubric h3{margin:1mm 0 1mm;font-size:8.2pt;font-weight:600;color:var(--ink)}
.legend{margin:0 0 1mm;font-size:7.8pt;color:var(--ink-2)}
.legend-item{margin-right:3.5mm;white-space:nowrap}
.legend-item i{display:inline-block;width:9px;height:2px;margin-right:3px;vertical-align:middle}
.source{margin:auto 0 0;padding-top:1.5mm;color:var(--muted);font-size:7.2pt}
.muted-note{margin:0;color:var(--muted);font-size:7.5pt}
.effectifs{margin:0 0 2mm;color:var(--ink-2);font-size:8pt}
.absent{margin:0 0 2mm;padding:1.5mm 2mm;border-left:2px solid var(--axis);color:var(--ink-2);
  font-size:8pt}
.absent b{color:var(--ink)}
svg.chart{display:block;width:100%;height:auto;overflow:visible}
svg .grid{stroke:var(--grid);stroke-width:1}
svg .axis{stroke:var(--axis);stroke-width:1}
svg .line{fill:none;stroke:var(--series-1);stroke-width:2;stroke-linejoin:round;
  stroke-linecap:round}
svg .wash{fill:var(--series-1);opacity:.1}
svg .dot{stroke:var(--surface);stroke-width:2}
svg .hit{fill:transparent}
svg .range{stroke:var(--series-1);stroke-width:2;stroke-linecap:round;opacity:.35}
svg .key{stroke-width:2}
svg text{font:inherit;font-size:7.6px}
svg .tick{fill:var(--muted);font-variant-numeric:tabular-nums}
svg .label{fill:var(--ink);font-weight:600;font-size:8px}
svg .muted{fill:var(--muted);font-size:7.2px}
svg .value{fill:var(--ink);font-weight:600;font-size:8px}
footer.colophon{margin-top:3mm;padding-top:2mm;border-top:1px solid var(--axis);
  color:var(--muted);font-size:7pt;line-height:1.35}
footer.colophon p{margin:0 0 .8mm}
footer.colophon strong{color:var(--ink-2)}
.annex h2{margin:0 0 2mm;font-size:13pt;font-weight:650}
.annex h3{margin:3mm 0 1mm;font-size:8.2pt;font-weight:650}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:0 7mm}
.communes{margin:0 0 1mm;color:var(--ink-2);font-size:7.6pt}
table{border-collapse:collapse;width:100%;font-size:7.4pt;margin-bottom:1mm}
th{text-align:left;font-weight:600;color:var(--ink-2);border-bottom:1px solid var(--axis);
  padding:.6mm 1mm}
td{border-bottom:1px solid var(--grid);padding:.45mm 1mm;vertical-align:top}
.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.reason{color:var(--muted);font-size:6.8pt}
.filters{margin:0;padding-left:4mm;color:var(--ink-2);font-size:7.4pt}
.filters li{margin-bottom:.8mm}
@media print{html,body{background:#fff}
  :root,:root[data-theme="dark"]{color-scheme:light;
    --page:#fff;--surface:#fff;--ink:#0b0b0b;--ink-2:#52514e;--muted:#6f6e69;--grid:#e1e0d9;
    --axis:#c3c2b7;--warn-bg:#fdf1dc;--warn:#7a4b00;--series-1:#2a78d6;--series-2:#eb6834;
    --ordinal-1:#86b6ef;--ordinal-2:#5598e7;--ordinal-3:#2a78d6;--ordinal-4:#1c5cab}
  .sheet{margin:0;padding:0;width:auto;min-height:0;box-shadow:none;
    break-after:page;page-break-after:always}
  .sheet:last-child{break-after:auto;page-break-after:auto}
  svg .hit{display:none}}
@media screen and (max-width:820px){.sheet{width:auto;min-height:0;margin:0;padding:16px}
  .grid,.columns{grid-template-columns:1fr}}
"""


def colophon(barometer: Barometer) -> str:
    meta = barometer.metadata
    return f"""<footer class="colophon">
  <p><strong>Sources</strong> — Demandes de valeurs foncières (DGFiP, publiées par Etalab),
  mutations {meta["sales_first_year"]} à {meta["sales_last_year"]}, releases
  {esc(meta["release_ds06"])} ; diagnostics de performance énergétique (ADEME), extrait du
  {date_fr(meta["first_deposit"])} au {date_fr(meta["last_deposit"])} ; plan cadastral (DGFiP,
  Etalab) {esc(meta["release_ds01"])} ; Référentiel national des bâtiments
  {esc(meta["release_ds02"])} ; BDNB (CSTB) {esc(meta["release_ds03"])} pour le découpage
  intercommunal. Données publiées sous
  Licence Ouverte 2.0 ; ce document en reprend l'attribution.</p>
  <p><strong>Aucune parcelle ni adresse n'est identifiable dans ce document.</strong> Toutes les
  valeurs sont des agrégats ; chaque taux est donné avec son effectif. Ce sont des fréquences
  observées sur le passé, pas la probabilité qu'un bien donné se vende.</p>
  <p>Mesures générées le {date_fr(meta["generated_on"])}, dernière mutation connue au
  {date_fr(meta["last_mutation"])}. Empreinte <code>{esc(meta["fingerprint"][:16])}</code>.
  Détail et filtres : <code>docs/data/barometre-marche-{esc(barometer.department)}.md</code>.</p>
</footer>"""


def masthead(barometer: Barometer, territory: Territory, face: str) -> str:
    meta = barometer.metadata
    if barometer.recounted:
        recount = (
            f'<span class="recount">Chiffres recomptés le {date_fr(meta["recounted_on"])}</span>'
        )
    else:
        recount = (
            '<span class="recount missing">Non recompté — document de travail, ne pas diffuser'
            "</span>"
        )
    if territory.communes:
        names = [name for _, name in territory.communes]
        shown = ", ".join(esc(name) for name in names[:4])
        more = f" et {len(names) - 4} autres" if len(names) > 4 else ""
        scope = f'<p class="scope">{len(names)} communes : {shown}{more}</p>'
    else:
        scope = '<p class="scope">Ensemble des communes du département</p>'
    return f"""<header class="masthead">
  <p class="eyebrow">Baromètre du marché immobilier · {face}</p>
  <h1>{esc(territory.title)}</h1>
  {scope}
  <p class="meta">Ventes {meta["sales_first_year"]}{EN_DASH}{meta["sales_last_year"]} · DPE
  {month_fr(meta["first_deposit"])} {EN_DASH} {month_fr(meta["last_deposit"])} · cohorte
  {meta["cohort_year"]}, dernière dont les douze mois sont couverts</p>
  {recount}
</header>"""


def page(barometer: Barometer, territory: Territory) -> str:
    title = f"Baromètre du marché — {territory.title}"
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{STYLE}</style></head><body>
<article class="sheet">
{masthead(barometer, territory, "le marché, la marge, l'énergie, le tempo")}
<div class="grid">
{market_card(barometer, territory)}
{margin_card(barometer, territory)}
{energy_card(barometer, territory)}
{tempo_card(barometer, territory)}
</div>
{colophon(barometer)}
</article>
<article class="sheet">
{masthead(barometer, territory, "verso")}
{annex(barometer, territory)}
{colophon(barometer)}
</article>
</body></html>
"""


def check_publishable(document: str) -> None:
    """BR-005 : aucun identifiant cadastral ne sort. Échoue plutôt que d'écrire."""
    if CADASTRAL_ID.search(document):
        raise ValueError("un identifiant cadastral apparaît dans le document")


def build(directory: Path) -> list[Path]:
    barometer = load(directory)
    written = []
    for territory in territories(barometer):
        document = page(barometer, territory)
        check_publishable(document)
        path = directory / f"document-{territory.slug}.html"
        path.write_text(document, encoding="utf-8")
        written.append(path)
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baromètre du marché — documents imprimables")
    parser.add_argument("--department", default="35")
    parser.add_argument("--root", type=Path, default=None, help="Dossier docs/data")
    arguments = parser.parse_args(argv)
    root = arguments.root or (Path(__file__).resolve().parents[2] / "docs" / "data")
    written = build(root / f"barometre-marche-{arguments.department}")
    for path in written:
        print(f"Écrit : {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
