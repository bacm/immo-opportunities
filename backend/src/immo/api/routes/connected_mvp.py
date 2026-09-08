from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from immo.auth import Principal, current_principal
from immo.connected_mvp import (
    add_note,
    add_review,
    add_review_outcome,
    add_saved_search,
    add_scenario,
    change_status,
    get_session,
    get_workspace,
    list_data_quality,
    list_import_runs,
    list_match_metrics,
)

router = APIRouter(prefix="/api/v1", tags=["connected-mvp"])
PrincipalDep = Annotated[Principal, Depends(current_principal)]

Role = Literal["platform_admin", "organization_admin", "analyst", "viewer"]
CandidateStatus = Literal[
    "new",
    "to_analyze",
    "retained",
    "contact_to_prepare",
    "contacted",
    "visit",
    "offer",
    "acquired",
    "lost",
    "rejected",
    "ignored",
]
RejectionReason = Literal[
    "land_false_positive",
    "adverse_planning",
    "no_access",
    "risk_too_high",
    "estimate_too_optimistic",
    "works_too_large",
    "already_known",
    "outside_strategy",
    "other",
]


class SessionResponse(BaseModel):
    user_id: str
    display_name: str
    email: str | None
    organization_id: str
    organization_name: str
    role: Role


class StatusRequest(BaseModel):
    status: CandidateStatus
    favorite: bool | None = None
    rejection_reasons: list[RejectionReason] = Field(
        default_factory=lambda: list[RejectionReason](), max_length=9
    )
    rejection_comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_rejection(self) -> "StatusRequest":
        if self.status == "rejected" and not self.rejection_reasons:
            raise ValueError("A rejected candidate requires at least one reason")
        if "other" in self.rejection_reasons and not (self.rejection_comment or "").strip():
            raise ValueError("The 'other' rejection reason requires a comment")
        if self.status != "rejected" and self.rejection_reasons:
            raise ValueError("Rejection reasons are only accepted for rejected candidates")
        return self


class CandidateStateResponse(BaseModel):
    status: CandidateStatus
    favorite: bool
    rejection_reasons: list[RejectionReason]
    rejection_comment: str | None
    updated_at: str | None


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class NoteResponse(BaseModel):
    id: str
    body: str
    author: str
    created_at: str


class ReviewRequest(BaseModel):
    decision: Literal["worth_deeper_analysis", "not_relevant", "uncertain"]
    rejection_reasons: list[RejectionReason] = Field(
        default_factory=lambda: list[RejectionReason](), max_length=9
    )
    confidence: int = Field(ge=1, le=5)
    field_visit_performed: bool = False
    strategy_code: Literal["division_extension", "renovation_resale"] | None = None
    protocol_version: str | None = Field(default=None, max_length=100)
    protocol_arm: Literal["top_score", "baseline", "random"] | None = None
    evaluation_split: Literal["development", "validation", "final"] | None = None
    segment_code: Literal["metropolitan", "medium_city", "periurban", "coastal", "rural"] | None = (
        None
    )
    blind_id: str | None = Field(default=None, max_length=100)
    double_review_group: str | None = Field(default=None, max_length=100)


class ReviewResponse(ReviewRequest):
    id: str
    author: str
    reviewed_at: str
    reviewer_pseudonym: str | None = None


class ReviewOutcomeRequest(BaseModel):
    stage: Literal["desk_analysis", "contact", "visit", "offer", "acquisition"]
    result: Literal["positive", "negative", "pending", "unknown"]
    details: dict[str, Any] = Field(default_factory=dict)
    observed_at: str


class ReviewOutcomeResponse(ReviewOutcomeRequest):
    id: str
    candidate_review_id: str
    created_at: str


class ScenarioRequest(BaseModel):
    purchase_price_eur: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    works_cost_eur: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    resale_price_eur: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    fees_eur: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    finance_cost_eur: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    holding_cost_eur: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)


class ScenarioResponse(BaseModel):
    id: str
    assumptions: dict[str, float]
    results: dict[str, float]
    created_at: str


class SavedSearchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    filters: dict[str, Any]


class SavedSearchResponse(SavedSearchRequest):
    id: str
    created_at: str


