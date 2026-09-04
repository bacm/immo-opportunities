from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from immo.market_data import find_market_context, list_market_data_coverage

router = APIRouter(prefix="/api/v1", tags=["market-data"])


class MarketContextResponse(BaseModel):
    property_unit_id: str
    snapshot_at: str
    comparables: list[dict[str, Any]]
    energy_assessment: dict[str, Any] | None
    urban_zone: dict[str, Any] | None
    risks: list[dict[str, Any]]


class CoverageResponse(BaseModel):
    data_source_id: str
    release_id: str | None
    acceptance_status: str | None
    source_published_on: str | None
    record_count: int | None
    matched_record_count: int | None
    coverage_ratio: float | None
    freshest_observation_at: str | None
    measured_at: str | None


@router.get("/market-data/coverage", response_model=list[CoverageResponse])
def market_data_coverage(
    commune_code: Annotated[str, Query(pattern=r"^[0-9A-Z]{5}$")],
) -> list[CoverageResponse]:
    try:
        records = list_market_data_coverage(commune_code=commune_code)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Market data coverage is unavailable") from exc
    return [CoverageResponse.model_validate(record) for record in records]


@router.get(
    "/property-units/{property_unit_id}/market-context",
    response_model=MarketContextResponse,
)
def property_unit_market_context(
    property_unit_id: str,
    snapshot_at: Annotated[date, Query()],
) -> MarketContextResponse:
    try:
        record = find_market_context(property_unit_id, snapshot_at=snapshot_at.isoformat())
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Market context is unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Property unit not found")
    return MarketContextResponse.model_validate(record)
