#!/usr/bin/env python3
"""Matérialiser URB-001, URB-003 et URB-005 sur les documents importés — D2.

Trois des cinq features d'urbanisme se calculent sans lire une ligne de règlement. Les deux
autres — `URB-002 zone_rule_profile` et `URB-004 residual_footprint_proxy_m2` — exigent qu'un
humain structure les règles d'un document, ce qui relève de `D2b` et représente près de quatre
années-personne à l'échelle nationale. Elles sortent ici **absentes avec motif**.

## La zone représentative est un rang, pas un seuil

Mesuré sur le PLUi de Rennes Métropole croisé avec 51 577 parcelles : **30,5 % des parcelles
touchent plusieurs zones**, jusqu'à quinze. Trop fréquent pour traiter le cas en exception.

Mais le partage est massivement déséquilibré — 92 % des parcelles multi-zones ont une zone
dominante au-delà de 95 %, et **91 % ont une seconde zone sous 1 %** de leur surface. C'est du
bruit de numérisation entre deux découpages, pas un zonage partagé. Et quatre partages sur cinq
portent sur des sous-zones du **même** `typezone`.

**La zone représentative est donc celle qui couvre la plus grande part de la parcelle.** Aucun
seuil n'est inventé — la revue B4 a montré ce qu'un seuil sur un recouvrement coûte : le relecteur
y jugeait faux à 12,4 % et juste à 15,6 %.

Les zones secondaires ne sont pas perdues : elles sont conservées en provenance. Une parcelle à
cheval est juridiquement soumise aux deux règlements sur ses parties respectives, et le scoring
devra en tenir compte plutôt que de croire la parcelle homogène.

## `typezone` et `libelle` ne se comparent pas de la même façon

`typezone` est normalisé CNIG — `U`, `AUc`, `A`, `N` — et comparable entre documents. `libelle` est
le code du règlement local : `UG2b` à Rennes n'a aucun rapport avec `UG2b` ailleurs. `URB-001`
porte les deux, et seul `typezone` est comparable.
"""

import argparse
import json
import sys
from typing import Any

import psycopg

from immo_pipelines.cadastre.settings import CadastreSettings

FEATURE_VERSION = 1

# Ce que D2b apportera, et qui reste absent avec motif jusque-la.
DEFERRED = {
    "URB-002": ("source_value_missing", "manually validated structured profile for exact version"),
    "URB-004": ("source_value_missing", "geometric proxy after all indispensable validated rules"),
}

# `URB-001` : la zone de rang 1, ses secondaires conservees en provenance.
ZONE_SQL = """
WITH parcelles AS (
    SELECT unit.id AS unit_id, geometry.geom
      FROM reference.property_unit AS unit
      JOIN reference.property_unit_member AS member
        ON member.property_unit_id = unit.id AND member.entity_type = 'parcel'
      JOIN reference.parcel AS parcel
        ON 'parcel:cadastre:' || parcel.cadastral_id = member.entity_id
      JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
     WHERE unit.commune_code = %(commune)s
),
parts AS (
    SELECT parcelles.unit_id, zone.zone_code, zone.zone_type, document.id AS document_id,
           ST_Area(ST_Intersection(parcelles.geom, zone.geom)) AS part,
           ST_Area(parcelles.geom) AS unit_area
      FROM parcelles
      JOIN observation.urban_zone AS zone ON ST_Intersects(parcelles.geom, zone.geom)
      JOIN observation.urban_document AS document ON document.id = zone.document_id
     WHERE document.release_id = %(release_id)s
       AND document.status = 'opposable'
       AND ST_Area(ST_Intersection(parcelles.geom, zone.geom)) > 0
),
classees AS (
    SELECT parts.*,
           rank() OVER (PARTITION BY unit_id ORDER BY part DESC) AS rang,
           count(*) OVER (PARTITION BY unit_id, part) AS ex_aequo
      FROM parts
)
SELECT unit_id,
       max(zone_code) FILTER (WHERE rang = 1) AS zone_code,
       max(zone_type) FILTER (WHERE rang = 1) AS zone_type,
       max(document_id) FILTER (WHERE rang = 1) AS document_id,
       max(ex_aequo) FILTER (WHERE rang = 1) AS ex_aequo,
       round((max(part) FILTER (WHERE rang = 1) / nullif(max(unit_area), 0))::numeric, 4) AS part,
       jsonb_agg(
           jsonb_build_object(
               'zone_code', zone_code, 'zone_type', zone_type,
               'share', round((part / nullif(unit_area, 0))::numeric, 4)
           ) ORDER BY part DESC
       ) AS zones
  FROM classees
 GROUP BY unit_id
"""

