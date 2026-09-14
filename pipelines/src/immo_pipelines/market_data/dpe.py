"""Lire un extrait DPE de l'ADEME : éligibilité, appariement déclaré, caractéristiques — D4.

Le moteur de features `REN-004..008` est livré et testé depuis v0.6 ; ce module lui apporte la
donnée réelle, et porte les décisions que la source ne prend pas pour nous.

## Ce que la source dit, et ce qu'elle ne dit pas

L'extrait accessible est la **vue virtuelle** de l'ADEME, filtrée en amont sur
`dpe_desactive = 0` : un diagnostic annulé n'y apparaît jamais et le jeu sous-jacent répond 403.
Le filtre existe donc ici, écrit et testé, mais il n'écarte rien sur cette release — c'est le
producteur qui garantit l'exclusion, pas notre code, et le rapport le dit.

Aucune colonne ne marque un DPE **simulé**, pour une raison simple : ce jeu est le registre des
diagnostics déposés, et une étiquette prédite vient d'ailleurs — de la BDNB Expert, que le
contrat DS-07 exclut nommément. La garde retenue est donc celle du **modèle déclaré** : un
diagnostic dont `modele_dpe` sort de la liste fermée des modèles réglementaires est écarté avec
son motif, plutôt qu'admis par défaut. C'est la règle que D1 a appliquée aux natures de mutation,
et elle a la même vertu : un modèle nouveau se fait connaître au lieu d'entrer sans bruit.

## L'appariement est déclaré par la source, il n'est pas calculé par nous

B4 a établi un résultat négatif qu'il ne faut pas redécouvrir : la relation adresse ↔ parcelle
n'est vérifiable par aucune règle géométrique. Rien ici ne tente d'y revenir. Les deux
rattachements utilisés sont des **jointures d'identifiant**, que la source publie :

| Champ source | Cible | Ce que ça vaut |
|---|---|---|
| `id_rnb` | `reference.building` | le producteur affirme l'identité du bâtiment |
| `identifiant_ban` | `reference.address` | le producteur affirme l'identité de l'adresse |

`meta.entity_match` porte déjà ce précédent : `rnb-ban-identifier`, méthode `source_relation`,
confiance 1.0. Un identifiant officiel déclaré vaut 1, et ce n'est pas un seuil inventé — c'est
la source qui l'affirme.

## Une contradiction de la source reste une contradiction

`statut_geocodage` annonce parfois « adresse non géocodée ban car aucune correspondance trouvée »
alors que `identifiant_ban` **est rempli** et se résout dans notre référentiel — et que
`score_ban` y est plus élevé que sur les lignes géocodées. Les deux champs se contredisent.

Nous ne tranchons pas : l'adresse est conservée, parce que la jointure d'identifiant, elle, est
vérifiable ; c'est la **confiance** qui devient absente avec son motif. C'est la quarantaine par
attribut de BUG-03 — l'enregistrement reste, l'attribut invérifiable s'en va motivé.
"""

from __future__ import annotations

import csv
import gzip
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

# 1 : premier import DPE. Eligibilite, appariement declare, caracteristiques d'enveloppe.
DPE_TRANSFORMATION_VERSION = "1"

# Les modeles reglementaires du DPE « logements existants » depuis juillet 2021. Liste **fermee** :
# un modele inconnu est ecarte avec son motif, jamais admis par defaut.
ASSESSMENT_MODELS = frozenset({"DPE 3CL 2021 méthode logement"})

# Les caracteristiques **declarees** du bien, par opposition aux sorties du calcul 3CL
# (deperditions, couts, consommations par generateur) que le contrat n'admet pas comme
# observations. `REN-007` ne porte que celles-ci.
#
# `qualite_isolation_plancher bas` s'ecrit bien avec une espace dans l'export CSV, la ou l'API
# JSON la nomme avec un souligne. Nommer la colonne telle qu'elle est evite une valeur
# silencieusement absente.
ENVELOPE_FIELDS: tuple[tuple[str, str], ...] = (
    ("qualite_isolation_enveloppe", "envelope"),
    ("qualite_isolation_murs", "walls"),
    ("qualite_isolation_menuiseries", "windows"),
    ("qualite_isolation_plancher bas", "lower_floor"),
    ("qualite_isolation_plancher_haut_comble_perdu", "roof_lost_attic"),
    ("qualite_isolation_plancher_haut_comble_amenage", "roof_converted_attic"),
    ("qualite_isolation_plancher_haut_toit_terrasse", "roof_terrace"),
    ("type_ventilation", "ventilation"),
    ("classe_inertie_batiment", "inertia"),
    ("ubat_w_par_m2_k", "ubat_w_per_m2_k"),
    ("hauteur_sous_plafond", "ceiling_height_m"),
)

# Ce que l'import persiste hors colonnes dediees : la provenance de l'appariement, la nature du
# bien et ce qui qualifie la fraicheur. Le reste des 226 colonnes reste dans l'archive, qui est
# faite pour cela.
PRESERVED_FIELDS: tuple[str, ...] = (
    "type_batiment",
    "periode_construction",
    "annee_construction",
    "surface_habitable_logement",
    "methode_application_dpe",
    "modele_dpe",
    "version_dpe",
    "statut_geocodage",
    "score_ban",
    "provenance_id_rnb",
    "numero_dpe_remplace",
    "numero_dpe_immeuble_associe",
    "date_fin_validite_dpe",
    "adresse_ban",
)

