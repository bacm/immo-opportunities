#!/usr/bin/env python3
"""Importer une famille de risque DS-09 en conservant sa granularité — D3.

La garantie centrale du ticket est négative : **une observation communale ne devient jamais une
exposition parcellaire.** Elle est tenue à trois endroits qui ne peuvent pas diverger :

1. la source du module `market_data.georisques`, qui fixe la granularité d'après ce que la source
   donne et non d'après ce qu'on voudrait ;
2. ce script, qui écrit `geom = NULL` pour toute observation communale ;
3. le schéma, dont `risk_observation_granularity` refuse une observation communale porteuse d'une
   géométrie — et l'inverse.

« La commune est concernée par un PPRI » et « la parcelle est en zone inondable » sont deux
affirmations différentes. La seconde exige une donnée zonale ; GASPAR n'en donne pas.

## Couverture connue n'est pas risque nul

`coverage_known` dit que la famille a été interrogée pour cette commune et qu'on sait donc ce que
la source y contient — fût-ce rien. Sans lui, une absence d'intersection serait indiscernable
d'une absence de donnée, et le moteur produirait un zéro là où il doit produire une absence.

## Idempotence

La clé d'idempotence et l'identifiant de run portent la version de transformation, et la release
est purgée avant écriture — un réimport de la même version doit pouvoir avoir lieu, leçon tirée
sur D4.
"""

import argparse
import gzip
import hashlib
import json
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

from immo_pipelines.cadastre.archive import MinioObjectStore
from immo_pipelines.cadastre.catalog import DatasetCatalog
from immo_pipelines.cadastre.manifest import load_release_manifest, project_root, resolve_asset
from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.market_data.georisques import (
    GEORISQUES_TRANSFORMATION_VERSION,
    Family,
    family,
)


