# Operations Guide (Agent-Executable)

## Deployment Commands

### Railway Deployment
```bash
# Set environment variables
railway variables set DATABASE_URL="${{POSTGRES_URL}}"
railway variables set REDIS_URL="${{REDIS_URL}}"
railway variables set DEFAULT_TENANT_ID="00000000-0000-0000-0000-000000000001"
railway variables set ENABLE_MULTI_TENANT="true"
railway variables set ENABLE_RLS_ENFORCEMENT="true"

# Deploy
railway up

# Run migrations
railway run alembic upgrade head

# Seed default tenant
railway run psql $DATABASE_URL -c "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Organization', NOW(), NOW()) ON CONFLICT DO NOTHING;"

# Verify deployment
railway logs
```

### Docker Deployment
```bash
# Build images
docker build -t app-backend:latest -f backend/Dockerfile .
docker build -t app-frontend:latest -f Dockerfile .

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed data
docker-compose exec postgres psql -U app_user -d app_db -c "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Organization', NOW(), NOW()) ON CONFLICT DO NOTHING;"
```

## Monitoring Queries

### File: backend/monitoring/tenant_health.sql
```sql
-- Check tenant data distribution
SELECT
    t.slug,
    t.name,
    COUNT(DISTINCT tm.user_id) as member_count,
    COUNT(DISTINCT ql.id) as query_count,
    COUNT(DISTINCT as2.id) as settings_count
FROM tenants t
LEFT JOIN tenant_memberships tm ON t.id = tm.tenant_id
LEFT JOIN query_logs ql ON t.id = ql.tenant_id
LEFT JOIN admin_settings as2 ON t.id = as2.tenant_id
WHERE t.deleted_at IS NULL
GROUP BY t.id, t.slug, t.name
ORDER BY member_count DESC;

-- Check RLS violations (should return 0)
SELECT COUNT(*) as violations
FROM (
    SELECT tenant_id FROM admin_settings
    UNION ALL
    SELECT tenant_id FROM query_logs
    UNION ALL
    SELECT tenant_id FROM api_keys
) data
WHERE tenant_id NOT IN (SELECT id FROM tenants WHERE deleted_at IS NULL);

-- Active tenants last 24h
SELECT
    t.slug,
    COUNT(ql.id) as queries_24h,
    MAX(ql.timestamp) as last_activity
FROM tenants t
JOIN query_logs ql ON t.id = ql.tenant_id
WHERE ql.timestamp > NOW() - INTERVAL '24 hours'
  AND t.deleted_at IS NULL
GROUP BY t.id, t.slug
ORDER BY queries_24h DESC;

-- Tenant storage usage
SELECT
    t.slug,
    pg_size_pretty(
        SUM(pg_total_relation_size(tablename::regclass))
    ) as total_size
FROM tenants t
CROSS JOIN (
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename IN ('admin_settings', 'query_logs', 'api_keys', 'followup_questions')
) tables
WHERE t.deleted_at IS NULL
GROUP BY t.slug
ORDER BY SUM(pg_total_relation_size(tablename::regclass)) DESC;
```

## Alert Configurations

### File: monitoring/alerts.yaml
```yaml
alerts:
  - name: rls_violation_detected
    query: |
      SELECT COUNT(*) FROM admin_settings
      WHERE tenant_id NOT IN (SELECT id FROM tenants WHERE deleted_at IS NULL)
    threshold: 0
    operator: ">"
    severity: critical
    message: "RLS violation detected - orphaned tenant data found"

  - name: tenant_query_spike
    query: |
      SELECT COUNT(*) FROM query_logs
      WHERE timestamp > NOW() - INTERVAL '5 minutes'
      GROUP BY tenant_id
      HAVING COUNT(*) > 1000
    threshold: 0
    operator: ">"
    severity: warning
    message: "Tenant query spike detected (>1000 queries in 5 min)"

  - name: failed_tenant_resolution
    query: |
      SELECT COUNT(*) FROM security_events
      WHERE event_type = 'tenant_resolution_failed'
      AND created_at > NOW() - INTERVAL '5 minutes'
    threshold: 10
    operator: ">"
    severity: warning
    message: "High rate of tenant resolution failures"

  - name: cross_tenant_access_attempt
    query: |
      SELECT COUNT(*) FROM security_events
      WHERE event_type = 'cross_tenant_access_attempt'
      AND created_at > NOW() - INTERVAL '1 hour'
    threshold: 5
    operator: ">"
    severity: critical
    message: "Multiple cross-tenant access attempts detected"
```

