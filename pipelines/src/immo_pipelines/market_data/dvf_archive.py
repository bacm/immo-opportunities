"""Lire le format DGFiP brut et le mettre à la forme geo-dvf — D8.

`geo-dvf` ne publie que les cinq derniers millésimes. 2014 à 2020 n'existent que dans les
publications DGFiP archivées, au format brut : séparateur `|`, virgule décimale, dates en
`JJ/MM/AAAA`, et **aucun identifiant de parcelle ni de mutation constitué**.

Ce module ne fait qu'une chose : produire des lignes de la forme que
[`dvf.py`](./dvf.py) consomme déjà. La qualification des mutations complexes, le choix de la
surface et la déduplication des lots restent là-bas, inchangés — le format d'entrée ne doit rien
changer à la règle métier.

## L'identifiant de parcelle se reconstruit, et ses pièges sont nommés

`Code departement` + `Code commune` + `Prefixe de section` + `Section` + `No plan`, en quatorze
caractères. Deux rembourrages sont obligatoires et silencieux si on les oublie :

- le **préfixe** vaut `000` quand il est absent, ce qui est le cas courant ;
- la **section** est cadrée à droite sur deux caractères, complétée par `0` : `A` devient `0A`.
  C'est ainsi que le cadastre l'écrit — 130 229 parcelles du 35 en `0A`.

## L'identité de mutation est reconstruite, et l'écart est mesuré

Le brut ne porte pas d'`id_mutation`. La clé retenue — date, commune, valeur foncière, numéro de
disposition — a été calibrée contre la vérité d'Etalab sur 2022, où les deux sources existent :
31 112 mutations reconstruites contre 31 072 publiées, soit **+0,13 %**. Aucune clé testée ne
reproduit exactement la partition ; celle-ci en est la plus proche, et l'écart est publié dans
`docs/data/dvf-quality-35.md` plutôt qu'absorbé.
"""

import csv
import gzip
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

DELIMITER = "|"

# Les colonnes que `dvf.py` consomme. Rien de plus n'est écrit : une colonne inutilisée
# donnerait l'illusion d'une donnée portée.
GEODVF_COLUMNS = (
    "id_mutation",
    "date_mutation",
    "nature_mutation",
    "valeur_fonciere",
    "code_commune",
    "id_parcelle",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "lot1_numero",
    "surface_terrain",
)


def commune_code(row: dict[str, str]) -> str:
    """`35` + `051` — le département tient sur deux caractères en métropole, trois outre-mer."""
    department = row["Code departement"].strip()
    commune = row["Code commune"].strip()
    return f"{department.rjust(2, '0')}{commune.rjust(3, '0')}"


def cadastral_id(row: dict[str, str]) -> str | None:
    """Quatorze caractères, ou rien du tout — jamais un identifiant tronqué."""
    section = row["Section"].strip()
    plan = row["No plan"].strip()
    if not section or not plan:
        return None
    prefix = (row["Prefixe de section"].strip() or "0").rjust(3, "0")
    return f"{commune_code(row)}{prefix}{section.rjust(2, '0')}{plan.rjust(4, '0')}"


def mutation_key(row: dict[str, str]) -> str:
    """La clé calibrée contre Etalab. Son écart de 0,13 % est documenté, pas ignoré."""
    return ":".join(
        (
            row["Date mutation"].strip(),
            commune_code(row),
            row["Valeur fonciere"].strip(),
            row["No disposition"].strip(),
        )
    )


def iso_date(value: str) -> str:
    """`JJ/MM/AAAA` vers `AAAA-MM-JJ`. Une date illisible reste vide plutôt que d'être devinée."""
    parts = value.strip().split("/")
    if len(parts) != 3:
        return ""
    day, month, year = parts
    return f"{year}-{month.rjust(2, '0')}-{day.rjust(2, '0')}"


def decimal(value: str) -> str:
    """La virgule décimale du brut devient un point. Une valeur vide le reste."""
    return value.strip().replace(",", ".")


def price(value: str) -> str:
    """Un prix de zéro est une **absence**, pas un prix.

    Les publications anciennes écrivent `0,00` là où les récentes laissent le champ vide : sur
    2022, brut et geo-dvf portent exactement les mêmes 656 valeurs absentes et aucun zéro, tandis
    que la publication d'avril 2019 en contient. C'est une évolution de format, pas une donnée.

    Le convertir en zéro ferait une vente à zéro euro, qu'un prix au m² transformerait en valeur
    crédible et fausse. Vidé ici, il devient `price_missing` par la règle ordinaire de `dvf.py`.
    """
    converted = decimal(value)
    if not converted:
        return ""
    return "" if float(converted) == 0 else converted


def to_geodvf(row: dict[str, str]) -> dict[str, str]:
    return {
        "id_mutation": mutation_key(row),
        "date_mutation": iso_date(row["Date mutation"]),
        "nature_mutation": row["Nature mutation"].strip(),
        "valeur_fonciere": price(row["Valeur fonciere"]),
        "code_commune": commune_code(row),
        "id_parcelle": cadastral_id(row) or "",
        "type_local": row["Type local"].strip(),
        "surface_reelle_bati": decimal(row["Surface reelle bati"]),
        "nombre_pieces_principales": row["Nombre pieces principales"].strip(),
        "lot1_numero": row["1er lot"].strip(),
        "surface_terrain": decimal(row["Surface terrain"]),
    }


def read_department(lines: Iterable[str], department: str) -> Iterator[dict[str, str]]:
    """Les lignes du département, mises à la forme geo-dvf. Le fichier source est national."""
    for row in csv.DictReader(lines, delimiter=DELIMITER):
        if row["Code departement"].strip().rjust(2, "0") == department:
            yield to_geodvf(row)


def convert(source: Path, destination: Path, department: str) -> dict[str, Any]:
    """Écrit un CSV gzip de la forme geo-dvf, et rend de quoi contrôler la conversion."""
    counters = {"lines": 0, "without_parcel": 0, "without_date": 0, "without_price": 0}
    opener = gzip.open if source.suffix == ".gz" else open
    with (
        opener(source, "rt", encoding="utf-8", newline="") as handle,  # type: ignore[operator]
        gzip.open(destination, "wt", encoding="utf-8", newline="") as out,
    ):
        writer: csv.DictWriter[str] = csv.DictWriter(out, fieldnames=list(GEODVF_COLUMNS))
        writer.writeheader()
        for converted in read_department(handle, department):
            counters["lines"] += 1
            if not converted["id_parcelle"]:
                counters["without_parcel"] += 1
            if not converted["date_mutation"]:
                counters["without_date"] += 1
            writer.writerow(converted)
    return counters
