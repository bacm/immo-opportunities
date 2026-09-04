from functools import lru_cache
from typing import TypedDict

from sqlalchemy import Engine, create_engine, text

from immo.config import get_settings


class DatabaseMetadata(TypedDict):
    status: str
    postgres_version: str
    postgis_version: str


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.sqlalchemy_url(),
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        pool_timeout=settings.database_pool_timeout_seconds,
    )


def check_database() -> DatabaseMetadata:
    with get_engine().connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT current_setting('server_version') AS postgres_version, "
                    "postgis_lib_version() AS postgis_version"
                )
            )
            .mappings()
            .one()
        )
    return {
        "status": "connected",
        "postgres_version": str(row["postgres_version"]),
        "postgis_version": str(row["postgis_version"]),
    }
