-- Seed script for multi-tenant database
-- This script creates sample tenants and user memberships for testing

-- First, let's check if we already have admin users
DO $$
DECLARE
    admin_user_id INTEGER;
BEGIN
    -- Get the admin user ID (assuming username 'admin' or 'nickberens360')
    SELECT id INTO admin_user_id FROM admin_users
    WHERE username IN ('admin', 'nickberens360')
    LIMIT 1;

    IF admin_user_id IS NULL THEN
        -- Create a default admin user if none exists
        INSERT INTO admin_users (username, password_hash, email, role, created_at)
        VALUES (
            'admin',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.Q.MrkmYrKz2W', -- 'admin123456789'
            'admin@localhost',
            'admin',
            NOW()
        ) RETURNING id INTO admin_user_id;
    END IF;

    -- Insert tenants
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

    -- Create tenant memberships for the admin user
    INSERT INTO tenant_memberships (user_id, tenant_id, role, created_at)
    VALUES
        (admin_user_id, '00000000-0000-0000-0000-000000000001', 'owner', NOW()),
        (admin_user_id, '11111111-1111-1111-1111-111111111111', 'admin', NOW()),
        (admin_user_id, '22222222-2222-2222-2222-222222222222', 'member', NOW()),
        (admin_user_id, '33333333-3333-3333-3333-333333333333', 'viewer', NOW())
    ON CONFLICT (user_id, tenant_id) DO UPDATE
    SET
        role = EXCLUDED.role,
        updated_at = NOW();

    -- Create some sample invitations
    INSERT INTO invitations (id, tenant_id, email, role, invited_by, token, expires_at, created_at)
    VALUES
        (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'newuser@acme.com', 'member',
         admin_user_id, encode(gen_random_bytes(32), 'hex'), NOW() + INTERVAL '7 days', NOW()),
        (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'developer@startup.com', 'admin',
         admin_user_id, encode(gen_random_bytes(32), 'hex'), NOW() + INTERVAL '7 days', NOW())
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Successfully seeded tenants and memberships for user ID: %', admin_user_id;
END $$;

-- Display the seeded data
SELECT 'Tenants:' as info;
SELECT id, slug, name, jsonb_pretty(settings) as settings, created_at
FROM tenants
ORDER BY created_at;

SELECT '' as separator;
SELECT 'User Memberships:' as info;
SELECT
    tm.user_id,
    au.username,
    t.name as tenant_name,
    tm.role,
    tm.created_at
FROM tenant_memberships tm
JOIN tenants t ON tm.tenant_id = t.id
JOIN admin_users au ON tm.user_id = au.id
ORDER BY tm.user_id, tm.created_at;

SELECT '' as separator;
SELECT 'Pending Invitations:' as info;
SELECT
    t.name as tenant_name,
    i.email,
    i.role,
    i.expires_at
FROM invitations i
JOIN tenants t ON i.tenant_id = t.id
WHERE i.accepted_at IS NULL
ORDER BY i.created_at;