.PHONY: lint lint-check lint-fix lint-fast type-check test-unit test-integration test-tenant test-rls test-coverage

lint-fix:
	black .
	isort .
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .

lint-check:
	black --check .
	isort --check-only .
	flake8 .

type-check:
	mypy backend/core --ignore-missing-imports

lint: lint-fix lint-check type-check

# Faster local lint (no mypy)
lint-fast:
	black .
	isort .
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .
	black --check .
	isort --check-only .
	flake8 .

# Test targets for faster dev cycles
test-unit:
	pytest -m "not integration and not slow" -q

test-integration:
	pytest -m "integration" -q

test-tenant:
	pytest -m "tenant" -q

test-rls:
	pytest -m "rls" -q

test-coverage:
	pytest --cov=backend --cov-report=term --cov-report=html

# Run indexing on a directory and print metrics JSON
index-report:
	python -m backend.scripts.indexing_report --dir "$(DIR)" $(if $(FORCE),--force,) $(if $(HETERO),--hetero,) $(if $(PERSIST_DIR),--persist-dir "$(PERSIST_DIR)",)

# Fast test targets with safe defaults for multi-tenant setup
.PHONY: test-tenant-fast test-integration-fast test-rls-pg

# Only tenant resolution tests; skips heavy app init and disables path-prefixed routers
test-tenant-fast:
	SKIP_APP_INIT=true ENABLE_PATH_PREFIX_ROUTERS=false ENABLE_MULTI_TENANT=true \
	pytest -q tests/integration/test_tenant_resolution.py

# All non-RLS integration tests with same fast env
test-integration-fast:
	SKIP_APP_INIT=true ENABLE_PATH_PREFIX_ROUTERS=false ENABLE_MULTI_TENANT=true \
	pytest -q -m "integration and not rls"

# RLS tests against a Postgres TEST_DATABASE_URL (skips if not set)
test-rls-pg:
	SKIP_APP_INIT=true ENABLE_PATH_PREFIX_ROUTERS=false ENABLE_MULTI_TENANT=true \
	pytest -q tests/integration/test_tenancy_rls.py

# Database utilities
.PHONY: db-upgrade db-seed

db-upgrade:
	@if [ -z "$(DATABASE_URL)" ]; then echo "DATABASE_URL not set"; exit 1; fi
	alembic -c backend/db/alembic.ini upgrade head

db-seed:
	@if [ -z "$(DATABASE_URL)" ]; then echo "DATABASE_URL not set"; exit 1; fi
	python3 backend/scripts/seed_db.py

# One-shot local setup: create venv, install deps, migrate DB, optional seed
.PHONY: setup-db setup-db-seed
setup-db:
	bash scripts/setup_db.sh

setup-db-seed:
	bash scripts/setup_db.sh --seed
