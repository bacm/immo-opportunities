import json
from decimal import Decimal
from typing import Any, TypedDict, cast

from sqlalchemy import text

from immo.database import get_engine


class AddressSearchRecord(TypedDict):
    id: str
    display_label: str
    commune_code: str
    department_code: str
    longitude: float
    latitude: float


class SourceIdentifierRecord(TypedDict):
    data_source_id: str
    source_entity_type: str
    source_identifier: str
    is_preferred: bool


class MatchReviewRecord(TypedDict):
    previous_decision: str
    reviewed_decision: str
    reviewer: str
    rationale: str
    reviewed_at: str


class EntityMatchRecord(TypedDict):
    id: int
    candidate_group_key: str
    left_entity_type: str
    left_entity_id: str
    right_entity_type: str
    right_entity_id: str
    method: str
    algorithm_code: str
    algorithm_version: str
    confidence: float
    decision: str
    critical: bool
    blocks_publication: bool
    rationale: str
    evidence: dict[str, Any]
    release_ids: list[str]
    left_source_identifiers: list[SourceIdentifierRecord]
    right_source_identifiers: list[SourceIdentifierRecord]
    reviews: list[MatchReviewRecord]


class AddressContextRecord(TypedDict):
    address: AddressSearchRecord
    matches: list[EntityMatchRecord]


def _json_object(value: object) -> dict[str, Any]:
    if isinstance(value, str):
        return cast(dict[str, Any], json.loads(value))
    return cast(dict[str, Any], value)


def _json_list(value: object) -> list[Any]:
    if isinstance(value, str):
        return cast(list[Any], json.loads(value))
    return cast(list[Any], value)


def _match_from_mapping(row: dict[str, Any]) -> EntityMatchRecord:
    reviews_raw = _json_list(row["reviews"])
    left_raw = _json_list(row["left_source_identifiers"])
    right_raw = _json_list(row["right_source_identifiers"])
    return {
        "id": int(row["id"]),
        "candidate_group_key": str(row["candidate_group_key"]),
        "left_entity_type": str(row["left_entity_type"]),
        "left_entity_id": str(row["left_entity_id"]),
        "right_entity_type": str(row["right_entity_type"]),
        "right_entity_id": str(row["right_entity_id"]),
        "method": str(row["method"]),
        "algorithm_code": str(row["algorithm_code"]),
        "algorithm_version": str(row["algorithm_version"]),
        "confidence": float(cast(Decimal | float, row["confidence"])),
        "decision": str(row["decision"]),
        "critical": bool(row["critical"]),
        "blocks_publication": bool(row["blocks_publication"]),
        "rationale": str(row["rationale"]),
        "evidence": _json_object(row["evidence"]),
        "release_ids": [str(item) for item in _json_list(row["release_ids"])],
        "left_source_identifiers": [cast(SourceIdentifierRecord, item) for item in left_raw],
        "right_source_identifiers": [cast(SourceIdentifierRecord, item) for item in right_raw],
        "reviews": [cast(MatchReviewRecord, item) for item in reviews_raw],
    }


MATCH_SELECT = """
    SELECT matched.*,
           COALESCE((
               SELECT jsonb_agg(jsonb_build_object(
                   'data_source_id', identifier.data_source_id,
                   'source_entity_type', identifier.source_entity_type,
                   'source_identifier', identifier.source_identifier,
                   'is_preferred', identifier.is_preferred
               ) ORDER BY identifier.is_preferred DESC, identifier.data_source_id)
                 FROM meta.entity_source_identifier AS identifier
                WHERE identifier.entity_type = matched.left_entity_type
                  AND identifier.entity_id = matched.left_entity_id
                  AND EXISTS (
                      SELECT 1 FROM meta.active_dataset_release AS active
                       WHERE active.release_id = identifier.last_release_id
                  )
           ), '[]'::jsonb) AS left_source_identifiers,
           COALESCE((
               SELECT jsonb_agg(jsonb_build_object(
                   'data_source_id', identifier.data_source_id,
                   'source_entity_type', identifier.source_entity_type,
                   'source_identifier', identifier.source_identifier,
                   'is_preferred', identifier.is_preferred
               ) ORDER BY identifier.is_preferred DESC, identifier.data_source_id)
                 FROM meta.entity_source_identifier AS identifier
                WHERE identifier.entity_type = matched.right_entity_type
                  AND identifier.entity_id = matched.right_entity_id
                  AND EXISTS (
                      SELECT 1 FROM meta.active_dataset_release AS active
                       WHERE active.release_id = identifier.last_release_id
                  )
           ), '[]'::jsonb) AS right_source_identifiers,
           COALESCE((
               SELECT jsonb_agg(jsonb_build_object(
                   'previous_decision', review.previous_decision,
                   'reviewed_decision', review.reviewed_decision,
                   'reviewer', review.reviewer,
                   'rationale', review.rationale,
                   'reviewed_at', review.reviewed_at
               ) ORDER BY review.reviewed_at)
                 FROM meta.entity_match_review AS review
                WHERE review.match_id = matched.id
           ), '[]'::jsonb) AS reviews
      FROM meta.entity_match AS matched
"""

