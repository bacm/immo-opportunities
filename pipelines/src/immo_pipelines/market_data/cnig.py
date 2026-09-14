"""Lire une archive CNIG du Géoportail de l'urbanisme — D2, DS-08.

Une archive CNIG contient des couches structurées — le document, ses communes, ses zones, ses
prescriptions — et des pièces écrites en PDF. **Seules les couches structurées sont lues ici.**
L'interprétation du texte des règlements est interdite dans ce ticket et le reste : le produit ne
rend pas de décision urbanistique opposable.

## Deux pièges de la norme, et pourquoi ils sont traités ici

**La casse des noms de champs varie d'un document à l'autre.** Le PLU communal `DU_35018` écrit
`INSEE` et `IDURBA` en majuscules ; le PLUi de Rennes Métropole les écrit en minuscules. Une
lecture sensible à la casse retourne une chaîne vide **sans lever d'erreur**, et le document
paraît alors ne couvrir aucune commune. Ce défaut a failli écarter silencieusement le PLUi de
Rennes Métropole et ses 43 communes ; il n'a été vu que parce que le symptôme était
invraisemblable.

**Le nom des fichiers varie aussi.** L'ancienne convention nomme la couche seule —
`ZONE_URBA.shp` — la nouvelle la préfixe du SIREN et la suffixe de la date —
`243500139_zone_urba_20251218.shp`. Les deux désignent la même couche.

Aucun des deux n'est une anomalie : ce sont deux générations de la norme CNIG, et un import qui
n'accepterait qu'une seule perdrait la moitié des documents.
"""

import io
import re
import zipfile
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, cast

# `pyshp` ne publie pas de types. Plutot que d'affaiblir le mode strict pour tout le depot, on
# isole la bibliotheque derriere ce module : l'inconnu s'arrete a sa lisiere, et tout ce qui en
# sort est typé — un `Feature`, jamais un objet opaque.
import shapefile  # type: ignore[import-untyped]

# Les couches structurees que D2 importe, dans l'ordre de specificite : `doc_urba_com` avant
# `doc_urba`, sans quoi le second capturerait le premier.
LAYERS = (
    "doc_urba_com",
    "doc_urba",
    "zone_urba",
    "prescription_surf",
    "prescription_lin",
    "prescription_pct",
    "info_surf",
    "info_lin",
    "info_pct",
)

# Les extensions d'un shapefile. `.cpg` porte l'encodage des attributs, `.prj` la projection.
SHAPEFILE_SUFFIXES = (".shp", ".dbf", ".shx", ".prj", ".cpg")


@dataclass(frozen=True, slots=True)
class Feature:
    """Un enregistrement CNIG : ses attributs, et sa géométrie quand elle existe.

    Les attributs sont exposés en minuscules, une fois pour toutes. C'est ici que se règle la
    variation de casse entre générations de norme, et non chez l'appelant : un accès direct au
    dictionnaire d'origine échouerait **silencieusement**, et c'est exactement ce qui a failli
    faire disparaître le PLUi de Rennes Métropole de l'import.
    """

    attributes: Mapping[str, str]
    geometry: Mapping[str, Any] | None

    def get(self, name: str) -> str:
        return self.attributes.get(name.lower(), "")


@dataclass(frozen=True, slots=True)
class LayerMembers:
    """Les fichiers d'une couche dans l'archive, par extension."""

    layer: str
    files: dict[str, str]

    @property
    def has_geometry(self) -> bool:
        return ".shp" in self.files


def find_layers(archive: zipfile.ZipFile) -> dict[str, LayerMembers]:
    """Reconnaître les couches de l'archive, quelle que soit la convention de nommage."""
    found: dict[str, dict[str, str]] = {}
    for member in archive.namelist():
        base = member.rsplit("/", 1)[-1].lower()
        suffix = "." + base.rsplit(".", 1)[-1] if "." in base else ""
        if suffix not in SHAPEFILE_SUFFIXES:
            continue
        for layer in LAYERS:
            # Le nom de couche, eventuellement precede d'un prefixe et suivi d'une date, elle
            # meme eventuellement suivie d'une lettre de version de procedure. Trois formes
            # observees sur des documents reels du 35 :
            #
            #   ZONE_URBA.shp                              PLU communal, norme ancienne
            #   243500139_zone_urba_20251218.shp           PLUi Rennes Metropole
            #   200070688_DOC_URBA_20250930_A.dbf          PLUi Couesnon, version A
            #
            # La troisieme a fait disparaitre Couesnon Marches de Bretagne et ses huit communes
            # du premier manifeste, sans aucune erreur : l'archive semblait ne contenir aucune
            # couche. Un import qui n'accepte pas une variante perd le document en silence.
            if re.search(rf"(^|[_\W]){layer}(_\d{{8}})?(_[A-Za-z0-9]{{1,3}})?\{suffix}$", base):
                found.setdefault(layer, {})[suffix] = member
                break
    return {layer: LayerMembers(layer, files) for layer, files in found.items()}


