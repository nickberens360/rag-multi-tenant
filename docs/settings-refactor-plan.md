# Settings & Configuration Refactor Plan

## Overview
This document outlines the simplification of the settings/configuration system from a complex three-tier system (env vars → database → defaults) to a clear, predictable two-tier system with explicit ownership and purpose.

## Current Problems
1. **Three competing configuration sources** causing unpredictability
2. **Environment variable parity issues** (production: 165 vars, development: 81 vars)
3. **Persistent database settings** that survive deployments unexpectedly
4. **No clear source of truth** for configuration values
5. **Too many settings exposed** in admin UI (~50+ settings when only ~15 are needed)
6. **Deployment fragility** due to configuration mismatches

## Proposed Solution

### Core Principle
- **Environment Variables** = Infrastructure & deployment settings (never change at runtime)
- **Database (Admin UI)** = Operational settings that need runtime changes
- **Clear precedence**: Database settings only for specific allowed keys, everything else from env vars

### Naming & Precedence
- Naming
  - Database keys use `snake_case` (e.g., `primary_llm`, `max_results`).
  - Environment variables use `UPPER_SNAKE_CASE` (e.g., `PRIMARY_LLM`, `MAX_RESULTS`).
- Precedence
  - Admin-managed keys: DB overrides env at runtime.
  - Env-only keys: no DB fallback; runtime reads env only.
- Explicit mapping (examples)
  - `PRIMARY_LLM` ↔ `primary_llm`
  - `CLAUDE_MODEL` ↔ `claude_model`
  - `GEMINI_MODEL` ↔ `gemini_model`
  - `MAX_RESULTS` ↔ `max_results`
  - `CACHE_TTL` ↔ `cache_ttl`
  - `ENABLE_CACHING` ↔ `enable_caching`
  - `RATE_LIMIT` ↔ `rate_limit` (display string, e.g., "100/minute")
  - Rate-limit controls align to security schema: `enable_rate_limiting`, `rate_limit_requests`, `rate_limit_window`

## Settings Categories

### 1. Admin-Managed Settings (Database)
These settings are stored encrypted in the database and manageable through the admin UI.

#### API Keys (2–3 settings)
```yaml
ANTHROPIC_API_KEY         # Rotatable, encrypted storage
GOOGLE_API_KEY           # Rotatable, encrypted storage
OPENAI_API_KEY          # Optional/future (runtime wiring not active)
```
**Why in Admin:** Need rotation, emergency replacement, secure encrypted storage

#### Content & Search Configuration (3 settings)
```yaml
followup_questions       # Managed via dedicated admin UI (resource/table)
search_threshold        # Search relevance threshold (0-100)
retrieval_score_threshold # Minimum score for RAG retrieval (0.1-0.9)
```
**Why in Admin:** Content management, affects user experience directly

#### Model Selection (3 settings)
```yaml
primary_llm             # claude/gemini (openai planned)
claude_model           # claude-3-5-sonnet/claude-3-haiku
gemini_model          # gemini-1.5-flash/gemini-1.5-pro
```
**Why in Admin:** May need to switch models for cost/performance/availability

#### Performance Tuning (3 settings)
```yaml
max_results            # Number of RAG results to retrieve (5-50)
cache_ttl             # Cache duration in seconds (0-7200)
enable_caching        # Toggle caching on/off
```
**Why in Admin:** Runtime performance optimization

#### Rate Limiting (4 settings)
```yaml
enable_rate_limiting     # Boolean toggle
rate_limit_requests      # Requests per window (e.g., 100)
rate_limit_window        # Window seconds (e.g., 60)
rate_limit               # Display string for clients (e.g., "100/minute")
```
**Why in Admin:** May need emergency adjustments

**Total Admin Settings: ~15** (with OpenAI optional)

### 2. Environment-Only Settings (Never in Admin UI)

