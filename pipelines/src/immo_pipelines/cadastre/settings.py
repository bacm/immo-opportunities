import os
from dataclasses import dataclass
from pathlib import Path


def _secret(name: str, default: str | None = None) -> str | None:
    file_value = os.getenv(f"{name}_FILE")
    if file_value:
        return Path(file_value).read_text(encoding="utf-8").strip()
    return os.getenv(name, default)


@dataclass(frozen=True)
class CadastreSettings:
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str

    @classmethod
    def from_environment(cls) -> "CadastreSettings":
        database_password = _secret("PIPELINE_DATABASE_PASSWORD")
        minio_access_key = _secret("PIPELINE_MINIO_ACCESS_KEY")
        minio_secret_key = _secret("PIPELINE_MINIO_SECRET_KEY")
        if not database_password or not minio_access_key or not minio_secret_key:
            raise ValueError("Pipeline database and MinIO secrets are required")
        return cls(
            database_host=os.getenv("PIPELINE_DATABASE_HOST", "postgres"),
            database_port=int(os.getenv("PIPELINE_DATABASE_PORT", "5432")),
            database_name=os.getenv("PIPELINE_DATABASE_NAME", "immo"),
            database_user=os.getenv("PIPELINE_DATABASE_USER", "immo"),
            database_password=database_password,
            minio_endpoint=os.getenv("PIPELINE_MINIO_ENDPOINT", "minio:9000"),
            minio_access_key=minio_access_key,
            minio_secret_key=minio_secret_key,
        )
