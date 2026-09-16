from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.exc import SQLAlchemyError

from immo.explorer import (
    EntityDetail,
    find_building,
    find_parcel,
    find_property_unit,
    list_areas,
    list_parcel_energy_assessments,
    list_parcel_transactions,
    list_property_units_in_viewport,
    search_entities,
)

router = APIRouter(prefix="/api/v1", tags=["real-map"])


class AreaResponse(BaseModel):
    id: str
    area_type: Literal["commune"]
    code: str
    name: str
    department_code: str
    center: list[float] = Field(min_length=2, max_length=2)
    bbox: list[float] = Field(min_length=4, max_length=4)


class SearchResponse(BaseModel):
    entity_type: Literal["address", "area", "parcel"]
    id: str
    label: str
    secondary_label: str
    center: list[float] = Field(min_length=2, max_length=2)
    bbox: list[float] = Field(min_length=4, max_length=4)


class PropertyUnitSummaryResponse(BaseModel):
    id: str
    cadastral_id: str
    commune_code: str
    commune_name: str
    area_m2: float = Field(ge=0)
    building_count: int = Field(ge=0)
    building_footprint_m2: float = Field(ge=0)
    center: list[float] = Field(min_length=2, max_length=2)


class ViewportResponse(BaseModel):
    coverage: Literal["covered", "outside_coverage"]
    partial: bool
    items: list[PropertyUnitSummaryResponse]


class BboxQuery(BaseModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def validate_extent(self) -> "BboxQuery":
        if self.west >= self.east or self.south >= self.north:
            raise ValueError("bbox coordinates must define a positive extent")
        if self.east - self.west > 1 or self.north - self.south > 1:
            raise ValueError("bbox is too large; zoom into the covered territory")
        return self


class EntityDetailResponse(BaseModel):
    id: str
    entity_type: Literal["parcel", "building", "property_unit"]
    label: str
    commune_code: str | None
    commune_name: str | None
    department_code: str
    area_m2: float | None = Field(default=None, ge=0)
    center: list[float] = Field(min_length=2, max_length=2)
    bbox: list[float] = Field(min_length=4, max_length=4)
    geometry: dict[str, Any]
    properties: dict[str, Any]
    related_entities: list[dict[str, Any]]
    sources: list[dict[str, Any]]


@router.get("/areas", response_model=list[AreaResponse])
def areas(
    department_code: str = Query(default="35", pattern=r"^[0-9A-Z]{2,3}$"),
    area_type: Literal["commune"] = "commune",
) -> list[AreaResponse]:
    try:
        records = list_areas(department_code=department_code, area_type=area_type)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Geographic areas are unavailable") from exc
    return [AreaResponse.model_validate(record) for record in records]


@router.get("/search", response_model=list[SearchResponse])
def search(
    query: str = Query(min_length=3, max_length=200),
    department_code: str = Query(default="35", pattern=r"^[0-9A-Z]{2,3}$"),
    limit: int = Query(default=10, ge=1, le=30),
) -> list[SearchResponse]:
    try:
        records = search_entities(query, department_code=department_code, limit=limit)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Geographic search is unavailable") from exc
    return [SearchResponse.model_validate(record) for record in records]


@router.get("/property-units", response_model=ViewportResponse)
def property_units(
    west: float,
    south: float,
    east: float,
    north: float,
    limit: int = Query(default=100, ge=1, le=250),
) -> ViewportResponse:
    try:
        bbox = BboxQuery(west=west, south=south, east=east, north=north)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid or oversized viewport") from exc
    try:
        record = list_property_units_in_viewport(**bbox.model_dump(), limit=limit)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503, detail="Visible property units are unavailable"
        ) from exc
    return ViewportResponse.model_validate(record)


def _entity_response(record: EntityDetail | None, detail: str) -> EntityDetailResponse:
    if record is None:
        raise HTTPException(status_code=404, detail=detail)
    return EntityDetailResponse.model_validate(record)


