import json
from decimal import Decimal
from typing import Any, TypedDict, cast

from sqlalchemy import text

from immo.database import get_engine


class MarketContextRecord(TypedDict):
    property_unit_id: str
    snapshot_at: str
    comparables: list[dict[str, Any]]
    energy_assessment: dict[str, Any] | None
    urban_zone: dict[str, Any] | None
    risks: list[dict[str, Any]]


class CoverageRecord(TypedDict):
    data_source_id: str
    release_id: str | None
    acceptance_status: str | None
    source_published_on: str | None
    record_count: int | None
    matched_record_count: int | None
    coverage_ratio: float | None
    freshest_observation_at: str | None
    measured_at: str | None


def _json(value: object) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _number(value: object) -> float | None:
    return None if value is None else float(cast(Decimal | float, value))


def list_market_data_coverage(*, commune_code: str) -> list[CoverageRecord]:
    statement = text(
        """
        SELECT source.id AS data_source_id, release.id AS release_id,
               release.acceptance_status, release.source_published_on,
               metric.record_count, metric.matched_record_count,
               metric.coverage_ratio, metric.freshest_observation_at,
               metric.measured_at
          FROM meta.data_source AS source
          LEFT JOIN LATERAL (
              SELECT candidate.*
                FROM meta.dataset_release AS candidate
               WHERE candidate.data_source_id = source.id
               ORDER BY
                    (candidate.acceptance_status = 'accepted') DESC,
                    candidate.source_published_on DESC NULLS LAST,
                    candidate.discovered_at DESC
               LIMIT 1
          ) AS release ON true
          LEFT JOIN meta.dataset_coverage_metric AS metric
            ON metric.release_id = release.id AND metric.commune_code = :commune_code
         WHERE source.id IN ('DS-06', 'DS-07', 'DS-08', 'DS-09')
         ORDER BY source.id
        """
    )
    with get_engine().connect() as connection:
        rows = list(connection.execute(statement, {"commune_code": commune_code}).mappings())
    return [
        {
            "data_source_id": str(row["data_source_id"]),
            "release_id": str(row["release_id"]) if row["release_id"] else None,
            "acceptance_status": (
                str(row["acceptance_status"]) if row["acceptance_status"] else None
            ),
            "source_published_on": (
                row["source_published_on"].isoformat() if row["source_published_on"] else None
            ),
            "record_count": int(row["record_count"]) if row["record_count"] is not None else None,
            "matched_record_count": (
                int(row["matched_record_count"])
                if row["matched_record_count"] is not None
                else None
            ),
            "coverage_ratio": _number(row["coverage_ratio"]),
            "freshest_observation_at": (
                row["freshest_observation_at"].isoformat()
                if row["freshest_observation_at"]
                else None
            ),
            "measured_at": row["measured_at"].isoformat() if row["measured_at"] else None,
        }
        for row in rows
    ]