#### Core Infrastructure
```yaml
# Database & Storage
RAILWAY_VOLUME_MOUNT_PATH: /data
SQLITE_JOURNAL_MODE: WAL

# Embedding & Chunking (changing these requires full reindex)
EMBEDDING_MODEL: models/embedding-001
## Target architecture is env-only; currently DB may override in code.
## When changed, follow the reindex flow (see below).
# CHUNK_SIZE, CHUNK_OVERLAP are not wired globally; manage via knowledge pipeline configs

# Security & Encryption
API_KEY_ENCRYPTION_SECRET: [generated-secret]
IP_HASH_SALT: [generated-salt]
CORS_ORIGINS: https://nickberens.me,https://www.nickberens.me

# Railway Platform
RAILWAY_ENVIRONMENT: production
RAILWAY_PROJECT_ID: [auto-set]
RAILWAY_SERVICE_ID: [auto-set]
# ... all other RAILWAY_* variables
```

#### Database Configuration
```yaml
# All these are technical settings that never need runtime changes
ADMIN_DB_TIMEOUT_SECONDS: 15
ADMIN_DB_BUSY_TIMEOUT_MS: 15000
ADMIN_DB_CONNECT_RETRIES: 7
ADMIN_DB_CONNECT_RETRY_DELAY_MS: 300
ADMIN_DB_WRITE_RETRIES: 3
ADMIN_DB_WRITE_RETRY_DELAY_MS: 50
ADMIN_DB_AUDIT_TIMEOUT_SECONDS: 0.05
```

#### System Configuration
```yaml
# Logging
LOG_LEVEL: INFO

# Timeouts & Retries
REQUEST_TIMEOUT: 60

# Feature Flags (set at deployment)
ENABLE_SMART_MODEL_SELECTION: true
ENABLE_FOLLOWUP_PREGENERATION: false
CONTENT_CLASSIFICATION_MODE: hybrid   # allowed: fast, startup_llm, hybrid

# Background knowledge sync (optional)
KNOWLEDGE_SYNC_INTERVAL_SECONDS: 0
KNOWLEDGE_SYNC_AUTO_RECONCILE: false

# Admin bootstrap (production must set password)
ADMIN_DEFAULT_USERNAME: admin
ADMIN_DEFAULT_PASSWORD: [generated-secret]

# Security
EXCLUDED_IPS: 1.2.3.4,5.6.7.8
DEBUG: false
```

## Implementation Steps

### Phase 1: Immediate Fixes (Day 1)

#### 1.1 Environment Variable Parity
```bash
# Export production variables (JSON is easiest to parse)
railway variables --environment production --json > prod.vars.json

# Create a sync script: scripts/sync-environments.sh
#!/usr/bin/env bash
set -euo pipefail

SRC_ENV=${1:-production}
DST_ENV=${2:-development}

echo "Exporting $SRC_ENV variables..."
railway variables --environment "$SRC_ENV" --json > /tmp/src.vars.json

echo "Syncing to $DST_ENV..."
# Requires: jq
jq -r 'to_entries[] | "\(.key)=\(.value)"' /tmp/src.vars.json | while IFS='=' read -r key value; do
  # Optionally skip secrets or allowlist keys here
  railway variables set --environment "$DST_ENV" "$key"="$value"
done
echo "Environment variables synced from $SRC_ENV to $DST_ENV"

# Note: If your Railway CLI version doesn't support this flow,
# use the Dashboard or adjust to your CLI version.
```

#### 1.2 Update App Initializer
```python
# backend/core/app_initializer_v2.py

async def initialize_app():
    """Ensure env vars always override database for infrastructure settings"""

    # Define which settings can be managed in admin
    ADMIN_MANAGED_SETTINGS = {
        'anthropic_api_key', 'google_api_key', 'openai_api_key',
        'followup_questions', 'search_threshold', 'retrieval_score_threshold',
        'primary_llm', 'claude_model', 'gemini_model',
        'max_results', 'cache_ttl', 'enable_caching',
        'enable_rate_limiting', 'rate_limit_requests', 'rate_limit_window', 'rate_limit'
    }

    # For ALL other settings, use env vars only (apply mapping from env UPPER to DB snake_case when needed)
    # Example mapping shown in "Naming & Precedence" section
    # Pseudocode: if env_key not mapped to an admin-managed db key -> treat as env-only
```

