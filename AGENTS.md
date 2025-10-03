# Repository Guidelines

## Project Structure & Module Organization
- Frontend: `src/` (Astro + Vue) with `pages/`, `components/`, `layouts/`, `styles/`, `utils/`.
- Static assets: `public/` (served as-is) and `src/assets/` (bundled).
- Backend: `backend/` (FastAPI) with `core/`, `routes/`, `models/`; entrypoint `backend/main.py`.
- Tests: `tests/` for Python (pytest); UI tests via Vitest (`vitest.config.mjs`).
- Config: `astro.config.mjs`, `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`.

## Build, Test, and Development Commands
- `npm run dev`: Start Astro dev server.
- `npm run build` / `npm run preview`: Build and preview frontend.
- `npm test` / `npm run test:run`: Run Vitest in watch/CI modes.
- `npm run backend:build` then `npm run backend:dev`: Build container and run FastAPI on `:8000` (stop with `npm run backend:stop`).
- `pytest -q`: Run Python tests (HTML coverage in `htmlcov/`).
- `make lint` (or `make lint-check`, `make type-check`): Linting and type checks.

## Coding Style & Naming Conventions
- Python: Black (120 cols), isort (black profile), flake8; 4-space indents; `snake_case` for functions/modules, `PascalCase` for classes.
- Frontend: Follow Astro/Vue idioms. Components as `PascalCase.vue`; composables as `useX.ts` in `src/composables/`.
- Run `pre-commit install` to enable hooks (YAML, flake8, mypy, etc.).

## Testing Guidelines
- Backend: pytest with markers (`unit`, `integration`, `slow`). Place tests in `tests/` as `test_*.py`.
- Coverage: configured in `pyproject.toml` for `backend/core`; HTML report at `htmlcov/index.html`. Keep or improve coverage.
- Frontend: Write component tests with Vitest + `@vue/test-utils`.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subject; optional scope (e.g., "fix terminal z-index issue"). Group related changes.
- PRs: clear description, linked issue/goal, testing notes, and screenshots/GIFs for UI changes. Include backend/CI test results.

## Security & Configuration Tips
- Env: copy `.env.example` to `.env`. Frontend reads `PUBLIC_*` vars; backend loads `.env` via `dotenv`.
- Secrets: never commit real keys/tokens; use local `.env` and CI secrets.

## Agentic Implementation Resources
- Multi-tenant plan and migration guides live under `docs/multi_tenant/`.
- Start with the Agent Playbook:
  - Guide: `docs/multi_tenant/agent_playbook.md`
  - Machine-readable index: `docs/multi_tenant/agent_playbook.yaml` (JSON: `docs/multi_tenant/agent_playbook.json`)
  - These outline step IDs, dependencies, files to touch, commands to run, and validations to perform.
