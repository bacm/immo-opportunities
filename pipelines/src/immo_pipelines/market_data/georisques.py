"""Interroger Géorisques, famille par famille, en conservant la granularité — D3, DS-09.

Le moteur `compute_risk_features` est livré et testé depuis v0.6 ; ce module lui apporte la donnée
réelle. La règle qu'il porte tient en une phrase : **une observation communale ne devient jamais
une exposition parcellaire.**

## Trois modes d'accès, parce que la source en a trois

L'inventaire écrit avant le premier lot — `docs/data/georisques-source-inventory-35.md` — a établi
qu'aucun téléchargement daté par famille et par département n'existe, et que Géorisques se
présente sous trois formes qu'aucune famille ne partage entièrement :

| Mode | Familles | Ce qu'on en tire |
|---|---|---|
| `department` | ICPE, cavités, mouvements de terrain, sites pollués | un appel, tout le 35 |
| `commune` | radon, GASPAR, AZI, CatNat | 335 appels, granularité communale |
| `download` | argiles | une couche nationale de 623 Mo |

Les servitudes d'utilité publique sont un quatrième cas, traité par `georisques_sup.py` : leur
source est le GPU, leur nature est celle de D3.

## Le piège central : un paramètre inconnu est ignoré, pas rejeté

`installations_classees?code_departement=35` répond **200 avec 138 248 résultats** — la France
entière — parce que le paramètre attendu s'appelle `departement`. Sur `ssp/instructions`, c'est
exactement l'inverse. Le code HTTP ne dit donc rien de la justesse du filtre.

D'où `belongs_to`, vérifié **ligne à ligne** : une réponse dont les enregistrements ne sont pas du
département demandé fait échouer la famille au lieu d'importer la France.

## Et un `500` qui veut dire « paramètre manquant »

`cavites` sans filtre répond `500 Des paramètres de recherches sont manquants`. Temporiser sur le
statut rejouerait cinq fois une requête mal formée : la distinction se fait sur le corps.

## Le lien `next` de la source pointe une machine interne

La pagination annoncée par l'API renvoie vers `http://api-georisques.bike-prod.brgm.fr/…`, un
hôte du réseau du producteur, injoignable depuis l'extérieur — en clair de surcroît. Le suivre
fait échouer toute famille de plus d'une page.

Les pages sont donc reconstruites à partir de `total_pages` et du paramètre `page`, sur l'hôte
public. C'est moins élégant que de suivre un lien, et c'est la seule façon qui fonctionne.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal, cast

from shapely.geometry.base import BaseGeometry

API = "https://www.georisques.gouv.fr/api/v1"
USER_AGENT = "ImmoOpportunitiesDataPipeline/0.1 (+https://github.com/)"

# 1 : premier import Georisques. Granularite d'origine persistee, aucune inference vers la parcelle.
GEORISQUES_TRANSFORMATION_VERSION = "1"

PAGE_SIZE = 1000
ATTEMPTS = 5
BACKOFF_SECONDS = 4

# La source dit « parametres manquants » avec un statut 500. Rejouer cinq fois une requete mal
# formee ne la rendrait pas valide : ce message est definitif, quel que soit le code HTTP.
PERMANENT_MESSAGES = ("paramètres de recherches sont manquants", "no endpoint")

Granularity = Literal["point", "zone", "parcel", "commune"]


class SourceFilterIgnored(RuntimeError):
    """La réponse contient des enregistrements hors du territoire demandé.

    Le cas n'est pas théorique : un nom de paramètre erroné renvoie la France entière avec un
    statut 200. Importer cela peuplerait `risk_observation` de 138 248 lignes dont 134 000 n'ont
    rien à y faire, sans qu'aucune erreur ne soit levée.
    """


class PermanentApiError(RuntimeError):
    """Une requête que rejouer ne sauvera pas."""


@dataclass(frozen=True, slots=True)
class Observation:
    """Une observation de risque, avec la granularité de la source qui la fonde."""

    source_identifier: str
    risk_type: str
    granularity: Granularity
    commune_code: str
    severity: str | None = None
    observed_at: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    # WKT en WGS84, converti en Lambert 93 a l'ecriture. `None` pour une observation communale :
    # la contrainte `risk_observation_granularity` l'exige, et c'est la garantie du ticket.
    geometry_wkt: str | None = None
    value: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


@dataclass(frozen=True, slots=True)
class Family:
    """Une famille de risque : son accès, son territoire, ce qu'elle produit."""

    key: str
    label: str
    mode: Literal["department", "commune", "download"]
    endpoint: str
    # Le nom du parametre territorial, qui change d'un endpoint a l'autre. Voir l'inventaire.
    territory_parameter: str
    granularity: Granularity
    normalize: Callable[[dict[str, Any]], Iterator[Observation]]
    # Comment reconnaitre qu'un enregistrement est bien du departement demande.
    commune_of: Callable[[dict[str, Any]], str | None]
    # Le SRID de la source, obligatoire au contrat. L'API repond en WGS84 ; la couche argiles est
    # deja en Lambert 93. Le supposer ferait deriver des geometries de plusieurs centaines de km.
    source_srid: int


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _french_date(value: Any) -> date | None:
    """`JJ/MM/AAAA` pour GASPAR, `AAAA-MM-JJ` ailleurs. Une date illisible reste absente."""
    text = _text(value)
    if text is None:
        return None
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return date.fromisoformat(time.strftime("%Y-%m-%d", time.strptime(text[:10], pattern)))
        except ValueError:
            continue
    return None


