#!/usr/bin/env python3
"""Profiler les ventes DVF écartées parce qu'elles portent sur plusieurs parcelles — H7.

Une maison cadastrée sur deux parcelles, son jardin sur la seconde, est aujourd'hui écartée avec
le motif `multiple_parcels`, alors qu'une maison sur une seule parcelle garde son prix quelle que
soit la surface de son terrain. Ce rapport mesure, **avant tout changement de règle**, ce que
sont ces ventes, et si celles qui n'ont qu'un lot bâti ressemblent aux ventes déjà admises.

Il lit les archives épinglées par le même chemin que l'import — `resolve_asset`, conversion du
format DGFiP, `read_mutations`, `Mutation` — pour que la déduplication des lots soit exactement
celle de l'import, et n'écrit rien en base.

La comparaison se fait **sans seuil** : même type de bien, même période, surface de terrain
cumulée et prix au m² en quartiles, côte à côte. Si les deux populations se ressemblent, admettre
les premières n'invente rien ; sinon, c'est une décision, pas une implémentation.
"""

import argparse
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import load_release_manifest, resolve_asset
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.dvf import Mutation, _distinct_lots, _surface, read_mutations
from immo_pipelines.market_data.dvf_archive import convert

RELEASES = ("2019-04-archive", "2026-09-13")
LAND_BUCKETS = (
    (500, "moins de 500 m²"),
    (1000, "500 à 1 000 m²"),
    (2500, "1 000 à 2 500 m²"),
    (10000, "2 500 à 10 000 m²"),
)
LARGEST_LAND = "10 000 m² et plus"
NO_LAND = "aucun terrain déclaré"
# Support minimal d'un couple (commune, année) pour servir de référence : celui de BAR-002
# (SPEC §13.4), paramètre déclaré, pas un seuil de sens.
REFERENCE_SUPPORT = 15


def land_surface(mutation: Mutation) -> float | None:
    """Surface de terrain cumulée : une fois par (parcelle, nature de culture, surface).

    `geo-dvf` répète la surface de terrain d'une parcelle sur chaque ligne de la même nature ;
    la compter une fois par triplet évite de la multiplier par le nombre de lots.
    """
    seen = {
        (row.get("id_parcelle") or "", row.get("nature_culture") or "", row.get("surface_terrain"))
        for row in mutation.rows
        if row.get("surface_terrain")
    }
    total = sum(float(surface) for _, _, surface in seen if surface and float(surface) > 0)
    return total if seen else None


def land_bucket(surface: float | None) -> str:
    if surface is None:
        return NO_LAND
    for bound, label in LAND_BUCKETS:
        if surface < bound:
            return label
    return LARGEST_LAND


