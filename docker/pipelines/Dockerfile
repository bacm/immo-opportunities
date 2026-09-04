FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY pipelines/pyproject.toml pipelines/pyproject.toml
RUN uv sync --frozen --package immo-pipelines --no-dev --no-install-package immo-pipelines

COPY pipelines pipelines
COPY contracts contracts
RUN uv sync --frozen --package immo-pipelines --no-dev

FROM python:3.13-slim

WORKDIR /workspace
ENV PATH="/workspace/.venv/bin:$PATH" PYTHONUNBUFFERED=1 DAGSTER_HOME=/opt/dagster
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /workspace/.venv /workspace/.venv
COPY pipelines pipelines
COPY contracts contracts
COPY docker/pipelines/entrypoint.sh /usr/local/bin/immo-dagster-entrypoint
RUN install -d -o 10001 -g 10001 /opt/dagster/storage \
    && cp pipelines/dagster.yaml pipelines/workspace.yaml /opt/dagster/ \
    && chmod 0555 /usr/local/bin/immo-dagster-entrypoint \
    && chown -R 10001:10001 /opt/dagster

USER 10001:10001
ENTRYPOINT ["immo-dagster-entrypoint"]
