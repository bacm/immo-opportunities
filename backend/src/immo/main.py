from fastapi import FastAPI

from immo import __version__
from immo.api.errors import install_exception_handlers
from immo.api.middleware import request_id_middleware
from immo.api.routes.brittany_pilot import router as brittany_pilot_router
from immo.api.routes.cadastre import router as cadastre_router
from immo.api.routes.connected_mvp import router as connected_mvp_router
from immo.api.routes.explorer import router as explorer_router
from immo.api.routes.health import router as health_router
from immo.api.routes.market_data import router as market_data_router
from immo.api.routes.meta import router as meta_router
from immo.api.routes.scoring import router as scoring_router
from immo.api.routes.spatial import router as spatial_router
from immo.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.docs_enabled else None
    app = FastAPI(
        title="Immo Opportunities API",
        version=__version__,
        docs_url=docs_url,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json" if settings.docs_enabled else None,
    )
    app.middleware("http")(request_id_middleware)
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(meta_router)
    app.include_router(cadastre_router)
    app.include_router(brittany_pilot_router)
    app.include_router(spatial_router)
    app.include_router(explorer_router)
    app.include_router(market_data_router)
    app.include_router(scoring_router)
    app.include_router(connected_mvp_router)
    return app


app = create_app()
