from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from immo.auth import Principal, current_principal
from immo.brittany_pilot import (
    get_brittany_readiness,
    publish_brittany,
    rollback_brittany,
    withdraw_brittany,
)

router = APIRouter(prefix="/api/v1/admin/brittany", tags=["brittany-pilot"])
PrincipalDep = Annotated[Principal, Depends(current_principal)]


class PublicationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class RollbackRequest(PublicationRequest):
    bundle_id: str = Field(pattern=r"^brittany:[0-9a-f-]{36}$")


@router.get("/readiness", response_model=dict[str, Any])
def brittany_readiness(principal: PrincipalDep) -> dict[str, Any]:
    return get_brittany_readiness(principal)


@router.post("/publications", response_model=dict[str, str])
def create_brittany_publication(
    payload: PublicationRequest, principal: PrincipalDep
) -> dict[str, str]:
    try:
        return publish_brittany(principal, reason=payload.reason)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=409, detail="Regional publication gates are not satisfied"
        ) from exc


@router.post("/rollback", response_model=dict[str, str])
def rollback_brittany_publication(
    payload: RollbackRequest, principal: PrincipalDep
) -> dict[str, str]:
    try:
        return rollback_brittany(principal, bundle_id=payload.bundle_id, reason=payload.reason)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=409, detail="Regional rollback is not eligible") from exc


@router.post("/withdraw", response_model=dict[str, str])
def withdraw_brittany_publication(
    payload: PublicationRequest, principal: PrincipalDep
) -> dict[str, str]:
    try:
        return withdraw_brittany(principal, reason=payload.reason)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=409, detail="No regional publication can be withdrawn"
        ) from exc
