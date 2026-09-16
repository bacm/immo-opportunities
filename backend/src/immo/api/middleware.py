import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
UNMATCHED_ROUTE = "unmatched"
logger = logging.getLogger("immo.access")


def route_template(request: Request) -> str:
    """Le gabarit de la route servie, jamais le chemin concret : un identifiant n'est pas une
    étiquette de métrique (G7)."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else UNMATCHED_ROUTE


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        logger.exception(
            "request_failed request_id=%s method=%s route=%s",
            request_id,
            request.method,
            route_template(request),
        )
        raise
    finally:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request_completed request_id=%s method=%s route=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            route_template(request),
            request.url.path,
            status_code,
            duration_ms,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["Server-Timing"] = f"app;dur={duration_ms}"
    return response
