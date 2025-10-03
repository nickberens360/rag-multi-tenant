# Phase 3: Infrastructure Settings Migration Guide

This guide covers Phase 3 of the settings migration process, which migrates infrastructure-related settings from database storage to environment variables for better deployment practices and Railway environment management.

## 🎯 Overview

Phase 3 implements the infrastructure layer of settings migration:

- **ENV-ONLY Settings**: Security-critical settings that should only exist as environment variables
- **ADMIN-MANAGED Settings**: Settings that can exist in both DB and env (env takes precedence)
- **Railway Environment Sync**: Tools to synchronize with Railway deployment environments
- **Deployment Validation**: Comprehensive pre-deployment checks

## 📋 Prerequisites

1. Phase 1 (settings consolidation) must be completed
2. Python 3.8+ with required dependencies installed
3. Railway CLI installed and authenticated (for Railway sync)
4. Access to the application database

## 🛠️ Migration Scripts

### 1. Infrastructure Settings Migration (`migrate_infra_settings.py`)

Migrates settings from database to environment variables based on classification.

#### Usage

```bash
# Analyze current state (read-only)
python3 scripts/migrate_infra_settings.py --analyze-only

# Dry run (shows what would be done)
python3 scripts/migrate_infra_settings.py

# Execute migration
python3 scripts/migrate_infra_settings.py --execute --output .env.production
```

#### Options

- `--execute`: Execute migration (default: dry-run)
- `--output FILE`: Output environment file path (default: `.env.migration`)
- `--analyze-only`: Only analyze current state without proposing changes

#### What it does

1. **Analyzes** current state of DB and environment variables
2. **Classifies** settings as ENV-ONLY vs ADMIN-MANAGED
3. **Generates** environment file with appropriate variables
4. **Creates** backup of current settings
5. **Validates** migration results

#### Output

Creates an environment file with:
- Migrated settings from database
- Placeholders for security-critical ENV-ONLY settings
- Warnings for conflicting values
- Documentation for each setting

### 2. Railway Environment Sync (`railway_env_sync.py`)

Synchronizes environment variables between local development and Railway deployment environments.

#### Usage

```bash
# Compare local vs Railway environments
python3 scripts/railway_env_sync.py compare --env-file .env

# Push local variables to Railway (dry-run)
python3 scripts/railway_env_sync.py push --env-file .env

# Push to Railway (execute)
python3 scripts/railway_env_sync.py push --env-file .env --execute

# Pull Railway variables to local file
python3 scripts/railway_env_sync.py pull --output .env.railway --execute

# Validate Railway deployment
python3 scripts/railway_env_sync.py validate
```

#### Options

- `--env-file FILE`: Local environment file (default: `.env`)
- `--environment NAME`: Railway environment name
- `--execute`: Execute changes (default: dry-run)
- `--output FILE`: Output file for pull action

#### What it does

1. **Compares** local and Railway environment variables
2. **Identifies** differences and conflicts
3. **Pushes** local variables to Railway (excluding sensitive ones)
4. **Pulls** Railway variables to local files
5. **Validates** Railway deployment configuration

### 3. Deployment Validation (`deployment_validation.py`)

Comprehensive validation of deployment configuration before going live.

#### Usage

```bash
# Full validation for production environment
python3 scripts/deployment_validation.py --environment production

# Run specific checks
python3 scripts/deployment_validation.py --check env --check api

# Save validation report
python3 scripts/deployment_validation.py --output validation_report.json
```

#### Available Checks

- `env`: Environment variables validation
- `api`: API connectivity tests
- `db`: Database access validation
- `precedence`: Settings precedence validation
- `railway`: Railway deployment health
- `smoke`: Basic application smoke tests

#### What it validates

1. **Environment Variables**: Critical vars present and valid
2. **API Connectivity**: Anthropic/Google API access
3. **Database Access**: Database connectivity and operations
4. **Settings Precedence**: Environment variables override DB
5. **Railway Health**: Deployment status and logs
6. **Smoke Tests**: Basic application functionality

## 📊 Settings Classification

### ENV-ONLY Settings (Security Critical)

These settings should **only** exist as environment variables:

```bash
# API Keys - Never store in database
ANTHROPIC_API_KEY=sk-ant-api03-...
GOOGLE_API_KEY=AI...
OPENAI_API_KEY=sk-...

# Database & Infrastructure
DATABASE_URL=sqlite:///path/to/db.sqlite
REDIS_URL=redis://localhost:6379

# Application Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Railway-specific
RAILWAY_ENVIRONMENT=production
RAILWAY_PROJECT_ID=...
RAILWAY_SERVICE_ID=...
```

### ADMIN-MANAGED Settings (Configurable)

These settings can exist in both DB and environment (env takes precedence):

