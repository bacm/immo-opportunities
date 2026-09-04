"""Add versioned market, energy, urban-planning and risk observations.

Revision ID: 20260806_0011
Revises: 20260805_0010
Create Date: 2026-08-06 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260806_0011"
down_revision: str | None = "20260805_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OBSERVATION_TABLES = (
    "transaction",
    "transaction_property",
    "energy_assessment",
    "urban_document",
    "urban_zone",
    "urban_constraint",
    "risk_observation",
)

MARKET_TABLES = ("market_area", "comparable_selection", "market_metric")

FEATURE_DEFINITIONS: tuple[dict[str, object], ...] = tuple(
    {
        "code": code,
        "name": name,
        "strategy": strategy,
        "datasets": datasets,
        "value_type": value_type,
        "unit": unit,
        "requirement": requirement,
    }
    for code, name, strategy, datasets, value_type, unit, requirement in (
        (
            "MKT-001",
            "local_land_value_level",
            "division_extension",
            ["DS-06"],
            "number",
            "EUR/m2",
            "required",
        ),
        (
            "MKT-002",
            "exit_value_estimate_range",
            "division_extension",
            ["DS-06"],
            "json",
            "EUR",
            "required",
        ),
        (
            "MKT-003",
            "comparable_count",
            "division_extension",
            ["DS-06"],
            "integer",
            "count",
            "required",
        ),
        (
            "MKT-004",
            "market_dispersion",
            "division_extension",
            ["DS-06"],
            "number",
            "EUR/m2",
            "optional",
        ),
        (
            "MKT-005",
            "market_liquidity_proxy",
            "division_extension",
            ["DS-06"],
            "number",
            "ratio",
            "optional",
        ),
        (
            "MKT-101",
            "comparable_sale_price_m2",
            "renovation_resale",
            ["DS-06"],
            "number",
            "EUR/m2",
            "required",
        ),
        (
            "MKT-102",
            "comparable_count",
            "renovation_resale",
            ["DS-06"],
            "integer",
            "count",
            "required",
        ),
        (
            "MKT-103",
            "comparable_dispersion",
            "renovation_resale",
            ["DS-06"],
            "number",
            "EUR/m2",
            "optional",
        ),
        (
            "MKT-104",
            "transaction_recency",
            "renovation_resale",
            ["DS-06"],
            "number",
            "months",
            "confidence_only",
        ),
        (
            "MKT-105",
            "local_price_trend",
            "renovation_resale",
            ["DS-06"],
            "number",
            "ratio/year",
            "optional",
        ),
        (
            "REN-001",
            "construction_period",
            "renovation_resale",
            ["DS-03", "DS-04"],
            "text",
            None,
            "optional",
        ),
        (
            "REN-002",
            "building_area_proxy_m2",
            "renovation_resale",
            ["DS-03", "DS-04"],
            "number",
            "m2",
            "required",
        ),
        (
            "REN-003",
            "building_height_floors_consistency",
            "renovation_resale",
            ["DS-03", "DS-04"],
            "text",
            None,
            "confidence_only",
        ),
        (
            "REN-004",
            "energy_label_observed",
            "renovation_resale",
            ["DS-07"],
            "text",
            None,
            "optional",
        ),
        (
            "REN-005",
            "energy_consumption_observed",
            "renovation_resale",
            ["DS-07"],
            "number",
            "kWhEP/m2/year",
            "optional",
        ),
        (
            "REN-006",
            "dpe_age_months",
            "renovation_resale",
            ["DS-07"],
            "integer",
            "months",
            "confidence_only",
        ),
        (
            "REN-007",
            "envelope_characteristics",
            "renovation_resale",
            ["DS-07"],
            "json",
            None,
            "optional",
        ),
        (
            "REN-008",
            "dpe_match_confidence",
            "renovation_resale",
            ["DS-03", "DS-05", "DS-07"],
            "number",
            "ratio",
            "confidence_only",
        ),
        ("URB-001", "urban_zone_code", "division_extension", ["DS-08"], "text", None, "required"),
        ("URB-002", "zone_rule_profile", "division_extension", ["DS-08"], "json", None, "required"),
        (
            "URB-003",
            "known_constraint_overlap",
            "division_extension",
            ["DS-08"],
            "json",
            None,
            "optional",
        ),
        (
            "URB-004",
            "residual_footprint_proxy_m2",
            "division_extension",
            ["LAND", "DS-08"],
            "number",
            "m2",
            "required",
        ),
        (
            "URB-005",
            "urban_rule_completeness",
            "division_extension",
            ["DS-08"],
            "number",
            "ratio",
            "confidence_only",
        ),
        (
            "RISK-001",
            "clay_exposure_2026",
            "division_extension",
            ["DS-09"],
            "text",
            None,
            "optional",
        ),
        ("RISK-002", "flood_overlap", "division_extension", ["DS-09"], "json", None, "optional"),
        (
            "RISK-003",
            "soil_pollution_proximity",
            "division_extension",
            ["DS-09"],
            "json",
            None,
            "optional",
        ),
        (
            "RISK-004",
            "cavity_proximity",
            "division_extension",
            ["DS-09"],
            "number",
            "m",
            "optional",
        ),
        (
            "RISK-101",
            "renovation_risk_profile",
            "renovation_resale",
            ["DS-09"],
            "json",
            None,
            "optional",
        ),
    )
)


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    op.execute(
        """
        INSERT INTO meta.data_source (
            id, name, producer, homepage_url, licence_spdx,
            licence_name, attribution, usage_notes
        ) VALUES
            ('DS-06', 'DVF+ open-data', 'DGFiP / Cerema',
             'https://www.data.gouv.fr/datasets/dvf-open-data', 'etalab-2.0',
             'Licence Ouverte 2.0', 'DVF, DGFiP / Cerema',
             'Mutations complexes non décomposées exclues des prix unitaires.'),
            ('DS-07', 'DPE Logements existants depuis juillet 2021', 'ADEME',
             'https://data.ademe.fr/datasets/dpe-v2-logements-existants', 'etalab-2.0',
             'Licence Ouverte 2.0', 'ADEME, Observatoire DPE-Audit',
             'DPE réellement déposés seulement; absence neutre; appariement explicite.'),
            ('DS-08', 'Géoportail de l urbanisme exports CNIG', 'Collectivités / GPU',
             'https://www.geoportail-urbanisme.gouv.fr/', 'etalab-2.0',
             'Licence Ouverte 2.0', 'Géoportail de l urbanisme et autorité compétente',
             'Règles structurées seulement après validation de la version du document.'),
            ('DS-09', 'Géorisques API et téléchargements', 'DGPR / BRGM',
             'https://www.georisques.gouv.fr/donnees/bases-de-donnees', 'etalab-2.0',
             'Licence Ouverte 2.0', 'Géorisques, DGPR / BRGM',
             'La granularité source est conservée; aucun risque communal projeté à la parcelle.')
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.execute(
        """
        CREATE TABLE observation."transaction" (
            id text PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            source_identifier text NOT NULL,
            mutation_date date NOT NULL,
            mutation_nature text NOT NULL,
            price_eur numeric(16, 2) NOT NULL CHECK (price_eur > 0),
            is_complex boolean NOT NULL,
            complex_reason text,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            geom geometry(Geometry, 2154),
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT transaction_source_identity UNIQUE (release_id, source_identifier),
            CONSTRAINT transaction_complex_reason CHECK (NOT is_complex OR complex_reason IS NOT NULL),
            CONSTRAINT transaction_geom_valid CHECK (geom IS NULL OR ST_IsValid(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observation.transaction_property (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            transaction_id text NOT NULL REFERENCES observation."transaction"(id) ON DELETE CASCADE,
            source_identifier text NOT NULL,
            property_type text NOT NULL,
            parcel_id text REFERENCES reference.parcel(id) ON DELETE SET NULL,
            building_id text REFERENCES reference.building(id) ON DELETE SET NULL,
            local_identifier text,
            surface_m2 numeric CHECK (surface_m2 IS NULL OR surface_m2 > 0),
            allocated_price_eur numeric(16, 2) CHECK (
                allocated_price_eur IS NULL OR allocated_price_eur > 0
            ),
            allocation_method text,
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT transaction_property_source UNIQUE (transaction_id, source_identifier),
            CONSTRAINT transaction_property_allocation CHECK (
                allocated_price_eur IS NULL OR allocation_method IS NOT NULL
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observation.energy_assessment (
            id text PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            dpe_number text NOT NULL,
            assessment_date date NOT NULL,
            deposited_at date,
            cancelled_at date,
            is_deposited boolean NOT NULL,
            is_simulated boolean NOT NULL DEFAULT false,
            address_id text REFERENCES reference.address(id) ON DELETE SET NULL,
            building_id text REFERENCES reference.building(id) ON DELETE SET NULL,
            match_id bigint REFERENCES meta.entity_match(id) ON DELETE SET NULL,
            match_confidence numeric(6, 5) CHECK (
                match_confidence IS NULL OR match_confidence BETWEEN 0 AND 1
            ),
            energy_label text CHECK (energy_label IS NULL OR energy_label IN ('A','B','C','D','E','F','G')),
            energy_consumption_kwh_m2_year numeric CHECK (
                energy_consumption_kwh_m2_year IS NULL OR energy_consumption_kwh_m2_year >= 0
            ),
            envelope_characteristics jsonb,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT energy_assessment_release_number UNIQUE (release_id, dpe_number),
            CONSTRAINT energy_assessment_observed_only CHECK (is_deposited AND NOT is_simulated),
            CONSTRAINT energy_assessment_target CHECK (address_id IS NOT NULL OR building_id IS NOT NULL)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observation.urban_document (
            id text PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            source_identifier text NOT NULL,
            document_type text NOT NULL,
            document_version text NOT NULL,
            authority_name text NOT NULL,
            published_at date NOT NULL,
            valid_from date NOT NULL,
            valid_to date,
            status text NOT NULL CHECK (status IN ('opposable', 'superseded', 'cancelled', 'informational')),
            commune_codes jsonb NOT NULL,
            source_url text,
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT urban_document_source UNIQUE (release_id, source_identifier),
            CONSTRAINT urban_document_validity CHECK (valid_to IS NULL OR valid_to >= valid_from)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observation.urban_zone (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            document_id text NOT NULL REFERENCES observation.urban_document(id) ON DELETE CASCADE,
            source_identifier text NOT NULL,
            zone_code text NOT NULL,
            zone_type text,
            rule_profile jsonb,
            rule_profile_version text,
            rule_profile_validated_at timestamptz,
            rule_profile_validated_by text,
            required_rule_count integer CHECK (required_rule_count IS NULL OR required_rule_count >= 0),
            validated_rule_count integer CHECK (validated_rule_count IS NULL OR validated_rule_count >= 0),
            geom geometry(MultiPolygon, 2154) NOT NULL,
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT urban_zone_source UNIQUE (document_id, source_identifier),
            CONSTRAINT urban_zone_geom_valid CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
            CONSTRAINT urban_zone_rule_validation CHECK (
                rule_profile IS NULL OR (
                    rule_profile_version IS NOT NULL
                    AND rule_profile_validated_at IS NOT NULL
                    AND rule_profile_validated_by IS NOT NULL
                )
            ),
            CONSTRAINT urban_zone_rule_counts CHECK (
                validated_rule_count IS NULL OR required_rule_count IS NOT NULL
                AND validated_rule_count <= required_rule_count
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observation.urban_constraint (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            document_id text NOT NULL REFERENCES observation.urban_document(id) ON DELETE CASCADE,
            source_identifier text NOT NULL,
            constraint_type text NOT NULL,
            constraint_code text,
            label text,
            geom geometry(Geometry, 2154) NOT NULL,
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT urban_constraint_source UNIQUE (document_id, source_identifier),
            CONSTRAINT urban_constraint_geom_valid CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE observation.risk_observation (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            source_identifier text NOT NULL,
            risk_type text NOT NULL,
            granularity text NOT NULL CHECK (granularity IN ('point', 'zone', 'parcel', 'commune')),
            commune_code text NOT NULL,
            department_code text NOT NULL,
            severity text,
            observed_at date,
            valid_from date,
            valid_to date,
            coverage_known boolean NOT NULL,
            geom geometry(Geometry, 2154),
            value jsonb NOT NULL DEFAULT '{}'::jsonb,
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT risk_observation_source UNIQUE (release_id, risk_type, source_identifier),
            CONSTRAINT risk_observation_geom_valid CHECK (geom IS NULL OR ST_IsValid(geom)),
            CONSTRAINT risk_observation_granularity CHECK (
                (granularity = 'commune' AND geom IS NULL) OR
                (granularity <> 'commune' AND geom IS NOT NULL)
            ),
            CONSTRAINT risk_observation_validity CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE market.market_area (
            id text PRIMARY KEY,
            segment_code text NOT NULL,
            segment_version text NOT NULL,
            label text NOT NULL,
            market_type text NOT NULL CHECK (market_type IN ('urban', 'rural', 'littoral', 'tourist', 'mixed')),
            commune_codes jsonb NOT NULL,
            valid_from date NOT NULL,
            valid_to date,
            rationale text NOT NULL,
            geom geometry(MultiPolygon, 2154) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT market_area_segment UNIQUE (segment_code, segment_version),
            CONSTRAINT market_area_geom_valid CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
            CONSTRAINT market_area_validity CHECK (valid_to IS NULL OR valid_to >= valid_from)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE market.comparable_selection (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            property_unit_id text REFERENCES reference.property_unit(id) ON DELETE CASCADE,
            building_id text REFERENCES reference.building(id) ON DELETE CASCADE,
            transaction_property_id bigint NOT NULL REFERENCES observation.transaction_property(id) ON DELETE CASCADE,
            snapshot_at date NOT NULL,
            strategy text NOT NULL,
            algorithm_version text NOT NULL,
            market_area_id text REFERENCES market.market_area(id) ON DELETE RESTRICT,
            distance_m numeric CHECK (distance_m IS NULL OR distance_m >= 0),
            segment_code text NOT NULL,
            transaction_date date NOT NULL,
            property_type text NOT NULL,
            surface_m2 numeric,
            normalized_price_m2 numeric,
            included boolean NOT NULL,
            decision_reason text NOT NULL,
            price_transformations jsonb NOT NULL DEFAULT '[]'::jsonb,
            source_release_ids jsonb NOT NULL,
            selected_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT comparable_selection_subject CHECK (num_nonnulls(property_unit_id, building_id) = 1),
            CONSTRAINT comparable_selection_snapshot CHECK (transaction_date <= snapshot_at),
            CONSTRAINT comparable_selection_value CHECK (
                NOT included OR normalized_price_m2 IS NOT NULL AND normalized_price_m2 > 0
            ),
            CONSTRAINT comparable_selection_identity UNIQUE NULLS NOT DISTINCT (
                property_unit_id, building_id, transaction_property_id,
                snapshot_at, strategy, algorithm_version
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE market.market_metric (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            market_area_id text NOT NULL REFERENCES market.market_area(id) ON DELETE CASCADE,
            metric_code text NOT NULL,
            metric_version text NOT NULL,
            segment_code text NOT NULL,
            snapshot_at date NOT NULL,
            numeric_value numeric,
            json_value jsonb,
            missing_reason text,
            comparable_count integer NOT NULL CHECK (comparable_count >= 0),
            source_release_ids jsonb NOT NULL,
            formula text NOT NULL,
            computed_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT market_metric_value CHECK (num_nonnulls(numeric_value, json_value, missing_reason) = 1),
            CONSTRAINT market_metric_identity UNIQUE (
                market_area_id, metric_code, metric_version, segment_code, snapshot_at
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meta.dataset_coverage_metric (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE CASCADE,
            commune_code text NOT NULL,
            record_count bigint NOT NULL CHECK (record_count >= 0),
            matched_record_count bigint CHECK (matched_record_count IS NULL OR matched_record_count >= 0),
            expected_record_count bigint CHECK (expected_record_count IS NULL OR expected_record_count >= 0),
            coverage_ratio numeric(7, 6) CHECK (coverage_ratio IS NULL OR coverage_ratio BETWEEN 0 AND 1),
            freshest_observation_at date,
            measured_at timestamptz NOT NULL DEFAULT now(),
            details jsonb NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT dataset_coverage_metric_identity UNIQUE (release_id, commune_code)
        )
        """
    )

    op.execute('CREATE INDEX transaction_geom_gist ON observation."transaction" USING gist (geom)')
    op.execute(
        'CREATE INDEX transaction_market_idx ON observation."transaction" (department_code, commune_code, mutation_date, mutation_nature)'
    )
    op.execute(
        "CREATE INDEX transaction_property_lookup_idx ON observation.transaction_property (property_type, surface_m2)"
    )
    op.execute(
        "CREATE INDEX energy_assessment_building_idx ON observation.energy_assessment (building_id, assessment_date DESC) WHERE cancelled_at IS NULL"
    )
    op.execute(
        "CREATE INDEX energy_assessment_address_idx ON observation.energy_assessment (address_id, assessment_date DESC) WHERE cancelled_at IS NULL"
    )
    op.execute("CREATE INDEX urban_zone_geom_gist ON observation.urban_zone USING gist (geom)")
    op.execute(
        "CREATE INDEX urban_constraint_geom_gist ON observation.urban_constraint USING gist (geom)"
    )
    op.execute(
        "CREATE INDEX risk_observation_geom_gist ON observation.risk_observation USING gist (geom)"
    )
    op.execute(
        "CREATE INDEX risk_observation_context_idx ON observation.risk_observation (department_code, commune_code, risk_type, granularity)"
    )
    op.execute("CREATE INDEX market_area_geom_gist ON market.market_area USING gist (geom)")
    op.execute(
        "CREATE INDEX comparable_selection_subject_idx ON market.comparable_selection (property_unit_id, building_id, snapshot_at, included)"
    )
    op.execute(
        "CREATE INDEX dataset_coverage_metric_commune_idx ON meta.dataset_coverage_metric (commune_code, release_id)"
    )

    op.execute("ALTER TABLE feature.feature_definition DROP CONSTRAINT feature_definition_code")
    op.execute(
        """
        ALTER TABLE feature.feature_definition
        ADD CONSTRAINT feature_definition_code
        CHECK (code ~ '^(LAND|BLD|MKT|REN|URB|RISK)-[0-9]{3}$')
        """
    )

    feature_definition = sa.table(
        "feature_definition",
        sa.column("code", sa.Text),
        sa.column("version", sa.Integer),
        sa.column("name", sa.Text),
        sa.column("strategy", sa.Text),
        sa.column("datasets", JSONB),
        sa.column("formula", sa.Text),
        sa.column("transformation_version", sa.Text),
        sa.column("value_type", sa.Text),
        sa.column("unit", sa.Text),
        sa.column("valid_min", sa.Numeric),
        sa.column("valid_max", sa.Numeric),
        sa.column("out_of_range_policy", sa.Text),
        sa.column("requirement", sa.Text),
        sa.column("missing_value_policy", sa.Text),
        sa.column("description", sa.Text),
        schema="feature",
    )
    op.bulk_insert(
        feature_definition,
        [
            {
                **definition,
                "version": 1,
                "formula": "See contracts/features/market-data-v1.json",
                "transformation_version": "market-data@1",
                "valid_min": None,
                "valid_max": None,
                "out_of_range_policy": "flag",
                "missing_value_policy": (
                    "Explicit absent value with reason; never silently converted to zero"
                ),
                "description": "Versioned in contracts/features/market-data-v1.json",
            }
            for definition in FEATURE_DEFINITIONS
        ],
    )

    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "DELETE FROM feature.feature_definition WHERE version = 1 AND code ~ '^(MKT|REN|URB|RISK)-'"
    )
    op.execute("ALTER TABLE feature.feature_definition DROP CONSTRAINT feature_definition_code")
    op.execute(
        "ALTER TABLE feature.feature_definition ADD CONSTRAINT feature_definition_code "
        "CHECK (code ~ '^(LAND|BLD)-[0-9]{3}$')"
    )
    op.execute("DROP TABLE meta.dataset_coverage_metric")
    for table in reversed(MARKET_TABLES):
        op.execute(f"DROP TABLE market.{table}")
    for table in reversed(OBSERVATION_TABLES):
        quoted = f'"{table}"' if table == "transaction" else table
        op.execute(f"DROP TABLE observation.{quoted}")
    op.execute("DELETE FROM meta.data_source WHERE id IN ('DS-06', 'DS-07', 'DS-08', 'DS-09')")
    op.execute("RESET ROLE")