### Phase 2: Add Safety Rails (Week 1)

#### 2.1 Create Settings Manifest
```python
# backend/core/settings_manifest.py

ADMIN_MANAGED_SETTINGS = {
    # Only these 15 settings appear in admin UI
    'anthropic_api_key': {'type': 'encrypted', 'category': 'api_keys'},
    'google_api_key': {'type': 'encrypted', 'category': 'api_keys'},
    'primary_llm': {'type': 'choice', 'choices': ['claude', 'gemini'], 'category': 'models'},
    'max_results': {'type': 'int', 'min': 5, 'max': 50, 'category': 'performance'},
    # ... etc for all 15
}

ENV_ONLY_SETTINGS = {
    # These 40+ settings NEVER appear in admin UI
    'CHUNK_SIZE': {'type': 'int', 'required': True, 'default': 1000},
    'EMBEDDING_MODEL': {'type': 'str', 'required': True},
    'RAILWAY_VOLUME_MOUNT_PATH': {'type': 'str', 'required': True},
    # ... etc
}

def validate_configuration():
    """Fail fast if critical settings are missing"""
    errors = []

    # Check env-only settings
    for key, config in ENV_ONLY_SETTINGS.items():
        if config.get('required') and not os.getenv(key):
            errors.append(f"Missing required env var: {key}")

    if errors:
        raise ConfigurationError("\n".join(errors))
```

#### 2.2 Create Railway Configuration File
```toml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "./Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"

[environments.production.variables]
ENVIRONMENT = "production"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
MAX_RESULTS = "15"
CHUNK_SIZE = "1000"
CHUNK_OVERLAP = "200"
# ... all infrastructure settings

[environments.development.variables]
ENVIRONMENT = "development"
# Inherits from production, override as needed
```

Note: Values like `CLAUDE_MODEL` and `MAX_RESULTS` here should be treated as seeds/defaults. At runtime, admin-managed DB values take precedence for those keys.

### Phase 3: Simplify Admin UI (Week 2)

#### 3.1 Update Admin Frontend Routes
```javascript
// admin/frontend/src/router/index.js
// Remove or hide routes for infrastructure settings
{
  // In the SPA, settings live under '/settings' (served under '/admin/settings' in production)
  path: '/settings',
  children: [
    { path: 'api-keys', component: APIKeysView },      // Keep
    { path: 'content', component: ContentSettingsView }, // Keep
    { path: 'performance', component: PerformanceView }, // Keep
    { path: 'models', component: ModelSelectionView },   // Keep
    // Remove: database, infrastructure, advanced, etc.
  ]
}
```

#### 3.2 Add Diagnostics Endpoint
```python
# backend/routes/admin.py

@router.get("/api/admin/diagnostics")
async def get_diagnostics():
    """Show configuration state for debugging"""

    # Check all required env vars
    env_status = {}
    for key in ENV_ONLY_SETTINGS:
        env_status[key] = "✓" if os.getenv(key) else "✗ MISSING"

    # Check admin-managed settings
    db_settings = await settings_manager.get_all()
    admin_status = {}
    for key in ADMIN_MANAGED_SETTINGS:
        admin_status[key] = "✓" if key in db_settings else "✗ MISSING"

    return {
        "environment": os.getenv("ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT") or "unknown",
        "env_variables": {
            "total": len(env_status),
            "missing": len([k for k, v in env_status.items() if "MISSING" in v]),
            "status": env_status
        },
        "admin_settings": {
            "total": len(admin_status),
            "configured": len([k for k, v in admin_status.items() if "✓" in v]),
            "status": admin_status
        },
        "health": "ERROR" if any("MISSING" in v for v in env_status.values()) else "OK"
    }
```

