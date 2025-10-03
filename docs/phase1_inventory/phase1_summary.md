# Phase 1: Settings Inventory Report

## Executive Summary

This document provides a complete inventory of all configuration settings in the Nick Berens Portfolio application as of Phase 1 of the settings migration project. The application uses a hybrid configuration system with three layers:

1. **Environment Variables** - For secrets and deployment-specific values
2. **Database Settings** - Admin-manageable settings via the admin UI
3. **Code Defaults** - Hardcoded fallback values

## Configuration Architecture

### Current State
The application implements a "database-first" configuration approach (config_v2.py) where:
- Settings check the database for overrides first
- Falls back to environment variables
- Finally uses hardcoded defaults

### Key Files
- `backend/core/config_v2.py` - Central configuration with database-first approach
- `backend/core/settings_manager.py` - Settings management with caching
- `backend/core/settings_schemas.py` - Dataclass definitions for all settings categories
- `backend/core/admin_database.py` - Database operations for settings storage

## Settings Classification

### Classification Criteria

**ENV-ONLY (Must remain environment variables):**
- Secrets and API keys
- Deployment-specific configuration
- Infrastructure settings
- Security-sensitive values that shouldn't be in database

**ADMIN-MANAGED (Can be managed via admin UI):**
- Application behavior settings
- Feature flags
- Performance tuning
- UI/UX preferences
- Non-sensitive configuration

## Settings Categories

### 1. Environment Variables (82 total)
- **27 ENV-ONLY settings** (secrets, deployment config, infrastructure)
- **55 ADMIN-MANAGED settings** (can be overridden via admin UI)

Key ENV-ONLY settings:
- API Keys: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GITHUB_TOKEN`
- Admin credentials: `ADMIN_DEFAULT_PASSWORD`, `ADMIN_DEFAULT_USERNAME`
- Deployment: `PUBLIC_API_URL`, `RAILWAY_*` settings
- Security: `IP_HASH_SALT`, `API_KEY_ENCRYPTION_SECRET`

### 2. Database/Admin Settings (12 setting categories)

| Category | Fields | Purpose |
|----------|--------|---------|
| followup_settings | 9 fields | Follow-up question configuration |
| response_settings | 17 fields | Response generation and caching |
| routing_settings | 6 fields | Query routing configuration |
| feature_flags | 12 fields | Feature toggles |
| system_config_settings | 10 fields | System configuration |
| security_settings | 11 fields | Security settings |
| rag_config_settings | 12 fields | RAG configuration |
| core_settings | 8 fields | Core app metadata |
| ux_settings | 8 fields | UI/UX preferences |
| search_retrieval_settings | 9 fields | Search and retrieval |
| knowledge_settings | 6 fields | Knowledge base indexing |
| system_settings | (future) | Unified settings storage |

### 3. Code Defaults (66 constants)
Located primarily in:
- `config_v2.py` - 60 default constants
- `performance_config.py` - 15 performance defaults
- `llm_chain.py` - Prompt templates

## Settings Access Patterns

### Dynamic Settings (DB-override capable)
```python
# Example from config_v2.py
@classmethod
def get_primary_llm(cls) -> str:
    try:
        from .settings_manager import get_settings_manager
        settings = get_settings_manager().get_system_config_settings()
        if settings and settings.primary_llm:
            return settings.primary_llm
    except Exception:
        pass
    return cls.PRIMARY_LLM_DEFAULT
```

### Static Settings (Env-only)
```python
# Direct environment access
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")
```

## Migration Considerations

### Settings to Keep as ENV-ONLY
1. **Security Secrets** - API keys, passwords, encryption keys
2. **Infrastructure** - Railway settings, deployment URLs
3. **Development Flags** - TESTING, SKIP_INDEXING, FORCE_REBUILD_DATA
4. **Core Environment** - ENVIRONMENT, IS_PRODUCTION, DEBUG_MODE

### Settings Ready for Admin Management
1. **LLM Configuration** - Models, providers, timeouts
2. **Search/Retrieval** - Thresholds, limits, algorithms
3. **Caching** - TTL, size limits, enable flags
4. **Feature Flags** - All toggle-based features
5. **Performance** - Optimization settings, timeouts
6. **UI/UX** - Themes, styles, display preferences

## Database Schema

### admin_settings Table
```sql
CREATE TABLE admin_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);
```

Settings are stored as JSON-serialized dataclass instances, allowing complex nested structures.

## Caching Strategy

The `SettingsManager` implements a TTL-based cache:
- Default TTL: 300 seconds (5 minutes)
- Thread-safe with locking
- Automatic invalidation on updates
- Cache status monitoring available

## Backward Compatibility

The system maintains backward compatibility through:
1. Module-level constant initialization from DB settings
2. Static attribute assignments for legacy code
3. Fallback chains (DB → Env → Default)
4. Legacy field support (e.g., `response_cache_ttl_seconds`)

## Statistics

- **Total Environment Variables**: 82
- **ENV-ONLY Settings**: 27 (33%)
- **Admin-Manageable Settings**: 55 (67%)
- **Database Setting Categories**: 12
- **Total Database Fields**: 108
- **Code Default Constants**: 66

## Files Inventory

### Data Files
- `docs/phase1_inventory/env_settings.tsv` - Complete environment variable inventory
- `docs/phase1_inventory/db_admin_settings.tsv` - Database settings schema
- `docs/phase1_inventory/code_defaults.tsv` - Hardcoded default values
- `docs/phase1_inventory/phase1_summary.md` - This summary document

### Key Source Files Analyzed
- 26 Python files with environment variable usage
- 3 main configuration files (config_v2.py, settings_manager.py, settings_schemas.py)
- 12 dataclass definitions for settings categories

## Next Steps (Phase 2)

Based on this inventory, Phase 2 should focus on:
1. Creating the new `backend/core/config.py` with proper separation
2. Updating all imports to use the new config module
3. Ensuring backward compatibility during the transition
4. Testing the migration thoroughly

## Conclusion

The application has a well-structured configuration system that already supports database-driven settings with appropriate fallbacks. The classification shows that 67% of current environment variables can be managed through the admin UI, while 33% must remain as environment variables for security and deployment reasons.

The existing infrastructure (SettingsManager, admin database, dataclasses) provides a solid foundation for the Phase 2 migration to create a cleaner separation between env-only and admin-managed settings.