# `URB-003` : comptage typé et aire d'intersection, jamais un jugement sur la contrainte.
CONSTRAINT_SQL = """
WITH parcelles AS (
    SELECT unit.id AS unit_id, geometry.geom
      FROM reference.property_unit AS unit
      JOIN reference.property_unit_member AS member
        ON member.property_unit_id = unit.id AND member.entity_type = 'parcel'
      JOIN reference.parcel AS parcel
        ON 'parcel:cadastre:' || parcel.cadastral_id = member.entity_id
      JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
     WHERE unit.commune_code = %(commune)s
)
SELECT parcelles.unit_id,
       jsonb_agg(
           jsonb_build_object(
               'constraint_type', constraint_row.constraint_type,
               'constraint_code', constraint_row.constraint_code,
               'intersection_m2',
               round(ST_Area(ST_Intersection(parcelles.geom, constraint_row.geom))::numeric, 1)
           ) ORDER BY constraint_row.constraint_type, constraint_row.constraint_code
       ) AS constraints,
       count(*) AS constraint_count
  FROM parcelles
  JOIN observation.urban_constraint AS constraint_row
    ON ST_Intersects(parcelles.geom, constraint_row.geom)
  JOIN observation.urban_document AS document ON document.id = constraint_row.document_id
 WHERE document.release_id = %(release_id)s
 GROUP BY parcelles.unit_id
"""


def persist(connection: psycopg.Connection[Any], rows: list[tuple[Any, ...]]) -> None:
    """Une ligne par feature et par unité, valeur **ou** motif d'absence, jamais les deux."""
    if not rows:
        return
    connection.cursor().executemany(
        """
        INSERT INTO feature.feature_value (
            property_unit_id, feature_code, feature_version, numeric_value, text_value,
            json_value, missing_reason, source_observation_ids, source_release_ids, formula,
            transformation_version
        ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s)
        ON CONFLICT (property_unit_id, building_id, feature_code, feature_version)
        DO UPDATE SET numeric_value = excluded.numeric_value,
                      text_value = excluded.text_value,
                      json_value = excluded.json_value,
                      missing_reason = excluded.missing_reason,
                      source_observation_ids = excluded.source_observation_ids,
                      source_release_ids = excluded.source_release_ids,
                      computed_at = now()
        """,
        rows,
    )


