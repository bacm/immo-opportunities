#!/usr/bin/env python3
"""Épingler une famille de risque DS-09 : constituer la réponse, l'archiver, la checksumer — D3.

## Pourquoi une réponse d'API archivée, et non un téléchargement

Le contrat DS-09 dit `preferred_format: versioned download; archived API response only when no
download exists`. L'inventaire écrit avant le premier lot —
`docs/data/georisques-source-inventory-35.md` — a établi qu'aucun téléchargement daté par famille
et par département n'existe. C'est donc le
second cas du contrat qui s'applique, pour les huit familles servies par l'API.

La conséquence est la même que pour DS-07 : **l'URL n'est pas un chemin de retour**, la rejouer
demain rendrait d'autres octets. C'est l'archive MinIO nommée au manifeste qui fait foi.

## Une famille est une release

Elles n'ont ni la même granularité, ni la même fraîcheur, ni le même producteur. Une release
unique « Géorisques » masquerait ces différences, et le verdict d'acceptation ne pourrait plus
être prononcé famille par famille — ce que le ticket exige.

## Les octets épinglés sont canoniques

Les enregistrements sont triés et réencodés avec des clés ordonnées. Sans cela, deux épinglages
d'une donnée inchangée donneraient deux empreintes différentes — l'ordre de pagination d'une API
n'est pas garanti stable — et le checksum ne prouverait plus rien.
"""

import argparse
import gzip
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.georisques import API, FAMILIES, Family, family, fetch
from immo_pipelines.progress import Progress


def communes(connection: psycopg.Connection[Any], department: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT code FROM reference.area
         WHERE area_type = 'commune' AND department_code = %s ORDER BY code
        """,
        (department,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def collect(item: Family, department: str, territories: list[str]) -> list[dict[str, Any]]:
    if item.mode == "department":
        return fetch(item, department, department=department)
    records: list[dict[str, Any]] = []
    progress = Progress(len(territories), f"DS-09 {item.key}")
    for territory in territories:
        records.extend(fetch(item, territory, department=department))
        progress.advance()
    return records


def canonical(records: list[dict[str, Any]]) -> bytes:
    ordered = sorted(records, key=lambda record: json.dumps(record, sort_keys=True))
    return json.dumps(ordered, ensure_ascii=False, sort_keys=True).encode("utf-8")


def object_key(item: Family, release: str, department: str) -> str:
    return f"ds-09/{item.key}/{release}/{department}/observations.json.gz"


def manifest(
    item: Family, release_key: str, department: str, asset: dict[str, Any]
) -> dict[str, Any]:
    return {
        "release_id": f"DS-09@{release_key}",
        "release_key": release_key,
        "source_published_on": release_key.split("--", 1)[1],
        "department": department,
        "contract_version": 1,
        "risk_family": item.key,
        "key_derivation": (
            "Date d'épinglage. Géorisques ne publie pas d'édition datée par famille : la clé "
            "identifie les octets relevés ce jour-là, pas une édition amont. Le format suit "
            "`key_format: risk-family--YYYY-MM-DD` du contrat."
        ),
        "discovery": {
            "catalog_entry": f"{API}/{item.endpoint}",
            "access_mode": item.mode,
            "territory_parameter": item.territory_parameter,
            "granularity": item.granularity,
            "api_is_not_a_path_back": (
                "L'URL rejouée demain rendrait d'autres octets. Seule l'archive nommée ci-dessous "
                "permet de retrouver les octets importés, et le SHA-256 la contraint."
            ),
            "silent_national_fallback": (
                "Un paramètre territorial inconnu n'est pas rejeté : il est ignoré, et la réponse "
                "couvre la France entière avec un statut 200. Le filtre est donc vérifié ligne à "
                "ligne à l'épinglage, pas déduit du code HTTP."
            ),
            "canonical_bytes": (
                "Enregistrements triés et clés ordonnées : l'ordre de pagination d'une API n'est "
                "pas garanti stable, et sans canonicalisation le checksum ne prouverait rien."
            ),
        },
        "assets": [asset],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--release", required=True, help="date d'épinglage, par exemple 2026-09-14")
    parser.add_argument(
        "--family",
        action="append",
        choices=[item.key for item in FAMILIES],
        help="limiter à une famille ; répétable. Par défaut, toutes.",
    )
    arguments = parser.parse_args()
    wanted = [family(key) for key in (arguments.family or [item.key for item in FAMILIES])]

    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    root = Path(__file__).resolve().parents[2] / "contracts" / "datasets" / "DS-09" / "releases"
    root.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        territories = communes(connection, arguments.department)
    if not territories:
        raise SystemExit(f"Aucune commune connue sur le {arguments.department}.")

    summary: dict[str, int] = {}
    for item in wanted:
        print(f"DS-09 {item.key} ({item.mode})", flush=True)
        records = collect(item, arguments.department, territories)
        payload = canonical(records)
        release_key = f"{item.key}--{arguments.release}"
        with tempfile.TemporaryDirectory(prefix="immo-georisques-") as temporary:
            local = Path(temporary) / "observations.json.gz"
            # `mtime=0` : l'empreinte doit dependre des seules donnees.
            with (
                local.open("wb") as handle,
                gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as archive,
            ):
                archive.write(payload)
            digest = hashlib.sha256(local.read_bytes()).hexdigest()
            key = object_key(item, release_key, arguments.department)
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
                "url": f"{API}/{item.endpoint}?{item.territory_parameter}=…",
                "sha256": digest,
                "byte_size": local.stat().st_size,
                "media_type": "application/json",
                "content_encoding": "gzip",
                "archive": {"object_key": key},
                "extract": {
                    "records": len(records),
                    "uncompressed_byte_size": len(payload),
                    "territories": 1 if item.mode == "department" else len(territories),
                },
            }
        path = root / f"{release_key}-{arguments.department}.json"
        path.write_text(
            json.dumps(
                manifest(item, release_key, arguments.department, asset),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        summary[item.key] = len(records)
        print(f"  {len(records)} enregistrements, sha256 {digest[:12]}… → {path.name}", flush=True)

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