# Le producteur declare l'echec de son propre geocodage par ce prefixe.
GEOCODING_FAILED = "adresse non géocodée"

# Les colonnes sans lesquelles l'extrait ne peut pas etre lu : identite, eligibilite, valeur,
# rattachement, territoire. Leur absence est un changement de schema amont, pas une valeur
# manquante — elle doit arreter l'import avant toute ecriture, pas produire 231 000 lignes vides.
REQUIRED_COLUMNS: tuple[str, ...] = (
    "numero_dpe",
    "date_etablissement_dpe",
    "date_reception_dpe",
    "modele_dpe",
    "etiquette_dpe",
    "conso_5_usages_par_m2_ep",
    "code_insee_ban",
    "id_rnb",
    "identifiant_ban",
    "score_ban",
    "statut_geocodage",
)


@dataclass(frozen=True, slots=True)
class Assessment:
    """Un diagnostic éligible, avec ce que la source déclare de son rattachement."""

    dpe_number: str
    assessment_date: date
    deposited_at: date
    commune_code: str
    energy_label: str | None
    consumption_kwh_m2_year: float | None
    rnb_id: str | None
    ban_id: str | None
    ban_score: float | None
    geocoding_contradicted: bool
    envelope: dict[str, Any]
    properties: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Rejection:
    """Un enregistrement écarté, et pourquoi. Jamais silencieux."""

    dpe_number: str
    reason: str
    detail: str


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "oui", "yes"}


def classify(row: dict[str, str], *, snapshot_at: date) -> Assessment | Rejection:
    """Dire si l'enregistrement est un diagnostic exploitable, ou pourquoi il ne l'est pas."""
    number = (row.get("numero_dpe") or "").strip()
    if not number:
        return Rejection("", "identifier_missing", "numero_dpe absent")
    # `dpe_desactive` n'existe que sur le jeu sous-jacent, inaccessible. La regle est ecrite pour
    # le jour ou un extrait le portera ; sur la vue virtuelle, elle n'ecarte rien.
    if _truthy(row.get("dpe_desactive")):
        return Rejection(number, "deactivated", "dpe_desactive déclaré par la source")
    model = (row.get("modele_dpe") or "").strip()
    if model not in ASSESSMENT_MODELS:
        return Rejection(number, "unknown_assessment_model", f"modele_dpe {model!r}")
    established = _date(row.get("date_etablissement_dpe"))
    if established is None:
        return Rejection(number, "assessment_date_missing", "date_etablissement_dpe illisible")
    received = _date(row.get("date_reception_dpe"))
    if received is None:
        # Un diagnostic que l'observatoire n'a pas recu n'est pas un diagnostic depose.
        return Rejection(number, "not_deposited", "date_reception_dpe absente")
    if established > snapshot_at:
        return Rejection(
            number, "after_snapshot", f"établi le {established.isoformat()} après le snapshot"
        )
    commune = (row.get("code_insee_ban") or "").strip()
    if not commune:
        return Rejection(number, "commune_missing", "code_insee_ban absent")

    label = (row.get("etiquette_dpe") or "").strip().upper() or None
    rnb = (row.get("id_rnb") or "").strip() or None
    ban = (row.get("identifiant_ban") or "").strip() or None
    status = (row.get("statut_geocodage") or "").strip()
    return Assessment(
        dpe_number=number,
        assessment_date=established,
        deposited_at=received,
        commune_code=commune,
        energy_label=label if label in set("ABCDEFG") else None,
        # L'etiquette repose sur la consommation en energie **primaire** par metre carre : c'est
        # celle-la que `REN-005` doit porter, pas l'energie finale ni un total non rapporte.
        consumption_kwh_m2_year=_number(row.get("conso_5_usages_par_m2_ep")),
        rnb_id=rnb,
        ban_id=ban,
        ban_score=_number(row.get("score_ban")),
        geocoding_contradicted=bool(ban) and status.startswith(GEOCODING_FAILED),
        envelope={
            key: row[column] for column, key in ENVELOPE_FIELDS if row.get(column) not in (None, "")
        },
        properties={
            field: row[field] for field in PRESERVED_FIELDS if row.get(field) not in (None, "")
        },
    )


def missing_columns(path: Path) -> tuple[str, ...]:
    """Les colonnes indispensables que l'extrait ne porte pas. Vide si le schéma tient."""
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        empty: list[str] = []
        header = next(csv.reader(handle), empty)
    return tuple(column for column in REQUIRED_COLUMNS if column not in set(header))


def read_extract(path: Path, *, snapshot_at: date) -> Iterator[Assessment | Rejection]:
    """Parcourir l'extrait archivé, ligne par ligne, sans jamais le charger en entier.

    L'extrait départemental pèse 370 Mo décompressés et ses descriptions d'installation
    contiennent des retours à la ligne : il se lit avec un lecteur CSV, pas ligne par ligne.
    """
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            yield classify(row, snapshot_at=snapshot_at)