@router.get("/parcels/{parcel_id}", response_model=EntityDetailResponse)
def parcel(parcel_id: str) -> EntityDetailResponse:
    try:
        record = find_parcel(parcel_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Parcel data is unavailable") from exc
    return _entity_response(record, "Parcel not found")


@router.get("/buildings/{building_id}", response_model=EntityDetailResponse)
def building(building_id: str) -> EntityDetailResponse:
    try:
        record = find_building(building_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Building data is unavailable") from exc
    return _entity_response(record, "Building not found")


class ParcelTransactionResponse(BaseModel):
    """Une mutation DVF rattachée à la parcelle.

    `allocated_price_eur` est nul quand le prix n'est pas allouable à ce lot, et
    `unallocated_reason` dit alors pourquoi — c'est le cas de 65,5 % des mutations. Aucun prix au
    m² n'est calculé : il n'existe pas en base et le dériver ici en fabriquerait un.
    """

    transaction_id: str
    mutation_date: str | None
    mutation_nature: str | None
    price_eur: float | None
    property_type: str | None
    surface_m2: float | None
    allocated_price_eur: float | None
    allocation_method: str | None
    unallocated_reason: str | None
    parcel_count: int | None
    lot_count: int | None


@router.get("/parcels/{parcel_id}/transactions", response_model=list[ParcelTransactionResponse])
def parcel_transactions(parcel_id: str) -> list[ParcelTransactionResponse]:
    """Vérification D6a : les mutations d'une parcelle, sur l'API privée sous RLS.

    Jamais par les tuiles — une transaction n'est pas un attribut de rendu.
    """
    try:
        records = list_parcel_transactions(parcel_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Spatial reference is unavailable") from exc
    return [ParcelTransactionResponse.model_validate(record) for record in records]


class ParcelEnergyAssessmentResponse(BaseModel):
    """Un diagnostic DPE atteignant la parcelle par un de ses bâtiments RNB.

    `relation_status` est celui du pont bâtiment ↔ parcelle, montré tel qu'il est en base : un
    bâtiment chevauche 2,24 parcelles en moyenne, et un rattachement ambigu présenté comme
    certain attribuerait le diagnostic à la mauvaise parcelle.

    `identifier_provenance` dit d'où vient l'`id_rnb` qui a servi au rattachement — « Reprise
    RNB » ou « Logiciel ». La confiance d'appariement ne figure pas ici : elle vaut 1,0 pour tous
    ces diagnostics, l'identifiant étant déclaré par le producteur, et l'afficher laisserait
    croire à une vérification qui n'a pas eu lieu.
    """

    dpe_number: str
    assessment_date: str | None
    energy_label: str | None
    energy_consumption_kwh_m2_year: float | None
    surface_habitable_m2: float | None
    building_type: str | None
    building_id: str | None
    relation_status: str
    identifier_provenance: str | None
    address_label: str | None
    release_id: str
    data_source_id: Literal["DS-07", "DS-13"]


@router.get(
    "/parcels/{parcel_id}/energy-assessments",
    response_model=list[ParcelEnergyAssessmentResponse],
)
def parcel_energy_assessments(parcel_id: str) -> list[ParcelEnergyAssessmentResponse]:
    """Vérification D6b : les diagnostics d'une parcelle, sur l'API privée sous RLS.

    Jamais par les tuiles — une étiquette énergétique n'est pas un attribut de rendu, et la
    colorer de A à G en ferait un signal de dégradation que le produit s'interdit.
    """
    try:
        records = list_parcel_energy_assessments(parcel_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Spatial reference is unavailable") from exc
    return [ParcelEnergyAssessmentResponse.model_validate(record) for record in records]


@router.get("/property-units/{property_unit_id}", response_model=EntityDetailResponse)
def property_unit(property_unit_id: str) -> EntityDetailResponse:
    try:
        record = find_property_unit(property_unit_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Property unit data is unavailable") from exc
    return _entity_response(record, "Property unit not found")