def _point_wkt(record: dict[str, Any]) -> str | None:
    longitude, latitude = record.get("longitude"), record.get("latitude")
    if longitude is None or latitude is None:
        return None
    return f"POINT({float(longitude)} {float(latitude)})"


def _rings(polygon: list[list[list[float]]]) -> str:
    rings = [
        "(" + ", ".join(f"{float(point[0])} {float(point[1])}" for point in ring) + ")"
        for ring in polygon
    ]
    return "(" + ", ".join(rings) + ")"


def _geojson_wkt(geometry: dict[str, Any] | None) -> str | None:
    """Convertir une géométrie GeoJSON polygonale en WKT.

    `Polygon` **et** `MultiPolygon` sont acceptés. Ne traiter que le second a coûté cher : le
    découpage des argiles par commune produit un `Polygon` dès que l'intersection est d'un seul
    tenant, et 1 131 observations sur 1 428 disparaissaient sans un mot — l'import se terminait
    en succès. Un type non polygonal reste refusé, et l'appelant le compte.
    """
    if not geometry:
        return None
    kind = geometry.get("type")
    if kind == "Polygon":
        polygon = cast(list[list[list[float]]], geometry.get("coordinates") or [])
        return f"MULTIPOLYGON({_rings(polygon)})" if polygon else None
    if kind != "MultiPolygon":
        return None
    coordinates = cast(list[list[list[list[float]]]], geometry.get("coordinates") or [])
    polygons = [_rings(polygon) for polygon in coordinates if polygon]
    return f"MULTIPOLYGON({', '.join(polygons)})" if polygons else None


def _icpe(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("codeInsee"))
    identifier = _text(record.get("codeAIOT"))
    geometry = _point_wkt(record)
    if commune is None or identifier is None or geometry is None:
        return
    yield Observation(
        source_identifier=identifier,
        risk_type="industrial_installation",
        granularity="point",
        commune_code=commune,
        severity=_text(record.get("regime")),
        observed_at=_french_date((record.get("date_maj") or "").split("/")[0] or None),
        geometry_wkt=geometry,
        value={
            "raison_sociale": _text(record.get("raisonSociale")),
            "regime": _text(record.get("regime")),
            "code_naf": _text(record.get("codeNaf")),
            "priorite_nationale": record.get("prioriteNationale"),
            # L'adresse est conservee telle quelle et n'est jamais utilisee pour rattacher :
            # l'inventaire a releve un etablissement du 35 portant une adresse du Finistere.
            "adresse": _text(record.get("adresse1")),
            "commune_declaree": _text(record.get("commune")),
            "code_postal_declare": _text(record.get("codePostal")),
        },
    )


