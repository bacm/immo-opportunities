FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY pipelines/pyproject.toml pipelines/pyproject.toml
RUN uv sync --frozen --package immo-backend --no-dev --no-install-package immo-backend

COPY backend backend
RUN uv sync --frozen --package immo-backend --no-dev

FROM python:3.13-slim

WORKDIR /workspace
ENV PATH="/workspace/.venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY --from=build /workspace/.venv /workspace/.venv
COPY backend backend

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "immo.main:app", "--host", "0.0.0.0", "--port", "8000"]