Security note: The endpoint should never return raw values for sensitive keys (API keys, salts, passwords). It should report presence/missing status only.

### Phase 4: Migration & Cleanup (Week 3)

#### 4.1 Migration Script
```python
# backend/scripts/migrate_settings_to_env.py

"""One-time migration to move infrastructure settings to env vars"""

async def migrate_settings():
    # Get all current database settings
    all_settings = await settings_manager.get_all()

    # Generate env var file for infrastructure settings using explicit mapping
    NAME_MAP = {
        'primary_llm': 'PRIMARY_LLM',
        'claude_model': 'CLAUDE_MODEL',
        'gemini_model': 'GEMINI_MODEL',
        'max_results': 'MAX_RESULTS',
        'cache_ttl': 'CACHE_TTL',
        'enable_caching': 'ENABLE_CACHING',
        # Add additional mappings as needed
    }

    with open('.env.infrastructure', 'w') as f:
        for key, value in all_settings.items():
            if key not in ADMIN_MANAGED_SETTINGS:
                env_key = NAME_MAP.get(key, key.upper())
                f.write(f"{env_key}={value}\n")
                # Remove from database
                await settings_manager.delete(key)

    print("Infrastructure settings exported to .env.infrastructure")
    print("Add these to Railway environment variables")
    print(f"Removed {len(all_settings) - len(ADMIN_MANAGED_SETTINGS)} settings from database")
```

#### 4.2 Deployment Validation
```bash
# scripts/validate-deployment.sh
#!/bin/bash

echo "Validating deployment configuration..."

# Validate required keys instead of counts
REQUIRED_FILE=${2:-scripts/required-env.txt}
echo "Validating required env keys using $REQUIRED_FILE..."
missing=0
while IFS= read -r key || [ -n "$key" ]; do
  [ -z "$key" ] && continue
  val=$(railway variables --environment "$1" --json | jq -r --arg k "$key" '.[$k] // empty')
  if [ -z "$val" ]; then
    echo "✗ Missing: $key"; missing=$((missing+1))
  else
    echo "✓ Present: $key"
  fi
done < "$REQUIRED_FILE"
if [ $missing -gt 0 ]; then
  echo "❌ Missing $missing required environment variables"; exit 1
fi

# Test critical endpoints
curl -f https://$RAILWAY_STATIC_URL/health || exit 1
curl -f https://$RAILWAY_STATIC_URL/api/admin/diagnostics || exit 1

echo "✓ Deployment validation passed"
```

## Benefits of This Approach

1. **Predictability**: Clear rules about where settings come from
2. **Security**: API keys encrypted in database, infrastructure settings protected
3. **Simplicity**: Admin UI only shows ~15 relevant settings instead of 50+
4. **Reliability**: Environment parity enforced, deployment validation
5. **Maintainability**: Less code, clearer separation of concerns
6. **Safety**: Can't accidentally break infrastructure from admin UI

## Rollback Plan

If issues arise:

1. **Quick rollback**: Railway keeps previous deployments, one-click rollback
2. **Settings backup**: Export current settings before migration
3. **Gradual migration**: Can migrate settings in batches
4. **Feature flag**: Add `USE_NEW_CONFIG_SYSTEM=true` to test before full migration

## Success Metrics

- [ ] Development and production have same number of env vars
- [ ] Admin UI shows only 15 settings (not 50+)
- [ ] Deployments succeed without manual intervention
- [ ] No configuration-related errors in logs
- [ ] `/api/admin/diagnostics` shows all green checkmarks
- [ ] Query responses work correctly in both environments

## ⚠️ IMPLEMENTATION REALITY CHECK

**CRITICAL UPDATE**: After comprehensive analysis of the current system, this refactor is significantly more complex than initially estimated.

### Current System Scale Discovery
- **70+ API endpoints** for settings management across 15 categories
- **Advanced frontend features**: Monaco JSON editors, version history, real-time validation
- **Complex backend**: 480-line settings manager, 1,340-line schemas, sophisticated caching
- **Deep integration**: Settings tied to authentication, audit trails, performance optimization

