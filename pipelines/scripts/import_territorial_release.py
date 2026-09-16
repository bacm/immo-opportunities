#!/usr/bin/env python3
"""Importer une source communale de l'INSEE, DS-14 à DS-16 — D7, ADR-023.

Une release produit une ligne par commune du référentiel et par indicateur, dans
`observation.territorial_indicator` : valeur ou motif d'absence, jamais un zéro inventé. Les
règles de lecture vivent dans `market_data.territorial` ; ce script résout les fichiers archivés,
écrit, et laisse la trace — run d'import, contrôles de contrat, couverture par commune.

## La distance au pôle

DS-16 dit à quelle aire appartient une commune et quelle est la commune-centre de l'aire. La
distance entre les deux se calcule ici, en base, entre centroïdes Lambert-93 des communes de
`reference.area`. Elle cite la release DS-01 active : une valeur dérivée garde sa provenance
(ADR-022). Une commune-centre hors du référentiel importé laisse la distance absente.

## Idempotence

Une seule clé par release et département, qui porte les empreintes de tous les fichiers et la
version de transformation ; la release est purgée avant écriture.
"""

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import (
    ManifestAsset,
    load_release_manifest,
    project_root,
    resolve_asset,
)
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.territorial import (
    GEOGRAPHY_VINTAGE,
    TERRITORIAL_TRANSFORMATION_VERSION,
    Indicator,
    attraction_areas,
    attraction_indicators,
    equipment_indicators,
    housing_indicators,
    melodi_rows,
    population_indicators,
)


def _period(manifest_path: Path, layer: str) -> str:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    (asset,) = [item for item in document["assets"] if item["layer"] == layer]
    return str(asset["extract"]["period"])


@dataclass(frozen=True, slots=True)
class Layer:
    name: str
    read: Callable[[Path, str, list[str]], list[Indicator]]


def _areas(path: Path, member: str) -> Path:
    """Le classeur DS-16 est distribué dans un zip : extraire le membre épinglé."""
    with zipfile.ZipFile(path) as archive:
        target = path.with_name(Path(member).name)
        target.write_bytes(archive.read(member))
    return target


SOURCES: dict[str, tuple[Layer, ...]] = {
    "DS-14": (
        Layer(
            "population",
            lambda path, period, communes: population_indicators(
                melodi_rows(path), communes, period
            ),
        ),
        Layer(
            "housing",
            lambda path, period, communes: housing_indicators(melodi_rows(path), communes, period),
        ),
    ),
    "DS-15": (
        Layer(
            "equipments",
            lambda path, period, communes: equipment_indicators(
                melodi_rows(path), communes, period
            ),
        ),
    ),
    "DS-16": (
        Layer(
            "areas",
            lambda path, period, communes: attraction_indicators(attraction_areas(path), communes),
        ),
    ),
}

SCHEMA_ERRORS = (KeyError, ValueError)


def contract_fingerprint(source: str) -> str:
    path = project_root() / "contracts" / "datasets" / source / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def insert(
    connection: psycopg.Connection[Any],
    indicators: list[Indicator],
    *,
    release_id: str,
    raw_asset_id: int,
    department: str,
) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO observation.territorial_indicator (
                release_id, raw_asset_id, department_code, commune_code, indicator_code,
                reference_period, geography_vintage, numeric_value, text_value,
                missing_reason, unit, transformation_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    release_id,
                    raw_asset_id,
                    department,
                    item.commune_code,
                    item.code,
                    item.reference_period,
                    GEOGRAPHY_VINTAGE,
                    item.numeric_value,
                    item.text_value,
                    item.missing_reason,
                    item.unit,
                    f"territorial@{TERRITORIAL_TRANSFORMATION_VERSION}",
                )
                for item in indicators
            ],
        )