def read_features(archive: zipfile.ZipFile, members: LayerMembers) -> Iterator[Feature]:
    """Parcourir une couche, attributs normalisés et géométrie au format GeoJSON.

    Les membres sont lus en mémoire : une couche CNIG pèse quelques mégaoctets au plus, et
    `shapefile.Reader` a besoin du `.shx` pour indexer les géométries.
    """
    dbf = members.files.get(".dbf")
    if dbf is None:
        return
    parts: dict[str, io.BytesIO] = {"dbf": io.BytesIO(archive.read(dbf))}
    if members.has_geometry:
        parts["shp"] = io.BytesIO(archive.read(members.files[".shp"]))
        if ".shx" in members.files:
            parts["shx"] = io.BytesIO(archive.read(members.files[".shx"]))
    # L'encodage des attributs DBF est declare par le `.cpg`, et ce fichier manque sur une partie
    # des documents : cinq des 88 premiers imports du 35 ont echoue sur un octet 0xe9, c'est-a-dire
    # un « é » en Latin-1. `pyshp` suppose UTF-8 par defaut et leve.
    #
    # A defaut de declaration, on essaie UTF-8 puis on retombe sur Latin-1, qui est l'encodage
    # historique des shapefiles et ne peut pas echouer — au pire il produit des caracteres faux,
    # la ou UTF-8 perdrait le document entier. Un libelle mal accentue reste lisible ; un document
    # absent ne l'est pas.
    declared = _declared_encoding(archive, members)
    reader = cast(Any, shapefile.Reader(**parts, encoding=declared, encodingErrors="replace"))

    if not members.has_geometry:
        for record in cast(Iterator[Any], reader.iterRecords()):
            yield Feature(attributes=_attributes(record), geometry=None)
        return

    # Acces **par index** et non par parcours sequentiel. Les deux ne sont pas equivalents :
    # `iterShapeRecords` lit le `.shp` d'un bout a l'autre et s'arrete au premier en-tete
    # d'enregistrement corrompu, quand l'acces indexe passe par le `.shx`, qui existe
    # precisement pour cela.
    #
    # Observe sur `DU_35136` : ses 309 geometries sont toutes lisibles une a une, et le parcours
    # sequentiel echoue sur un `KeyError` negatif — un octet de padding lu comme un type de
    # forme. Le document entier etait perdu pour un defaut d'alignement.
    #
    # Un enregistrement illisible est compte et saute ; il ne fait pas perdre la couche.
    for index in range(len(reader)):
        try:
            geometry = reader.shape(index).__geo_interface__
            record = reader.record(index)
        except Exception:
            continue
        yield Feature(
            attributes=_attributes(record),
            geometry=cast("Mapping[str, Any]", geometry),
        )


def _declared_encoding(archive: zipfile.ZipFile, members: LayerMembers) -> str:
    """L'encodage déclaré par le `.cpg`, ou Latin-1 à défaut.

    Latin-1 plutôt qu'UTF-8 comme repli : il décode n'importe quel octet sans lever, là où UTF-8
    échoue sur un accent Latin-1 et fait perdre le document entier.
    """
    cpg = members.files.get(".cpg")
    if cpg is None:
        return "latin-1"
    label = archive.read(cpg).decode("ascii", errors="ignore").strip().lower()
    if "utf" in label:
        return "utf-8"
    return "latin-1"


def _attributes(record: Any) -> dict[str, str]:
    """Normaliser les noms de champs et nettoyer les valeurs.

    Deux raisons, toutes deux observées sur des documents réels : la casse des noms varie d'une
    génération de norme à l'autre, et les attributs DBF sont à largeur fixe, donc complétés
    d'espaces.
    """
    raw = cast("dict[str, object]", record.as_dict())
    return {
        str(key).lower(): "" if value is None else str(value).strip() for key, value in raw.items()
    }
