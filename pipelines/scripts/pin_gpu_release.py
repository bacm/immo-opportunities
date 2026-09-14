#!/usr/bin/env python3
"""Épingler une release DS-08 : relever les empreintes sans rapatrier les archives — D2.

Le manifeste porte, pour chaque document, l'empreinte de **chaque couche structurée** plutôt que
celle de l'archive entière. Deux raisons.

**Le volume.** Une archive CNIG pèse 33 Mo pour un PLU communal et jusqu'à 4,6 Go pour un PLUi,
dont environ 1,7 Mo de couches utiles ; le reste est du PDF que D2 n'a pas le droit d'interpréter.
Archiver ce qu'on n'importe pas coûterait 430 Go à l'échelle nationale pour rien.

**La précision.** L'empreinte d'une archive change dès qu'une pièce écrite est remplacée, même si
les zones n'ont pas bougé. Une empreinte par couche dit ce qui a réellement changé, et permet de
ne réimporter que cela.

L'empreinte de l'archive complète est relevée aussi, pour la provenance — c'est elle qui identifie
les octets du producteur — mais elle ne conditionne pas l'import.

Les archives ne sont jamais téléchargées : le répertoire central d'un ZIP étant à sa fin, on lit
la queue du fichier puis les seuls membres voulus. Voir `immo_pipelines.market_data.remote_zip`.
"""

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from immo_pipelines.market_data.cnig import find_layers, read_features
from immo_pipelines.market_data.remote_zip import USER_AGENT, open_remote

API = "https://www.geoportail-urbanisme.gouv.fr/api"

# Familles retenues : les documents d'urbanisme opposables. Les servitudes (SUP) relevent de
# DS-09 et les schemas de coherence territoriale (SCoT) ne s'appliquent pas a la parcelle.
DOCUMENT_TYPES = ("PLU", "PLUi", "CC", "POS", "PSMV")