### Implementation Challenges Identified

#### 1. **Massive Scope Mismatch**
- **Current**: 50+ individual settings across 15 categories
- **Proposed**: 15 admin-managed settings
- **Reality**: The plan vastly underestimates existing complexity

#### 2. **Critical Dependencies**
- **Frontend**: 7 sophisticated Vue components with advanced UX features
- **Backend**: Complex caching, audit logging, real-time updates
- **Integration**: Settings deeply coupled with authentication and security systems

#### 3. **Advanced Features at Risk**
- Monaco-based JSON editors for taxonomy management (1,877 lines)
- Version history and diff functionality
- Auto-generation capabilities
- Real-time validation and preview systems

## REVISED IMPLEMENTATION PLAN

### Timeline: 16 weeks (4 months) - Incremental Migration Approach

#### Phase 1: Impact Assessment (Week 1-2)
- [ ] Audit all current settings usage across frontend and backend
- [ ] Map dependencies between settings and core application features
- [ ] Identify settings that can be safely moved to env-only
- [ ] Document breaking changes for each component

#### Phase 2: Incremental Migration (Week 3-8)
- [ ] Start with least-used settings that have minimal frontend integration
- [ ] Migrate one category at a time while maintaining backward compatibility
- [ ] Update frontend components incrementally to handle new architecture
- [ ] Maintain dual support during transition period

#### Phase 3: Infrastructure Settings Migration (Week 9-12)
- [ ] Create comprehensive environment variable sync tooling
- [ ] Implement validation for environment-only settings
- [ ] Update deployment scripts and Railway configuration
- [ ] Remove database storage for infrastructure settings

#### Phase 4: Frontend Simplification (Week 13-16)
- [ ] Remove or hide admin UI for environment-only settings
- [ ] Simplify remaining admin components
- [ ] Add diagnostics and health check endpoints
- [ ] Update documentation and user guides

### Reindex Flow (when EMBEDDING_MODEL or chunking changes)
- Pause ingestion/background sync
- Export current vector store snapshot (backup)
- Rebuild embeddings for all indexed sources
- Validate retrieval metrics (sample queries)
- Deploy new config and switch traffic
- Remove old vectors when stable

## Critical Success Factors

- **Zero Downtime**: Migration must not disrupt production operations
- **Feature Preservation**: All advanced features (Monaco editors, version history) must be maintained
- **Backward Compatibility**: Gradual transition with fallback mechanisms
- **Comprehensive Testing**: Each phase requires thorough validation

## Risk Mitigation

1. **Incremental Approach**: Migrate one settings category at a time
2. **Feature Flags**: Use toggles to control new vs old system behavior
3. **Comprehensive Backups**: Full database and configuration snapshots
4. **Rollback Plan**: Quick revert capability for each migration phase

## Updated Timeline

- **Original Estimate**: 4 weeks
- **Realistic Estimate**: 16 weeks (4 months)
- **Complexity Factor**: 4x more complex than initially planned

## Notes

- **DO NOT** attempt wholesale replacement - incremental migration only
- Keep backups of all current settings before each migration phase
- Test extensively in development environment for each phase
- Document any custom settings that don't fit the pattern
- Consider adding Terraform/IaC for Railway configuration in future
- This is now classified as a **major architecture refactor**, not a simple cleanup

## Appendix

### Central Config Schema (design sketch)
- Define Pydantic models for:
  - Env-only settings (validated at startup; fail fast on missing required)
  - Admin-managed settings (validated on write; dynamic at runtime)
- Merge function:
  - Read env → overlay DB for allowed admin keys (using explicit name mapping)
  - Secrets are always env-sourced; DB holds encrypted API keys for runtime clients

### Admin UI Routing Note
- The admin SPA is served under `/admin`. Client routes in the SPA use `/settings/...`, which resolve to `/admin/settings/...` in production.
