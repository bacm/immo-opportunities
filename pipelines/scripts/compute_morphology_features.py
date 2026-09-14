#!/usr/bin/env python3
"""Matérialiser LAND-001..010 et BLD-001..003 sur les releases acceptées — B5.

Le moteur pur est livré et testé depuis v0.3 ; ce qui manquait, c'est le calcul sur données
réelles **acceptées**, avec provenance intacte.

## Ce qui est calculable aujourd'hui, et ce qui ne l'est pas

Une seule release est acceptée sur le 35 : le **cadastre Etalab**. Le RNB est `pending`, la BD
TOPO, la BDNB et la BAN sont `display_only`. Les features qui en dépendent sortent donc
**absentes avec motif**, jamais à zéro et jamais imputées :

| Feature | Source | Sort |
|---|---|---|
| LAND-001..007, 009 | cadastre, accepté | calculées |
| LAND-008 | BD TOPO, `display_only` | `source_not_accepted` |
| LAND-010 | cadastre, champ `type` sans table de valeurs au contrat | `source_value_missing` |
| BLD-001..003 | BDNB et BD TOPO, `display_only` | `source_not_accepted` |

`LAND-010` mérite une explication : le cadastre distingue bien deux types de bâti, et 27,1 % des
enregistrements portent le code `02`. Mais le contrat `DS-01/v1.json` déclare `type` comme
`string|null` **sans dire ce que valent `01` et `02`**. Décider ici que `02` signifie « léger »
serait inventer une interprétation. La feature reste donc absente jusqu'à ce que la table de
valeurs soit sourcée et écrite au contrat.

## Le bâti utilisé est le bâti cadastral, pas le RNB

Ce n'est pas un contournement du fait que le RNB soit `pending` : c'est ce que le contrat
`morphology-v1` demande depuis le début — `datasets: [DS-01, DS-03, DS-04]`, sans DS-02. Et c'est
cohérent avec ce que la revue manuelle a mesuré, le bâti cadastral étant levé avec le parcellaire
et coïncidant avec lui par construction.

Les bâtiments sont comptés **dédupliqués**, par `reference.physical_building` (BUG-12) : compter
les enregistrements surestimerait `LAND-009` de 44 %.
"""

import argparse
import json
import sys
from collections.abc import Iterator

import psycopg
from shapely import wkb
from shapely.geometry.base import BaseGeometry

from immo_pipelines.cadastre.settings import CadastreSettings
from immo_pipelines.spatial.features import BuildingFootprint, compute_land_features

FEATURE_VERSION = 1

# Features dont la source n'est pas acceptee sur ce territoire, avec le motif exact.
UNSUPPORTED_LAND = {
    "LAND-008": (
        "source_not_accepted",
        "length(intersection(boundary(unit), buffer(public roads, threshold)))",
    ),
    "LAND-010": ("source_value_missing", "area(union(light buildings)) / LAND-002"),
}
UNSUPPORTED_BUILDING = {
    "BLD-001": ("source_not_accepted", "highest-priority observed use without prediction"),
    "BLD-002": ("source_not_accepted", "highest-priority observed height without imputation"),
    "BLD-003": (
        "source_not_accepted",
        "highest-priority observed dwelling count without imputation",
    ),
}


def accepted_release(connection: psycopg.Connection[object], source_name: str) -> str | None:
    row = connection.execute(
        """
        SELECT release.id FROM meta.dataset_release AS release
          JOIN meta.data_source AS source ON source.id = release.data_source_id
         WHERE source.name = %s AND release.acceptance_status = 'accepted'
         ORDER BY release.source_published_on DESC LIMIT 1
        """,
        (source_name,),
    ).fetchone()
    return str(row[0]) if row else None