ACTIVE_MATCH_PREDICATE = """
    jsonb_array_length(matched.release_ids) > 0
    AND NOT EXISTS (
        SELECT 1
          FROM jsonb_array_elements_text(matched.release_ids) AS source_release(release_id)
         WHERE NOT EXISTS (
             SELECT 1 FROM meta.active_dataset_release AS active
              WHERE active.release_id = source_release.release_id
         )
    )
    AND EXISTS (
        SELECT 1
          FROM meta.entity_source_identifier AS identifier
          JOIN meta.active_dataset_release AS active
            ON active.release_id = identifier.last_release_id
         WHERE identifier.entity_type = matched.left_entity_type
           AND identifier.entity_id = matched.left_entity_id
    )
    AND EXISTS (
        SELECT 1
          FROM meta.entity_source_identifier AS identifier
          JOIN meta.active_dataset_release AS active
            ON active.release_id = identifier.last_release_id
         WHERE identifier.entity_type = matched.right_entity_type
           AND identifier.entity_id = matched.right_entity_id
    )
"""


def find_entity_match(match_id: int) -> EntityMatchRecord | None:
    statement = text(
        MATCH_SELECT + " WHERE matched.id = :match_id AND (" + ACTIVE_MATCH_PREDICATE + ")"
    )
    with get_engine().connect() as connection:
        mapping = connection.execute(statement, {"match_id": match_id}).mappings().one_or_none()
    return _match_from_mapping(dict(mapping)) if mapping is not None else None


def search_addresses(
    query: str,
    *,
    commune_code: str | None,
    limit: int,
) -> list[AddressSearchRecord]:
    statement = text(
        """
        SELECT id, display_label, commune_code, department_code,
               ST_X(ST_Transform(geom, 4326)) AS longitude,
               ST_Y(ST_Transform(geom, 4326)) AS latitude
          FROM reference.address AS address
         WHERE normalized_label % unaccent(lower(:query))
           AND (:commune_code IS NULL OR commune_code = :commune_code)
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
         ORDER BY similarity(normalized_label, unaccent(lower(:query))) DESC, display_label
         LIMIT :limit
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(
            statement,
            {"query": query, "commune_code": commune_code, "limit": limit},
        ).mappings()
        return [
            {
                "id": str(row["id"]),
                "display_label": str(row["display_label"]),
                "commune_code": str(row["commune_code"]),
                "department_code": str(row["department_code"]),
                "longitude": float(cast(Decimal | float, row["longitude"])),
                "latitude": float(cast(Decimal | float, row["latitude"])),
            }
            for row in rows
        ]


def find_address_context(address_id: str) -> AddressContextRecord | None:
    address_statement = text(
        """
        SELECT id, display_label, commune_code, department_code,
               ST_X(ST_Transform(geom, 4326)) AS longitude,
               ST_Y(ST_Transform(geom, 4326)) AS latitude
          FROM reference.address AS address
         WHERE id = :address_id
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
        """
    )
    match_statement = text(
        MATCH_SELECT
        + """
         WHERE (
                   (matched.left_entity_type = 'address'
                    AND matched.left_entity_id = :address_id)
                OR (matched.right_entity_type = 'address'
                    AND matched.right_entity_id = :address_id)
               )
           AND ("""
        + ACTIVE_MATCH_PREDICATE
        + """)
         ORDER BY matched.decision, matched.confidence DESC, matched.id
        """
    )
    with get_engine().connect() as connection:
        address = (
            connection.execute(address_statement, {"address_id": address_id})
            .mappings()
            .one_or_none()
        )
        if address is None:
            return None
        matches = connection.execute(match_statement, {"address_id": address_id}).mappings()
        address_record: AddressSearchRecord = {
            "id": str(address["id"]),
            "display_label": str(address["display_label"]),
            "commune_code": str(address["commune_code"]),
            "department_code": str(address["department_code"]),
            "longitude": float(cast(Decimal | float, address["longitude"])),
            "latitude": float(cast(Decimal | float, address["latitude"])),
        }
        return {
            "address": address_record,
            "matches": [_match_from_mapping(dict(row)) for row in matches],
        }
