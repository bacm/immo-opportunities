#!/usr/bin/env python3
"""Épingler une release DS-07 : constituer l'extrait DPE, l'archiver, le checksumer — D4.

## Pourquoi un extrait, et pas un fichier du producteur

L'ADEME ne publie aucun fichier daté téléchargeable pour les DPE : la seule voie d'accès est
l'API `data-fair` de `data.ademe.fr`, dont le contenu change à chaque mise à jour du dépôt.
Le contrat DS-07 l'a prévu — `key_format: YYYY-MM-DD-extract`, `preferred_format: CSV/API extract
archived before import`.

La conséquence est que **l'URL n'est pas un chemin de retour** : la rejouer demain donnerait
d'autres octets. C'est l'archive MinIO nommée au manifeste qui fait foi, et le SHA-256 relevé ici
qui la contraint. `resolve_asset` la trouvera avant de songer à l'amont.

## Ce que l'extrait contient

**Toutes les colonnes de la source**, sans projection. Le contrat dit `additional_properties:
preserve` et un extrait est le seul objet réplicable : y choisir des colonnes aujourd'hui
obligerait à ré-épingler pour en ajouter une demain, sur une source qui aura changé entre-temps
— donc à perdre la comparaison entre millésimes. 226 colonnes, environ 370 Mo, 85 Mo compressés.

L'import, lui, ne persiste qu'un sous-ensemble déclaré : voir `import_dpe_release.py`.

## Le filtre des DPE désactivés est en amont, et nous ne pouvons pas le lever

Le jeu accessible est une **vue virtuelle** filtrée sur `dpe_desactive = 0` par l'ADEME. Le jeu
sous-jacent, qui porte les diagnostics désactivés, répond 403. Nous ne voyons donc jamais un DPE
annulé, et le manifeste le dit plutôt que de laisser croire à une couverture complète.
"""

import argparse
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings

DATASET = "dpe03existant"
API = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET}/lines"
USER_AGENT = "ImmoOpportunitiesDataPipeline/0.1 (+https://github.com/)"

# La page maximale acceptee par data-fair. Une page de 10 000 lignes pese 16 Mo et demande une
# trentaine de secondes ; un departement en compte vingt-quatre.
PAGE_SIZE = 10000

# Un echec passager ne dit rien de la source : il dit que le reseau a lache. Voir
# ARCHITECTURE.md §10.6 — on temporise devant un service public plutot que d'abandonner le lot.
ATTEMPTS = 5
BACKOFF_SECONDS = 5


def _request(url: str) -> tuple[bytes, dict[str, str]]:
    last: Exception | None = None
    for attempt in range(ATTEMPTS):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=300) as response:
                # Les en-tetes HTTP sont insensibles a la casse, un `dict` ne l'est pas : la
                # normalisation evite qu'un `Last-Modified` capitalise fasse silencieusement
                # tomber la date de publication dans son repli.
                return response.read(), {
                    name.lower(): value for name, value in response.headers.items()
                }
        except Exception as error:
            last = error
            delay = BACKOFF_SECONDS * (attempt + 1)
            print(f"  échec passager ({error}), reprise dans {delay} s", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"{ATTEMPTS} tentatives échouées sur {url}") from last


def _next_link(headers: dict[str, str]) -> str | None:
    """L'URL de la page suivante, que data-fair porte dans l'en-tête `Link` en sortie CSV.

    Le corps CSV ne peut pas la porter — c'est du texte tabulaire — et le curseur `after` de
    data-fair n'est pas reconstructible depuis les colonnes exportées : `_i`, sur lequel il
    porte, n'est pas une colonne du jeu. Suivre l'en-tête est donc la seule pagination stable.
    """
    link = headers.get("link")
    if not link:
        return None
    for part in link.split(","):
        target, _, relation = part.partition(";")
        if relation.strip() == "rel=next":
            return target.strip().strip("<>")
    return None


def _strip_header(payload: bytes) -> bytes:
    """Retirer la ligne d'en-tête d'une page de rang deux ou plus.

    Sans risque pour un CSV dont les champs contiennent des retours à la ligne — les descriptions
    d'installation en contiennent — parce que l'en-tête, lui, n'en contient pas : le premier
    `\\n` du flux termine donc bien l'en-tête et rien d'autre.
    """
    cut = payload.find(b"\n")
    return payload[cut + 1 :] if cut >= 0 else b""