def communes(connection: psycopg.Connection[object], department: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT commune_code FROM reference.parcel
         WHERE department_code = %s AND commune_code IS NOT NULL ORDER BY 1
        """,
        (department,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def unit_rows(
    connection: psycopg.Connection[object], commune: str
) -> Iterator[tuple[str, BaseGeometry, list[BuildingFootprint]]]:
    """Une unité foncière par parcelle, avec les bâtiments physiques qui la touchent.

    Le regroupement par bâtiment physique est appliqué **avant** le comptage : c'est lui qui fait
    de `LAND-009` un comptage de bâtiments et non d'enregistrements.

    La sous-requête est latérale et corrélée à la géométrie de la parcelle, de sorte que l'index
    GiST du bâti soit utilisé parcelle par parcelle. Joindre le bâti de la commune entière puis
    filtrer produirait un produit croisé de plusieurs millions de lignes par commune.
    """
    cursor = connection.execute(
        """
        SELECT unit.id,
               ST_AsBinary(parcel_geometry.geom) AS parcel_geom,
               coalesce(touching.buildings, '[]'::jsonb) AS buildings
          FROM reference.property_unit AS unit
          JOIN reference.property_unit_member AS member
            ON member.property_unit_id = unit.id AND member.entity_type = 'parcel'
          JOIN reference.parcel AS parcel
            ON 'parcel:cadastre:' || parcel.cadastral_id = member.entity_id
          JOIN reference.parcel_geometry AS parcel_geometry ON parcel_geometry.id = parcel.id
          LEFT JOIN LATERAL (
              SELECT jsonb_agg(
                         jsonb_build_object(
                             'id', grouped.physical_building_id,
                             'geom', encode(ST_AsBinary(grouped.geom), 'hex')
                         )
                     ) AS buildings
                FROM (
                    SELECT physical_member.physical_building_id,
                           ST_Union(building.geom) AS geom
                      FROM reference.active_cadastral_building AS building
                      JOIN reference.physical_building_member AS physical_member
                        -- `building_id` est du texte : les identifiants RNB en sont, ceux
                        -- du cadastre sont des entiers. Le texte est le type commun.
                        ON physical_member.building_id = building.id::text
                     WHERE ST_Intersects(building.geom, parcel_geometry.geom)
                     GROUP BY physical_member.physical_building_id
                ) AS grouped
          ) AS touching ON true
         WHERE unit.commune_code = %s
        """,
        (commune,),
    )
    for unit_id, parcel_geom, buildings in cursor:
        footprints = [
            BuildingFootprint(
                entity_id=str(item["id"]),
                geometry=wkb.loads(bytes.fromhex(item["geom"])),
                source_ids=(str(item["id"]),),
            )
            for item in buildings
        ]
        yield str(unit_id), wkb.loads(bytes(parcel_geom)), footprints


def persist(
    connection: psycopg.Connection[object],
    unit_id: str,
    results: dict[str, object],
    release_ids: list[str],
) -> None:
    """Une ligne par feature, valeur **ou** motif d'absence, jamais les deux ni aucun des deux."""
    rows = []
    for code, result in results.items():
        rows.append(
            (
                unit_id,
                code,
                FEATURE_VERSION,
                getattr(result, "numeric_value", None),
                getattr(result, "text_value", None),
                getattr(result, "missing_reason", None),
                json.dumps(list(getattr(result, "source_ids", ()))),
                json.dumps(release_ids),
                getattr(result, "formula", ""),
                getattr(result, "transformation_version", "morphology@1"),
            )
        )
    connection.cursor().executemany(
        """
        INSERT INTO feature.feature_value (
            property_unit_id, feature_code, feature_version, numeric_value, text_value,
            missing_reason, source_observation_ids, source_release_ids, formula,
            transformation_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        ON CONFLICT (property_unit_id, building_id, feature_code, feature_version)
        DO UPDATE SET numeric_value = excluded.numeric_value,
                      text_value = excluded.text_value,
                      missing_reason = excluded.missing_reason,
                      source_observation_ids = excluded.source_observation_ids,
                      source_release_ids = excluded.source_release_ids,
                      formula = excluded.formula,
                      transformation_version = excluded.transformation_version,
                      computed_at = now()
        """,
        rows,
    )


class Absent:
    """Une feature dont la source n'est pas utilisable, avec son motif et sa formule."""

    def __init__(self, reason: str, formula: str) -> None:
        self.numeric_value = None
        self.text_value = None
        self.missing_reason = reason
        self.source_ids: tuple[str, ...] = ()
        self.formula = formula
        self.transformation_version = "morphology@1"


# `BLD-001..003` ne sont pas materialisees dans cette passe, et c'est un constat, pas un oubli.
#
# Les trois features decrivent un batiment — usage, hauteur, nombre de logements — et leurs
# sources, BDNB et BD TOPO, sont `display_only`. Elles sortiraient donc toutes trois en
# `source_not_accepted`, ce qui serait sans interet mais sans danger.
#
# Le vrai obstacle est ailleurs : `feature.feature_value.building_id` refere
# `reference.building`, c'est-a-dire les **enregistrements RNB**. Or BUG-12 a etabli que le sujet
# du contrat est le **batiment physique**, et que compter des enregistrements surestime de 44 %.
# Ecrire ces lignes sur des enregistrements RNB reviendrait a graver dans le stockage le sujet
# que le ticket precedent vient d'invalider — et sur une source qui n'est meme pas acceptee.
#
# La correction est un changement de schema, hors du perimetre de B5. Le rapport le dit, et les
# trois features y figurent comme indisponibles pour le departement entier, avec ce motif.


def main() -> int:
    parser = argparse.ArgumentParser(description="Matérialiser les features morphologiques")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument("--commune", default=None, help="limiter à une commune, pour vérifier")
    arguments = parser.parse_args()

    settings = CadastreSettings.from_environment()
    with psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
        row_factory=psycopg.rows.tuple_row,
    ) as connection:
        cadastre = accepted_release(connection, "Cadastre Etalab consolidé issu du PCI Vecteur")
        if cadastre is None:
            print(
                "Aucune release cadastre acceptée : rien ne peut être calculé sans imputer.",
                file=sys.stderr,
            )
            return 1
        connection.execute("SET ROLE pipeline_rw")
        targets = (
            [arguments.commune] if arguments.commune else communes(connection, arguments.department)
        )
        computed = 0
        for commune in targets:
            for unit_id, parcel_geometry, footprints in unit_rows(connection, commune):
                results: dict[str, object] = dict(
                    compute_land_features(
                        [parcel_geometry],
                        footprints,
                        # Le bâti cadastral est levé avec le parcellaire : la résolution est
                        # complète au sens du moteur, il n'y a pas d'appariement en attente.
                        building_resolution_complete=True,
                        roads=None,
                        roads_accepted=False,
                    )
                )
                for code, (reason, formula) in UNSUPPORTED_LAND.items():
                    results[code] = Absent(reason, formula)
                persist(connection, unit_id, results, [cadastre])
                computed += 1
            connection.commit()
            print(f"{commune} : {computed} unités cumulées", flush=True)
    print(
        json.dumps(
            {"department": arguments.department, "units": computed},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
