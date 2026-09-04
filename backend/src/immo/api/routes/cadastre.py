from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from immo.cadastre import find_active_parcel

router = APIRouter(prefix="/api/v1/cadastre", tags=["cadastre"])


class ParcelProvenanceResponse(BaseModel):
    data_source_id: str
    release_id: str
    release_key: str
    source_published_on: str | None
    raw_asset_id: int
    layer: str
    source_url: str
    object_key: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_row_number: int
    record_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    transformation_version: str
    was_repaired: bool
    repair_method: str | None


class CadastralParcelResponse(BaseModel):
    cadastral_id: str
    department_code: str
    commune_code: str
    prefix: str
    section: str
    number: str
    stated_area_m2: int | None
    geometry: dict[str, Any]
    provenance: ParcelProvenanceResponse


@router.get("/parcels/{cadastral_id}", response_model=CadastralParcelResponse)
def cadastral_parcel(cadastral_id: str) -> CadastralParcelResponse:
    try:
        parcel = find_active_parcel(cadastral_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Cadastral data is unavailable") from exc
    if parcel is None:
        raise HTTPException(status_code=404, detail="Active cadastral parcel not found")
    return CadastralParcelResponse.model_validate(parcel)
