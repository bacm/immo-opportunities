from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from immo.database import check_database

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "ready"]


@router.get("/health/live", response_model=HealthResponse, include_in_schema=False)
def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse, include_in_schema=False)
def ready() -> HealthResponse:
    try:
        check_database()
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return HealthResponse(status="ready")
