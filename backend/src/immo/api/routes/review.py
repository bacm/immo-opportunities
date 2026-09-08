from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from immo.review import (
    next_blind_case,
    record_verdict,
    review_progress,
    review_results,
)

router = APIRouter(prefix="/api/v1/review", tags=["matching-review"])


class BlindCaseResponse(BaseModel):
    """Un cas à juger, **sans** la décision du moteur.

    Aucun champ de ce modèle ne porte la décision, la confiance ou la justification. Les
    exposer ferait mesurer à la revue l'accord avec le moteur au lieu de l'exactitude, ce que
    le protocole de B4 interdit explicitement.
    """

    id: int
    sample_id: str
    territorial_stratum: str
    commune_code: str | None
    commune_name: str | None
    drawn_rank: int
    left_label: str | None
    left_kind: str | None
    right_label: str | None
    right_kind: str | None
    longitude: float | None
    latitude: float | None


class ReviewProgressResponse(BaseModel):
    sample_id: str
    seed: int
    target_size: int
    size_rationale: str
    protocol_document: str
    drawn_at: str
    total_cases: int
    judged_cases: int


class VerdictRequest(BaseModel):
    case_id: int
    # « indécidable » est un résultat valide : il ne doit être ni forcé ni compté comme correct.
    verdict: Literal["correct", "incorrect", "undecidable"]
    reviewer: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=3, max_length=2000)
    # Ce que le relecteur a réellement consulté. Un verdict rendu sur la seule sortie du moteur
    # ne mesurerait rien.
    evidence_consulted: str = Field(min_length=3, max_length=500)


class VerdictResponse(BaseModel):
    id: int
    case_id: int
    verdict: str
    recorded_at: str


class StratumResultResponse(BaseModel):
    matching_stratum: str
    territorial_stratum: str
    drawn: int
    judged: int
    correct: int
    incorrect: int
    undecidable: int
    # Calculé sur les seuls cas tranchés, nul si aucun ne l'est.
    accuracy: float | None


@router.get("/samples/{sample_id}", response_model=ReviewProgressResponse)
def sample_progress(sample_id: str) -> ReviewProgressResponse:
    try:
        record = review_progress(sample_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Review store is unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Review sample not found")
    return ReviewProgressResponse.model_validate(record)


@router.get("/samples/{sample_id}/next", response_model=BlindCaseResponse)
def next_case(sample_id: str) -> BlindCaseResponse:
    try:
        record = next_blind_case(sample_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Review store is unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="No unjudged case left in this sample")
    return BlindCaseResponse.model_validate(record)


@router.post("/verdicts", response_model=VerdictResponse, status_code=201)
def submit_verdict(payload: VerdictRequest) -> VerdictResponse:
    try:
        record = record_verdict(
            case_id=payload.case_id,
            verdict=payload.verdict,
            reviewer=payload.reviewer,
            rationale=payload.rationale,
            evidence_consulted=payload.evidence_consulted,
        )
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Review store is unavailable") from exc
    return VerdictResponse.model_validate(record)


@router.get("/samples/{sample_id}/results", response_model=list[StratumResultResponse])
def sample_results(
    sample_id: str,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[StratumResultResponse]:
    try:
        records = review_results(sample_id)
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Review store is unavailable") from exc
    return [StratumResultResponse.model_validate(record) for record in records[:limit]]