def insert_centre_distance(
    connection: psycopg.Connection[Any], *, release_id: str, department: str
) -> Counter[str]:
    """`aav_distance_centre_m`, depuis `aav_commune_centre` et la release DS-01 active."""
    active = connection.execute(
        """
        SELECT release_id FROM meta.active_dataset_release
         WHERE data_source_id = 'DS-01' AND scope_type = 'department' AND scope_code = %s
        """,
        (department,),
    ).fetchone()
    if active is None:
        raise SystemExit(f"Aucune release DS-01 active sur le {department}.")
    connection.execute(
        """
        INSERT INTO observation.territorial_indicator (
            release_id, raw_asset_id, department_code, commune_code, indicator_code,
            reference_period, geography_vintage, numeric_value, missing_reason, unit,
            source_release_ids, formula, transformation_version
        )
        SELECT centre.release_id, centre.raw_asset_id, centre.department_code,
               centre.commune_code, 'aav_distance_centre_m', centre.reference_period,
               centre.geography_vintage,
               round(ST_Distance(ST_Centroid(commune.geom), ST_Centroid(pole.geom))::numeric, 1),
               CASE
                   WHEN centre.missing_reason IS NOT NULL THEN centre.missing_reason
                   WHEN pole.id IS NULL OR commune.id IS NULL THEN 'source_value_missing'
               END,
               'm',
               jsonb_build_array(centre.release_id, %(ds01)s::text),
               'ST_Distance(ST_Centroid(commune), ST_Centroid(commune-centre de l''aire)), '
               'Lambert-93, reference.area',
               centre.transformation_version
          FROM observation.territorial_indicator AS centre
          LEFT JOIN reference.area AS commune
                 ON commune.area_type = 'commune' AND commune.code = centre.commune_code
          LEFT JOIN reference.area AS pole
                 ON pole.area_type = 'commune' AND pole.code = centre.text_value
         WHERE centre.release_id = %(release_id)s
           AND centre.indicator_code = 'aav_commune_centre'
        """,
        {"release_id": release_id, "ds01": str(active[0])},
    )
    rows = connection.execute(
        """
        SELECT coalesce(missing_reason, 'measured'), count(*)
          FROM observation.territorial_indicator
         WHERE release_id = %s AND indicator_code = 'aav_distance_centre_m'
         GROUP BY 1
        """,
        (release_id,),
    ).fetchall()
    return Counter({f"distance_{reason}": int(count) for reason, count in rows})


