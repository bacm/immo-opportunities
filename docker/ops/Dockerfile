ARG SOPS_VERSION=3.13.0

FROM ghcr.io/getsops/sops:v${SOPS_VERSION} AS sops

FROM python:3.13.5-slim-bookworm

ARG ANSIBLE_CORE_VERSION=2.19.2

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
      age \
      ca-certificates \
      git \
      jq \
      make \
      openssh-client \
      rsync \
    && python -m pip install --no-cache-dir "ansible-core==${ANSIBLE_CORE_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=sops /usr/local/bin/sops /usr/local/bin/sops
COPY infra/ansible/collections/requirements.yml /tmp/requirements.yml

RUN ansible-galaxy collection install \
      --collections-path /usr/share/ansible/collections \
      --requirements-file /tmp/requirements.yml \
    && rm /tmp/requirements.yml \
    && useradd --create-home --uid 1000 ops

USER ops
WORKDIR /workspace

CMD ["/bin/bash"]
