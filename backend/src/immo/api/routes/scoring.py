import base64
import binascii
import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from immo.scoring import (
    find_opportunity,
    find_score_definition,
    list_opportunities,
    list_opportunity_comparables,
    list_opportunity_evidence,
    list_opportunity_history,
    list_opportunity_sources,
)

router = APIRouter(prefix="/api/v1", tags=["scoring"])

Strategy = Literal["division_extension", "renovation_resale"]
ConfidenceLevel = Literal["high", "medium", "low", "not_publishable"]


class OpportunitySummaryResponse(BaseModel):
    id: str
    property_unit_id: str
    strategy: Strategy
    score: float | None = Field(default=None, ge=0, le=100)
    score_class: Literal["low", "review", "interesting", "high_priority"] | None
    confidence_score: float = Field(ge=0, le=100)
    confidence_level: ConfidenceLevel
    segment_code: str
    snapshot_at: str
    calculated_at: str
    baseline_selected: bool


class OpportunityDetailResponse(OpportunitySummaryResponse):
    definition_id: str
    definition_version: int
    eligible: bool
    eligibility_results: list[dict[str, Any]]
    missing_features: list[str]
    publication_blockers: list[str]
    release_ids: list[str]
    financial_scenario: dict[str, Any] | None
    components: list[dict[str, Any]]


class ScoreDefinitionResponse(BaseModel):
    id: str
    version: int
    strategy: Strategy
    contract_path: str
    contract_digest: str
    feature_registry_version: int
    parameters: dict[str, Any]
    publication_eligible: bool
    meaning: str
    active: bool
    components: list[dict[str, Any]]
    features: list[dict[str, Any]]
    eligibility: list[dict[str, Any]]


def _not_found(value: Any, detail: str) -> Any:
    if value is None:
        raise HTTPException(status_code=404, detail=detail)
    return value


@router.get("/opportunities", response_model=list[OpportunitySummaryResponse])
def opportunities(
    response: Response,
    strategy: Strategy | None = None,
    minimum_score: float | None = Query(default=None, ge=0, le=100),
    confidence_level: ConfidenceLevel | None = None,
    department_code: Literal["22", "29", "35", "56"] | None = None,
    limit: int = Query(default=50, ge=1, le=250),
    cursor: str | None = Query(default=None, max_length=64),
) -> list[OpportunitySummaryResponse]:
    try:
        decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode()) if cursor else None
        cursor_score = float(decoded["score"]) if decoded else None
        cursor_id = str(decoded["id"]) if decoded else None
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(status_code=422, detail="Invalid opportunity cursor") from exc
    try:
        records = list_opportunities(
            strategy=strategy,
            minimum_score=minimum_score,
            confidence_level=confidence_level,
            department_code=department_code,
            limit=limit + 1,
            cursor_score=cursor_score,
            cursor_id=cursor_id,
        )
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Opportunities are unavailable") from exc
    if len(records) > limit:
        last = records[limit - 1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps({"score": last["score"], "id": last["id"]}, separators=(",", ":")).encode()
        ).decode()
        response.headers["X-Next-Cursor"] = next_cursor
        records = records[:limit]
    return [OpportunitySummaryResponse.model_validate(record) for record in records]


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetailResponse)
def opportunity(opportunity_id: str) -> OpportunityDetailResponse:
    try:
        record = find_opportunity(opportunity_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Opportunity is unavailable") from exc
    return OpportunityDetailResponse.model_validate(_not_found(record, "Opportunity not found"))


@router.get(
    "/opportunities/{opportunity_id}/history", response_model=list[OpportunitySummaryResponse]
)
def opportunity_history(opportunity_id: str) -> list[OpportunitySummaryResponse]:
    try:
        records = list_opportunity_history(opportunity_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Opportunity history is unavailable") from exc
    return [
        OpportunitySummaryResponse.model_validate(item)
        for item in _not_found(records, "Opportunity not found")
    ]


@router.get("/opportunities/{opportunity_id}/evidence", response_model=list[dict[str, Any]])
def opportunity_evidence(opportunity_id: str) -> list[dict[str, Any]]:
    try:
        records = list_opportunity_evidence(opportunity_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Score evidence is unavailable") from exc
    return _not_found(records, "Opportunity not found")


@router.get("/opportunities/{opportunity_id}/comparables", response_model=list[dict[str, Any]])
def opportunity_comparables(opportunity_id: str) -> list[dict[str, Any]]:
    try:
        records = list_opportunity_comparables(opportunity_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503, detail="Opportunity comparables are unavailable"
        ) from exc
    return _not_found(records, "Opportunity not found")


@router.get("/opportunities/{opportunity_id}/sources", response_model=list[dict[str, Any]])
def opportunity_sources(opportunity_id: str) -> list[dict[str, Any]]:
    try:
        records = list_opportunity_sources(opportunity_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Opportunity sources are unavailable") from exc
    return _not_found(records, "Opportunity not found")


@router.get("/score-definitions/{definition_id}", response_model=ScoreDefinitionResponse)
def score_definition(definition_id: str) -> ScoreDefinitionResponse:
    try:
        record = find_score_definition(definition_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Score definition is unavailable") from exc
    return ScoreDefinitionResponse.model_validate(_not_found(record, "Score definition not found"))
