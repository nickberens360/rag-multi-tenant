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