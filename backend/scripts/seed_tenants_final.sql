-- Final corrected seed script with proper role values
-- Valid tenant_membership roles: owner, admin, member

-- Seed the database
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

    -- Get admin_user_id if it already existed
    IF admin_user_id IS NULL THEN
        SELECT id INTO admin_user_id FROM admin_users WHERE username = 'admin';
    END IF;

    -- Create a test user
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

    -- Get test_user_id if it already existed
    IF test_user_id IS NULL THEN
        SELECT id INTO test_user_id FROM admin_users WHERE username = 'testuser';
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

    -- Create tenant memberships for admin user (using only valid roles: owner, admin, member)
    INSERT INTO tenant_memberships (user_id, tenant_id, role, created_at)
    VALUES
        (admin_user_id, '00000000-0000-0000-0000-000000000001', 'owner', NOW()),
        (admin_user_id, '11111111-1111-1111-1111-111111111111', 'admin', NOW()),
        (admin_user_id, '22222222-2222-2222-2222-222222222222', 'admin', NOW()),
        (admin_user_id, '33333333-3333-3333-3333-333333333333', 'admin', NOW())
    ON CONFLICT (user_id, tenant_id) DO UPDATE
    SET role = EXCLUDED.role;

    -- Create tenant memberships for test user (limited access using valid roles)
    INSERT INTO tenant_memberships (user_id, tenant_id, role, created_at)
    VALUES
        (test_user_id, '00000000-0000-0000-0000-000000000001', 'member', NOW()),
        (test_user_id, '11111111-1111-1111-1111-111111111111', 'member', NOW())
    ON CONFLICT (user_id, tenant_id) DO UPDATE
    SET role = EXCLUDED.role;

    -- Create sample invitations
    INSERT INTO invitations (tenant_id, email, role, inviter_user_id, token, expires_at, status, created_at)
    VALUES
        ('11111111-1111-1111-1111-111111111111', 'newuser@acme.com', 'member',
         admin_user_id, encode(gen_random_bytes(32), 'hex'), NOW() + INTERVAL '7 days', 'pending', NOW()),
        ('22222222-2222-2222-2222-222222222222', 'developer@startup.com', 'admin',
         admin_user_id, encode(gen_random_bytes(32), 'hex'), NOW() + INTERVAL '7 days', 'pending', NOW())
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Successfully seeded data. Admin user ID: %, Test user ID: %', admin_user_id, test_user_id;
END $$;

-- Display summary of seeded data
SELECT '=== SEEDED TENANTS ===' as info;
SELECT id, slug, name, jsonb_pretty(settings) as settings
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
    i.status,
    i.expires_at::date as expires_on
FROM invitations i
JOIN tenants t ON i.tenant_id = t.id
WHERE i.status = 'pending'
ORDER BY i.created_at;