def download_extract(department: str, destination: Path) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "format": "csv",
            "size": PAGE_SIZE,
            "qs": f"code_departement_ban:{department}",
            # Tri stable : le curseur `after` de data-fair porte sur la cle de tri, et un tri
            # par pertinence ferait reapparaitre ou disparaitre des lignes entre deux pages.
            "sort": "_i",
        }
    )
    url: str | None = f"{API}?{query}"
    pages = 0
    raw_bytes = 0
    header: bytes = b""
    last_modified: str | None = None
    # `mtime=0` : le gzip doit dependre des seules donnees, sans quoi deux epinglages du meme
    # contenu auraient deux empreintes differentes.
    with (
        destination.open("wb") as handle,
        gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as archive,
    ):
        while url:
            payload, headers = _request(url)
            last_modified = headers.get("last-modified") or last_modified
            # Le BOM ouvre chaque page ; le conserver au milieu du fichier casserait la
            # lecture de la colonne suivante.
            payload = payload.removeprefix("﻿".encode())
            if pages == 0:
                header = payload[: payload.find(b"\n")]
            else:
                payload = _strip_header(payload)
            if not payload.strip():
                break
            raw_bytes += len(payload)
            archive.write(payload)
            pages += 1
            print(f"  page {pages} : {raw_bytes / 1e6:.0f} Mo cumulés", flush=True)
            url = _next_link(headers)
    digest = hashlib.sha256()
    with destination.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    columns = next(csv.reader([header.decode("utf-8")]), [])
    return {
        "sha256": digest.hexdigest(),
        "byte_size": destination.stat().st_size,
        "uncompressed_byte_size": raw_bytes + len(header) + 1,
        "pages": pages,
        "column_count": len(columns),
        "source_last_modified": last_modified,
    }


def object_key(release: str, department: str) -> str:
    return f"ds-07/{release}/{department}/assessments.csv.gz"


def manifest(
    release: str, department: str, extract: dict[str, Any], published_on: str
) -> dict[str, Any]:
    return {
        "release_id": f"DS-07@{release}",
        "release_key": release,
        "source_published_on": published_on,
        "department": department,
        "contract_version": 1,
        "key_derivation": (
            "Date de constitution de l'extrait. L'ADEME ne publie pas d'édition datée des DPE : "
            "la clé identifie les octets relevés ce jour-là via l'API, pas une édition amont. "
            "`source_published_on` reprend le `last-modified` annoncé par l'API pour le jeu."
        ),
        "discovery": {
            "catalog_entry": f"https://data.ademe.fr/datasets/{DATASET}",
            "api_is_not_a_path_back": (
                "L'URL rejouée demain rendrait d'autres octets : le jeu est mis à jour en "
                "continu. Seule l'archive nommée ci-dessous permet de retrouver les octets "
                "importés, et le SHA-256 la contraint."
            ),
            "upstream_filter": (
                "Le jeu accessible est une vue virtuelle filtrée par l'ADEME sur "
                "`dpe_desactive = 0`. Le jeu sous-jacent, qui porte les diagnostics désactivés, "
                "répond 403. Un DPE annulé n'est donc jamais observable ici : l'exclusion est "
                "celle du producteur, pas la nôtre."
            ),
            "projection": (
                "Aucune : les 226 colonnes de la source sont archivées. Le contrat demande "
                "`additional_properties: preserve`, et un extrait ne se ré-épingle pas à "
                "l'identique."
            ),
        },
        "assets": [
            {
                "layer": "assessments",
                "url": f"{API}?format=csv&qs=code_departement_ban%3A{department}&sort=_i",
                "sha256": extract["sha256"],
                "byte_size": extract["byte_size"],
                "media_type": "text/csv",
                "content_encoding": "gzip",
                "archive": {"object_key": object_key(release, department)},
                "extract": {
                    "pages": extract["pages"],
                    "page_size": PAGE_SIZE,
                    "column_count": extract["column_count"],
                    "uncompressed_byte_size": extract["uncompressed_byte_size"],
                },
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pin one ADEME DPE department extract")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--release", required=True, help="clé de release, par exemple 2026-09-14")
    arguments = parser.parse_args()

    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "datasets"
        / "DS-07"
        / "releases"
        / f"{arguments.release}-{arguments.department}.json"
    )
    with tempfile.TemporaryDirectory(prefix="immo-dpe-pin-") as temporary:
        local = Path(temporary) / "assessments.csv.gz"
        print(f"DS-07 {arguments.department} : constitution de l'extrait", flush=True)
        extract = download_extract(arguments.department, local)
        key = object_key(arguments.release, arguments.department)
        object_store.put_file(
            local,
            key,
            {
                "content-type": "text/csv",
                "x-amz-meta-sha256": extract["sha256"],
                "x-amz-meta-release": f"DS-07@{arguments.release}",
            },
        )
        print(f"archivé sous {key}", flush=True)
        stamp = extract["source_last_modified"]
        if not stamp:
            # Sans date de publication amont, le manifeste ne dirait pas de quand datent les
            # octets : mieux vaut echouer que d'ecrire la cle d'epinglage a sa place.
            raise SystemExit("L'API n'a pas renvoyé de `last-modified` : release non datable.")
        published_on = parsedate_to_datetime(stamp).date().isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                manifest(arguments.release, arguments.department, extract, published_on),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        f"{extract['pages']} pages, {extract['byte_size'] / 1e6:.0f} Mo compressés, "
        f"sha256 {extract['sha256'][:12]}… → {path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
