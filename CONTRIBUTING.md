Contributing Guide

Thank you for contributing! This guide summarizes how to set up your environment, run checks, and make effective pull requests for this project.

Local setup
- Python: 3.11 recommended. Install dev deps: `pip install -r requirements-dev.txt`
- Node: use the version compatible with Astro/Vite. Install deps: `npm ci`
- Pre-commit hooks: `pre-commit install` (runs formatting on commit)

Common tasks
- Lint/format Python: `make lint` (or `make lint-fast` while iterating)
- Type-check: `make type-check`
- Run backend tests: `pytest -q`
- Frontend dev: `npm run dev`
- Frontend tests (Vitest): `npm test` or `npm run test:run`

Coverage
- For ad hoc coverage reports on backend core: `pytest -q --cov=backend/core --cov-report=term-missing`
- HTML coverage is written to `htmlcov/` if enabled.

Backend conventions
- FastAPI app lives at `backend/main.py`. Routers in `backend/routes/`. Core services in `backend/core/`.
- Prefer adding shared logic to core services; keep routers thin.
- Use `logging` (module-level logger) instead of `print()` in runtime paths.
- Keep settings validation in `backend/core/settings_schemas.py` and access via `get_settings_manager()`.

Frontend conventions
- Components under `src/components/` (PascalCase.vue). Composables under `src/composables/`.
- Prefer TypeScript for new composables/stores (`useX.ts`).
- Keep API boundaries typed and covered by small Vitest tests when possible.

Security & configuration
- Use `.env.example` as a baseline; never commit secrets.
- Backend loads `.env` via `dotenv`; frontend reads `PUBLIC_*` env vars.

Pull requests
- Use the provided PR template. Include a concise summary and testing notes.
- Run `make lint` and `pytest -q` before opening the PR.
- For routing changes, update deprecation headers and docs accordingly.

Triaging & milestones
- Small cleanup tasks go into the “Quick Wins” milestone.
- Larger efforts (e.g., rate limiting consolidation, admin DB modularization) should be tracked as epics with task lists.

