# Phase 3 Migration Scripts

Infrastructure settings migration scripts for transitioning from database-driven to environment-based configuration.

## 🚀 Quick Start

```bash
# 1. Analyze current state
python3 migrate_infra_settings.py --analyze-only

# 2. Generate migration plan (dry-run)
python3 migrate_infra_settings.py --output .env.migration

# 3. Compare with Railway
python3 railway_env_sync.py compare --env-file .env.migration

# 4. Validate deployment readiness
python3 deployment_validation.py --environment production
```

## 📜 Scripts Overview

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `migrate_infra_settings.py` | DB → Env migration | Settings classification, dry-run mode, backup |
| `railway_env_sync.py` | Railway sync | Compare, push, pull, validate Railway envs |
| `deployment_validation.py` | Pre-deployment checks | API tests, DB validation, smoke tests |

## 🎯 Common Workflows

### Development Setup
```bash
# Create development environment
python3 migrate_infra_settings.py --output .env.development
# Edit .env.development with development-specific values
python3 deployment_validation.py --environment development
```

### Production Deployment
```bash
# Generate production config
python3 migrate_infra_settings.py --execute --output .env.production

# Sync with Railway
python3 railway_env_sync.py push --env-file .env.production --execute

# Validate before deploy
python3 deployment_validation.py --environment production
```

### Environment Comparison
```bash
# Compare local vs Railway
python3 railway_env_sync.py compare --env-file .env.production

# Pull Railway config
python3 railway_env_sync.py pull --output .env.railway
```

## ⚙️ Configuration Types

### 🔒 ENV-ONLY (Security Critical)
- `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- `DATABASE_URL`, `REDIS_URL`
- `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`

### 🎛️ ADMIN-MANAGED (Configurable)
- LLM models and configuration
- Cache and performance settings
- Security timeouts and limits
- Knowledge base settings

## 🛡️ Safety Features

- **Dry-run mode**: Default for all destructive operations
- **Automatic backups**: Created before any migration
- **Validation checks**: Comprehensive pre-deployment testing
- **Rollback support**: Restore from backups if needed

## 📋 Prerequisites

- Python 3.8+
- Railway CLI (for Railway sync)
- Database access
- Required Python packages installed

## 📖 Full Documentation

See [`../docs/PHASE3_MIGRATION_GUIDE.md`](../docs/PHASE3_MIGRATION_GUIDE.md) for complete documentation.

---

**⚠️ Important**: Always test in development first and use dry-run mode before executing changes in production!