def find_market_context(property_unit_id: str, *, snapshot_at: str) -> MarketContextRecord | None:
    unit_statement = text("SELECT id FROM reference.property_unit WHERE id = :property_unit_id")
    comparable_statement = text(
        """
        SELECT selection.included, selection.decision_reason,
               selection.distance_m, selection.segment_code,
               selection.transaction_date, selection.property_type,
               selection.surface_m2, selection.normalized_price_m2,
               selection.price_transformations, selection.source_release_ids,
               transaction.source_identifier AS transaction_source_id
          FROM market.comparable_selection AS selection
          JOIN observation.transaction_property AS property
            ON property.id = selection.transaction_property_id
          JOIN observation."transaction" AS transaction
            ON transaction.id = property.transaction_id
         WHERE selection.property_unit_id = :property_unit_id
           AND selection.snapshot_at = CAST(:snapshot_at AS date)
         ORDER BY selection.included DESC, selection.distance_m, transaction.source_identifier
        """
    )
    energy_statement = text(
        """
        WITH members AS (
            SELECT entity_type, entity_id
              FROM reference.property_unit_member
             WHERE property_unit_id = :property_unit_id
               AND member_role IN ('primary', 'supporting')
        ), candidates AS (
            SELECT assessment.*,
                   (assessment.building_id IN (
                       SELECT entity_id FROM members WHERE entity_type = 'building'
                   )) AS direct_building,
                   count(*) FILTER (WHERE assessment.building_id IS NULL) OVER ()
                       AS unresolved_address_count
              FROM observation.energy_assessment AS assessment
              JOIN meta.active_dataset_release AS active
                ON active.release_id = assessment.release_id
               AND active.data_source_id = 'DS-07'
             WHERE assessment.assessment_date <= CAST(:snapshot_at AS date)
               AND assessment.is_deposited AND NOT assessment.is_simulated
               AND (assessment.cancelled_at IS NULL
                    OR assessment.cancelled_at > CAST(:snapshot_at AS date))
               AND (
                    assessment.building_id IN (
                        SELECT entity_id FROM members WHERE entity_type = 'building'
                    )
                    OR (
                        assessment.building_id IS NULL
                        AND assessment.address_id IN (
                            SELECT entity_id FROM members WHERE entity_type = 'address'
                        )
                    )
               )
        )
        SELECT id, dpe_number, assessment_date, energy_label,
               energy_consumption_kwh_m2_year, envelope_characteristics,
               match_confidence, release_id, direct_building
          FROM candidates
         WHERE direct_building OR unresolved_address_count = 1
         ORDER BY direct_building DESC, assessment_date DESC, dpe_number
         LIMIT 1
        """
    )
    urban_statement = text(
        """
        SELECT zone.zone_code, zone.source_identifier, document.id AS document_id,
               document.document_version, document.published_at, document.release_id,
               ST_Area(ST_Intersection(zone.geom, unit.geom)) / NULLIF(ST_Area(unit.geom), 0)
                   AS overlap_ratio,
               zone.rule_profile, zone.rule_profile_validated_at
          FROM reference.property_unit_geometry AS unit
          JOIN observation.urban_zone AS zone ON zone.geom && unit.geom
          JOIN observation.urban_document AS document ON document.id = zone.document_id
          JOIN meta.active_dataset_release AS active
            ON active.release_id = document.release_id AND active.data_source_id = 'DS-08'
         WHERE unit.id = :property_unit_id
           AND document.status = 'opposable'
           AND document.published_at <= CAST(:snapshot_at AS date)
           AND document.valid_from <= CAST(:snapshot_at AS date)
           AND (document.valid_to IS NULL OR document.valid_to >= CAST(:snapshot_at AS date))
           AND ST_Intersects(zone.geom, unit.geom)
         ORDER BY overlap_ratio DESC, zone.source_identifier
         LIMIT 1
        """
    )
    risk_statement = text(
        """
        SELECT risk.source_identifier, risk.risk_type, risk.granularity,
               risk.severity, risk.observed_at, risk.valid_from, risk.valid_to,
               risk.coverage_known, risk.value, risk.release_id,
               CASE
                   WHEN risk.granularity = 'commune' THEN false
                   ELSE ST_Intersects(risk.geom, unit.geom)
               END AS applies_to_unit
          FROM reference.property_unit_geometry AS unit
          JOIN observation.risk_observation AS risk
            ON risk.commune_code = unit.commune_code
          JOIN meta.active_dataset_release AS active
            ON active.release_id = risk.release_id AND active.data_source_id = 'DS-09'
         WHERE unit.id = :property_unit_id
           AND (risk.valid_from IS NULL OR risk.valid_from <= CAST(:snapshot_at AS date))
           AND (risk.valid_to IS NULL OR risk.valid_to >= CAST(:snapshot_at AS date))
           AND (risk.granularity = 'commune' OR risk.geom && unit.geom)
         ORDER BY applies_to_unit DESC, risk.risk_type, risk.source_identifier
        """
    )
    parameters = {"property_unit_id": property_unit_id, "snapshot_at": snapshot_at}
    with get_engine().connect() as connection:
        if connection.execute(unit_statement, parameters).first() is None:
            return None
        comparable_rows = list(connection.execute(comparable_statement, parameters).mappings())
        energy = connection.execute(energy_statement, parameters).mappings().one_or_none()
        urban = connection.execute(urban_statement, parameters).mappings().one_or_none()
        risk_rows = list(connection.execute(risk_statement, parameters).mappings())

    comparables = [
        {
            "transaction_source_id": str(row["transaction_source_id"]),
            "included": bool(row["included"]),
            "reason": str(row["decision_reason"]),
            "distance_m": _number(row["distance_m"]),
            "segment_code": str(row["segment_code"]),
            "transaction_date": row["transaction_date"].isoformat(),
            "property_type": str(row["property_type"]),
            "surface_m2": _number(row["surface_m2"]),
            "normalized_price_m2": _number(row["normalized_price_m2"]),
            "price_transformations": _json(row["price_transformations"]),
            "release_ids": _json(row["source_release_ids"]),
        }
        for row in comparable_rows
    ]
    energy_record = (
        {
            "id": str(energy["id"]),
            "dpe_number": str(energy["dpe_number"]),
            "assessment_date": energy["assessment_date"].isoformat(),
            "energy_label": energy["energy_label"],
            "energy_consumption_kwh_m2_year": _number(energy["energy_consumption_kwh_m2_year"]),
            "envelope_characteristics": _json(energy["envelope_characteristics"]),
            "match_confidence": _number(energy["match_confidence"]),
            "direct_building_match": bool(energy["direct_building"]),
            "release_id": str(energy["release_id"]),
        }
        if energy is not None
        else None
    )
    urban_record = (
        {
            "zone_code": str(urban["zone_code"]),
            "source_identifier": str(urban["source_identifier"]),
            "document_id": str(urban["document_id"]),
            "document_version": str(urban["document_version"]),
            "published_at": urban["published_at"].isoformat(),
            "overlap_ratio": _number(urban["overlap_ratio"]),
            "rule_profile": _json(urban["rule_profile"]),
            "rule_profile_validated_at": (
                urban["rule_profile_validated_at"].isoformat()
                if urban["rule_profile_validated_at"]
                else None
            ),
            "release_id": str(urban["release_id"]),
        }
        if urban is not None
        else None
    )
    risks = [
        {
            "source_identifier": str(row["source_identifier"]),
            "risk_type": str(row["risk_type"]),
            "granularity": str(row["granularity"]),
            "severity": row["severity"],
            "observed_at": row["observed_at"].isoformat() if row["observed_at"] else None,
            "valid_from": row["valid_from"].isoformat() if row["valid_from"] else None,
            "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
            "coverage_known": bool(row["coverage_known"]),
            "applies_to_unit": bool(row["applies_to_unit"]),
            "value": _json(row["value"]),
            "release_id": str(row["release_id"]),
        }
        for row in risk_rows
    ]
    return {
        "property_unit_id": property_unit_id,
        "snapshot_at": snapshot_at,
        "comparables": comparables,
        "energy_assessment": energy_record,
        "urban_zone": urban_record,
        "risks": risks,
    }
