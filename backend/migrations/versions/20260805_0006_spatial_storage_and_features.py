"""Avoid duplicate parcel geometry storage and seed morphology definitions.

Revision ID: 20260805_0006
Revises: 20260805_0005
Create Date: 2026-08-05 12:00:00
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0006"
down_revision: str | None = "20260805_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FEATURE_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "code": "LAND-001",
        "name": "parcel_area_m2",
        "datasets": ["DS-01"],
        "formula": "area(union(resolved parcels))",
        "value_type": "number",
        "unit": "m2",
        "minimum": 0,
        "maximum": None,
        "requirement": "required",
    },
    {
        "code": "LAND-002",
        "name": "building_footprint_m2",
        "datasets": ["DS-01", "DS-03", "DS-04"],
        "formula": "area(intersection(unit geometry, union(deduplicated resolved buildings)))",
        "value_type": "number",
        "unit": "m2",
        "minimum": 0,
        "maximum": None,
        "requirement": "required",
    },
    {
        "code": "LAND-003",
        "name": "footprint_ratio",
        "datasets": ["LAND-001", "LAND-002"],
        "formula": "LAND-002 / LAND-001",
        "value_type": "number",
        "unit": "ratio",
        "minimum": 0,
        "maximum": 1,
        "requirement": "required",
    },
    {
        "code": "LAND-004",
        "name": "unbuilt_area_proxy_m2",
        "datasets": ["LAND-001", "LAND-002"],
        "formula": "LAND-001 - LAND-002",
        "value_type": "number",
        "unit": "m2",
        "minimum": 0,
        "maximum": None,
        "requirement": "required",
    },
    {
        "code": "LAND-005",
        "name": "parcel_compactness",
        "datasets": ["DS-01"],
        "formula": "4 * pi * area / perimeter^2",
        "value_type": "number",
        "unit": "ratio",
        "minimum": 0,
        "maximum": 1,
        "requirement": "optional",
    },
    {
        "code": "LAND-006",
        "name": "parcel_width_proxy_m",
        "datasets": ["DS-01"],
        "formula": "shortest edge(minimum rotated rectangle(unit))",
        "value_type": "number",
        "unit": "m",
        "minimum": 0,
        "maximum": None,
        "requirement": "optional",
    },
    {
        "code": "LAND-007",
        "name": "building_boundary_distance_m",
        "datasets": ["DS-01", "DS-04"],
        "formula": "distance(union(resolved buildings), boundary(unit))",
        "value_type": "number",
        "unit": "m",
        "minimum": 0,
        "maximum": None,
        "requirement": "optional",
    },
    {
        "code": "LAND-008",
        "name": "road_access_proxy",
        "datasets": ["DS-01", "DS-04"],
        "formula": "length(intersection(boundary(unit), buffer(public roads, threshold)))",
        "value_type": "number",
        "unit": "m",
        "minimum": 0,
        "maximum": None,
        "requirement": "optional",
    },
    {
        "code": "LAND-009",
        "name": "building_count",
        "datasets": ["DS-01", "DS-03", "DS-04"],
        "formula": "count(distinct resolved physical buildings)",
        "value_type": "integer",
        "unit": "count",
        "minimum": 0,
        "maximum": None,
        "requirement": "required",
    },
    {
        "code": "LAND-010",
        "name": "light_construction_ratio",
        "datasets": ["DS-04"],
        "formula": "area(union(light buildings)) / LAND-002",
        "value_type": "number",
        "unit": "ratio",
        "minimum": 0,
        "maximum": 1,
        "requirement": "optional",
    },
    {
        "code": "BLD-001",
        "name": "building_use",
        "datasets": ["DS-03", "DS-04"],
        "formula": "highest-priority observed use without prediction",
        "value_type": "text",
        "unit": None,
        "minimum": None,
        "maximum": None,
        "requirement": "optional",
    },
    {
        "code": "BLD-002",
        "name": "building_height_m",
        "datasets": ["DS-03", "DS-04"],
        "formula": "highest-priority observed height without imputation",
        "value_type": "number",
        "unit": "m",
        "minimum": 0,
        "maximum": 400,
        "requirement": "optional",
    },
    {
        "code": "BLD-003",
        "name": "dwelling_count_observed",
        "datasets": ["DS-03", "DS-04"],
        "formula": "highest-priority observed dwelling count without imputation",
        "value_type": "integer",
        "unit": "count",
        "minimum": 0,
        "maximum": None,
        "requirement": "optional",
    },
)


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    op.execute("DROP FUNCTION reference.refresh_cadastre_spatial_reference(text)")
    op.execute("DROP INDEX reference.parcel_geom_gist")
    op.execute("DROP INDEX reference.property_unit_geom_gist")
    op.execute("ALTER TABLE reference.parcel DROP CONSTRAINT parcel_geom_valid")
    op.execute("ALTER TABLE reference.parcel DROP CONSTRAINT parcel_geom_nonempty")
    op.execute("ALTER TABLE reference.property_unit DROP CONSTRAINT property_unit_geom_valid")
    op.execute("ALTER TABLE reference.property_unit DROP CONSTRAINT property_unit_geom_nonempty")
    op.execute("ALTER TABLE reference.parcel DROP COLUMN geom")
    op.execute("ALTER TABLE reference.property_unit DROP COLUMN geom")

    op.execute(
        """
        CREATE VIEW reference.parcel_geometry AS
        SELECT parcel.id, parcel.cadastral_id, parcel.commune_code, parcel.department_code,
               source.release_id, source.raw_asset_id, source.geom
          FROM reference.parcel AS parcel
          JOIN reference.active_cadastral_parcel AS source
            ON source.cadastral_id = parcel.cadastral_id
           AND source.department_code = parcel.department_code
        """
    )
    op.execute(
        """
        CREATE VIEW reference.property_unit_geometry AS
        SELECT unit.id, unit.commune_code, unit.department_code,
               ST_Multi(ST_UnaryUnion(ST_Collect(parcel.geom)))::geometry(MultiPolygon, 2154) AS geom
          FROM reference.property_unit AS unit
          JOIN reference.property_unit_member AS member
            ON member.property_unit_id = unit.id AND member.entity_type = 'parcel'
          JOIN reference.parcel_geometry AS parcel ON parcel.id = member.entity_id
         WHERE member.member_role IN ('primary', 'supporting')
         GROUP BY unit.id, unit.commune_code, unit.department_code
        """
    )

    op.execute(
        """
        CREATE FUNCTION reference.refresh_cadastre_spatial_reference(p_department_code text)
        RETURNS TABLE(area_count bigint, parcel_count bigint, property_unit_count bigint)
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            INSERT INTO reference.area (id, area_type, code, name, department_code, geom)
            SELECT 'area:commune:' || source.code, 'commune', source.code,
                   source.name, source.department_code, source.geom
              FROM reference.administrative_area AS source
              JOIN meta.active_dataset_release AS active
                ON active.data_source_id = 'DS-01'
               AND active.scope_type = 'department'
               AND active.scope_code = source.department_code
               AND active.release_id = source.release_id
             WHERE source.department_code = p_department_code AND source.area_type = 'commune'
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name, geom = EXCLUDED.geom, updated_at = clock_timestamp();

            INSERT INTO reference.parcel (id, cadastral_id, commune_code, department_code)
            SELECT 'parcel:cadastre:' || cadastral_id, cadastral_id,
                   commune_code, department_code
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT (id) DO UPDATE SET
                commune_code = EXCLUDED.commune_code,
                department_code = EXCLUDED.department_code,
                updated_at = clock_timestamp();

            INSERT INTO meta.entity_source_identifier (
                entity_type, entity_id, data_source_id, source_entity_type,
                source_identifier, first_release_id, last_release_id, is_preferred
            )
            SELECT 'parcel', 'parcel:cadastre:' || cadastral_id, 'DS-01', 'cadastral_parcel',
                   cadastral_id, release_id, release_id, true
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT (entity_type, entity_id, data_source_id, source_entity_type, source_identifier)
            DO UPDATE SET last_release_id = EXCLUDED.last_release_id, updated_at = clock_timestamp();

            INSERT INTO reference.property_unit (
                id, stable_key, unit_type, commune_code, department_code,
                publication_eligible, exclusion_reason
            )
            SELECT 'property-unit:parcel:' || cadastral_id,
                   'cadastre:' || cadastral_id, 'single_parcel',
                   commune_code, department_code, false, 'entity_resolution_incomplete'
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT (id) DO UPDATE SET
                commune_code = EXCLUDED.commune_code,
                department_code = EXCLUDED.department_code,
                updated_at = clock_timestamp();

            INSERT INTO reference.property_unit_member (
                property_unit_id, entity_type, entity_id, member_role
            )
            SELECT 'property-unit:parcel:' || cadastral_id, 'parcel',
                   'parcel:cadastre:' || cadastral_id, 'primary'
              FROM reference.active_cadastral_parcel
             WHERE department_code = p_department_code
            ON CONFLICT DO NOTHING;

            RETURN QUERY SELECT
                (SELECT count(*) FROM reference.area WHERE department_code = p_department_code),
                (SELECT count(*) FROM reference.parcel WHERE department_code = p_department_code),
                (SELECT count(*) FROM reference.property_unit WHERE department_code = p_department_code);
        END
        $function$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION reference.refresh_cadastre_spatial_reference(text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION reference.refresh_cadastre_spatial_reference(text) TO pipeline_rw"
    )

    statement = sa.text(
        """
        INSERT INTO feature.feature_definition (
            code, version, name, strategy, datasets, formula, transformation_version,
            value_type, unit, valid_min, valid_max, out_of_range_policy,
            requirement, missing_value_policy, description
        ) VALUES (
            :code, 1, :name, 'division_extension', CAST(:datasets AS jsonb), :formula,
            CASE WHEN :code LIKE 'BLD-%' THEN 'building-observation@1' ELSE 'morphology@1' END,
            :value_type, :unit, :minimum, :maximum, 'flag', :requirement,
            'absent with an explicit reason; never coerce unavailable to zero',
            :name || ' — versioned morphology feature'
        )
        ON CONFLICT (code, version) DO NOTHING
        """
    )
    connection = op.get_bind()
    for definition in FEATURE_DEFINITIONS:
        connection.execute(
            statement,
            {**definition, "datasets": json.dumps(definition["datasets"])},
        )

    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "DELETE FROM feature.feature_definition WHERE version = 1 AND (code LIKE 'LAND-%' OR code LIKE 'BLD-%')"
    )
    op.execute("DROP FUNCTION reference.refresh_cadastre_spatial_reference(text)")
    op.execute("DROP VIEW reference.property_unit_geometry")
    op.execute("DROP VIEW reference.parcel_geometry")
    op.execute("ALTER TABLE reference.parcel ADD COLUMN geom geometry(MultiPolygon, 2154)")
    op.execute("ALTER TABLE reference.property_unit ADD COLUMN geom geometry(MultiPolygon, 2154)")
    op.execute("CREATE INDEX parcel_geom_gist ON reference.parcel USING gist (geom)")
    op.execute("CREATE INDEX property_unit_geom_gist ON reference.property_unit USING gist (geom)")
    op.execute("RESET ROLE")
