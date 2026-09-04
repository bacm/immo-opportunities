import json
from decimal import Decimal
from typing import Any, Literal, TypedDict, cast

from sqlalchemy import text

from immo.database import get_engine


class AreaRecord(TypedDict):
    id: str
    area_type: str
    code: str
    name: str
    department_code: str
    center: list[float]
    bbox: list[float]


class SearchRecord(TypedDict):
    entity_type: Literal["address", "area", "parcel"]
    id: str
    label: str
    secondary_label: str
    center: list[float]
    bbox: list[float]


class ParcelSummary(TypedDict):
    id: str
    cadastral_id: str
    commune_code: str
    commune_name: str
    area_m2: float
    building_count: int
    building_footprint_m2: float
    center: list[float]


class ViewportResult(TypedDict):
    coverage: Literal["covered", "outside_coverage"]
    partial: bool
    items: list[ParcelSummary]


class EntityDetail(TypedDict):
    id: str
    entity_type: str
    label: str
    commune_code: str | None
    commune_name: str | None
    department_code: str
    area_m2: float | None
    center: list[float]
    bbox: list[float]
    geometry: dict[str, Any]
    properties: dict[str, Any]
    related_entities: list[dict[str, Any]]
    sources: list[dict[str, Any]]


def _number(value: object) -> float:
    return float(cast(Decimal | float, value))


def _bbox(row: dict[str, Any]) -> list[float]:
    return [_number(row[key]) for key in ("west", "south", "east", "north")]


def _center(row: dict[str, Any]) -> list[float]:
    return [_number(row["longitude"]), _number(row["latitude"])]


