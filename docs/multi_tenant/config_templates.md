# Configuration Templates (Agent-Executable)

## File: .env.example
```bash
# Database
DATABASE_URL=postgresql://app_user:secure_password@localhost:5432/app_db
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001
DEFAULT_TENANT_SLUG=default
SQL_ECHO=false

# Redis (for caching tenant lookups)
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32
SESSION_SECRET_KEY=generate-with-secrets-token-hex-32
SESSION_COOKIE_DOMAIN=.yourapp.com
SESSION_COOKIE_SECURE=true

# API Keys (keep existing)
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# App
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
TRUSTED_HOSTS=["localhost","*.yourapp.com"]

# Feature Flags
ENABLE_MULTI_TENANT=true
ENABLE_RLS_ENFORCEMENT=true
TENANT_RESOLUTION_MODE=subdomain_then_path
```

## File: backend/db/alembic.ini
```ini
[alembic]
script_location = backend/db
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://app_user:password@localhost:5432/app_db

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 120

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

## File: backend/db/env.py
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

config = context.config

# Override with environment variable if present
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## File: docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app_db
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_user -d app_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

## File: backend/db/init.sql
```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create app user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';
    END IF;
END$$;

-- Grant permissions
GRANT CREATE ON SCHEMA public TO app_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;

-- Ensure app user cannot bypass RLS
ALTER ROLE app_user NOBYPASSRLS;

-- Create default tenant (run after alembic migrations)
-- INSERT INTO tenants (id, slug, name, created_at, updated_at)
-- VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Organization', NOW(), NOW())
-- ON CONFLICT (id) DO NOTHING;
```

## File: railway.toml
```toml
[build]
builder = "NIXPACKS"
buildCommand = "npm run build && npm run backend:build"

[deploy]
startCommand = "npm run backend:prod"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[services]]
name = "postgres"
image = "postgres:16"

[[services.volumes]]
mount = "/var/lib/postgresql/data"
name = "postgres_data"

[[services]]
name = "redis"
image = "redis:7-alpine"

[[services.volumes]]
mount = "/data"
name = "redis_data"

[env]
DATABASE_URL = "${{POSTGRES_URL}}"
REDIS_URL = "${{REDIS_URL}}"
```

## File: backend/core/config.py (additions)
```python
# Multi-tenant configuration
DEFAULT_TENANT_ID = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
DEFAULT_TENANT_SLUG = os.getenv("DEFAULT_TENANT_SLUG", "default")
ENABLE_MULTI_TENANT = os.getenv("ENABLE_MULTI_TENANT", "true").lower() == "true"
ENABLE_RLS_ENFORCEMENT = os.getenv("ENABLE_RLS_ENFORCEMENT", "true").lower() == "true"
TENANT_RESOLUTION_MODE = os.getenv("TENANT_RESOLUTION_MODE", "subdomain_then_path")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))

# Redis for caching
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TENANT_CACHE_TTL = int(os.getenv("REDIS_TENANT_CACHE_TTL", "300"))  # 5 minutes

# Session configuration
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", None)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "lax"
```

## Commands to execute

```bash
# Initialize database
cp docs/multi_tenant/config_templates.md/.env.example .env
docker-compose up -d postgres redis
sleep 5
alembic upgrade head

# Seed default tenant
psql $DATABASE_URL -c "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Organization', NOW(), NOW()) ON CONFLICT DO NOTHING;"

# Verify RLS
psql $DATABASE_URL -c "SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000001'; SELECT COUNT(*) FROM tenants;"
```