## Logging Configuration

### File: backend/core/logging_config.py
```python
import logging
import json
from pythonjsonlogger import jsonlogger

def setup_structured_logging():
    """Configure structured JSON logging."""
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={'timestamp': '@timestamp', 'level': 'severity'}
    )
    logHandler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logHandler)

    return logger

def log_tenant_operation(logger, operation, tenant_id, **kwargs):
    """Log tenant-specific operations."""
    logger.info(
        "tenant_operation",
        extra={
            "operation": operation,
            "tenant_id": tenant_id,
            **kwargs
        }
    )

def log_rls_check(logger, table, tenant_id, success, **kwargs):
    """Log RLS check results."""
    logger.info(
        "rls_check",
        extra={
            "table": table,
            "tenant_id": tenant_id,
            "success": success,
            **kwargs
        }
    )
```

## Backup and Recovery

### File: scripts/tenant_backup.sh
```bash
#!/bin/bash
# Backup specific tenant data

TENANT_ID=$1
BACKUP_DIR="/backups/tenants/${TENANT_ID}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p ${BACKUP_DIR}

# Export tenant data
psql $DATABASE_URL << EOF > ${BACKUP_DIR}/tenant_${TIMESTAMP}.sql
\set tenant_id '${TENANT_ID}'
BEGIN;
SET LOCAL app.tenant_id = :'tenant_id';

\echo 'Exporting admin_settings...'
\copy (SELECT * FROM admin_settings) TO '${BACKUP_DIR}/admin_settings_${TIMESTAMP}.csv' CSV HEADER;

\echo 'Exporting query_logs...'
\copy (SELECT * FROM query_logs) TO '${BACKUP_DIR}/query_logs_${TIMESTAMP}.csv' CSV HEADER;

\echo 'Exporting api_keys...'
\copy (SELECT * FROM api_keys) TO '${BACKUP_DIR}/api_keys_${TIMESTAMP}.csv' CSV HEADER;

COMMIT;
EOF

# Compress backup
tar -czf ${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz ${BACKUP_DIR}/*_${TIMESTAMP}.*
rm ${BACKUP_DIR}/*_${TIMESTAMP}.*

echo "Backup completed: ${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"
```

### File: scripts/tenant_restore.sh
```bash
#!/bin/bash
# Restore specific tenant data

TENANT_ID=$1
BACKUP_FILE=$2

RESTORE_DIR="/tmp/restore_${TENANT_ID}"
mkdir -p ${RESTORE_DIR}

# Extract backup
tar -xzf ${BACKUP_FILE} -C ${RESTORE_DIR}

# Restore data
psql $DATABASE_URL << EOF
\set tenant_id '${TENANT_ID}'
BEGIN;
SET LOCAL app.tenant_id = :'tenant_id';

-- Clear existing data
DELETE FROM admin_settings;
DELETE FROM query_logs;
DELETE FROM api_keys;

-- Import data
\copy admin_settings FROM '${RESTORE_DIR}/admin_settings_*.csv' CSV HEADER;
\copy query_logs FROM '${RESTORE_DIR}/query_logs_*.csv' CSV HEADER;
\copy api_keys FROM '${RESTORE_DIR}/api_keys_*.csv' CSV HEADER;

COMMIT;
EOF

rm -rf ${RESTORE_DIR}
echo "Restore completed for tenant ${TENANT_ID}"
```

## Performance Tuning