def _cavity(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    identifier = _text(record.get("identifiant"))
    geometry = _point_wkt(record)
    if commune is None or identifier is None or geometry is None:
        return
    yield Observation(
        source_identifier=identifier,
        risk_type="cavity",
        granularity="point",
        commune_code=commune,
        severity=_text(record.get("type")),
        geometry_wkt=geometry,
        value={
            "type": _text(record.get("type")),
            "nom": _text(record.get("nom")),
            "reperage_geo": _text(record.get("reperage_geo")),
        },
    )


def _landslide(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    identifier = _text(record.get("identifiant"))
    geometry = _point_wkt(record)
    if commune is None or identifier is None or geometry is None:
        return
    yield Observation(
        source_identifier=identifier,
        risk_type="landslide",
        granularity="point",
        commune_code=commune,
        severity=_text(record.get("type")),
        observed_at=_french_date(record.get("date_debut")),
        geometry_wkt=geometry,
        value={
            "type": _text(record.get("type")),
            "fiabilite": _text(record.get("fiabilite")),
            "precision_lieu": _text(record.get("precision_lieu")),
            "lieu": _text(record.get("lieu")),
        },
    )


def _soil_pollution(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    identifier = _text(record.get("identifiant_ssp"))
    geometry = _geojson_wkt(record.get("geom"))
    if commune is None or identifier is None:
        return
    yield Observation(
        source_identifier=identifier,
        # La granularite suit ce que la source donne : une instruction sans emprise reste une
        # observation communale, elle ne devient pas une zone faute de mieux.
        risk_type="soil_pollution",
        granularity="zone" if geometry else "commune",
        commune_code=commune,
        severity=_text(record.get("statut")),
        observed_at=_french_date(record.get("date_maj")),
        geometry_wkt=geometry,
        value={
            "nom_etablissement": _text(record.get("nom_etablissement")),
            "statut": _text(record.get("statut")),
            "fiche_risque": _text(record.get("fiche_risque")),
            "adresse": _text(record.get("adresse")),
        },
    )


def _clay(record: dict[str, Any]) -> Iterator[Observation]:
    """Une zone d'exposition déjà découpée par commune à l'épinglage.

    Le niveau vient de la source — `Faible`, `Moyen`, `Fort` — et n'est ni recodé ni pondéré : le
    lien risque → score se décide en E1, pas ici.
    """
    commune = _text(record.get("commune_code"))
    identifier = _text(record.get("source_identifier"))
    geometry = _geojson_wkt(cast(dict[str, Any] | None, record.get("geom")))
    if commune is None or identifier is None or geometry is None:
        return
    yield Observation(
        source_identifier=identifier,
        risk_type="clay",
        granularity="zone",
        commune_code=commune,
        severity=_text(record.get("alea")),
        geometry_wkt=geometry,
        value={"alea": _text(record.get("alea")), "niveau": record.get("niveau")},
    )


def _sup(record: dict[str, Any]) -> Iterator[Observation]:
    """Une assiette de servitude, déjà découpée par commune à l'épinglage.

    Le `risk_type` porte la **catégorie** de servitude — `sup_PM1` pour les risques naturels,
    `sup_AC1` pour les monuments historiques. Les fondre en un seul type effacerait ce qui les
    distingue : une servitude de dégagement aéronautique et un périmètre de PPRI ne se lisent pas
    de la même façon dans un scénario de division.
    """
    commune = _text(record.get("commune_code"))
    identifier = _text(record.get("source_identifier"))
    category = _text(record.get("category"))
    geometry = _geojson_wkt(cast("dict[str, Any] | None", record.get("geom")))
    if commune is None or identifier is None or category is None or geometry is None:
        return
    yield Observation(
        source_identifier=identifier,
        risk_type=f"sup_{category}",
        granularity="zone",
        commune_code=commune,
        severity=_text(record.get("type_assiette")),
        geometry_wkt=geometry,
        value={
            "category": category,
            "document": _text(record.get("document")),
            "nom_assiette": _text(record.get("nom_assiette")),
            "type_assiette": _text(record.get("type_assiette")),
            "idass": _text(record.get("idass")),
        },
    )


def _radon(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    potential = _text(record.get("classe_potentiel"))
    if commune is None or potential is None:
        return
    yield Observation(
        source_identifier=f"radon:{commune}",
        risk_type="radon",
        granularity="commune",
        commune_code=commune,
        severity=potential,
        value={
            "classe_potentiel": potential,
            "libelle_commune": _text(record.get("libelle_commune")),
        },
    )


# Les risques recenses par GASPAR, dont le libelle porte la famille. Le rattachement au type
# canonique du moteur n'est fait que pour ce qu'il sait traiter ; le reste garde son libelle.
GASPAR_RISK_TYPES = {
    "Inondation": "flood",
    "Submersion Marine": "coastal_flood",
    "Mouvement de terrain": "landslide",
    "Séisme": "earthquake",
    "Radon": "radon",
    "Retrait-gonflement des argiles": "clay",
}


def _gaspar_risks(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    if commune is None:
        return
    for detail in cast(list[dict[str, Any]], record.get("risques_detail") or []):
        label = _text(detail.get("libelle_risque_long"))
        number = _text(detail.get("num_risque"))
        if label is None or number is None:
            continue
        yield Observation(
            source_identifier=f"gaspar:{commune}:{number}",
            risk_type=GASPAR_RISK_TYPES.get(label, label),
            # **Toujours communal.** GASPAR dit qu'une commune est concernee ; il ne dit pas ou.
            # En faire une exposition parcellaire est precisement l'interdit du ticket.
            granularity="commune",
            commune_code=commune,
            value={"libelle_risque": label, "num_risque": number},
        )


def _flood_atlas(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    identifier = _text(record.get("code_national_azi"))
    if commune is None or identifier is None:
        return
    yield Observation(
        source_identifier=f"azi:{commune}:{identifier}",
        risk_type="flood",
        granularity="commune",
        commune_code=commune,
        observed_at=_french_date(record.get("date_diffusion")),
        value={
            "libelle_azi": _text(record.get("libelle_azi")),
            "bassin_risques": _text(record.get("libelle_bassin_risques")),
            "code_national_azi": identifier,
        },
    )


def _natural_disaster(record: dict[str, Any]) -> Iterator[Observation]:
    commune = _text(record.get("code_insee"))
    identifier = _text(record.get("code_national_catnat"))
    if commune is None or identifier is None:
        return
    yield Observation(
        source_identifier=f"catnat:{commune}:{identifier}",
        risk_type="natural_disaster",
        granularity="commune",
        commune_code=commune,
        observed_at=_french_date(record.get("date_debut_evt")),
        value={
            "libelle_risque": _text(record.get("libelle_risque_jo")),
            "date_debut": _text(record.get("date_debut_evt")),
            "date_fin": _text(record.get("date_fin_evt")),
            "code_national_catnat": identifier,
        },
    )


FAMILIES: tuple[Family, ...] = (
    Family(
        "industrial-installation",
        "Installations classées",
        "department",
        "installations_classees",
        "departement",
        "point",
        _icpe,
        lambda record: _text(record.get("codeInsee")),
        4326,
    ),
    Family(
        "cavity",
        "Cavités souterraines",
        "department",
        "cavites",
        "departement",
        "point",
        _cavity,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "landslide",
        "Mouvements de terrain",
        "department",
        "mvt",
        "departement",
        "point",
        _landslide,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "soil-pollution",
        "Sites et sols pollués",
        "department",
        "ssp/instructions",
        # Ce endpoint-ci veut `code_departement` la ou les trois precedents veulent `departement`.
        "code_departement",
        "zone",
        _soil_pollution,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "radon",
        "Potentiel radon",
        "commune",
        "radon",
        "code_insee",
        "commune",
        _radon,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "gaspar-risks",
        "Risques recensés GASPAR",
        "commune",
        "gaspar/risques",
        "code_insee",
        "commune",
        _gaspar_risks,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "flood-atlas",
        "Atlas des zones inondables",
        "commune",
        "gaspar/azi",
        "code_insee",
        "commune",
        _flood_atlas,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "natural-disaster",
        "Arrêtés de catastrophe naturelle",
        "commune",
        "gaspar/catnat",
        "code_insee",
        "commune",
        _natural_disaster,
        lambda record: _text(record.get("code_insee")),
        4326,
    ),
    Family(
        "clay",
        "Exposition au retrait-gonflement des argiles",
        "download",
        "argiles/AleaRG_Fxx_L93.zip",
        "DPT",
        "zone",
        _clay,
        lambda record: _text(record.get("commune_code")),
        # La couche est deja en Lambert 93 : la reprojeter depuis le WGS84 la deplacerait de
        # plusieurs centaines de kilometres, sans qu'aucune contrainte ne s'en apercoive.
        2154,
    ),
    Family(
        "sup",
        "Servitudes d'utilité publique",
        "download",
        "geoportail-urbanisme.gouv.fr/api/document",
        "territory",
        "zone",
        _sup,
        lambda record: _text(record.get("commune_code")),
        # Les couches CNIG sont en Lambert 93.
        2154,
    ),
)


def family(key: str) -> Family:
    for candidate in FAMILIES:
        if candidate.key == key:
            return candidate
    raise KeyError(f"famille inconnue : {key}")


def _is_permanent(body: str) -> bool:
    lowered = body.lower()
    return any(marker in lowered for marker in PERMANENT_MESSAGES)


def request(url: str) -> dict[str, Any]:
    """Un appel, avec temporisation — mais seulement pour ce qu'une reprise peut sauver."""
    last: Exception | None = None
    for attempt in range(ATTEMPTS):
        try:
            message = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(message, timeout=120) as response:
                payload: dict[str, Any] = json.load(response)
                return payload
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            if _is_permanent(body):
                raise PermanentApiError(f"{url} : {body[:200]}") from error
            last = error
        except Exception as error:
            last = error
        time.sleep(BACKOFF_SECONDS * (attempt + 1))
    raise RuntimeError(f"{ATTEMPTS} tentatives échouées sur {url}") from last


def _page_url(item: Family, territory: str, page: int) -> str:
    query = urllib.parse.urlencode(
        {item.territory_parameter: territory, "page_size": PAGE_SIZE, "page": page}
    )
    return f"{API}/{item.endpoint}?{query}"


def fetch(item: Family, territory: str, *, department: str) -> list[dict[str, Any]]:
    """Toutes les pages d'une famille pour un territoire, filtre vérifié ligne à ligne.

    Les pages sont numérotées plutôt que suivies : le lien `next` de la source pointe une machine
    de son réseau interne, injoignable d'ici.
    """
    records: list[dict[str, Any]] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = request(_page_url(item, territory, page))
        total_pages = int(payload.get("total_pages") or 0) or 1
        rows = cast(list[dict[str, Any]], payload.get("data") or [])
        for record in rows:
            commune = item.commune_of(record)
            if commune is not None and not commune.startswith(department):
                raise SourceFilterIgnored(
                    f"{item.key} : {item.endpoint} a renvoyé la commune {commune}, hors du "
                    f"département {department}. Le filtre `{item.territory_parameter}` n'a pas "
                    "été appliqué — un paramètre inconnu est ignoré, pas rejeté."
                )
        records.extend(rows)
        if not rows:
            break
        page += 1
    return records


def commune_shapes(connection: Any, department: str) -> tuple[list[str], list[Any]]:
    """Les géométries communales du département, pour découper une zone qui les traverse."""
    from shapely.wkb import loads as wkb_loads

    rows = connection.execute(
        """
        SELECT code, ST_AsBinary(geom) FROM reference.area
         WHERE area_type = 'commune' AND department_code = %s ORDER BY code
        """,
        (department,),
    ).fetchall()
    shapes = [wkb_loads(bytes(row[1])) for row in rows]
    return [str(row[0]) for row in rows], shapes


def split_by_commune(
    features: list[dict[str, Any]],
    codes: list[str],
    shapes: list[BaseGeometry],
    *,
    label: str,
) -> list[dict[str, Any]]:
    """Découper des zones par commune, sans jamais leur en attribuer une arbitrairement.

    `risk_observation.commune_code` est obligatoire et une zone traverse les communes. Chaque
    observation porte donc **l'intersection réelle**, pas le polygone entier réattribué. Découper
    est exact ; choisir une commune ne le serait pas.

    Une intersection réduite à une ligne ou à un point est écartée : un contact de frontière n'est
    pas une exposition, et l'écrire en fabriquerait une.
    """
    from shapely import STRtree, make_valid
    from shapely.geometry import mapping, shape

    from immo_pipelines.progress import Progress

    tree = STRtree(shapes)
    records: list[dict[str, Any]] = []
    progress = Progress(len(features), label)
    for feature in features:
        geometry = shape(feature["geom"])
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        for position in cast(list[int], list(tree.query(geometry))):
            piece = geometry.intersection(shapes[int(position)])
            if piece.is_empty or float(piece.area) <= 0:
                continue
            records.append(
                {
                    **{key: value for key, value in feature.items() if key != "geom"},
                    "source_identifier": f"{feature['source_identifier']}:{codes[int(position)]}",
                    "commune_code": codes[int(position)],
                    "geom": mapping(piece),
                }
            )
        progress.advance()
    return records
