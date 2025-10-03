-- Complete seed script for multi-tenant database
-- Creates necessary user tables and populates with test data

-- Create admin_users table if it doesn't exist
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fix tenant table schema if settings column is missing
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}';

-- Fix invitations table schema if role column is missing
ALTER TABLE invitations
ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'member';

-- Now run the seeding
DO $$
DECLARE
    admin_user_id INTEGER;
    test_user_id INTEGER;
BEGIN
    -- Create or get admin user
    INSERT INTO admin_users (username, password_hash, email, role)
    VALUES (
        'admin',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.Q.MrkmYrKz2W', -- 'admin123456789'
        'admin@localhost',
        'admin'
    )
    ON CONFLICT (username) DO UPDATE
    SET email = EXCLUDED.email
    RETURNING id INTO admin_user_id;

    -- Create a test user as well
    INSERT INTO admin_users (username, password_hash, email, role)
    VALUES (
        'testuser',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.Q.MrkmYrKz2W', -- 'admin123456789'
        'testuser@localhost',
        'viewer'
    )
    ON CONFLICT (username) DO UPDATE
    SET email = EXCLUDED.email
    RETURNING id INTO test_user_id;

    -- Insert tenants with proper settings
    INSERT INTO tenants (id, slug, name, settings, created_at, updated_at)
    VALUES
        ('00000000-0000-0000-0000-000000000001', 'default', 'Default Organization',
         '{"theme": "light", "features": {"api_enabled": true}}', NOW(), NOW()),
        ('11111111-1111-1111-1111-111111111111', 'acme-corp', 'ACME Corporation',
         '{"theme": "dark", "features": {"api_enabled": true, "advanced_analytics": true}}', NOW(), NOW()),
        ('22222222-2222-2222-2222-222222222222', 'tech-startup', 'Tech Startup Inc',
         '{"theme": "light", "features": {"api_enabled": true, "beta_features": true}}', NOW(), NOW()),
        ('33333333-3333-3333-3333-333333333333', 'consulting-pro', 'Consulting Pro LLC',
         '{"theme": "light", "features": {"api_enabled": true, "white_label": true}}', NOW(), NOW())
    ON CONFLICT (id) DO UPDATE
    SET
        name = EXCLUDED.name,
        settings = EXCLUDED.settings,
        updated_at = NOW();

    -- Create tenant memberships for admin user (all organizations)
    INSERT INTO tenant_memberships (user_id, tenant_id, role, created_at)
    VALUES
        (admin_user_id, '00000000-0000-0000-0000-000000000001', 'owner', NOW()),
        (admin_user_id, '11111111-1111-1111-1111-111111111111', 'admin', NOW()),
        (admin_user_id, '22222222-2222-2222-2222-222222222222', 'admin', NOW()),
        (admin_user_id, '33333333-3333-3333-3333-333333333333', 'admin', NOW())
    ON CONFLICT (user_id, tenant_id) DO UPDATE
    SET
        role = EXCLUDED.role,
        updated_at = NOW();

    -- Create tenant memberships for test user (limited access)
    INSERT INTO tenant_memberships (user_id, tenant_id, role, created_at)
    VALUES
        (test_user_id, '00000000-0000-0000-0000-000000000001', 'member', NOW()),
        (test_user_id, '11111111-1111-1111-1111-111111111111', 'viewer', NOW())
    ON CONFLICT (user_id, tenant_id) DO UPDATE
    SET
        role = EXCLUDED.role,
        updated_at = NOW();

    -- Create sample invitations
    INSERT INTO invitations (id, tenant_id, email, role, invited_by, token, expires_at, created_at)
    VALUES
        (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'newuser@acme.com', 'member',
         admin_user_id, encode(gen_random_bytes(32), 'hex'), NOW() + INTERVAL '7 days', NOW()),
        (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'developer@startup.com', 'admin',
         admin_user_id, encode(gen_random_bytes(32), 'hex'), NOW() + INTERVAL '7 days', NOW())
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Successfully seeded data. Admin user ID: %, Test user ID: %', admin_user_id, test_user_id;
END $$;

-- Display summary of seeded data
SELECT '=== SEEDED TENANTS ===' as info;
SELECT id, slug, name,
       CASE
         WHEN settings IS NOT NULL THEN jsonb_pretty(settings)
         ELSE 'No settings'
       END as settings
FROM tenants
ORDER BY created_at;

SELECT '' as separator;
SELECT '=== USER ACCOUNTS ===' as info;
SELECT id, username, email, role
FROM admin_users
ORDER BY id;

SELECT '' as separator;
SELECT '=== TENANT MEMBERSHIPS ===' as info;
SELECT
    au.username,
    t.name as tenant_name,
    t.slug as tenant_slug,
    tm.role as member_role
FROM tenant_memberships tm
JOIN tenants t ON tm.tenant_id = t.id
JOIN admin_users au ON tm.user_id = au.id
ORDER BY au.username, t.name;

SELECT '' as separator;
SELECT '=== ACTIVE INVITATIONS ===' as info;
SELECT
    t.name as tenant_name,
    i.email,
    i.role as invited_role,
    i.expires_at::date as expires_on
FROM invitations i
JOIN tenants t ON i.tenant_id = t.id
WHERE i.accepted_at IS NULL
ORDER BY i.created_at;