def contract_fingerprint() -> str:
    path = project_root() / "contracts" / "datasets" / "DS-09" / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_records(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload: list[dict[str, Any]] = json.load(handle)
    return payload


STAGE = """
CREATE TEMP TABLE risk_stage (
    source_identifier text,
    risk_type text,
    granularity text,
    commune_code text,
    severity text,
    observed_at date,
    valid_from date,
    valid_to date,
    geometry_wkt text,
    value jsonb,
    source_row_number bigint
) ON COMMIT DROP
"""


def insert(
    connection: psycopg.Connection[Any],
    item: Family,
    records: list[dict[str, Any]],
    *,
    release_id: str,
    raw_asset_id: int,
    department: str,
    import_run_id: str,
    covered_communes: set[str],
) -> Counter[str]:
    """Normaliser, réparer ce qui se répare, et n'inventer aucune précision.

    Une géométrie invalide est d'abord réparée — `ST_MakeValid`, même convention que DS-01. Ce
    qui n'en ressort pas valide **ne disparaît pas** : l'observation est conservée à la
    granularité `commune`, avec son motif, et la géométrie source part en quarantaine.

    Descendre en précision est sûr : on affirme moins que la source. C'est l'inverse — faire d'une
    observation communale une exposition parcellaire — que le ticket interdit.
    """
    counters: Counter[str] = Counter()
    rows: list[tuple[Any, ...]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        counters["source_records"] += 1
        produced = 0
        for observation in item.normalize(record):
            produced += 1
            key = (observation.risk_type, observation.source_identifier)
            if key in seen:
                # La source republie parfois le meme objet sur deux pages. Le compter plutot que
                # de faire echouer le lot, et ne l'ecrire qu'une fois.
                counters["duplicate"] += 1
                continue
            seen.add(key)
            rows.append(
                (
                    f"v{GEORISQUES_TRANSFORMATION_VERSION}:{observation.source_identifier}",
                    observation.risk_type,
                    observation.granularity,
                    observation.commune_code,
                    observation.severity,
                    observation.observed_at,
                    observation.valid_from,
                    observation.valid_to,
                    observation.geometry_wkt,
                    json.dumps(observation.value, ensure_ascii=False),
                    len(rows),
                )
            )
        if produced == 0:
            # Un enregistrement qui ne produit aucune observation n'est pas un non-evenement :
            # c'est soit un champ obligatoire absent, soit une geometrie d'un type qu'on ne sait
            # pas lire. Le compter est ce qui empeche une perte silencieuse de recommencer.
            counters["yielded_nothing"] += 1
    connection.execute(STAGE)
    with connection.cursor().copy(
        """
        COPY risk_stage (
            source_identifier, risk_type, granularity, commune_code, severity, observed_at,
            valid_from, valid_to, geometry_wkt, value, source_row_number
        ) FROM STDIN
        """
    ) as copy:
        for row in rows:
            copy.write_row(row)

    connection.execute(
        """
        CREATE TEMP TABLE risk_resolved ON COMMIT DROP AS
        SELECT stage.*,
               CASE WHEN stage.geometry_wkt IS NULL THEN NULL
                    ELSE ST_MakeValid(
                        ST_Transform(ST_GeomFromText(stage.geometry_wkt, %(srid)s), 2154)
                    ) END AS canonical
          FROM risk_stage AS stage
        """,
        {"srid": item.source_srid},
    )
    connection.execute(
        """
        INSERT INTO observation.risk_observation (
            release_id, raw_asset_id, source_identifier, risk_type, granularity,
            commune_code, department_code, severity, observed_at, valid_from, valid_to,
            coverage_known, geom, value
        )
        SELECT %(release_id)s, %(raw_asset_id)s, source_identifier, risk_type,
               CASE WHEN usable THEN granularity ELSE 'commune' END,
               commune_code, %(department)s, severity, observed_at, valid_from, valid_to,
               commune_code = ANY(%(covered)s::text[]),
               CASE WHEN usable THEN canonical ELSE NULL END,
               CASE WHEN usable OR geometry_wkt IS NULL THEN value
                    ELSE value || jsonb_build_object(
                        'geometry_quarantined', 'unrepairable_geometry',
                        'declared_granularity', granularity
                    ) END
          FROM (
              SELECT *, canonical IS NOT NULL
                         AND NOT ST_IsEmpty(canonical)
                         AND ST_IsValid(canonical) AS usable
                FROM risk_resolved
          ) AS resolved
        """,
        {
            "release_id": release_id,
            "raw_asset_id": raw_asset_id,
            "department": department,
            "covered": sorted(covered_communes),
        },
    )
    connection.execute(
        """
        INSERT INTO meta.geometry_quarantine (
            release_id, import_run_id, raw_asset_id, layer, source_feature_id,
            source_row_number, reason_code, reason_detail, source_geometry,
            source_properties, repair_attempted, transformation_version
        )
        SELECT %(release_id)s, %(import_run_id)s, %(raw_asset_id)s, 'observations',
               source_identifier, source_row_number, 'unrepairable_geometry',
               'ST_MakeValid n''a pas produit de géométrie valide et non vide ; '
               'l''observation est conservée à la granularité commune',
               to_jsonb(geometry_wkt), value, true,
               %(version)s
          FROM risk_resolved
         WHERE geometry_wkt IS NOT NULL
           AND (canonical IS NULL OR ST_IsEmpty(canonical) OR NOT ST_IsValid(canonical))
        """,
        {
            "release_id": release_id,
            "import_run_id": import_run_id,
            "raw_asset_id": raw_asset_id,
            "version": f"georisques@{GEORISQUES_TRANSFORMATION_VERSION}",
        },
    )
    measured = connection.execute(
        """
        SELECT granularity, count(*) FROM observation.risk_observation
         WHERE release_id = %(release_id)s GROUP BY granularity
        """,
        {"release_id": release_id},
    ).fetchall()
    for granularity, count in measured:
        counters[f"granularity_{granularity}"] = int(count)
    degraded = connection.execute(
        "SELECT count(*) FROM meta.geometry_quarantine"
        " WHERE release_id = %s AND import_run_id = %s",
        (release_id, import_run_id),
    ).fetchone()
    counters["geometry_quarantined"] = int((degraded or [0])[0])
    counters["observations"] = len(rows)
    return counters


def record_coverage(connection: psycopg.Connection[Any], release_id: str, covered: set[str]) -> int:
    """Une ligne par commune interrogée, y compris celles où la source ne dit rien.

    C'est la distinction que le contrat DS-09 appelle `coverage_absence` : une commune absente de
    cette table n'a pas été interrogée, une commune présente à zéro l'a été et la source n'y a
    rien. Les confondre ferait passer une absence d'information pour une absence de risque.
    """
    result = connection.execute(
        """
        INSERT INTO meta.dataset_coverage_metric (
            release_id, commune_code, record_count, matched_record_count,
            coverage_ratio, freshest_observation_at, details
        )
        SELECT %(release_id)s, commune.code,
               count(observation.id),
               count(observation.id) FILTER (WHERE observation.granularity <> 'commune'),
               CASE WHEN count(observation.id) = 0 THEN NULL
                    ELSE round(
                        count(observation.id) FILTER (
                            WHERE observation.granularity <> 'commune'
                        )::numeric / count(observation.id), 6
                    ) END,
               max(observation.observed_at),
               jsonb_build_object(
                   'granularities',
                   coalesce(
                       jsonb_object_agg(observation.granularity, 1)
                           FILTER (WHERE observation.granularity IS NOT NULL),
                       '{}'::jsonb
                   ),
                   'queried', true
               )
          FROM unnest(%(covered)s::text[]) AS commune(code)
          LEFT JOIN observation.risk_observation AS observation
                 ON observation.commune_code = commune.code
                AND observation.release_id = %(release_id)s
         GROUP BY commune.code
        ON CONFLICT ON CONSTRAINT dataset_coverage_metric_identity DO UPDATE SET
            record_count = EXCLUDED.record_count,
            matched_record_count = EXCLUDED.matched_record_count,
            coverage_ratio = EXCLUDED.coverage_ratio,
            freshest_observation_at = EXCLUDED.freshest_observation_at,
            details = EXCLUDED.details,
            measured_at = now()
        """,
        {"release_id": release_id, "covered": sorted(covered)},
    )
    return result.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description="Import one DS-09 risk family release")
    parser.add_argument("release", help="clé de release, par exemple cavity--2026-09-14")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    item = family(arguments.release.split("--", 1)[0])
    manifest = load_release_manifest("DS-09", arguments.release, arguments.department)
    asset = manifest.asset("observations")
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    import_run_id = (
        f"georisques:{manifest.release_key}:{manifest.department}:"
        f"{GEORISQUES_TRANSFORMATION_VERSION}"
    )

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
            schema_fingerprint=contract_fingerprint(),
            department_code=manifest.department,
            data_source_id="DS-09",
            # Le SRID est celui de la famille, jamais une constante : l'API repond en WGS84 et
            # la couche argiles est deja en Lambert 93. Confondre les deux deplacerait ses
            # polygones de plusieurs centaines de kilometres, sans qu'aucune contrainte ne le
            # voie — ils resteraient des polygones valides.
            source_srid=item.source_srid,
        )
        covered = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT code FROM reference.area
                 WHERE area_type = 'commune' AND department_code = %s
                """,
                (manifest.department,),
            ).fetchall()
        }
        connection.execute("SET ROLE pipeline_rw")
        with tempfile.TemporaryDirectory(prefix="immo-georisques-") as temporary:
            local = Path(temporary) / "observations.json.gz"
            resolved = resolve_asset(
                catalog=catalog,
                object_store=object_store,
                manifest=manifest,
                asset=asset,
                destination=local,
            )
            idempotency_key = (
                f"{manifest.release_id}:{manifest.department}:observations:"
                f"{resolved.sha256}:{GEORISQUES_TRANSFORMATION_VERSION}"
            )
            existing = connection.execute(
                "SELECT id, status FROM meta.import_run WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if existing is not None and existing[1] == "succeeded":
                print(f"déjà importé par {existing[0]}, rien à faire")
                return 0
            if existing is not None:
                connection.execute("DELETE FROM meta.import_run WHERE id = %s", (existing[0],))
            connection.execute(
                """
                INSERT INTO meta.import_run (
                    id, release_id, territory_type, territory_code, idempotency_key,
                    status, runner_metadata
                ) VALUES (%s, %s, 'department', %s, %s, 'running',
                          jsonb_build_object('layer', 'observations', 'risk_family', %s::text,
                                             'raw_asset_id', %s::bigint))
                """,
                (
                    import_run_id,
                    manifest.release_id,
                    manifest.department,
                    idempotency_key,
                    item.key,
                    resolved.raw_asset_id,
                ),
            )
            # Purge de la release entiere avant ecriture : un reimport de la meme version doit
            # pouvoir avoir lieu. Leçon de D4, ou la purge ne visait que les autres versions.
            connection.execute(
                "DELETE FROM observation.risk_observation WHERE release_id = %s",
                (manifest.release_id,),
            )
            records = read_records(local)
            counters = insert(
                connection,
                item,
                records,
                release_id=manifest.release_id,
                raw_asset_id=resolved.raw_asset_id,
                department=manifest.department,
                import_run_id=import_run_id,
                covered_communes=covered,
            )
            counters["communes_queried"] = record_coverage(connection, manifest.release_id, covered)
            connection.execute(
                """
                UPDATE meta.import_run SET
                    status = 'succeeded', completed_at = now(),
                    source_row_count = %(source)s, normalized_row_count = %(normalized)s,
                    deduplicated_row_count = %(duplicates)s,
                    runner_metadata = runner_metadata || %(detail)s::jsonb
                 WHERE id = %(id)s
                """,
                {
                    "id": import_run_id,
                    "source": counters["source_records"],
                    "normalized": counters["observations"],
                    "duplicates": counters["duplicate"],
                    "detail": json.dumps(
                        {**counters, "asset_origin": resolved.origin}, sort_keys=True
                    ),
                },
            )
            connection.commit()

    print(json.dumps({item.key: dict(sorted(counters.items()))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
