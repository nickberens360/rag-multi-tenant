# Configuration Architecture

This backend uses a database‑first configuration model with code defaults.

- Secrets and deployment are read from environment variables.
- All non‑secret application settings live in the admin database and are editable via the Admin UI.
- Code defaults live in `backend/core/config_v2.py` as safe fallbacks.

## Sources of Truth

- Secrets (env): `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, optional `GITHUB_TOKEN`, `IP_HASH_SALT`, `ADMIN_DEFAULT_*`
- Deployment (env): `ENVIRONMENT`, `PUBLIC_API_URL`, `PUBLIC_GITHUB_*`, `PUBLIC_GA_TRACKING_ID`
- Response settings (DB): caching, cache TTL, response LLM and model names
- System configuration (DB): rate limit string, processing model names, cache sizing
- Security (DB): enable/disable rate limiting, anonymize IPs, excluded IPs
- RAG configuration (DB): MMR toggles, score thresholds, etc.
- Search & retrieval (DB): similarity threshold, max results
- Knowledge (DB): index directories, heterogeneity fallback

## How to Access Settings

Use one of these patterns:

- Quick access (code defaults + DB override):
  - `from backend.core.config_v2 import AppConfig`
  - Examples: `AppConfig.get_rate_limit()`, `AppConfig.get_primary_llm()`, `AppConfig.get_rag_index_dirs()`

- Full settings objects (preferred for non‑trivial logic):
  - `from backend.core.settings_manager import get_settings_manager`
  - Examples:
    - `get_settings_manager().get_response_settings()`
    - `get_settings_manager().get_system_config_settings()`
    - `get_settings_manager().get_security_settings()`
    - `get_settings_manager().get_rag_config_settings()`
    - `get_settings_manager().get_search_retrieval_settings()`
    - `get_settings_manager().get_knowledge_settings()`

## Do Not

- Do not import `backend.core.config` (legacy). Always use `backend.core.config_v2`.
- Do not add new environment variables for non‑secret settings. Prefer DB settings with code defaults.

## Minimal .env

```bash
# Required secrets
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Deployment
ENVIRONMENT=development
PUBLIC_API_URL=http://localhost:8000
```

Note: Container env‑files (Podman/Docker) do not strip inline comments. Keep values comment‑free or rely on the app’s ENVIRONMENT sanitation (which strips trailing `#...`).

## Migration Notes

- Legacy `backend/core/config.py` has been removed.
- Replace any remaining imports with `backend.core.config_v2`.
- Caching and rate limiting:
  - Enable/disable caching via ResponseSettings (DB)
  - Rate limit string via SystemConfigurationSettings (DB)
  - Enable/disable rate limiting via SecuritySettings (DB)

