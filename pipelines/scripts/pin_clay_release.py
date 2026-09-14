#!/usr/bin/env python3
"""Épingler la famille `clay` de DS-09 : la couche nationale d'exposition aux argiles — D3.

## Un téléchargement, pas une API — et le contrat le préfère

Le contrat DS-09 dit `preferred_format: versioned download`. Les argiles sont la seule famille qui
en a un : `files.georisques.fr/argiles/AleaRG_Fxx_L93.zip`, **623 Mo**, une unique couche
nationale `ExpoArgile_Fxx_L93` de 122 222 polygones et 823 Mo décompressés.

L'URL ne porte pas de marqueur de version. Son `Last-Modified` est le 16 juin 2021 et le
producteur distingue explicitement une version 2020 d'une version 2026 : ce n'est pas un alias
mouvant en pratique, et l'empreinte du fichier national est relevée ici pour qu'un changement se
constate au lieu de passer.

## Ce qui est archivé n'est pas ce qui est téléchargé

Archiver 623 Mo de couche nationale pour 789 polygones bretons serait la faute que D2 a refusée
sur les archives CNIG. On archive **l'extrait départemental**, avec sa propre empreinte, et le
manifeste porte en plus celle du fichier national pour la provenance.

La sélection ne se devine pas : la couche porte un champ `DPT`. Aucun filtre géométrique n'est
nécessaire, et aucun n'est appliqué.

## Le découpage par commune est fait ici, et il ne crée pas de précision

`risk_observation.commune_code` est obligatoire, et un polygone d'aléa traverse les communes. Il
est donc **découpé** par commune : chaque observation porte l'intersection réelle, pas le polygone
entier réattribué à une commune arbitraire. Découper une zone est exact ; lui inventer une
commune ne le serait pas.
"""

import argparse
import gzip
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, cast

import psycopg
import shapefile  # type: ignore[import-untyped]

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.georisques import commune_shapes, family, split_by_commune

NATIONAL_URL = "https://files.georisques.fr/argiles/AleaRG_Fxx_L93.zip"
LAYER = "ExpoArgile_Fxx_L93"
# La couche est en Lambert 93, comme son nom l'indique et comme son `.prj` le declare.
SOURCE_SRID = 2154


def digest_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def department_features(archive: Path, department: str) -> list[dict[str, Any]]:
    """Les polygones du département, lus en flux : la couche nationale ne tient pas en mémoire."""
    with zipfile.ZipFile(archive) as bundle, tempfile.TemporaryDirectory() as temporary:
        for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            member = f"{LAYER}{suffix}"
            if member in bundle.namelist():
                (Path(temporary) / member).write_bytes(bundle.read(member))
        reader = cast(
            Any,
            shapefile.Reader(
                str(Path(temporary) / LAYER), encoding="latin-1", encodingErrors="replace"
            ),
        )
        kept: list[dict[str, Any]] = []
        for index, item in enumerate(cast(Any, reader.iterShapeRecords())):
            record = list(item.record)
            if str(record[0]).strip() != department:
                continue
            kept.append(
                {
                    "source_identifier": str(index),
                    "dpt": str(record[0]).strip(),
                    "niveau": float(record[1]),
                    "alea": str(record[2]).strip(),
                    "geom": item.shape.__geo_interface__,
                }
            )
    return kept


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--release", required=True, help="date d'épinglage, par exemple 2026-09-14")
    parser.add_argument("--archive", type=Path, required=True, help="le ZIP national déjà obtenu")
    arguments = parser.parse_args()

    item = family("clay")
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    national_digest = digest_of(arguments.archive)
    print(f"archive nationale : sha256 {national_digest[:12]}…", flush=True)

    features = department_features(arguments.archive, arguments.department)
    print(f"{len(features)} polygones sur le {arguments.department}", flush=True)

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        codes, shapes = commune_shapes(connection, arguments.department)
    records = split_by_commune(features, codes, shapes, label="DS-09 clay")
    payload = json.dumps(
        sorted(records, key=lambda record: str(record["source_identifier"])),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")

    release_key = f"{item.key}--{arguments.release}"
    key = f"ds-09/{item.key}/{release_key}/{arguments.department}/observations.json.gz"
    with tempfile.TemporaryDirectory(prefix="immo-clay-") as temporary:
        local = Path(temporary) / "observations.json.gz"
        with (
            local.open("wb") as handle,
            gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as compressed,
        ):
            compressed.write(payload)
        digest = digest_of(local)
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
            "url": NATIONAL_URL,
            "sha256": digest,
            "byte_size": local.stat().st_size,
            "media_type": "application/json",
            "content_encoding": "gzip",
            "archive": {"object_key": key},
            "extract": {
                "records": len(records),
                "source_features": len(features),
                "uncompressed_byte_size": len(payload),
                "national_archive_sha256": national_digest,
                "national_archive_url": NATIONAL_URL,
                "source_layer": LAYER,
                "source_srid": SOURCE_SRID,
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
                    "Date d'épinglage de l'extrait départemental. Le fichier national ne porte "
                    "pas de version dans son URL ; son empreinte et son `Last-Modified` — "
                    "16 juin 2021 — sont relevés pour qu'un changement se constate."
                ),
                "discovery": {
                    "catalog_entry": (
                        "https://www.georisques.gouv.fr/donnees/bases-de-donnees/"
                        "retrait-gonflement-des-argiles-version-2020"
                    ),
                    "access_mode": "download",
                    "granularity": item.granularity,
                    "extract_rationale": (
                        "623 Mo nationaux pour 789 polygones départementaux : on archive "
                        "l'extrait, pas la couche entière, et le manifeste porte l'empreinte du "
                        "fichier national pour la provenance. Même arbitrage que D2 sur les "
                        "archives CNIG."
                    ),
                    "selection": (
                        "Champ `DPT` de la couche. Aucun filtre géométrique n'est nécessaire, et "
                        "aucun n'est appliqué."
                    ),
                    "commune_split": (
                        "Un polygone d'aléa traverse les communes ; il est découpé par "
                        "intersection réelle. Les contacts réduits à une ligne ou un point sont "
                        "écartés : un contact de frontière n'est pas une exposition."
                    ),
                },
                "assets": [asset],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(records)} observations, sha256 {digest[:12]}… → {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
