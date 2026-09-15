"""Ce que les deux listes exploratoires partagent — E8 et E8f.

Extrait de `pipelines/scripts/exploratory_candidates.py` quand un second consommateur réel est
apparu : la liste des biens probablement en vente. Rien ici n'est anticipé pour un troisième.

Les deux listes ne posent pas la même question — « où pourrait-on construire » et « qui est sur le
marché » — mais elles partagent la mécanique : mise en aveugle sous graine, affichage d'une absence
avec son motif, prédicats d'usage du bâti, rang moyen à ex æquo partagés.
"""

import csv
import random
from pathlib import Path
from typing import Any

# Valeur publiée par BD TOPO, jamais recodée.
RESIDENTIAL_USE = "Résidentiel"
UNKNOWN_USE = "Indifférencié"

# `usage_1` se contredit avec `nature` : un parking d'entreprise peut être déclaré
# « Résidentiel » et « Industriel, agricole ou commercial » à la fois. On lit les deux.
NON_RESIDENTIAL_NATURES = frozenset(
    {
        "Industriel, agricole ou commercial",
        "Serre",
        "Silo",
        "Eglise",
        "Chapelle",
        "Tour, donjon",
        "Tribune",
        "Fort, blockhaus, casemate",
        "Moulin à vent",
        "Monument",
    }
)


def zone_type(zone: str | None) -> str | None:
    """`U|UE2c(d)` — le type CNIG précède la barre, le libellé local la suit."""
    return zone.split("|", 1)[0] if zone else None


def uses(row: dict[str, Any]) -> list[str]:
    return [use for use in (row.get("uses") or "").split(" · ") if use]


def is_residential(row: dict[str, Any]) -> bool:
    """Au moins un bâtiment que BD TOPO déclare résidentiel.

    `Indifférencié` n'est pas « non résidentiel » : c'est un inconnu, et il est compté comme tel
    par `use_populations`. Exiger le résidentiel connu écarte donc aussi l'inconnu — la liste est
    un échantillon à contester, pas un inventaire, et ce qu'elle perd est publié.
    """
    return RESIDENTIAL_USE in uses(row)


def has_non_residential_nature(row: dict[str, Any]) -> bool:
    """`nature` contredit parfois `usage_1`, et c'est elle qui a raison sur les cas vus."""
    natures = {nature for nature in (row.get("natures") or "").split(" · ") if nature}
    return bool(natures & NON_RESIDENTIAL_NATURES)


def use_populations(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Trois populations distinctes, jamais fondues en un seul taux d'absence."""
    known = [row for row in rows if uses(row)]
    return {
        "usage résidentiel connu": sum(1 for row in known if is_residential(row)),
        "usage non résidentiel connu": sum(
            1 for row in known if not is_residential(row) and uses(row) != [UNKNOWN_USE]
        ),
        "usage indifférencié": sum(1 for row in known if uses(row) == [UNKNOWN_USE]),
        "aucun bâtiment BD TOPO rattaché": len(rows) - len(known),
    }


def mean_rank(
    rows: list[dict[str, Any]], signals: tuple[tuple[str, bool], ...]
) -> dict[str, tuple[float, int]]:
    """Rang moyen sur les seuls signaux présents, et leur nombre."""
    totals: dict[str, list[float]] = {row["property_unit_id"]: [] for row in rows}
    for signal, descending in signals:
        present = [row for row in rows if row[signal] is not None]
        present.sort(key=lambda row: row[signal], reverse=descending)
        # Les ex æquo partagent leur rang. Sans ça, l'ordre d'arrivée des lignes SQL — qui
        # n'est pas ordonné — départagerait deux unités identiques, et le classement ne serait
        # pas reproductible.
        start = 0
        while start < len(present):
            end = start
            while end + 1 < len(present) and present[end + 1][signal] == present[start][signal]:
                end += 1
            shared = ((start + end) / 2 + 1) / len(present)
            for row in present[start : end + 1]:
                totals[row["property_unit_id"]].append(shared)
            start = end + 1
    return {
        unit: (sum(ranks) / len(ranks) if ranks else 1.0, len(ranks))
        for unit, ranks in totals.items()
    }


def blind(
    baseline: list[dict[str, Any]], ranked: list[dict[str, Any]], seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mélange les deux listes et retourne (liste aveugle, correspondance).

    Un candidat présent dans les deux ordres n'apparaît qu'une fois et porte les deux origines :
    le dupliquer donnerait deux verdicts sur le même bien et fausserait la comparaison.
    """
    origins: dict[str, set[str]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for label, rows in (("baseline", baseline), ("classement", ranked)):
        for row in rows:
            origins.setdefault(row["property_unit_id"], set()).add(label)
            by_id[row["property_unit_id"]] = row

    units = sorted(by_id)
    random.Random(seed).shuffle(units)
    blind_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    for position, unit in enumerate(units, start=1):
        reference = f"C{position:03d}"
        blind_rows.append({"reference": reference, **by_id[unit]})
        key_rows.append(
            {
                "reference": reference,
                "property_unit_id": unit,
                "cadastral_id": by_id[unit]["cadastral_id"],
                "origine": "+".join(sorted(origins[unit])),
            }
        )
    return blind_rows, key_rows


def cell(row: dict[str, Any], name: str, digits: int = 0) -> str:
    """Une valeur absente s'affiche absente, avec son motif."""
    value = row.get(name)
    if value is None:
        return f"absent — {row.get(f'{name}_missing') or 'non calculé'}"
    return f"{float(value):,.{digits}f}".replace(",", " ") if digits >= 0 else str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
