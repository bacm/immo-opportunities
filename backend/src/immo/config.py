from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IMMO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    docs_enabled: bool = True
    git_sha: str = "development"
    database_url: str | None = None
    database_host: str = "postgres"
    database_port: int = 5432
    database_name: str = "immo"
    database_user: str = "immo"
    database_password_file: Path | None = None
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_pool_timeout_seconds: int = Field(default=5, ge=1, le=30)
    oidc_enabled: bool = False
    oidc_issuer: str = "http://localhost:8080/auth/realms/immo"
    oidc_jwks_url: str = "http://keycloak:8080/auth/realms/immo/protocol/openid-connect/certs"
    oidc_audience: str = "immo-api"
    oidc_jwks_cache_seconds: int = Field(default=300, ge=30, le=3600)

    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        password = None
        if self.database_password_file:
            password = self.database_password_file.read_text(encoding="utf-8").strip()
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.database_user,
            password=password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