### File: backend/db/indexes.sql
```sql
-- Tenant-specific indexes for hot paths
CREATE INDEX CONCURRENTLY idx_admin_settings_tenant_key
ON admin_settings(tenant_id, setting_key);

CREATE INDEX CONCURRENTLY idx_query_logs_tenant_timestamp
ON query_logs(tenant_id, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_api_keys_tenant_active
ON api_keys(tenant_id, is_active)
WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_followup_questions_tenant_category
ON followup_questions(tenant_id, category_id);

CREATE INDEX CONCURRENTLY idx_tenant_memberships_user
ON tenant_memberships(user_id);

-- Partial indexes for common queries
CREATE INDEX CONCURRENTLY idx_tenants_active
ON tenants(slug)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY idx_invitations_pending
ON invitations(token)
WHERE status = 'pending' AND expires_at > NOW();
```

### File: backend/db/vacuum.sql
```sql
-- Regular maintenance queries
VACUUM ANALYZE tenants;
VACUUM ANALYZE tenant_memberships;
VACUUM ANALYZE admin_settings;
VACUUM ANALYZE query_logs;

-- Check table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup, 0), 3) AS dead_ratio
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;
```

## Tenant Lifecycle Management

### File: backend/services/tenant_lifecycle.py
```python
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

def create_tenant(session: Session, slug: str, name: str, owner_user_id: int):
    """Create new tenant with owner."""
    tenant_id = str(uuid.uuid4())

    # Create tenant
    session.execute(
        text("""
            INSERT INTO tenants (id, slug, name, created_at, updated_at)
            VALUES (:id, :slug, :name, NOW(), NOW())
        """),
        {"id": tenant_id, "slug": slug, "name": name}
    )

    # Add owner
    session.execute(
        text("""
            INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
            VALUES (:tenant_id, :user_id, 'owner', NOW())
        """),
        {"tenant_id": tenant_id, "user_id": owner_user_id}
    )

    # Initialize default settings
    session.execute(
        text("""
            INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at)
            VALUES
                (:tenant_id, 'enable_followup_questions', 'true', NOW()),
                (:tenant_id, 'max_query_length', '1000', NOW()),
                (:tenant_id, 'response_style', 'detailed', NOW())
        """),
        {"tenant_id": tenant_id}
    )

    session.commit()
    return tenant_id

def soft_delete_tenant(session: Session, tenant_id: str):
    """Soft delete tenant."""
    session.execute(
        text("""
            UPDATE tenants
            SET deleted_at = NOW()
            WHERE id = :tenant_id
        """),
        {"tenant_id": tenant_id}
    )
    session.commit()

def purge_deleted_tenant(session: Session, tenant_id: str):
    """Permanently remove soft-deleted tenant data."""
    # Verify tenant is soft-deleted
    result = session.execute(
        text("SELECT deleted_at FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": tenant_id}
    )
    deleted_at = result.scalar()

    if not deleted_at:
        raise ValueError("Tenant is not soft-deleted")

    # Delete in dependency order
    tables = [
        "query_logs",
        "api_keys",
        "followup_questions",
        "followup_categories",
        "admin_settings",
        "invitations",
        "tenant_memberships",
        "tenants"
    ]

    for table in tables:
        if table == "tenants":
            session.execute(
                text(f"DELETE FROM {table} WHERE id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
        else:
            session.execute(
                text(f"DELETE FROM {table} WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            )

    session.commit()
```

## Commands Summary
```bash
# Deploy to Railway
railway up && railway run alembic upgrade head

# Monitor tenant health
psql $DATABASE_URL -f backend/monitoring/tenant_health.sql

# Backup tenant
./scripts/tenant_backup.sh "tenant-uuid"

# Create performance indexes
psql $DATABASE_URL -f backend/db/indexes.sql

# Check for RLS violations
psql $DATABASE_URL -c "SELECT COUNT(*) FROM admin_settings WHERE tenant_id NOT IN (SELECT id FROM tenants);"
```