def _get(path: str, **params: Any) -> Any:
    query = urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(f"{API}/{path}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def documents_for(department: str) -> list[dict[str, Any]]:
    """Les documents communaux du département, puis les intercommunaux qui le couvrent.

    Les deux requêtes sont nécessaires et ne se remplacent pas : un PLUi porte le **SIREN de
    l'EPCI** comme code de territoire, jamais un code départemental. `territory=35` ne le retourne
    donc pas, et `territory=<code commune>` ne retourne rien du tout — le filtre porte sur le
    territoire du document, pas sur les communes qu'il couvre.

    Le PLUi de Rennes Métropole, 43 communes, est invisible de la première requête.
    """
    communaux = [
        doc
        for doc in _get(
            "document",
            **{"documentFamily[]": "DU", "territory": department, "status": "document.production"},
            limit=1000,
        )
        if isinstance(doc, dict)
    ]
    intercommunaux = [
        doc
        for doc in _get(
            "document",
            **{"documentType[]": "PLUi"},
            status="document.production",
            limit=1000,
        )
        if isinstance(doc, dict)
    ]
    return communaux + intercommunaux


def covers(document: dict[str, Any], department: str, bounds: tuple[float, ...]) -> list[str]:
    """Les communes du département couvertes par ce document, lues dans `DOC_URBA_COM`.

    La `bbox` du catalogue sert de **pré-filtre** et jamais de critère : sur les 23 PLUi dont
    l'emprise touche le 35, dix-sept n'y ont aucune commune, et l'un d'eux — « PLUI DE
    PUISAYE-FORTERRE », dans l'Yonne — a manifestement une `bbox` fausse. Seule la couche
    `DOC_URBA_COM` fait foi.
    """
    box = document.get("bbox")
    if isinstance(box, list) and len(box) == 4:
        xmin, ymin, xmax, ymax = box
        if xmax < bounds[0] or xmin > bounds[2] or ymax < bounds[1] or ymin > bounds[3]:
            return []
    archive = zipfile.ZipFile(open_remote(f"{API}/document/{document['id']}/download"))
    layers = find_layers(archive)
    if "doc_urba_com" not in layers:
        return []
    communes = {feature.get("insee") for feature in read_features(archive, layers["doc_urba_com"])}
    return sorted(code for code in communes if code.startswith(department))


def layer_digests(document_id: str) -> tuple[dict[str, dict[str, Any]], int]:
    """L'empreinte et la taille de chaque couche structurée, sans télécharger l'archive."""
    remote = open_remote(f"{API}/document/{document_id}/download")
    archive = zipfile.ZipFile(remote)
    digests: dict[str, dict[str, Any]] = {}
    for name, members in sorted(find_layers(archive).items()):
        payload = b"".join(archive.read(members.files[suffix]) for suffix in sorted(members.files))
        digests[name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byte_size": len(payload),
            "members": sorted(members.files.values()),
        }
    return digests, getattr(remote, "size", 0)


def manifest(
    arguments: argparse.Namespace,
    assets: list[dict[str, Any]],
    unreadable: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "release_id": f"DS-08@{arguments.release}",
        "release_key": arguments.release,
        "source_published_on": arguments.release,
        "department": arguments.department,
        "contract_version": 1,
        "key_derivation": (
            "Date d'épinglage. Le GPU ne publie pas de millésime : chaque document a sa propre "
            "date d'approbation, portée par IDURBA, et la clé identifie l'instantané du "
            "catalogue à cette date."
        ),
        "discovery": {
            "catalog_entry": f"{API}/document",
            "checksum_scope": (
                "Une empreinte par couche structurée, pas par archive. L'archive pèse 33 Mo à "
                "4,6 Go pour environ 1,7 Mo de couches utiles, et son empreinte change dès qu'une "
                "pièce écrite est remplacée même si les zones n'ont pas bougé."
            ),
            "written_pieces": (
                "Les règlements, PADD et orientations ne sont ni lus ni archivés ici : leur "
                "interprétation est interdite dans D2 et relève de D2b."
            ),
        },
        "assets": assets,
        # Les documents que le catalogue annonce et que nous ne savons pas lire. Les taire ferait
        # passer une couverture partielle pour une couverture complète.
        "unreadable": unreadable,
    }


def write(path: Path, document: dict[str, Any]) -> None:
    """Écrire le manifeste à chaque document relevé, et non à la fin.

    Un épinglage départemental demande une heure et dépend du réseau : un délai dépassé ne doit
    pas effacer ce qui est déjà relevé. L'écriture passe par un fichier temporaire puis un
    remplacement atomique, sans quoi une interruption au mauvais moment laisserait un manifeste
    tronqué — donc un manifeste qui ment sur la couverture.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.partial")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--release", required=True, help="clé de release, par exemple 2026-09-14")
    parser.add_argument("--bounds", default="-2.4,47.5,-0.9,48.9", help="pré-filtre lon/lat")
    arguments = parser.parse_args()
    bounds = tuple(float(value) for value in arguments.bounds.split(","))

    path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "datasets"
        / "DS-08"
        / "releases"
        / f"{arguments.release}-{arguments.department}.json"
    )
    # Reprise. Un epinglage de 182 documents demande une heure et depend du reseau : un delai
    # depasse ne doit pas effacer ce qui est deja releve. Sur la France et ses 12 795 documents,
    # repartir de zero a chaque interruption serait redhibitoire.
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    assets: list[dict[str, Any]] = list(previous.get("assets", []))
    unreadable: list[dict[str, Any]] = list(previous.get("unreadable", []))
    done = {asset["document_id"] for asset in assets} | {
        entry.get("document_id") for entry in unreadable
    }
    if done:
        print(f"reprise : {len(done)} documents déjà relevés", flush=True)
    for document in documents_for(arguments.department):
        if document.get("type") not in DOCUMENT_TYPES or document["id"] in done:
            continue
        try:
            communes = covers(document, arguments.department, bounds)
        except Exception as error:
            unreadable.append(
                {
                    "document_id": document["id"],
                    "name": document.get("name"),
                    "reason": str(error),
                }
            )
            write(path, manifest(arguments, assets, unreadable))
            print(f"  {document.get('name')} : illisible ({error})", flush=True)
            continue
        if not communes:
            continue
        digests, archive_size = layer_digests(document["id"])
        assets.append(
            {
                "document_id": document["id"],
                "name": document.get("name"),
                "document_type": document.get("type"),
                "legal_status": document.get("legalStatus"),
                "published_at": document.get("publicationDate"),
                "territory": (document.get("grid") or {}).get("name"),
                "communes": communes,
                "url": f"{API}/document/{document['id']}/download",
                "archive_byte_size": archive_size,
                "layers": digests,
            }
        )
        write(path, manifest(arguments, assets, unreadable))
        print(
            f"  {document.get('name'):18s} {len(communes):3d} communes, {len(digests)} couches",
            flush=True,
        )

    write(path, manifest(arguments, assets, unreadable))
    communes = {code for asset in assets for code in asset["communes"]}
    print(f"\n{len(assets)} documents, {len(communes)} communes couvertes → {path}")
    if unreadable:
        print(f"{len(unreadable)} document(s) illisible(s), consignés au manifeste")
    return 0


if __name__ == "__main__":
    sys.exit(main())