def commune_rows(
    connection: psycopg.Connection[Any], commune: str, release_id: str
) -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    counters = {"zoned": 0, "ex_aequo": 0, "constrained": 0}
    rows: list[tuple[Any, ...]] = []
    releases = json.dumps([release_id])

    zones = {
        record[0]: record
        for record in connection.execute(
            ZONE_SQL, {"commune": commune, "release_id": release_id}
        ).fetchall()
    }
    constraints = {
        record[0]: record
        for record in connection.execute(
            CONSTRAINT_SQL, {"commune": commune, "release_id": release_id}
        ).fetchall()
    }

    units = [
        record[0]
        for record in connection.execute(
            "SELECT id FROM reference.property_unit WHERE commune_code = %s", (commune,)
        ).fetchall()
    ]

    for unit in units:
        zone = zones.get(unit)
        if zone is None:
            # Aucune zone opposable ne couvre cette parcelle : c'est le RNU, ou une commune sans
            # document. Une absence motivee, jamais un blanc.
            rows.append(
                (
                    unit,
                    "URB-001",
                    FEATURE_VERSION,
                    None,
                    None,
                    None,
                    "source_not_accepted",
                    json.dumps([]),
                    releases,
                    "representative overlap with opposable zone at snapshot",
                    "market-data@1",
                )
            )
        elif zone[4] and int(zone[4]) > 1:
            # Ex aequo parfait : le rang ne departage pas, et choisir serait arbitraire. La
            # quatrieme classe existe pour cela.
            counters["ex_aequo"] += 1
            rows.append(
                (
                    unit,
                    "URB-001",
                    FEATURE_VERSION,
                    None,
                    None,
                    None,
                    "ambiguous_match",
                    json.dumps(zone[6]),
                    releases,
                    "representative overlap with opposable zone at snapshot",
                    "market-data@1",
                )
            )
        else:
            counters["zoned"] += 1
            rows.append(
                (
                    unit,
                    "URB-001",
                    FEATURE_VERSION,
                    None,
                    # `zone_type` normalise en premier, `libelle` local ensuite : seul le premier
                    # est comparable entre documents.
                    f"{zone[2]}|{zone[1]}",
                    None,
                    None,
                    json.dumps(zone[6]),
                    releases,
                    "representative overlap with opposable zone at snapshot",
                    "market-data@1",
                )
            )

        constraint = constraints.get(unit)
        if constraint is None:
            # Zero contrainte n'est affirmable que sur une couverture acceptee complete, ce que
            # DS-08 n'a pas — 300 communes sur 332. L'absence reste une absence.
            rows.append(
                (
                    unit,
                    "URB-003",
                    FEATURE_VERSION,
                    None,
                    None,
                    None,
                    "source_not_accepted",
                    json.dumps([]),
                    releases,
                    "typed constraint count and intersection area",
                    "market-data@1",
                )
            )
        else:
            counters["constrained"] += 1
            rows.append(
                (
                    unit,
                    "URB-003",
                    FEATURE_VERSION,
                    None,
                    None,
                    json.dumps(constraint[1]),
                    None,
                    json.dumps([]),
                    releases,
                    "typed constraint count and intersection area",
                    "market-data@1",
                )
            )

        # `URB-005` vaut zero partout tant que D2b n'a rien valide. C'est un resultat, pas un
        # echec : la feature existe pour publier l'incompletude de l'interpretation reglementaire.
        rows.append(
            (
                unit,
                "URB-005",
                FEATURE_VERSION,
                0.0,
                None,
                None,
                None,
                json.dumps([]),
                releases,
                "validated required rules / required rules",
                "market-data@1",
            )
        )

        for code, (reason, formula) in DEFERRED.items():
            rows.append(
                (
                    unit,
                    code,
                    FEATURE_VERSION,
                    None,
                    None,
                    None,
                    reason,
                    json.dumps([]),
                    releases,
                    formula,
                    "market-data@1",
                )
            )

    return rows, counters


def main() -> int:
    parser = argparse.ArgumentParser(description="Matérialiser URB-001, URB-003 et URB-005")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--release", default="DS-08@2026-09-14")
    parser.add_argument("--commune", default=None, help="limiter à une commune, pour vérifier")
    arguments = parser.parse_args()

    settings = CadastreSettings.from_environment()
    totals = {"units": 0, "zoned": 0, "ex_aequo": 0, "constrained": 0}
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    ) as connection:
        connection.execute("SET ROLE pipeline_rw")
        connection.execute("SET LOCAL statement_timeout = '1800s'")
        communes = (
            [arguments.commune]
            if arguments.commune
            else [
                record[0]
                for record in connection.execute(
                    "SELECT DISTINCT commune_code FROM reference.property_unit "
                    "WHERE department_code = %s ORDER BY 1",
                    (arguments.department,),
                ).fetchall()
            ]
        )
        for commune in communes:
            rows, counters = commune_rows(connection, commune, arguments.release)
            persist(connection, rows)
            connection.commit()
            totals["units"] += len(rows) // 5
            for key, value in counters.items():
                totals[key] += value
            print(
                f"  {commune} : {len(rows) // 5} unités, {counters['zoned']} zonées, "
                f"{counters['constrained']} contraintes",
                flush=True,
            )

    print(json.dumps(totals, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
