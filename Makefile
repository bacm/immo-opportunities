SHELL := /bin/bash
.DEFAULT_GOAL := help

UV_CACHE_DIR ?= $(CURDIR)/.runtime/uv-cache
export UV_CACHE_DIR

ENV ?= staging
COMPOSE_ENV_FILE ?= $(if $(wildcard .env),.env,.env.example)
OPS_IMAGE ?= immo-opportunities-ops:local
INVENTORY ?= infra/ansible/inventories/generated/$(ENV).json
SOPS_FILE = /workspace/secrets/$(ENV).sops.yaml
AGE_KEY_FILE ?= $(HOME)/.config/sops/age/keys.txt
SSH_PRIVATE_KEY_FILE ?= $(HOME)/.ssh/id_ed25519
SSH_KNOWN_HOSTS_FILE ?= $(HOME)/.ssh/known_hosts
FORMAT_DATA_VOLUMES ?= false
DEPARTMENT ?= 35

OPS_RUN = docker run --rm \
	-v "$(CURDIR):/workspace" \
	-w /workspace \
	-e ANSIBLE_CONFIG=/workspace/infra/ansible/ansible.cfg \
	$(OPS_IMAGE)

.PHONY: help config validate dev-secrets dev up rebuild down logs ops-build \
	inventory ansible-syntax bootstrap deploy smoke check python-check web-check \
	openapi openapi-check migrate database-permissions cadastre-fixture rnb-import ban-import ban-census mvt-benchmark e2e backlog backlog-check

help:
	@echo "make dev-secrets                  Generate disposable local secrets"
	@echo "make dev                          Start local infrastructure"
	@echo "make backlog                      Regenerate the backlog tracking table"
	@echo "make rebuild                      Rebuild and recreate all containers"
	@echo "make validate                     Validate Compose and Ansible syntax"
	@echo "make check                        Run application quality checks"
	@echo "make openapi                      Regenerate the OpenAPI contract"
	@echo "make migrate                      Apply database migrations"
	@echo "make cadastre-fixture             Verify DS-01 on local PostGIS and MinIO"
	@echo "make rnb-import DEPARTMENT=35     Archive/import one pinned DS-02 Brittany partition"
	@echo "make ban-import DEPARTMENT=35     Archive/import one pinned DS-05 Brittany partition"
	@echo "make ban-census ARCHIVE=path      Recount a pinned DS-05 archive, no database"
	@echo "make mvt-benchmark                Measure cold/hot p95 for local MVT routes"
	@echo "make e2e                          Run the local real-map Playwright flow"
	@echo "make inventory ENV=production     Render inventory from VPS_* variables"
	@echo "make bootstrap ENV=production     Bootstrap a clean VPS"
	@echo "make deploy ENV=production        Deploy idempotently"

config:
	COMPOSE_ENV_FILE=$(COMPOSE_ENV_FILE) ./scripts/check-compose-config

dev-secrets:
	./scripts/init-dev-secrets

dev: dev-secrets up

up: config
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml up -d --wait

rebuild: config
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml up -d --build --force-recreate --wait

down:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml down

logs:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml logs -f

migrate:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm migrate

database-permissions:
	COMPOSE_ENV_FILE=$(COMPOSE_ENV_FILE) ./scripts/check-database-permissions

mvt-benchmark:
	./scripts/benchmark-mvt "$${MVT_BASE_URL:-http://localhost:8080}"

e2e:
	pnpm --filter @immo/web test:e2e

cadastre-fixture:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/verify_cadastre_fixture.py

rnb-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_rnb_release.py 2026-09-05 --department $(DEPARTMENT)

ban-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_ban_release.py 2026-06-17 --department $(DEPARTMENT)

bdnb-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_bdnb_release.py 2026-02-a --department $(DEPARTMENT)

bdtopo-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_bdtopo_release.py 2026-06-15 --department $(DEPARTMENT)

ban-census:
	test -n "$(ARCHIVE)"
	uv run --package immo-pipelines python pipelines/scripts/ban_census.py 2026-06-17 \
		--department $(DEPARTMENT) --archive $(ARCHIVE)

