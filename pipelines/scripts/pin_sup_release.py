#!/usr/bin/env python3
"""Épingler la famille `sup` de DS-09 : les servitudes d'utilité publique — D3.

## Pourquoi les servitudes sont ici et non dans D2

Une SUP n'est pas un document d'urbanisme. Un PLU **exprime un projet communal** ; une SUP
**constate une contrainte extérieure** — un périmètre de captage, une canalisation, un monument,
une servitude aéronautique — qui s'impose au document sans en dépendre.

C'est la nature même de ce que D3 traite : une contrainte subie, rattachée à un objet
géographique, avec sa granularité propre. Les ranger avec les PLU aurait mélangé un projet et une
contrainte dans la même table, et rendu `URB-005` — la complétude des règles d'urbanisme —
dépendante d'objets qui n'ont aucune règle à valider.

La source, elle, reste le Géoportail de l'urbanisme, et la machinerie est celle que D2 a écrite :
`market_data.cnig` et `market_data.remote_zip`. Effet secondaire heureux, pas raison du choix.

## Une seule release, neuf catégories

`PM1` (risques naturels) et `AC1` (monuments historiques) n'ont rien de commun sinon d'être
subies. La catégorie voyage donc **sur chaque observation** — `risk_type = sup_PM1` — comme les
six types de risque de `gaspar-risks` voyagent dans leur propre release. Une release par document
aurait multiplié les verdicts sans rien distinguer de plus.

## `PM1` est le seul zonage inondation opposable du 35

Les endpoints GASPAR ne donnent que le fait communal — « la commune est concernée ». L'assiette
d'une PM1 est une géométrie de zone. C'est la différence entre les deux affirmations que le
ticket interdit de confondre.
"""

import argparse
import gzip
import hashlib
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, cast

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.cnig import find_layers, read_features
from immo_pipelines.market_data.georisques import commune_shapes, family, split_by_commune
from immo_pipelines.market_data.remote_zip import open_remote

GPU = "https://www.geoportail-urbanisme.gouv.fr/api"
# `ASSIETTE_SUP_S` porte le perimetre opposable ; `GENERATEUR_SUP_S` porte l'objet qui le genere
# — la canalisation, le monument. C'est l'assiette qui s'impose a la parcelle.
SUP_LAYERS = ("assiette_sup_s",)