```bash
# System Configuration
DEFAULT_LLM_MODEL=claude
RESPONSE_LLM=claude
PROCESSING_LLM=claude_haiku
CLAUDE_MODEL=claude-3-5-sonnet-20241022
GEMINI_MODEL=gemini-1.5-flash

# Performance
CACHE_TTL_SECONDS=3600
MAX_CACHE_SIZE=1000
RATE_LIMIT=100/minute

# Security
SESSION_TIMEOUT_MINUTES=480
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=300
ENABLE_RATE_LIMITING=true

# Knowledge Base
INDEX_ON_STARTUP=true
BACKGROUND_SYNC_INTERVAL=0
AUTO_REINDEX_DELTAS=false
INDEX_DIRECTORIES=backend/knowledge,public
```

## 🚀 Migration Process

### Step 1: Analysis

```bash
# Analyze current configuration
python3 scripts/migrate_infra_settings.py --analyze-only
```

Review the output to understand:
- Missing critical environment variables
- Settings currently in database vs environment
- Potential conflicts

### Step 2: Migration Planning

```bash
# Generate migration plan (dry-run)
python3 scripts/migrate_infra_settings.py --output .env.migration
```

Review the generated `.env.migration` file and:
- Verify migrated values are correct
- Set placeholders for ENV-ONLY settings
- Resolve any warnings

### Step 3: Environment Setup

Create appropriate environment files for each deployment:

```bash
# Development environment
cp .env.migration .env.development

# Staging environment
cp .env.migration .env.staging

# Production environment
cp .env.migration .env.production
```

Set security-critical variables manually:

```bash
# Edit each environment file
vim .env.production

# Set real API keys and secrets
ANTHROPIC_API_KEY=sk-ant-api03-real-key
GOOGLE_API_KEY=real-google-key
# ... other environment-specific values
```

### Step 4: Railway Sync

```bash
# Compare with Railway environment
python3 scripts/railway_env_sync.py compare --env-file .env.production

# Push to Railway (dry-run first)
python3 scripts/railway_env_sync.py push --env-file .env.production

# Execute push
python3 scripts/railway_env_sync.py push --env-file .env.production --execute
```

### Step 5: Validation

```bash
# Validate deployment configuration
python3 scripts/deployment_validation.py --environment production

# Run specific validations
python3 scripts/deployment_validation.py --check env --check api
```

Fix any validation errors before deployment.

### Step 6: Deploy and Monitor

1. Deploy to Railway with new environment configuration
2. Monitor deployment logs for any issues
3. Run post-deployment validation
4. Verify application functionality

## ⚠️ Important Notes

### Security Considerations

1. **Never commit real API keys** to version control
2. **Use Railway secrets** for production API keys
3. **Rotate keys** if they may have been exposed
4. **Audit environment access** regularly

### Runtime Precedence

The application follows this precedence order:
1. **Environment variables** (highest priority)
2. **Database settings** (admin-configurable)
3. **Default values** (fallback)

This allows:
- Deployment-specific overrides via environment
- Runtime configuration via admin interface
- Safe defaults for development

### Rollback Procedure

If migration causes issues:

1. **Restore from backup**:
   ```bash
   # Backup is automatically created during migration
   # File name: settings_backup_YYYYMMDD_HHMMSS.json
   ```

2. **Revert Railway variables**:
   ```bash
   python3 scripts/railway_env_sync.py pull --output .env.backup
   # Compare and restore needed variables
   ```

3. **Validate restored state**:
   ```bash
   python3 scripts/deployment_validation.py --environment production
   ```

## 🔧 Troubleshooting

### Common Issues

1. **Database Lock Errors**
   - Wait for other processes to finish
   - Check for hung database connections
   - Restart the application if needed

2. **Railway CLI Issues**
   - Ensure Railway CLI is installed and updated
   - Check authentication: `railway whoami`
   - Link to correct project: `railway link`

3. **API Key Validation Failures**
   - Verify API keys are valid and have sufficient quota
   - Check network connectivity
   - Review API rate limits

4. **Settings Precedence Not Working**
   - Clear application cache
   - Restart the application
   - Verify environment variables are loaded

### Getting Help

1. Check the validation report for specific errors
2. Review application logs for runtime issues
3. Use `--analyze-only` mode to understand current state
4. Run individual validation checks to isolate problems

## 📈 Benefits

After Phase 3 migration:

1. **Better Security**: API keys and secrets in environment variables
2. **Easier Deployment**: Configuration via Railway environment
3. **Development Flexibility**: Local overrides via `.env` files
4. **Production Safety**: Validation before deployment
5. **Operational Clarity**: Clear separation of concerns

## 🔄 Next Steps

1. Monitor application performance after migration
2. Update deployment documentation
3. Train team on new configuration management
4. Plan for Phase 4 if additional optimizations are needed

---

For questions or issues, refer to the individual script help messages or create an issue in the project repository.