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
	openapi openapi-check migrate database-permissions cadastre-fixture rnb-import ban-import ban-census mvt-benchmark e2e backlog backlog-check \
	invariants doc-budget ticket-check dod

help:
	@echo "make dev-secrets                  Generate disposable local secrets"
	@echo "make dev                          Start local infrastructure"
	@echo "make backlog                      Regenerate the backlog tracking table"
	@echo "make rebuild                      Rebuild and recreate all containers"
	@echo "make validate                     Validate Compose and Ansible syntax"
	@echo "make check                        Run application quality checks"
	@echo "make invariants [BASE=<ref>]      Check CLAUDE.md invariants on added diff lines"
	@echo "make doc-budget                   Check reference documents stay within their line budget"
	@echo "make ticket-check [BASE=<ref>]    Check every commit touching code carries a ticket id"
	@echo "make dod ID=<ticket>              Check what is mechanical in a ticket Definition of Done"
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

# Garde-fou : `rebuild` recree PostgreSQL et coupe toute connexion en cours. Un import ou un
# calcul en arriere-plan y perd sa transaction courante — c'est arrive deux fois, sur l'import GPU
# puis sur le calcul URB, a chaque fois parce qu'un autre ticket demandait une reconstruction.
# Voir ARCHITECTURE.md §10.6.
rebuild: check-no-batch config
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml up -d --build --force-recreate --wait

check-no-batch:
	@if pgrep -f 'import_.*_release\.py|compute_.*_features\.py|build_physical_buildings\.py' >/dev/null; then \
		echo "Un lot est en cours : rebuild couperait sa connexion PostgreSQL."; \
		pgrep -fl 'import_.*_release\.py|compute_.*_features\.py|build_physical_buildings\.py' | head -3; \
		echo "L'arrêter, ou forcer avec FORCE_REBUILD=1."; \
		[ -n "$(FORCE_REBUILD)" ] || exit 1; \
	fi

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

gpu-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_gpu_release.py 2026-09-14 \
		--department $(DEPARTMENT) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY),--only $(ONLY),)

dvf-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_dvf_release.py 2026-09-13 \
		--department $(DEPARTMENT) $(if $(YEAR),--year $(YEAR),)

dvf-archive-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_dvf_release.py 2019-04-archive \
		--department $(DEPARTMENT) $(if $(YEAR),--year $(YEAR),)

dpe-pin:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/contracts:/workspace/contracts \
		dagster-code python pipelines/scripts/pin_dpe_release.py \
		--release $(RELEASE) --department $(DEPARTMENT)

dpe-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_dpe_release.py 2026-09-14-extract \
		--department $(DEPARTMENT) $(if $(SNAPSHOT),--snapshot $(SNAPSHOT),)

dpe-report:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/dpe_matching_report.py --department $(DEPARTMENT)

georisques-pin:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/contracts:/workspace/contracts \
		dagster-code python pipelines/scripts/pin_georisques_release.py \
		--release $(RELEASE) --department $(DEPARTMENT) $(if $(FAMILY),--family $(FAMILY),)

georisques-pin-clay:
	test -n "$(ARCHIVE)"
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/contracts:/workspace/contracts -v $(dir $(abspath $(ARCHIVE))):/archives:ro \
		dagster-code python pipelines/scripts/pin_clay_release.py \
		--release $(RELEASE) --department $(DEPARTMENT) \
		--archive /archives/$(notdir $(ARCHIVE))

georisques-pin-sup:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/contracts:/workspace/contracts \
		dagster-code python pipelines/scripts/pin_sup_release.py \
		--release $(RELEASE) --department $(DEPARTMENT)

georisques-import:
	test -n "$(RELEASE)"
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_georisques_release.py $(RELEASE) \
		--department $(DEPARTMENT)

georisques-report:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/georisques_coverage_report.py \
		--department $(DEPARTMENT)

market-data-quality:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/market_data_quality_report.py \
		--department $(DEPARTMENT)

urban-features:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/compute_urban_features.py \
		--department $(DEPARTMENT) $(if $(COMMUNE),--commune $(COMMUNE),)

exploratory-candidates:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/exploratory_candidates.py \
		--commune $(COMMUNE) $(if $(SIZE),--size $(SIZE),) \
		$(if $(LOT_WIDTH),--lot-width $(LOT_WIDTH),)

field-test-kit:
	uv run --package immo-pipelines python pipelines/scripts/field_test_kit.py --commune $(COMMUNE)

biens-en-vente:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/market_listing_candidates.py \
		--commune $(COMMUNE) $(if $(SIZE),--size $(SIZE),) \
		$(if $(FRESH_MONTHS),--fresh-months $(FRESH_MONTHS),)

market-barometer:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/market_barometer.py \
		--department $(or $(DEPARTMENT),35) \
		$(if $(GENERATED_ON),--generated-on $(GENERATED_ON),)

morphology-features:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/compute_morphology_features.py \
		--department $(DEPARTMENT) $(if $(COMMUNE),--commune $(COMMUNE),)

physical-buildings:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/build_physical_buildings.py \
		--source $(SOURCE) --department $(DEPARTMENT)

ban-import:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/import_ban_release.py 2026-06-17 --department $(DEPARTMENT)

matching-refresh:
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		dagster-code python pipelines/scripts/refresh_spatial_matching.py --department $(DEPARTMENT)

matching-report: matching-refresh
	docker compose --env-file $(COMPOSE_ENV_FILE) \
		-f compose.yaml -f compose.dev.yaml -f compose.observability.yaml run --rm \
		-v $(PWD)/docs/data:/workspace/docs/data \
		dagster-code python pipelines/scripts/spatial_matching_report.py --department $(DEPARTMENT)

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
	uv run --package immo-backend ruff check backend pipelines scripts/tests
	uv run --package immo-backend ruff format --check backend pipelines scripts/tests
	uv run --package immo-backend pyright backend/src
	uv run --package immo-pipelines pyright pipelines/src
	uv run --package immo-backend pytest backend/tests
	uv run --package immo-pipelines pytest pipelines/tests
	uv run --package immo-pipelines pytest scripts/tests

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

# Les interdits de CLAUDE.md, verifies sur les lignes ajoutees. Sans BASE, le travail en
# cours ; avec, la difference entre la reference et HEAD.
invariants:
	./scripts/check-diff-invariants $(if $(BASE),--base $(BASE),)

# Un commit sans identifiant n'est pas signale par `make dod`, il lui est invisible.
# Sans BASE, les commits absents de origin/main. La suite scripts/tests couvre en plus
# l'historique depuis l'ecriture de la regle, donc `make check` porte deja le controle.
ticket-check:
	./scripts/check-commit-ticket $(if $(BASE),--base $(BASE),)

# Un document de reference qui deborde ne se relit plus. Le raisonnement va dans
# docs/decisions/, jamais charge en entier.
doc-budget:
	./scripts/check-doc-budget

# `check` et `backlog-check` d'abord : le script en depend pour les points 4 et 6.
dod: check backlog-check
	test -n "$(ID)"
	./scripts/check-ticket-dod $(ID) --check-ran

check: python-check web-check openapi-check config invariants doc-budget