def documents(department: str) -> list[dict[str, Any]]:
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode(
        {"documentFamily[]": "SUP", "territory": department, "status": "document.production"},
        doseq=True,
    )
    request = urllib.request.Request(
        f"{GPU}/document?{query}&limit=1000", headers={"User-Agent": "ImmoOpportunities/0.1"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = cast(list[dict[str, Any]], json.load(response))
    return [item for item in payload if isinstance(item, dict)]


def category_of(name: str) -> str:
    """La catégorie CNIG, lue dans le nom normalisé `<siren>_SUP_<dept>_<CAT>`."""
    parts = name.split("_")
    return parts[-1] if len(parts) >= 4 else "inconnue"


# Un 403 du GPU n'est pas toujours un refus : sur le 35, `552049447_SUP_35_T1` a echoue une fois
# puis repondu a la tentative suivante, quand les trois documents du SIREN 120064019 le refusent
# systematiquement. Sans reprise, un refus passager retire un document du manifeste et personne
# n'y revient — la couverture retrecit en silence. Voir ARCHITECTURE.md §10.6.
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_BACKOFF_SECONDS = 8


def assiettes(document: dict[str, Any]) -> tuple[list[dict[str, Any]], str, int]:
    """Les assiettes d'un document, avec l'empreinte de la couche qui les porte.

    L'empreinte est celle de la **couche**, pas de l'archive : même arbitrage que D2 — l'archive
    change dès qu'une pièce écrite est remplacée, la couche ne change que si les périmètres
    bougent.
    """
    last: Exception | None = None
    archive: zipfile.ZipFile | None = None
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            archive = zipfile.ZipFile(open_remote(f"{GPU}/document/{document['id']}/download"))
            break
        except Exception as error:
            last = error
            if attempt + 1 < DOWNLOAD_ATTEMPTS:
                time.sleep(DOWNLOAD_BACKOFF_SECONDS * (attempt + 1))
    if archive is None:
        raise RuntimeError(f"{DOWNLOAD_ATTEMPTS} tentatives échouées : {last}") from last
    layers = find_layers(archive, SUP_LAYERS)
    members = layers.get("assiette_sup_s")
    if members is None:
        return [], "", 0
    payload = b"".join(archive.read(members.files[suffix]) for suffix in sorted(members.files))
    digest = hashlib.sha256(payload).hexdigest()
    category = category_of(str(document.get("name") or ""))
    features: list[dict[str, Any]] = []
    for index, feature in enumerate(read_features(archive, members)):
        if feature.geometry is None:
            continue
        features.append(
            {
                "source_identifier": f"{document['id']}:{index}",
                "category": category,
                "document": str(document.get("name")),
                "idass": feature.attributes.get("idass"),
                "nom_assiette": feature.attributes.get("nomass"),
                "type_assiette": feature.attributes.get("typeass"),
                "geom": feature.geometry,
            }
        )
    return features, digest, len(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--release", required=True, help="date d'épinglage, par exemple 2026-09-14")
    arguments = parser.parse_args()

    item = family("sup")
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )

    features: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    unreadable: list[dict[str, Any]] = []
    for document in documents(arguments.department):
        name = str(document.get("name"))
        try:
            found, digest, size = assiettes(document)
        except Exception as error:
            unreadable.append({"document": name, "reason": str(error)})
            print(f"  {name} : illisible ({error})", flush=True)
            continue
        if not found:
            # Un document annonce sans assiette n'est pas une erreur passagere : c'est une
            # couverture partielle, et la taire ferait passer le manifeste pour complet.
            unreadable.append({"document": name, "reason": "aucune couche `assiette_sup_s`"})
            print(f"  {name} : aucune assiette", flush=True)
            continue
        features.extend(found)
        sources.append(
            {
                "document": name,
                "document_id": document.get("id"),
                "category": category_of(name),
                "legal_status": document.get("legalStatus"),
                "published_at": document.get("publicationDate"),
                "layer_sha256": digest,
                "layer_byte_size": size,
                "assiettes": len(found),
            }
        )
        print(f"  {name:28s} {category_of(name):5s} {len(found):4d} assiettes", flush=True)

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        codes, shapes = commune_shapes(connection, arguments.department)
    records = split_by_commune(features, codes, shapes, label="DS-09 sup")
    payload = json.dumps(
        sorted(records, key=lambda record: str(record["source_identifier"])),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")

    release_key = f"{item.key}--{arguments.release}"
    key = f"ds-09/{item.key}/{release_key}/{arguments.department}/observations.json.gz"
    with tempfile.TemporaryDirectory(prefix="immo-sup-") as temporary:
        local = Path(temporary) / "observations.json.gz"
        with (
            local.open("wb") as handle,
            gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as compressed,
        ):
            compressed.write(payload)
        digest = hashlib.sha256(local.read_bytes()).hexdigest()
        object_store.put_file(
            local,
            key,
            {
                "content-type": "application/json",
                "x-amz-meta-sha256": digest,
                "x-amz-meta-release": f"DS-09@{release_key}",
            },
        )
        asset = {
            "layer": "observations",
            "url": f"{GPU}/document?documentFamily[]=SUP&territory={arguments.department}",
            "sha256": digest,
            "byte_size": local.stat().st_size,
            "media_type": "application/json",
            "content_encoding": "gzip",
            "archive": {"object_key": key},
            "extract": {
                "records": len(records),
                "source_features": len(features),
                "documents": sources,
                "uncompressed_byte_size": len(payload),
            },
        }
    path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "datasets"
        / "DS-09"
        / "releases"
        / f"{release_key}-{arguments.department}.json"
    )
    path.write_text(
        json.dumps(
            {
                "release_id": f"DS-09@{release_key}",
                "release_key": release_key,
                "source_published_on": arguments.release,
                "department": arguments.department,
                "contract_version": 1,
                "risk_family": item.key,
                "key_derivation": (
                    "Date d'épinglage du catalogue. Chaque servitude a sa propre date "
                    "d'approbation, portée par son nom normalisé ; la clé identifie "
                    "l'instantané du catalogue à cette date."
                ),
                "discovery": {
                    "catalog_entry": f"{GPU}/document",
                    "access_mode": "download",
                    "granularity": item.granularity,
                    "checksum_scope": (
                        "Une empreinte par couche `ASSIETTE_SUP_S`, pas par archive : l'archive "
                        "change dès qu'une pièce écrite est remplacée, la couche ne change que "
                        "si les périmètres bougent. Même arbitrage que D2."
                    ),
                    "why_here_and_not_d2": (
                        "Une SUP constate une contrainte extérieure ; un PLU exprime un projet "
                        "communal. Les ranger ensemble aurait rendu `URB-005` dépendante "
                        "d'objets sans règle à valider."
                    ),
                },
                "assets": [asset],
                # Les documents annonces que nous ne savons pas lire. Les taire ferait passer une
                # couverture partielle pour complete.
                "unreadable": unreadable,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(records)} observations, {len(sources)} documents, sha256 {digest[:12]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
