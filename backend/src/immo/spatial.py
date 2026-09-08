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
    # Une adresse dont la position source est contradictoire garde son identité et perd son
    # point : les coordonnées sont absentes, jamais choisies arbitrairement. `position_status`
    # porte le motif afin que l'absence soit distinguable d'un zéro ou d'un non applicable.
    longitude: float | None
    latitude: float | None
    position_status: str


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


def _optional_coordinate(value: object) -> float | None:
    """Une coordonnée absente reste absente : jamais convertie en zéro."""
    if value is None:
        return None
    return float(cast(Decimal | float, value))


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


# Les cinq sources du referentiel spatial. Les sources metier DS-06 a DS-09 ont leur propre
# couverture, exposee par `market_data.list_market_data_coverage`.
SPATIAL_SOURCE_IDS = ("DS-01", "DS-02", "DS-03", "DS-04", "DS-05")


def commune_coverage(commune_code: str) -> dict[str, Any] | None:
    """Couverture d'une commune, source par source.

    Trois etats que l'utilisateur ne doit jamais confondre :

    - **`not_covered`** : aucune source active ici. Une absence de candidat ne veut alors rien
      dire, et la presenter comme un resultat vide laisserait croire qu'un territoire est sans
      interet alors qu'il n'a simplement jamais ete importe.
    - **`partial`** : certaines sources seulement. Le classement est incomplet, et les sources
      manquantes sont **nommees** — un avertissement generique n'apprend rien.
    - **`covered`** : les cinq sources spatiales sont actives sur ce territoire.

    Une source est comptee couverte si elle a une release **active** sur le departement de la
    commune, et au moins une observation dans cette commune. Les deux conditions comptent :
    un pointeur actif sans donnee locale ne couvre pas la commune, et des donnees sans pointeur
    actif ne sont pas lisibles par l'API.
    """
    statement = text(
        """
        WITH commune AS (
            SELECT code, name, department_code
              FROM reference.area
             WHERE area_type = 'commune' AND code = :commune_code
        ), source AS (
            SELECT data_source.id, data_source.name
              FROM meta.data_source
             WHERE data_source.id = ANY(:source_ids)
        )
        SELECT commune.code AS commune_code, commune.name AS commune_name,
               commune.department_code, source.id AS data_source_id,
               source.name AS source_name,
               active.release_id,
               release.acceptance_status,
               coalesce(observed.record_count, 0) AS record_count
          FROM commune
          CROSS JOIN source
          LEFT JOIN meta.active_dataset_release AS active
                 ON active.data_source_id = source.id
                AND active.scope_type = 'department'
                AND active.scope_code = commune.department_code
          LEFT JOIN meta.dataset_release AS release ON release.id = active.release_id
          LEFT JOIN LATERAL (
              SELECT sum(
                         metric.certain_count + metric.ambiguous_count
                       + metric.rejected_count + metric.unmatched_count
                     ) AS record_count
                FROM meta.entity_match_metric AS metric
               WHERE metric.release_id = active.release_id
                 AND metric.commune_code = commune.code
          ) AS observed ON true
         ORDER BY source.id
        """
    )
    with get_engine().connect() as connection:
        rows = list(
            connection.execute(
                statement,
                {"commune_code": commune_code, "source_ids": list(SPATIAL_SOURCE_IDS)},
            ).mappings()
        )
    if not rows:
        return None

    sources: list[dict[str, Any]] = []
    for row in rows:
        # DS-01 ne produit aucune metrique d'appariement : c'est le referentiel contre lequel
        # les autres s'apparient. Son pointeur actif suffit donc a le declarer couvrant.
        record_count = int(row["record_count"])
        has_release = row["release_id"] is not None
        covered = has_release and (record_count > 0 or row["data_source_id"] == "DS-01")
        sources.append(
            {
                "data_source_id": str(row["data_source_id"]),
                "name": str(row["source_name"]),
                "release_id": str(row["release_id"]) if row["release_id"] else None,
                "acceptance_status": (
                    str(row["acceptance_status"]) if row["acceptance_status"] else None
                ),
                "covered": covered,
                "record_count": record_count,
            }
        )
    covered_count = sum(1 for source in sources if source["covered"])
    if covered_count == 0:
        state = "not_covered"
    elif covered_count < len(sources):
        state = "partial"
    else:
        state = "covered"
    return {
        "commune_code": str(rows[0]["commune_code"]),
        "commune_name": str(rows[0]["commune_name"]) if rows[0]["commune_name"] else None,
        "department_code": str(rows[0]["department_code"]),
        "state": state,
        "sources": sources,
        # Nommees, jamais comptees : « 2 sources manquantes » n'apprend rien a l'utilisateur.
        "missing_sources": [
            f"{source['data_source_id']} {source['name']}"
            for source in sources
            if not source["covered"]
        ],
    }


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
               ST_Y(ST_Transform(geom, 4326)) AS latitude,
               COALESCE(
                   (SELECT quarantine.reason_code
                      FROM meta.attribute_quarantine AS quarantine
                     WHERE quarantine.entity_type = 'address'
                       AND quarantine.entity_id = address.id
                       AND quarantine.attribute = 'geom'
                     LIMIT 1),
                   CASE WHEN address.geom IS NULL THEN 'unknown_position' ELSE 'available' END
               ) AS position_status
          FROM reference.address AS address
         WHERE normalized_label % unaccent(lower(:query))
           -- Le CAST est obligatoire : sans lui, PostgreSQL ne peut pas deduire le type
           -- d'un parametre qui n'apparait que compare a NULL et a une colonne, et rejette
           -- la requete par AmbiguousParameter des que commune_code vaut NULL. Meme motif
           -- que dans scoring.py.
           AND (CAST(:commune_code AS text) IS NULL OR commune_code = CAST(:commune_code AS text))
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
                "longitude": _optional_coordinate(row["longitude"]),
                "latitude": _optional_coordinate(row["latitude"]),
                "position_status": str(row["position_status"]),
            }
            for row in rows
        ]


def find_address_context(address_id: str) -> AddressContextRecord | None:
    address_statement = text(
        """
        SELECT id, display_label, commune_code, department_code,
               ST_X(ST_Transform(geom, 4326)) AS longitude,
               ST_Y(ST_Transform(geom, 4326)) AS latitude,
               COALESCE(
                   (SELECT quarantine.reason_code
                      FROM meta.attribute_quarantine AS quarantine
                     WHERE quarantine.entity_type = 'address'
                       AND quarantine.entity_id = address.id
                       AND quarantine.attribute = 'geom'
                     LIMIT 1),
                   CASE WHEN address.geom IS NULL THEN 'unknown_position' ELSE 'available' END
               ) AS position_status
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
            "longitude": _optional_coordinate(address["longitude"]),
            "latitude": _optional_coordinate(address["latitude"]),
            "position_status": str(address["position_status"]),
        }
        return {
            "address": address_record,
            "matches": [_match_from_mapping(dict(row)) for row in matches],
        }