class WorkspaceResponse(BaseModel):
    state: CandidateStateResponse
    history: list[dict[str, Any]]
    notes: list[NoteResponse]
    scenarios: list[ScenarioResponse]


@router.get("/session", response_model=SessionResponse)
def session(principal: PrincipalDep) -> SessionResponse:
    return SessionResponse.model_validate(get_session(principal))


@router.get("/opportunities/{opportunity_id}/workspace", response_model=WorkspaceResponse)
def opportunity_workspace(opportunity_id: str, principal: PrincipalDep) -> WorkspaceResponse:
    return WorkspaceResponse.model_validate(get_workspace(principal, opportunity_id))


@router.patch("/opportunities/{opportunity_id}/status", response_model=CandidateStateResponse)
def update_opportunity_status(
    opportunity_id: str,
    payload: StatusRequest,
    principal: PrincipalDep,
) -> CandidateStateResponse:
    return CandidateStateResponse.model_validate(
        change_status(
            principal,
            opportunity_id,
            status=payload.status,
            favorite=payload.favorite,
            rejection_reasons=list(payload.rejection_reasons),
            rejection_comment=payload.rejection_comment,
        )
    )


@router.post(
    "/opportunities/{opportunity_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    opportunity_id: str,
    payload: NoteRequest,
    principal: PrincipalDep,
) -> NoteResponse:
    return NoteResponse.model_validate(add_note(principal, opportunity_id, payload.body))


@router.post(
    "/opportunities/{opportunity_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    opportunity_id: str,
    payload: ReviewRequest,
    principal: PrincipalDep,
) -> ReviewResponse:
    return ReviewResponse.model_validate(
        add_review(
            principal,
            opportunity_id,
            decision=payload.decision,
            rejection_reasons=list(payload.rejection_reasons),
            confidence=payload.confidence,
            field_visit_performed=payload.field_visit_performed,
            strategy_code=payload.strategy_code,
            protocol_version=payload.protocol_version,
            protocol_arm=payload.protocol_arm,
            evaluation_split=payload.evaluation_split,
            segment_code=payload.segment_code,
            blind_id=payload.blind_id,
            double_review_group=payload.double_review_group,
        )
    )


@router.post(
    "/reviews/{review_id}/outcomes",
    response_model=ReviewOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review_outcome(
    review_id: str,
    payload: ReviewOutcomeRequest,
    principal: PrincipalDep,
) -> ReviewOutcomeResponse:
    return ReviewOutcomeResponse.model_validate(
        add_review_outcome(principal, review_id, **payload.model_dump())
    )


@router.post(
    "/opportunities/{opportunity_id}/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scenario(
    opportunity_id: str,
    payload: ScenarioRequest,
    principal: PrincipalDep,
) -> ScenarioResponse:
    return ScenarioResponse.model_validate(
        add_scenario(principal, opportunity_id, payload.model_dump())
    )


@router.post(
    "/saved-searches",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_search(
    payload: SavedSearchRequest,
    principal: PrincipalDep,
) -> SavedSearchResponse:
    return SavedSearchResponse.model_validate(
        add_saved_search(principal, name=payload.name, filters=payload.filters)
    )


@router.get("/admin/import-runs", response_model=list[dict[str, Any]])
def admin_import_runs(
    request: Request,
    principal: PrincipalDep,
    limit: int = Query(default=50, ge=1, le=250),
) -> list[dict[str, Any]]:
    return list_import_runs(principal, request.state.request_id, limit)


@router.get("/admin/match-metrics", response_model=list[dict[str, Any]])
def admin_match_metrics(
    request: Request,
    principal: PrincipalDep,
    relation_type: str | None = Query(default=None, max_length=64),
    commune_code: str | None = Query(default=None, min_length=5, max_length=5),
    limit: int = Query(default=200, ge=1, le=2000),
) -> list[dict[str, Any]]:
    return list_match_metrics(
        principal, request.state.request_id, limit, relation_type, commune_code
    )


@router.get("/admin/data-quality", response_model=list[dict[str, Any]])
def admin_data_quality(
    request: Request,
    principal: PrincipalDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    return list_data_quality(principal, request.state.request_id, limit)