def list_areas(*, department_code: str, area_type: str) -> list[AreaRecord]:
    statement = text(
        """
        SELECT id, area_type, code, COALESCE(name, code) AS name, department_code,
               ST_X(ST_Transform(ST_PointOnSurface(geom), 4326)) AS longitude,
               ST_Y(ST_Transform(ST_PointOnSurface(geom), 4326)) AS latitude,
               ST_XMin(ST_Envelope(ST_Transform(geom, 4326))) AS west,
               ST_YMin(ST_Envelope(ST_Transform(geom, 4326))) AS south,
               ST_XMax(ST_Envelope(ST_Transform(geom, 4326))) AS east,
               ST_YMax(ST_Envelope(ST_Transform(geom, 4326))) AS north
          FROM reference.area
         WHERE department_code = :department_code AND area_type = :area_type
         ORDER BY name, code
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(
            statement,
            {"department_code": department_code, "area_type": area_type},
        ).mappings()
        return [
            {
                "id": str(row["id"]),
                "area_type": str(row["area_type"]),
                "code": str(row["code"]),
                "name": str(row["name"]),
                "department_code": str(row["department_code"]),
                "center": _center(dict(row)),
                "bbox": _bbox(dict(row)),
            }
            for row in rows
        ]


def search_entities(query: str, *, department_code: str, limit: int) -> list[SearchRecord]:
    statement = text(
        """
        WITH candidates AS (
            SELECT 'area'::text AS entity_type,
                   area.id,
                   COALESCE(area.name, area.code) AS label,
                   'Commune · ' || area.code AS secondary_label,
                   area.geom,
                   CASE
                       WHEN unaccent(lower(COALESCE(area.name, '')))
                            = unaccent(lower(:query)) THEN 1.0
                       WHEN unaccent(lower(COALESCE(area.name, '')))
                            LIKE unaccent(lower(:query)) || '%' THEN 0.95
                       ELSE similarity(
                           unaccent(lower(COALESCE(area.name, ''))),
                           unaccent(lower(:query))
                       )
                   END AS relevance
              FROM reference.area AS area
             WHERE area.department_code = :department_code
               AND area.area_type = 'commune'
               AND (
                    unaccent(lower(COALESCE(area.name, '')))
                        LIKE '%' || unaccent(lower(:query)) || '%'
                    OR area.code LIKE upper(:query) || '%'
               )
            UNION ALL
            SELECT 'parcel', parcel.id, parcel.cadastral_id,
                   'Parcelle · ' || parcel.commune_code,
                   geometry.geom,
                   CASE WHEN parcel.cadastral_id
                        = regexp_replace(upper(:query), '[^0-9A-Z]', '', 'g')
                        THEN 1.0 ELSE 0.9 END
              FROM reference.parcel AS parcel
              JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
             WHERE parcel.department_code = :department_code
               AND parcel.cadastral_id LIKE
                   regexp_replace(upper(:query), '[^0-9A-Z]', '', 'g') || '%'
            UNION ALL
            SELECT 'address', address.id, address.display_label,
                   'Adresse · ' || address.commune_code,
                   address.geom,
                   similarity(address.normalized_label, unaccent(lower(:query)))
              FROM reference.address AS address
             WHERE address.department_code = :department_code
               AND address.normalized_label % unaccent(lower(:query))
               AND EXISTS (
                   SELECT 1
                     FROM meta.entity_source_identifier AS identifier
                     JOIN meta.active_dataset_release AS active
                       ON active.release_id = identifier.last_release_id
                      AND active.data_source_id = 'DS-05'
                      AND active.scope_type = 'department'
                      AND active.scope_code = address.department_code
                    WHERE identifier.entity_type = 'address'
                      AND identifier.entity_id = address.id
                      AND identifier.data_source_id = 'DS-05'
               )
        ), ranked AS (
            SELECT *,
                   ST_Transform(ST_PointOnSurface(geom), 4326) AS center_4326,
                   ST_Envelope(ST_Transform(geom, 4326)) AS envelope_4326
              FROM candidates
             ORDER BY relevance DESC, label
             LIMIT :limit
        )
        SELECT entity_type, id, label, secondary_label,
               ST_X(center_4326) AS longitude,
               ST_Y(center_4326) AS latitude,
               ST_XMin(envelope_4326) AS west,
               ST_YMin(envelope_4326) AS south,
               ST_XMax(envelope_4326) AS east,
               ST_YMax(envelope_4326) AS north
          FROM ranked
         ORDER BY relevance DESC, label
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(
            statement,
            {"query": query, "department_code": department_code, "limit": limit},
        ).mappings()
        return [
            {
                "entity_type": cast(Literal["address", "area", "parcel"], row["entity_type"]),
                "id": str(row["id"]),
                "label": str(row["label"]),
                "secondary_label": str(row["secondary_label"]),
                "center": _center(dict(row)),
                "bbox": _bbox(dict(row)),
            }
            for row in rows
        ]


def list_property_units_in_viewport(
    *, west: float, south: float, east: float, north: float, limit: int
) -> ViewportResult:
    statement = text(
        """
        WITH bounds AS (
            SELECT ST_Transform(ST_MakeEnvelope(:west, :south, :east, :north, 4326), 2154) AS geom
        ), coverage AS (
            SELECT EXISTS (
                SELECT 1 FROM reference.area, bounds
                 WHERE area.department_code IN ('22', '29', '35', '56')
                   AND area.area_type = 'commune'
                   AND area.geom && bounds.geom
                   AND ST_Intersects(area.geom, bounds.geom)
            ) AS is_covered
        ), visible AS MATERIALIZED (
            SELECT parcel.id,
                   parcel.cadastral_id,
                   parcel.commune_code,
                   parcel.department_code,
                   geometry.geom,
                   ST_Distance(
                       ST_PointOnSurface(geometry.geom), ST_Centroid(bounds.geom)
                   ) AS distance
              FROM reference.parcel AS parcel
              JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
              CROSS JOIN bounds
             WHERE parcel.department_code IN ('22', '29', '35', '56')
               AND geometry.geom && bounds.geom
               AND ST_Intersects(geometry.geom, bounds.geom)
             ORDER BY distance, parcel.cadastral_id
             LIMIT :fetch_limit
        )
        SELECT visible.id,
               visible.cadastral_id,
               visible.commune_code,
               COALESCE(area.name, visible.commune_code) AS commune_name,
               ST_Area(visible.geom) AS area_m2,
               COALESCE(buildings.building_count, 0) AS building_count,
               COALESCE(buildings.building_footprint_m2, 0) AS building_footprint_m2,
               ST_X(ST_Transform(ST_PointOnSurface(visible.geom), 4326)) AS longitude,
               ST_Y(ST_Transform(ST_PointOnSurface(visible.geom), 4326)) AS latitude,
               coverage.is_covered
          FROM visible
          CROSS JOIN coverage
          LEFT JOIN reference.area AS area
            ON area.area_type = 'commune' AND area.code = visible.commune_code
          LEFT JOIN LATERAL (
              SELECT count(*) AS building_count,
                     ST_Area(ST_UnaryUnion(ST_Collect(
                         ST_Intersection(building.geom, visible.geom)
                     )))
                         AS building_footprint_m2
                FROM reference.active_cadastral_building AS building
               WHERE building.department_code = visible.department_code
                 AND building.geom && visible.geom
                 AND ST_Intersects(building.geom, visible.geom)
          ) AS buildings ON true
         ORDER BY visible.distance, visible.cadastral_id
        """
    )
    coverage_statement = text(
        """
        SELECT EXISTS (
            SELECT 1
              FROM reference.area
             WHERE department_code IN ('22', '29', '35', '56') AND area_type = 'commune'
               AND geom && ST_Transform(ST_MakeEnvelope(:west, :south, :east, :north, 4326), 2154)
               AND ST_Intersects(
                   geom,
                   ST_Transform(ST_MakeEnvelope(:west, :south, :east, :north, 4326), 2154)
               )
        )
        """
    )
    parameters = {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "fetch_limit": limit + 1,
    }
    with get_engine().connect() as connection:
        rows = list(connection.execute(statement, parameters).mappings())
        if rows:
            covered = bool(rows[0]["is_covered"])
        else:
            covered = bool(connection.execute(coverage_statement, parameters).scalar_one())

    partial = len(rows) > limit
    return {
        "coverage": "covered" if covered else "outside_coverage",
        "partial": partial,
        "items": [
            {
                "id": "property-unit:parcel:" + str(row["cadastral_id"]),
                "cadastral_id": str(row["cadastral_id"]),
                "commune_code": str(row["commune_code"]),
                "commune_name": str(row["commune_name"]),
                "area_m2": _number(row["area_m2"]),
                "building_count": int(row["building_count"]),
                "building_footprint_m2": _number(row["building_footprint_m2"]),
                "center": _center(dict(row)),
            }
            for row in rows[:limit]
        ],
    }


def _detail_from_row(row: dict[str, Any], *, entity_type: str) -> EntityDetail:
    geometry = row["geometry"]
    properties = row["properties"]
    related = row["related_entities"]
    sources = row["sources"]
    return {
        "id": str(row["id"]),
        "entity_type": entity_type,
        "label": str(row["label"]),
        "commune_code": str(row["commune_code"]) if row["commune_code"] else None,
        "commune_name": str(row["commune_name"]) if row["commune_name"] else None,
        "department_code": str(row["department_code"]),
        "area_m2": _number(row["area_m2"]) if row["area_m2"] is not None else None,
        "center": _center(row),
        "bbox": _bbox(row),
        "geometry": cast(
            dict[str, Any], json.loads(geometry) if isinstance(geometry, str) else geometry
        ),
        "properties": cast(dict[str, Any], properties),
        "related_entities": cast(list[dict[str, Any]], related),
        "sources": cast(list[dict[str, Any]], sources),
    }


def find_parcel(parcel_id: str) -> EntityDetail | None:
    cadastral_id = parcel_id.removeprefix("parcel:cadastre:")
    statement = text(
        """
        SELECT parcel.id,
               parcel.cadastral_id AS label,
               parcel.commune_code,
               area.name AS commune_name,
               parcel.department_code,
               ST_Area(geometry.geom) AS area_m2,
               ST_X(ST_Transform(ST_PointOnSurface(geometry.geom), 4326)) AS longitude,
               ST_Y(ST_Transform(ST_PointOnSurface(geometry.geom), 4326)) AS latitude,
               ST_XMin(ST_Envelope(ST_Transform(geometry.geom, 4326))) AS west,
               ST_YMin(ST_Envelope(ST_Transform(geometry.geom, 4326))) AS south,
               ST_XMax(ST_Envelope(ST_Transform(geometry.geom, 4326))) AS east,
               ST_YMax(ST_Envelope(ST_Transform(geometry.geom, 4326))) AS north,
               ST_AsGeoJSON(ST_Transform(geometry.geom, 4326))::jsonb AS geometry,
               jsonb_build_object(
                   'cadastral_id', parcel.cadastral_id,
                   'section', source.section,
                   'number', source.number,
                   'stated_area_m2', source.stated_area_m2
               ) AS properties,
               COALESCE((
                   SELECT jsonb_agg(jsonb_build_object(
                       'entity_type', 'building',
                       'id', 'building:cadastre:' || building.source_feature_id,
                       'label', building.source_feature_id
                   ) ORDER BY building.source_feature_id)
                     FROM reference.active_cadastral_building AS building
                    WHERE building.geom && geometry.geom
                      AND ST_Intersects(building.geom, geometry.geom)
               ), '[]'::jsonb) AS related_entities,
               jsonb_build_array(jsonb_build_object(
                   'data_source_id', 'DS-01',
                   'release_id', geometry.release_id,
                   'raw_asset_id', geometry.raw_asset_id,
                   'producer', 'Etalab · DGFiP'
               )) AS sources
          FROM reference.parcel AS parcel
          JOIN reference.parcel_geometry AS geometry ON geometry.id = parcel.id
          JOIN reference.active_cadastral_parcel AS source
            ON source.cadastral_id = parcel.cadastral_id
          LEFT JOIN reference.area AS area
            ON area.area_type = 'commune' AND area.code = parcel.commune_code
         WHERE parcel.cadastral_id = :cadastral_id
        """
    )
    with get_engine().connect() as connection:
        row = connection.execute(statement, {"cadastral_id": cadastral_id}).mappings().one_or_none()
    return _detail_from_row(dict(row), entity_type="parcel") if row else None


def find_building(building_id: str) -> EntityDetail | None:
    source_feature_id = building_id.removeprefix("building:cadastre:")
    statement = text(
        """
        SELECT 'building:cadastre:' || building.source_feature_id AS id,
               building.source_feature_id AS label,
               building.commune_code,
               area.name AS commune_name,
               building.department_code,
               ST_Area(building.geom) AS area_m2,
               ST_X(ST_Transform(ST_PointOnSurface(building.geom), 4326)) AS longitude,
               ST_Y(ST_Transform(ST_PointOnSurface(building.geom), 4326)) AS latitude,
               ST_XMin(ST_Envelope(ST_Transform(building.geom, 4326))) AS west,
               ST_YMin(ST_Envelope(ST_Transform(building.geom, 4326))) AS south,
               ST_XMax(ST_Envelope(ST_Transform(building.geom, 4326))) AS east,
               ST_YMax(ST_Envelope(ST_Transform(building.geom, 4326))) AS north,
               ST_AsGeoJSON(ST_Transform(building.geom, 4326))::jsonb AS geometry,
               jsonb_build_object(
                   'cadastral_type', building.cadastral_type,
                   'cadastral_name', building.cadastral_name,
                   'was_repaired', building.was_repaired
               ) AS properties,
               COALESCE((
                   SELECT jsonb_agg(DISTINCT jsonb_build_object(
                       'entity_type', 'parcel',
                       'id', parcel.id,
                       'label', parcel.cadastral_id
                   ))
                     FROM reference.parcel_geometry AS geometry
                     JOIN reference.parcel AS parcel ON parcel.id = geometry.id
                    WHERE geometry.geom && building.geom
                      AND ST_Intersects(geometry.geom, building.geom)
               ), '[]'::jsonb) AS related_entities,
               jsonb_build_array(jsonb_build_object(
                   'data_source_id', 'DS-01',
                   'release_id', building.release_id,
                   'raw_asset_id', building.raw_asset_id,
                   'producer', 'Etalab · DGFiP'
               )) AS sources
          FROM reference.active_cadastral_building AS building
          LEFT JOIN reference.area AS area
            ON area.area_type = 'commune' AND area.code = building.commune_code
         WHERE building.source_feature_id = :source_feature_id
        """
    )
    with get_engine().connect() as connection:
        row = (
            connection.execute(statement, {"source_feature_id": source_feature_id})
            .mappings()
            .one_or_none()
        )
    return _detail_from_row(dict(row), entity_type="building") if row else None


def find_property_unit(property_unit_id: str) -> EntityDetail | None:
    parcel_id = property_unit_id.removeprefix("property-unit:parcel:")
    if not parcel_id.startswith("parcel:cadastre:"):
        parcel_id = "parcel:cadastre:" + parcel_id.removeprefix("cadastre:")
    detail = find_parcel(parcel_id)
    if detail is None:
        return None
    detail["id"] = property_unit_id
    detail["entity_type"] = "property_unit"
    detail["properties"] = {
        **detail["properties"],
        "unit_type": "single_parcel",
        "parcel_id": parcel_id,
    }
    return detail
