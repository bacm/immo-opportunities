from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from immo.connected_mvp import (
    MembershipNotFoundError,
    OpportunityNotFoundError,
    PermissionDeniedError,
)


def error_body(request: Request, code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    message = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(request, "http_error", message, exc.detail),
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        content=error_body(
            request,
            "validation_error",
            "Request validation failed",
            jsonable_encoder(exc.errors(), custom_encoder={ValueError: str}),
        ),
    )


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    del exc
    return JSONResponse(
        status_code=500,
        content=error_body(request, "internal_error", "An unexpected error occurred"),
    )


async def access_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, OpportunityNotFoundError):
        return JSONResponse(
            status_code=404,
            content=error_body(request, "not_found", "Opportunity not found"),
        )
    if isinstance(exc, MembershipNotFoundError):
        message = "The authenticated user has no organization membership"
    else:
        assert isinstance(exc, PermissionDeniedError)
        message = str(exc)
    return JSONResponse(
        status_code=403,
        content=error_body(request, "forbidden", message),
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(MembershipNotFoundError, access_exception_handler)
    app.add_exception_handler(PermissionDeniedError, access_exception_handler)
    app.add_exception_handler(OpportunityNotFoundError, access_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