@dataclass
class Population:
    """Des ventes comparables : effectif, terrain cumulé, prix au m² du lot bâti."""

    count: int = 0
    land: list[float] = field(default_factory=list)
    no_land: int = 0
    price_m2: list[float] = field(default_factory=list)
    land_buckets: Counter[str] = field(default_factory=Counter)
    price_by_land: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    # (commune, année) → prix au m², pour le contrôle par commune et année du baromètre.
    price_by_place: dict[tuple[str, str], list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def add(self, mutation: Mutation, built: dict[str, str]) -> None:
        self.count += 1
        surface = land_surface(mutation)
        self.land_buckets[land_bucket(surface)] += 1
        if surface is None:
            self.no_land += 1
        else:
            self.land.append(surface)
        living = _surface(built)
        if mutation.price is not None and living is not None:
            self.price_m2.append(mutation.price / living)
            self.price_by_land[land_bucket(surface)].append(mutation.price / living)
            head = mutation.rows[0]
            place = (head.get("code_commune") or "", (head.get("date_mutation") or "")[:4])
            self.price_by_place[place].append(mutation.price / living)


@dataclass
class Profile:
    mutations: int = 0
    reasons: Counter[str] = field(default_factory=Counter)
    # Ventes `multiple_parcels` en version 4, selon ce que la règle en vigueur en fait.
    reordered: Counter[str] = field(default_factory=Counter)
    built_lots: Counter[str] = field(default_factory=Counter)
    parcels: Counter[str] = field(default_factory=Counter)
    single_built_types: Counter[str] = field(default_factory=Counter)
    land_natures: Counter[str] = field(default_factory=Counter)
    # (type de bien) → population ; `candidates` : un seul lot bâti, plusieurs parcelles ;
    # `admitted` : un seul lot bâti, une seule parcelle, prix déjà alloué aujourd'hui.
    candidates: dict[str, Population] = field(default_factory=lambda: defaultdict(Population))
    admitted: dict[str, Population] = field(default_factory=lambda: defaultdict(Population))


def v4_reason(mutation: Mutation) -> str | None:
    """Le motif de la version 4 de l'import, parcelles testées avant les lots — la référence.

    Recopiée ici, et ici seulement, pour que le rapport montre ce que H7 a changé : la règle en
    vigueur est `Mutation.complexity()`.
    """
    if mutation.price is None:
        return "price_missing"
    if len(mutation.parcels) > 1:
        return "multiple_parcels"
    lots = mutation.priced_lots()
    if len(lots) != 1:
        return "no_priced_lot" if not lots else "multiple_priced_lots"
    if _surface(lots[0]) is None:
        return "surface_missing"
    return None


def count_bucket(count: int) -> str:
    return str(count) if count < 5 else "5 et plus"


def observe(profile: Profile, mutation: Mutation) -> None:
    profile.mutations += 1
    reason = v4_reason(mutation)
    current = mutation.complexity()
    profile.reasons[reason or "allocatable"] += 1
    built = _distinct_lots([row for row in mutation.rows if row["type_local"]])
    if reason is None and len(built) == 1:
        profile.admitted[built[0]["type_local"]].add(mutation, built[0])
    if reason != "multiple_parcels":
        return
    profile.reordered[current or "allocatable"] += 1
    profile.built_lots[count_bucket(len(built))] += 1
    profile.parcels[count_bucket(len(mutation.parcels))] += 1
    for row in mutation.rows:
        if not row["type_local"] and row.get("nature_culture"):
            profile.land_natures[row["nature_culture"]] += 1
    if len(built) == 1:
        profile.single_built_types[built[0]["type_local"]] += 1
        if current is None:
            profile.candidates[built[0]["type_local"]].add(mutation, built[0])


def read_release(
    connection: psycopg.Connection[Any], release: str, department: str, temporary: Path
) -> Iterable[Mutation]:
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    catalog = DatasetCatalog(connection)
    manifest = load_release_manifest("DS-06", release, department)
    for asset in manifest.assets:
        raw = asset.layer.startswith("mutations-raw-")
        year = asset.layer.removeprefix("mutations-raw-").removeprefix("mutations-")
        destination = temporary / (f"{year}.txt" if raw else f"{year}.csv.gz")
        resolve_asset(
            catalog=catalog,
            object_store=object_store,
            manifest=manifest,
            asset=asset,
            destination=destination,
        )
        if raw:
            converted = temporary / f"{year}.csv.gz"
            convert(destination, converted, department)
            destination.unlink()
            destination = converted
        print(f"{release} {year}", flush=True)
        yield from read_mutations(destination).values()
        destination.unlink()


# --- Rendu ------------------------------------------------------------------------------------

NBSP = "\N{NO-BREAK SPACE}"


def number(value: float) -> str:
    return f"{round(value):,}".replace(",", NBSP)


def share(part: int, whole: int) -> str:
    return "—" if not whole else f"{part / whole * 100:.1f}{NBSP}%".replace(".", ",")


def quartiles(values: Sequence[float]) -> tuple[str, str, str]:
    if len(values) < 4:
        return ("—", "—", "—")
    q1, q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return (number(q1), number(q2), number(q3))


def median(values: Sequence[float]) -> str:
    return "—" if not values else f"{number(statistics.median(values))} €"


def counter_table(
    title: str, counter: Counter[str], whole: int, header: str, unit: str = "Mutations"
) -> list[str]:
    lines = [f"### {title}", "", f"| {header} | {unit} | Part |", "|---|---:|---:|"]
    if not counter:
        lines.append("| — | — | — |")
    for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {key} | {number(value)} | {share(value, whole)} |")
    return [*lines, ""]


def comparison(profile: Profile, types: Sequence[str]) -> list[str]:
    lines = [
        "| Type | Population | Ventes | Sans terrain | Terrain Q1 | Terrain médiane | "
        "Terrain Q3 | Prix au m² Q1 | Médiane | Q3 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for local_type in types:
        for label, population in (
            ("admises, une parcelle", profile.admitted[local_type]),
            ("candidates, plusieurs parcelles", profile.candidates[local_type]),
        ):
            land = quartiles(population.land)
            price = quartiles(population.price_m2)
            lines.append(
                f"| {local_type} | {label} | {number(population.count)} | "
                f"{number(population.no_land)} | {land[0]} | {land[1]} | {land[2]} | "
                f"{price[0]} € | {price[1]} € | {price[2]} € |"
            )
    return [*lines, ""]


def relative_prices(population: Population, reference: Population) -> tuple[int, list[float]]:
    """Chaque prix rapporté à la médiane des ventes admises de sa commune, la même année.

    Rend l'effectif sans référence (couple commune-année sous le support) et les ratios des autres.
    """
    medians = {
        place: statistics.median(values)
        for place, values in reference.price_by_place.items()
        if len(values) >= REFERENCE_SUPPORT
    }
    without = 0
    ratios: list[float] = []
    for place, values in population.price_by_place.items():
        if place not in medians:
            without += len(values)
            continue
        ratios.extend(value / medians[place] for value in values)
    return without, ratios


def decimal(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def ratio_quartiles(values: Sequence[float]) -> tuple[str, str, str]:
    if len(values) < 4:
        return ("—", "—", "—")
    q1, q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return (decimal(q1), decimal(q2), decimal(q3))


def place_comparison(profile: Profile, local_type: str) -> list[str]:
    admitted = profile.admitted[local_type]
    lines = [
        f"Contrôle par commune et année ({local_type}) : prix au m² rapporté à la médiane "
        f"des ventes admises de la même commune la même année, pour les couples d'au moins "
        f"{REFERENCE_SUPPORT} ventes admises. Un ratio de 1 veut dire « au prix de sa commune ».",
        "",
        "| Population | Avec référence | Sans référence | Ratio Q1 | Médiane | Q3 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, population in (
        ("admises, une parcelle", admitted),
        ("candidates, plusieurs parcelles", profile.candidates[local_type]),
    ):
        without, ratios = relative_prices(population, admitted)
        q1, q2, q3 = ratio_quartiles(ratios)
        lines.append(
            f"| {label} | {number(len(ratios))} | {number(without)} | {q1} | {q2} | {q3} |"
        )
    return [*lines, ""]


def bucket_comparison(profile: Profile, local_type: str) -> list[str]:
    labels = [label for _, label in LAND_BUCKETS] + [LARGEST_LAND, NO_LAND]
    admitted = profile.admitted[local_type]
    candidates = profile.candidates[local_type]
    lines = [
        f"| Terrain cumulé ({local_type}) | Admises | Part | Prix au m² médian | "
        "Candidates | Part | Prix au m² médian |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label in labels:
        a, c = admitted.land_buckets[label], candidates.land_buckets[label]
        lines.append(
            f"| {label} | {number(a)} | {share(a, admitted.count)} | "
            f"{median(admitted.price_by_land[label])} | "
            f"{number(c)} | {share(c, candidates.count)} | "
            f"{median(candidates.price_by_land[label])} |"
        )
    return [*lines, ""]


def render(profiles: dict[str, Profile], department: str, generated_on: date) -> str:
    lines = [
        f"# Ventes DVF sur plusieurs parcelles — {department}",
        "",
        f"**Généré le** {generated_on.isoformat()} par `make dvf-multi-parcel-profile` — ticket "
        "[H7](../backlog/H7-mutations-multi-parcelles.md).",
        "**Non recompté.** Aucun chiffre ne sort de ce fichier sans `recompte-preuve`.",
        "",
        "Lu depuis les archives épinglées de DS-06, par le code de l'import : mêmes lots",
        "dédupliqués, règle de complexité en vigueur (version 5) et règle de la version 4,",
        "recopiée pour référence. Rien n'est écrit en base. Aucune mutation individuelle ici.",
        "",
        "**Filtres communs.** Une mutation est un acte (`id_mutation`, ou la clé reconstruite de",
        "l'archive DGFiP). Un lot bâti est une ligne à `type_local` renseigné, dédupliquée comme à",
        "l'import. Le terrain cumulé compte une fois chaque triplet (parcelle, nature de culture,",
        "surface). Le prix au m² est le prix de l'acte rapporté à la surface bâtie du lot unique ;",
        "aucune nature de mutation n'est filtrée ici. Une valeur foncière nulle compte comme",
        "absente (196 actes de l'archive, aucun sur 2021-2025). La nature de culture n'est pas",
        "convertie depuis l'archive DGFiP : son tableau n'existe que pour 2021-2025, en lignes,",
        "et le terrain cumulé de l'archive se compte par (parcelle, surface). Les tranches de",
        "terrain sont fermées à gauche, ouvertes à droite ; les demi-unités vont au pair.",
        "",
    ]
    lines += [
        "## Critère d'admission retenu",
        "",
        "Écrit avant le code, à partir des tableaux ci-dessous (H7, choix 3).",
        "",
        "- **Ce qui est admis** : une mutation dont le prix est présent et qui porte **un seul lot",
        "  bâti distinct, avec surface**, quel que soit le nombre de parcelles. Le prix va à ce",
        "  lot, le terrain venant avec — la règle déjà appliquée à une vente sur une parcelle.",
        "- **Ce qui ne l'est pas** : zéro ou plusieurs lots chiffrables, surface absente, prix",
        "  absent — comme en version 4, avec le motif le plus précis, testé avant les parcelles.",
        "- **Pourquoi sans seuil de terrain.** Les candidates portent plus de terrain et un prix",
        "  au m² brut plus bas que les ventes admises. Mais à commune et année égales, leur ratio",
        "  médian au prix de la commune est proche de celui des admises : l'écart brut vient du",
        "  lieu, pas du terrain annexé. Une vente sur une parcelle est déjà admise quelle que soit",
        "  sa surface de terrain ; en exiger une des candidates serait inventer un seuil.",
        "- **Limite du contrôle.** Il ne couvre que les couples commune-année d'au moins",
        "  15 ventes admises, soit environ la moitié des candidates : les communes où la règle",
        "  rend le plus de ventes sont celles où l'absence de dérive ne se mesure pas encore.",
        "  L'argument y tient par cohérence avec les ventes sur une parcelle, pas par mesure.",
        "- **Ce qui change pour le baromètre** : des ventes rurales en plus, là où le support de",
        "  BAR-001 et BAR-002 manque ; une dispersion un peu plus large du prix au m², visible",
        "  dans le premier quartile du ratio.",
        "",
    ]
    for release, profile in profiles.items():
        blocked = profile.reasons["multiple_parcels"]
        lines += [
            f"## Release `DS-06@{release}`",
            "",
            f"**{number(profile.mutations)}** mutations ; **{number(blocked)}** "
            f"`multiple_parcels` ({share(blocked, profile.mutations)}).",
            "",
            *counter_table(
                "Toutes les mutations, par motif en version 4",
                profile.reasons,
                profile.mutations,
                "Motif",
            ),
            *counter_table(
                "Les `multiple_parcels`, par nombre de lots bâtis distincts",
                profile.built_lots,
                blocked,
                "Lots bâtis",
            ),
            *counter_table(
                "Les `multiple_parcels`, par nombre de parcelles",
                profile.parcels,
                blocked,
                "Parcelles",
            ),
            *counter_table(
                "Les `multiple_parcels` à un seul lot bâti, par type de local",
                profile.single_built_types,
                sum(profile.single_built_types.values()),
                "Type",
            ),
            *counter_table(
                "Nature de culture des lignes de terrain des `multiple_parcels`",
                profile.land_natures,
                sum(profile.land_natures.values()),
                "Nature",
                unit="Lignes de terrain",
            ),
            *counter_table(
                "Les `multiple_parcels` de la version 4, par motif en version 5",
                profile.reordered,
                blocked,
                "Motif en version 5",
            ),
            "### Candidates et ventes déjà admises, côte à côte",
            "",
            "*Admises* : un seul lot bâti, une seule parcelle, prix alloué en version 4.",
            "*Candidates* : un seul lot bâti avec surface, plusieurs parcelles, prix présent.",
            "",
            *comparison(profile, ("Maison", "Appartement")),
            *bucket_comparison(profile, "Maison"),
            *place_comparison(profile, "Maison"),
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", default="35")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    department: str = arguments.department
    output: Path = arguments.output or Path(f"docs/data/dvf-multi-parcelles-{department}.md")

    settings = CadastreSettings.from_environment()
    profiles: dict[str, Profile] = {}
    with (
        psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password,
        ) as connection,
        tempfile.TemporaryDirectory(prefix="immo-dvf-profile-") as temporary,
    ):
        for release in RELEASES:
            profile = Profile()
            for mutation in read_release(connection, release, department, Path(temporary)):
                observe(profile, mutation)
            profiles[release] = profile
    output.write_text(render(profiles, department, date.today()), encoding="utf-8")
    print(f"Rapport écrit : {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
