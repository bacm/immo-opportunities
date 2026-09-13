#!/usr/bin/env python3
"""Regrouper les enregistrements contigus en bâtiments physiques — BUG-12.

Les contrats `LAND-002` et `LAND-009` demandent des bâtiments physiques, dédupliqués. Ce script
matérialise ce regroupement ; il ne touche à aucune donnée source.

Le regroupement se fait par contiguïté (`ST_ClusterDBSCAN`, 1 cm), commune par commune. Le choix
est validé par recoupement entre deux levés indépendants — voir
`docs/data/physical-building-grouping-35.md`.

Idempotent : relancer pour la même source, le même département et la même version de regroupement
reconstruit à l'identique. La version est incluse dans l'identifiant du groupe, de sorte qu'un
changement de méthode ne peut pas se confondre avec l'existant — la leçon de BUG-09, où une clé
d'idempotence sans version rendait un correctif inapplicable.
"""

import argparse
import sys

import psycopg

from immo_pipelines.cadastre.settings import CadastreSettings

# 1 : contiguite stricte a 1 cm, par commune.
GROUPING_VERSION = "1"

# 1 cm : deux enregistrements qui partagent un mur ne sont jamais separes par plus que le bruit
# de numerisation. Elargir davantage souderait des batiments voisins reellement distincts.
EPSILON_METRES = 0.01

SOURCES = {
    "rnb": ("reference.building", "id"),
    "cadastre": ("reference.active_cadastral_building", "id"),
}


def build(source: str, department: str) -> dict[str, int]:
    table, identifier = SOURCES[source]
    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        connection.execute("SET ROLE pipeline_rw")
        connection.execute(
            """
            DELETE FROM reference.physical_building
             WHERE source = %s AND department_code = %s AND grouping_version = %s
            """,
            (source, department, GROUPING_VERSION),
        )
        connection.execute(
            f"""
            CREATE TEMPORARY TABLE grouped ON COMMIT DROP AS
            WITH clustered AS (
                SELECT source.{identifier} AS building_id,
                       source.commune_code,
                       ST_ClusterDBSCAN(source.geom, eps := %(epsilon)s, minpoints := 1)
                           OVER (PARTITION BY source.commune_code) AS cluster_index
                  FROM {table} AS source
                 WHERE source.department_code = %(department)s
                   AND source.commune_code IS NOT NULL
            )
            SELECT clustered.building_id, clustered.commune_code,
                   -- L'identifiant derive du plus petit membre : deterministe, reproductible,
                   -- et sans sequence a gerer. L'indice de grappe, lui, depend de l'ordre de
                   -- lecture et ne doit jamais sortir d'ici.
                   'physical:' || %(source)s || ':' || %(version)s || ':'
                       || min(clustered.building_id) OVER (
                              PARTITION BY clustered.commune_code, clustered.cluster_index
                          ) AS physical_building_id
              FROM clustered
            """,
            {
                "epsilon": EPSILON_METRES,
                "department": department,
                "source": source,
                "version": GROUPING_VERSION,
            },
        )
        connection.execute(
            """
            INSERT INTO reference.physical_building (
                id, source, commune_code, department_code, member_count, grouping_version
            )
            SELECT physical_building_id, %(source)s, commune_code, %(department)s,
                   count(*), %(version)s
              FROM grouped
             GROUP BY physical_building_id, commune_code
            """,
            {"source": source, "department": department, "version": GROUPING_VERSION},
        )
        connection.execute(
            """
            INSERT INTO reference.physical_building_member (physical_building_id, building_id)
            SELECT physical_building_id, building_id FROM grouped
            """
        )
        counts = connection.execute(
            """
            SELECT count(*), coalesce(sum(member_count), 0)
              FROM reference.physical_building
             WHERE source = %s AND department_code = %s AND grouping_version = %s
            """,
            (source, department, GROUPING_VERSION),
        ).fetchone()
    return {"physical_buildings": int(counts[0]), "source_records": int(counts[1])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sorted(SOURCES), required=True)
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    arguments = parser.parse_args()

    result = build(arguments.source, arguments.department)
    excess = result["source_records"] - result["physical_buildings"]
    share = 100 * excess / result["source_records"] if result["source_records"] else 0
    print(
        f"{arguments.source} {arguments.department} : "
        f"{result['source_records']} enregistrements → {result['physical_buildings']} bâtiments "
        f"({share:.1f} % de surcomptage évité)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
