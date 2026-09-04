from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from immo.config import get_settings


@dataclass(frozen=True)
class Principal:
    subject: str
    email: str | None
    display_name: str


@lru_cache
def _jwk_client(url: str, cache_seconds: int) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=cache_seconds)


def _decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    signing_key = _jwk_client(
        settings.oidc_jwks_url, settings.oidc_jwks_cache_seconds
    ).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.oidc_audience,
        issuer=settings.oidc_issuer,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )
    return dict(claims)


def current_principal(request: Request) -> Principal:
    settings = get_settings()
    if not settings.oidc_enabled:
        if settings.environment not in {"development", "test"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC must be enabled outside development and test",
            )
        return Principal(
            subject="development-user",
            email="development@localhost",
            display_name="Utilisateur local",
        )

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = _decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Access token has no subject")
    email = claims.get("email")
    name = claims.get("name") or claims.get("preferred_username") or subject
    return Principal(
        subject=subject,
        email=email if isinstance(email, str) else None,
        display_name=str(name),
    )