def record_coverage(connection: psycopg.Connection[Any], release_id: str) -> int:
    """Une ligne par commune : indicateurs écrits, dont valués."""
    result = connection.execute(
        """
        INSERT INTO meta.dataset_coverage_metric (
            release_id, commune_code, record_count, matched_record_count,
            coverage_ratio, details
        )
        SELECT release_id, commune_code, count(*),
               count(*) FILTER (WHERE missing_reason IS NULL),
               round(count(*) FILTER (WHERE missing_reason IS NULL)::numeric / count(*), 6),
               jsonb_build_object(
                   'missing_reasons',
                   coalesce(
                       jsonb_object_agg(missing_reason, 1)
                           FILTER (WHERE missing_reason IS NOT NULL),
                       '{}'::jsonb
                   )
               )
          FROM observation.territorial_indicator
         WHERE release_id = %(release_id)s
         GROUP BY release_id, commune_code
        ON CONFLICT ON CONSTRAINT dataset_coverage_metric_identity DO UPDATE SET
            record_count = EXCLUDED.record_count,
            matched_record_count = EXCLUDED.matched_record_count,
            coverage_ratio = EXCLUDED.coverage_ratio,
            details = EXCLUDED.details,
            measured_at = now()
        """,
        {"release_id": release_id},
    )
    return result.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description="Import one DS-14, DS-15 or DS-16 release")
    parser.add_argument("source", choices=sorted(SOURCES))
    parser.add_argument("release", help="clé de release, par exemple rp-2023")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    source = arguments.source
    manifest = load_release_manifest(source, arguments.release, arguments.department)
    manifest_path = (
        project_root()
        / "contracts"
        / "datasets"
        / source
        / "releases"
        / f"{manifest.release_key}-{manifest.department}.json"
    )
    fingerprint = contract_fingerprint(source)
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    import_run_id = (
        f"territorial:{source}:{manifest.release_key}:{manifest.department}:"
        f"{TERRITORIAL_TRANSFORMATION_VERSION}"
    )
    counters: Counter[str] = Counter()

    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        catalog = DatasetCatalog(connection)
        catalog.register_release(
            release_id=manifest.release_id,
            release_key=manifest.release_key,
            published_on=date.fromisoformat(manifest.source_published_on),
            schema_fingerprint=fingerprint,
            department_code=manifest.department,
            data_source_id=source,
            # Aucune géométrie source : le SRID déclaré est le SRID canonique.
            source_srid=2154,
        )
        communes = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT code FROM reference.area
                 WHERE area_type = 'commune' AND department_code = %s ORDER BY code
                """,
                (manifest.department,),
            ).fetchall()
        ]
        if not communes:
            raise SystemExit(f"Aucune commune connue sur le {manifest.department}.")

        with tempfile.TemporaryDirectory(prefix="immo-territorial-") as temporary:
            resolved: list[tuple[Layer, ManifestAsset, Path, int, str, str]] = []
            for layer in SOURCES[source]:
                asset = manifest.asset(layer.name)
                local = Path(temporary) / f"{layer.name}.zip"
                result = resolve_asset(
                    catalog=catalog,
                    object_store=object_store,
                    manifest=manifest,
                    asset=asset,
                    destination=local,
                    prefer_curl=True,
                )
                resolved.append(
                    (layer, asset, local, result.raw_asset_id, result.sha256, result.origin)
                )

            idempotency_key = (
                f"{manifest.release_id}:{manifest.department}:"
                + ",".join(f"{layer.name}={sha}" for layer, _, _, _, sha, _ in resolved)
                + f":{TERRITORIAL_TRANSFORMATION_VERSION}"
            )
            connection.execute("SET ROLE pipeline_rw")
            existing = connection.execute(
                "SELECT id, status FROM meta.import_run WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if existing is not None and existing[1] == "succeeded":
                print(f"déjà importé par {existing[0]}, rien à faire")
                return 0
            connection.execute("DELETE FROM meta.import_run WHERE id = %s", (import_run_id,))
            connection.execute(
                """
                INSERT INTO meta.import_run (
                    id, release_id, territory_type, territory_code, idempotency_key,
                    status, runner_metadata
                ) VALUES (%s, %s, 'department', %s, %s, 'running',
                          jsonb_build_object('layers', %s::jsonb))
                """,
                (
                    import_run_id,
                    manifest.release_id,
                    manifest.department,
                    idempotency_key,
                    json.dumps(
                        {
                            layer.name: {"raw_asset_id": raw_id, "asset_origin": origin}
                            for layer, _, _, raw_id, _, origin in resolved
                        }
                    ),
                ),
            )
            connection.execute(
                "DELETE FROM observation.territorial_indicator WHERE release_id = %s",
                (manifest.release_id,),
            )
            for layer, asset, local, raw_asset_id, _, _ in resolved:
                path = local
                if source == "DS-16" and asset.member_path is not None:
                    path = _areas(local, asset.member_path)
                try:
                    indicators = layer.read(path, _period(manifest_path, layer.name), communes)
                    schema_valid = bool(indicators)
                except SCHEMA_ERRORS as error:
                    print(f"{layer.name} : schéma inattendu — {error}", file=sys.stderr)
                    indicators = []
                    schema_valid = False
                catalog.record_asset_checks(
                    release_id=manifest.release_id,
                    department_code=manifest.department,
                    layer=layer.name,
                    checksum_valid=True,
                    schema_valid=schema_valid,
                    schema_fingerprint=fingerprint,
                )
                connection.execute("SET ROLE pipeline_rw")
                if not schema_valid:
                    connection.commit()
                    raise SystemExit(f"{manifest.release_id} {layer.name} : schéma refusé")
                insert(
                    connection,
                    indicators,
                    release_id=manifest.release_id,
                    raw_asset_id=raw_asset_id,
                    department=manifest.department,
                )
                counters[f"{layer.name}_rows"] = len(indicators)
                for item in indicators:
                    counters[f"{layer.name}_{item.missing_reason or 'valued'}"] += 1
            if source == "DS-16":
                counters.update(
                    insert_centre_distance(
                        connection, release_id=manifest.release_id, department=manifest.department
                    )
                )
            counters["communes"] = record_coverage(connection, manifest.release_id)
            # Les lignes lues dans les fichiers, puis celles écrites : les distances au pôle sont
            # dérivées en base et ne viennent d'aucune ligne source.
            total = sum(value for key, value in counters.items() if key.endswith("_rows"))
            written = total + sum(
                value for key, value in counters.items() if key.startswith("distance_")
            )
            connection.execute(
                """
                UPDATE meta.import_run SET
                    status = 'succeeded', completed_at = now(),
                    source_row_count = %(total)s, normalized_row_count = %(written)s,
                    deduplicated_row_count = 0,
                    runner_metadata = runner_metadata || %(detail)s::jsonb
                 WHERE id = %(id)s
                """,
                {
                    "id": import_run_id,
                    "total": total,
                    "written": written,
                    "detail": json.dumps(dict(sorted(counters.items()))),
                },
            )
            connection.commit()

    print(json.dumps({manifest.release_id: dict(sorted(counters.items()))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
