from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from immo import __version__
from immo.config import get_settings
from immo.database import DatabaseMetadata, check_database

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


class VersionResponse(BaseModel):
    application: str
    version: str
    git_sha: str
    environment: str
    database: DatabaseMetadata


@router.get("/version", response_model=VersionResponse)
def application_version() -> VersionResponse:
    settings = get_settings()
    try:
        database = check_database()
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="Database metadata is unavailable") from exc
    return VersionResponse(
        application="immo-api",
        version=__version__,
        git_sha=settings.git_sha,
        environment=settings.environment,
        database=database,
    )
