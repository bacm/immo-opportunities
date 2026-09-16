#!/usr/bin/env python3
"""Importer une release DS-07 ou DS-13 : diagnostics déposés, rattachés par identifiant déclaré.

D4 pour les logements existants (DS-07), D9 pour les neufs (DS-13, ADR-021). Les deux jeux ont
les mêmes colonnes et suivent les mêmes règles ; seuls diffèrent le contrat et la liste fermée des
modèles. Un DPE neuf n'entre dans aucune mesure : ce sont les lecteurs qui filtrent la source.

Le moteur `compute_renovation_features` est livré et testé depuis v0.6 ; ce script lui apporte la
donnée réelle. Les règles d'éligibilité et la lecture de l'extrait vivent dans
`immo_pipelines.market_data.dpe`, sous test ; ce fichier-ci porte la résolution en base et la
mesure.

## Ce qui est écarté, et où le motif va

Un enregistrement inéligible n'est pas perdu : son numéro et son motif entrent dans
`meta.attribute_quarantine`, et ses octets restent dans l'archive. Un diagnostic éligible mais
qu'aucun identifiant ne rattache y entre aussi, sur l'attribut `target` — la contrainte
`energy_assessment_target` interdit une observation qui ne se rattache à rien, et c'est la bonne
garde : une observation sans sujet ne sert à aucune feature.

## L'absence de DPE ne dit rien

Rien ici ne produit de signal à partir d'une absence. Un bâtiment sans diagnostic n'est pas
suspect : il est sans diagnostic. `compute_renovation_features` sort alors `REN-004..008` absentes
avec motif, et la confiance baisse — la contribution au score, elle, ne bouge pas. C'est vérifié
par test, pas seulement affirmé.

## Idempotence

La clé d'idempotence et l'identifiant de run portent la version de transformation, et les lignes
des versions précédentes de la même release sont purgées avant écriture. Sans cela, un correctif
de code n'atteindrait jamais les données — constaté sur BUG-09 — ou ferait coexister deux états,
ce que l'écran de vérification de D6a a montré aussitôt.
"""

import argparse
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
from immo_pipelines.market_data.dpe import (
    DPE_FAMILIES,
    DPE_TRANSFORMATION_VERSION,
    DpeFamily,
    Rejection,
    missing_columns,
    read_extract,
)
from immo_pipelines.progress import Progress

STAGE = """
CREATE TEMP TABLE dpe_stage (
    dpe_number text PRIMARY KEY,
    assessment_date date NOT NULL,
    deposited_at date NOT NULL,
    commune_code text NOT NULL,
    energy_label text,
    consumption numeric,
    rnb_id text,
    ban_id text,
    ban_score numeric,
    geocoding_contradicted boolean NOT NULL,
    envelope jsonb NOT NULL,
    properties jsonb NOT NULL
) ON COMMIT DROP
"""


def contract_fingerprint(source_id: str) -> str:
    path = project_root() / "contracts" / "datasets" / source_id / "v1.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assessment_id(release_id: str, dpe_number: str) -> str:
    return f"energy-assessment:dpe:{release_id}:v{DPE_TRANSFORMATION_VERSION}:{dpe_number}"


def stage_rows(
    connection: psycopg.Connection[Any],
    path: Path,
    *,
    snapshot_at: date,
    release_id: str,
    import_run_id: str,
    family: DpeFamily,
) -> Counter[str]:
    """Charger l'extrait dans une table de travail, en consignant chaque rejet avec son motif."""
    counters: Counter[str] = Counter()
    rejections: list[tuple[Any, ...]] = []
    progress = Progress(0, family.source_id)
    with connection.cursor().copy(
        """
        COPY dpe_stage (
            dpe_number, assessment_date, deposited_at, commune_code, energy_label, consumption,
            rnb_id, ban_id, ban_score, geocoding_contradicted, envelope, properties
        ) FROM STDIN
        """
    ) as copy:
        seen: set[str] = set()
        for record in read_extract(path, snapshot_at=snapshot_at, models=family.models):
            counters["source_rows"] += 1
            if isinstance(record, Rejection):
                counters[f"rejected_{record.reason}"] += 1
                rejections.append(
                    (
                        release_id,
                        import_run_id,
                        "energy_assessment",
                        assessment_id(release_id, record.dpe_number or "unknown"),
                        "record",
                        record.reason,
                        record.detail,
                    )
                )
                continue
            if record.dpe_number in seen:
                # La source publie un numero de DPE unique ; un doublon serait une anomalie de
                # l'extrait, pas du diagnostic. Le compter plutot que de faire echouer le COPY.
                counters["duplicate_dpe_number"] += 1
                continue
            seen.add(record.dpe_number)
            copy.write_row(
                (
                    record.dpe_number,
                    record.assessment_date,
                    record.deposited_at,
                    record.commune_code,
                    record.energy_label,
                    record.consumption_kwh_m2_year,
                    record.rnb_id,
                    record.ban_id,
                    record.ban_score,
                    record.geocoding_contradicted,
                    json.dumps(record.envelope, ensure_ascii=False),
                    json.dumps(record.properties, ensure_ascii=False),
                )
            )
            counters["staged"] += 1
            if counters["source_rows"] % 25000 == 0:
                progress.retotal(counters["source_rows"])
                print(f"  {counters['source_rows']} lignes lues", flush=True)
    if rejections:
        connection.cursor().executemany(
            """
            INSERT INTO meta.attribute_quarantine (
                release_id, import_run_id, entity_type, entity_id,
                attribute, reason_code, reason_detail
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT attribute_quarantine_identity DO UPDATE SET
                import_run_id = EXCLUDED.import_run_id,
                reason_code = EXCLUDED.reason_code,
                reason_detail = EXCLUDED.reason_detail
            """,
            rejections,
        )
    return counters


