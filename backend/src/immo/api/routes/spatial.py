from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from immo.spatial import (
    commune_coverage,
    find_address_context,
    find_entity_match,
    search_addresses,
)

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial-reference"])


class AddressSearchResponse(BaseModel):
    id: str
    display_label: str
    commune_code: str
    department_code: str
    # Absentes lorsque la position de l'adresse est retenue faute de valeur source fiable.
    # `position_status` porte alors le motif : l'inconnu reste distinct d'un zéro (FR-007).
    longitude: float | None
    latitude: float | None
    position_status: str


class SourceCoverageResponse(BaseModel):
    data_source_id: str
    name: str
    release_id: str | None
    acceptance_status: str | None
    covered: bool
    record_count: int = Field(ge=0)


class CommuneCoverageResponse(BaseModel):
    commune_code: str
    commune_name: str | None
    department_code: str
    # `not_covered` n'est pas `covered` avec zero resultat : le premier dit que l'absence ne
    # veut rien dire, le second qu'aucun bien ne correspond. Les confondre laisserait croire
    # qu'un territoire est vide alors qu'il n'a jamais ete importe.
    state: Literal["covered", "partial", "not_covered"]
    sources: list[SourceCoverageResponse]
    missing_sources: list[str]


class SourceIdentifierResponse(BaseModel):
    data_source_id: str
    source_entity_type: str
    source_identifier: str
    is_preferred: bool


class MatchReviewResponse(BaseModel):
    previous_decision: Literal["certain", "ambiguous", "rejected"]
    reviewed_decision: Literal["certain", "ambiguous", "rejected"]
    reviewer: str
    rationale: str
    reviewed_at: str


class EntityMatchResponse(BaseModel):
    id: int
    candidate_group_key: str
    left_entity_type: str
    left_entity_id: str
    right_entity_type: str
    right_entity_id: str
    method: Literal[
        "official_identifier",
        "source_relation",
        "spatial_intersection",
        "proximity",
        "normalized_address",
        "temporal_consistency",
        "manual",
    ]
    algorithm_code: str
    algorithm_version: str
    confidence: float = Field(ge=0, le=1)
    decision: Literal["certain", "ambiguous", "rejected"]
    critical: bool
    blocks_publication: bool
    rationale: str
    evidence: dict[str, Any]
    release_ids: list[str]
    left_source_identifiers: list[SourceIdentifierResponse]
    right_source_identifiers: list[SourceIdentifierResponse]
    reviews: list[MatchReviewResponse]


class AddressContextResponse(BaseModel):
    address: AddressSearchResponse
    matches: list[EntityMatchResponse]


@router.get("/coverage", response_model=CommuneCoverageResponse)
def coverage(
    commune_code: str = Query(pattern=r"^[0-9A-Z]{5}$"),
) -> CommuneCoverageResponse:
    try:
        record = commune_coverage(commune_code)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Spatial reference is unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Commune not found")
    return CommuneCoverageResponse.model_validate(record)


@router.get("/addresses", response_model=list[AddressSearchResponse])
def address_search(
    query: str = Query(min_length=3, max_length=200),
    commune_code: str | None = Query(default=None, pattern=r"^[0-9A-Z]{5}$"),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[AddressSearchResponse]:
    try:
        records = search_addresses(query, commune_code=commune_code, limit=limit)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Spatial reference is unavailable") from exc
    return [AddressSearchResponse.model_validate(record) for record in records]


@router.get("/addresses/{address_id}", response_model=AddressContextResponse)
def address_context(address_id: str) -> AddressContextResponse:
    try:
        record = find_address_context(address_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Spatial reference is unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return AddressContextResponse.model_validate(record)


@router.get("/matches/{match_id}", response_model=EntityMatchResponse)
def match_inspection(match_id: int) -> EntityMatchResponse:
    try:
        record = find_entity_match(match_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Spatial reference is unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Entity match not found")
    return EntityMatchResponse.model_validate(record)