python-check:
	uv run --package immo-backend ruff check backend pipelines
	uv run --package immo-backend ruff format --check backend pipelines
	uv run --package immo-backend pyright backend/src
	uv run --package immo-pipelines pyright pipelines/src
	uv run --package immo-backend pytest backend/tests
	uv run --package immo-pipelines pytest pipelines/tests

web-check:
	pnpm typecheck
	pnpm build

openapi:
	uv run --package immo-backend python backend/scripts/export_openapi.py
	pnpm --filter @immo/web generate:api

openapi-check:
	uv run --package immo-backend python backend/scripts/export_openapi.py --check

ops-build:
	docker build -f docker/ops/Dockerfile -t $(OPS_IMAGE) .

inventory:
	ENV=$(ENV) INVENTORY=$(INVENTORY) ./scripts/render-vps-inventory

ansible-syntax: ops-build
	$(OPS_RUN) ansible-playbook -i infra/ansible/inventories/$(ENV).example.yml \
		infra/ansible/playbooks/bootstrap.yml --syntax-check \
		-e immo_repo_root=/workspace -e immo_sops_file=/workspace/secrets/$(ENV).sops.yaml
	$(OPS_RUN) ansible-playbook -i infra/ansible/inventories/$(ENV).example.yml \
		infra/ansible/playbooks/deploy.yml --syntax-check \
		-e immo_repo_root=/workspace -e immo_sops_file=/workspace/secrets/$(ENV).sops.yaml

bootstrap: ops-build
	test -f $(INVENTORY)
	test -f secrets/$(ENV).sops.yaml
	test -f $(AGE_KEY_FILE)
	test -f $(SSH_PRIVATE_KEY_FILE)
	test -f $(SSH_KNOWN_HOSTS_FILE)
	docker run --rm \
		--user 0:0 \
		-v "$(CURDIR):/workspace" -w /workspace \
		-v "$(SSH_PRIVATE_KEY_FILE):/root/.ssh/id_ed25519:ro" \
		-v "$(SSH_KNOWN_HOSTS_FILE):/root/.ssh/known_hosts:ro" \
		-v "$(AGE_KEY_FILE):/root/.config/sops/age/keys.txt:ro" \
		-e SOPS_AGE_KEY_FILE=/root/.config/sops/age/keys.txt \
		-e ANSIBLE_CONFIG=/workspace/infra/ansible/ansible.cfg \
		$(OPS_IMAGE) ansible-playbook -i $(INVENTORY) infra/ansible/playbooks/bootstrap.yml \
		-e immo_repo_root=/workspace -e immo_sops_file=$(SOPS_FILE) \
		-e immo_allow_format_data_volumes=$(FORMAT_DATA_VOLUMES)

deploy: ops-build
	test -f $(INVENTORY)
	test -f secrets/$(ENV).sops.yaml
	test -f $(AGE_KEY_FILE)
	test -f $(SSH_PRIVATE_KEY_FILE)
	test -f $(SSH_KNOWN_HOSTS_FILE)
	docker run --rm \
		--user 0:0 \
		-v "$(CURDIR):/workspace" -w /workspace \
		-v "$(SSH_PRIVATE_KEY_FILE):/root/.ssh/id_ed25519:ro" \
		-v "$(SSH_KNOWN_HOSTS_FILE):/root/.ssh/known_hosts:ro" \
		-v "$(AGE_KEY_FILE):/root/.config/sops/age/keys.txt:ro" \
		-e SOPS_AGE_KEY_FILE=/root/.config/sops/age/keys.txt \
		-e ANSIBLE_CONFIG=/workspace/infra/ansible/ansible.cfg \
		$(OPS_IMAGE) ansible-playbook -i $(INVENTORY) infra/ansible/playbooks/deploy.yml \
		-e immo_repo_root=/workspace -e immo_sops_file=$(SOPS_FILE)

smoke:
	COMPOSE_ENV_FILE=$(COMPOSE_ENV_FILE) ./scripts/smoke-test "$${SITE_ADDRESS:-}"

validate: config ansible-syntax
	./scripts/check-secrets-encrypted

backlog:
	./scripts/backlog-status

backlog-check:
	./scripts/backlog-status --check

check: python-check web-check openapi-check config