def resolve_and_insert(
    connection: psycopg.Connection[Any],
    *,
    release_id: str,
    raw_asset_id: int,
    department: str,
    import_run_id: str,
) -> Counter[str]:
    """Rattacher par identifiant déclaré, puis écrire ce qui a un sujet.

    Les deux jointures sont des égalités d'identifiant, jamais une géométrie ni une distance :
    B4 a établi qu'aucune règle géométrique ne rend la relation adresse ↔ parcelle vérifiable, et
    rien ici n'y revient.
    """
    connection.execute(
        """
        CREATE TEMP TABLE dpe_resolved ON COMMIT DROP AS
        SELECT stage.*,
               building.id AS building_id,
               address.id AS address_id,
               CASE WHEN building.id IS NOT NULL THEN 'rnb_identifier'
                    WHEN address.id IS NOT NULL THEN 'ban_identifier'
                    ELSE 'none' END AS match_method
          FROM dpe_stage AS stage
          LEFT JOIN reference.building AS building
                 ON building.id = 'building:rnb:' || stage.rnb_id
          LEFT JOIN reference.address AS address
                 ON address.id = 'address:ban:' || stage.ban_id
        """
    )
    connection.execute(
        """
        INSERT INTO observation.energy_assessment (
            id, release_id, raw_asset_id, dpe_number, assessment_date, deposited_at,
            is_deposited, is_simulated, address_id, building_id, match_confidence,
            energy_label, energy_consumption_kwh_m2_year, envelope_characteristics,
            commune_code, department_code, properties
        )
        SELECT %(prefix)s || dpe_number, %(release_id)s, %(raw_asset_id)s, dpe_number,
               assessment_date, deposited_at, true, false, address_id, building_id,
               -- Un identifiant officiel declare par le producteur vaut 1 : c'est la convention
               -- deja portee par `rnb-ban-identifier` dans meta.entity_match, pas un seuil
               -- invente. A defaut, le score de geocodage de la source — sauf quand elle se
               -- contredit, auquel cas la confiance devient absente avec son motif.
               CASE WHEN building_id IS NOT NULL THEN 1.0
                    WHEN geocoding_contradicted THEN NULL
                    ELSE ban_score END,
               energy_label, consumption, envelope, commune_code, %(department)s,
               properties || jsonb_build_object('match_method', match_method)
          FROM dpe_resolved
         WHERE building_id IS NOT NULL OR address_id IS NOT NULL
        """,
        {
            "prefix": f"energy-assessment:dpe:{release_id}:v{DPE_TRANSFORMATION_VERSION}:",
            "release_id": release_id,
            "raw_asset_id": raw_asset_id,
            "department": department,
        },
    )
    connection.execute(
        """
        INSERT INTO meta.attribute_quarantine (
            release_id, import_run_id, entity_type, entity_id,
            attribute, reason_code, reason_detail, evidence
        )
        SELECT %(release_id)s, %(import_run_id)s, 'energy_assessment',
               %(prefix)s || dpe_number, 'target', 'unresolved_source_identifier',
               'aucun identifiant déclaré ne se résout dans le référentiel',
               jsonb_build_object('id_rnb', rnb_id, 'identifiant_ban', ban_id,
                                  'commune_code', commune_code)
          FROM dpe_resolved
         WHERE building_id IS NULL AND address_id IS NULL
        ON CONFLICT ON CONSTRAINT attribute_quarantine_identity DO UPDATE SET
            import_run_id = EXCLUDED.import_run_id, evidence = EXCLUDED.evidence
        """,
        {
            "release_id": release_id,
            "import_run_id": import_run_id,
            "prefix": f"energy-assessment:dpe:{release_id}:v{DPE_TRANSFORMATION_VERSION}:",
        },
    )
    connection.execute(
        """
        INSERT INTO meta.attribute_quarantine (
            release_id, import_run_id, entity_type, entity_id,
            attribute, reason_code, reason_detail, evidence
        )
        SELECT %(release_id)s, %(import_run_id)s, 'energy_assessment',
               %(prefix)s || dpe_number, 'match_confidence',
               'contradictory_geocoding_status',
               'statut_geocodage annonce un échec alors que identifiant_ban se résout',
               jsonb_build_object('identifiant_ban', ban_id, 'score_ban', ban_score)
          FROM dpe_resolved
         WHERE building_id IS NULL AND address_id IS NOT NULL AND geocoding_contradicted
        ON CONFLICT ON CONSTRAINT attribute_quarantine_identity DO UPDATE SET
            import_run_id = EXCLUDED.import_run_id, evidence = EXCLUDED.evidence
        """,
        {
            "release_id": release_id,
            "import_run_id": import_run_id,
            "prefix": f"energy-assessment:dpe:{release_id}:v{DPE_TRANSFORMATION_VERSION}:",
        },
    )
    row = connection.execute(
        """
        SELECT count(*) FILTER (WHERE match_method = 'rnb_identifier'),
               count(*) FILTER (WHERE match_method = 'ban_identifier'),
               count(*) FILTER (WHERE match_method = 'none'),
               count(*) FILTER (WHERE geocoding_contradicted AND match_method = 'ban_identifier')
          FROM dpe_resolved
        """
    ).fetchone()
    assert row is not None
    return Counter(
        {
            "matched_building": int(row[0]),
            "matched_address_only": int(row[1]),
            "unmatched": int(row[2]),
            "confidence_quarantined": int(row[3]),
        }
    )


def record_coverage(connection: psycopg.Connection[Any], release_id: str) -> int:
    """Le taux d'appariement par commune, y compris là où il est faible.

    Publié tel quel : l'adresse d'un diagnostic est saisie à la main et un taux modeste est un
    résultat attendu, pas un défaut à corriger en relâchant les règles.
    """
    result = connection.execute(
        """
        INSERT INTO meta.dataset_coverage_metric (
            release_id, commune_code, record_count, matched_record_count,
            coverage_ratio, freshest_observation_at, details
        )
        SELECT %(release_id)s, commune_code, count(*),
               count(*) FILTER (WHERE building_id IS NOT NULL),
               round(
                   count(*) FILTER (WHERE building_id IS NOT NULL)::numeric / count(*), 6
               ),
               max(assessment_date),
               jsonb_build_object(
                   'matched_building', count(*) FILTER (WHERE match_method = 'rnb_identifier'),
                   'matched_address_only',
                   count(*) FILTER (WHERE match_method = 'ban_identifier'),
                   'unmatched', count(*) FILTER (WHERE match_method = 'none'),
                   'confidence_quarantined',
                   count(*) FILTER (
                       WHERE geocoding_contradicted AND match_method = 'ban_identifier'
                   )
               )
          FROM dpe_resolved
         GROUP BY commune_code
        ON CONFLICT ON CONSTRAINT dataset_coverage_metric_identity DO UPDATE SET
            record_count = EXCLUDED.record_count,
            matched_record_count = EXCLUDED.matched_record_count,
            coverage_ratio = EXCLUDED.coverage_ratio,
            freshest_observation_at = EXCLUDED.freshest_observation_at,
            details = EXCLUDED.details,
            measured_at = now()
        """,
        {"release_id": release_id},
    )
    return result.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive and import one ADEME DPE extract")
    parser.add_argument("release")
    parser.add_argument("--source", choices=sorted(DPE_FAMILIES), default="DS-07")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument(
        "--snapshot",
        default=None,
        help="date de snapshot ISO ; par défaut la date de publication de la release",
    )
    arguments = parser.parse_args()

    family = DPE_FAMILIES[arguments.source]
    manifest = load_release_manifest(family.source_id, arguments.release, arguments.department)
    asset = manifest.asset("assessments")
    snapshot_at = (
        date.fromisoformat(arguments.snapshot)
        if arguments.snapshot
        else date.fromisoformat(manifest.source_published_on)
    )
    settings = CadastreSettings.from_environment()
    object_store = MinioObjectStore(
        settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key
    )
    # DS-07 garde son identifiant de run historique ; les autres sources le préfixent.
    prefix = "dpe" if family.source_id == "DS-07" else f"dpe-{family.source_id.lower()}"
    import_run_id = (
        f"{prefix}:{manifest.release_key}:{manifest.department}:{DPE_TRANSFORMATION_VERSION}"
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
            schema_fingerprint=contract_fingerprint(family.source_id),
            department_code=manifest.department,
            data_source_id=family.source_id,
            # Les coordonnees BAN de l'extrait sont en Lambert 93. Le DPE lui-meme ne porte pas
            # de geometrie : la colonne dit d'ou viendraient les points, pas ce qu'on importe.
            source_srid=2154,
        )
        connection.execute("SET ROLE pipeline_rw")
        connection.commit()
        with tempfile.TemporaryDirectory(prefix="immo-dpe-") as temporary:
            local = Path(temporary) / "assessments.csv.gz"
            resolved = resolve_asset(
                catalog=catalog,
                object_store=object_store,
                manifest=manifest,
                asset=asset,
                destination=local,
            )
            # Une colonne indispensable absente est un changement de schema amont : il arrete
            # l'import avant toute ecriture, plutot que de produire des lignes vides.
            missing = missing_columns(local)
            catalog.record_asset_checks(
                release_id=manifest.release_id,
                department_code=manifest.department,
                layer="assessments",
                checksum_valid=True,
                schema_valid=not missing,
                schema_fingerprint=contract_fingerprint(family.source_id),
            )
            if missing:
                raise SystemExit(f"Colonnes absentes de l'extrait : {', '.join(missing)}")
            # `record_asset_checks` termine par `RESET ROLE` : reprendre le role d'ecriture.
            connection.execute("SET ROLE pipeline_rw")

            idempotency_key = (
                f"{manifest.release_id}:{manifest.department}:assessments:"
                f"{resolved.sha256}:{DPE_TRANSFORMATION_VERSION}"
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
                          jsonb_build_object('layer', 'assessments', 'raw_asset_id', %s::bigint,
                                             'snapshot_at', %s::text))
                """,
                (
                    import_run_id,
                    manifest.release_id,
                    manifest.department,
                    idempotency_key,
                    resolved.raw_asset_id,
                    snapshot_at.isoformat(),
                ),
            )
            # Purger **toute** la release avant d'ecrire, pas seulement ses versions
            # precedentes.
            #
            # Ne retirer que les autres versions laissait un reimport de la meme version buter
            # sur `energy_assessment_pkey` : un run interrompu, ou rejoue apres correctif de
            # mesure, ne repartait pas. La version vit dans l'identifiant pour qu'un correctif
            # atteigne les donnees — encore faut-il que l'ecriture puisse avoir lieu.
            #
            # L'import lit l'extrait entier a chaque fois : un remplacement complet de la
            # release est donc exact, et aucune table ne refere `energy_assessment`.
            connection.execute(
                "DELETE FROM observation.energy_assessment WHERE release_id = %(release_id)s",
                {"release_id": manifest.release_id},
            )
            connection.execute(STAGE)
            counters = stage_rows(
                connection,
                local,
                snapshot_at=snapshot_at,
                release_id=manifest.release_id,
                import_run_id=import_run_id,
                family=family,
            )
            counters += resolve_and_insert(
                connection,
                release_id=manifest.release_id,
                raw_asset_id=resolved.raw_asset_id,
                department=manifest.department,
                import_run_id=import_run_id,
            )
            counters["communes"] = record_coverage(connection, manifest.release_id)
            connection.execute(
                """
                UPDATE meta.import_run SET
                    status = 'succeeded', completed_at = now(),
                    source_row_count = %(source)s, normalized_row_count = %(normalized)s,
                    quarantined_row_count = %(quarantined)s,
                    deduplicated_row_count = %(duplicates)s,
                    runner_metadata = runner_metadata || %(detail)s::jsonb
                 WHERE id = %(id)s
                """,
                {
                    "id": import_run_id,
                    "source": counters["source_rows"],
                    "normalized": counters["matched_building"] + counters["matched_address_only"],
                    "quarantined": counters["source_rows"]
                    - counters["matched_building"]
                    - counters["matched_address_only"],
                    "duplicates": counters["duplicate_dpe_number"],
                    "detail": json.dumps(
                        {**counters, "asset_origin": resolved.origin}, sort_keys=True
                    ),
                },
            )
            connection.commit()

    print(json.dumps(dict(sorted(counters.items())), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
