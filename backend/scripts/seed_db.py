import os
import sys

import bcrypt
from sqlalchemy import create_engine, text


def get_env(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def main() -> int:
    database_url = get_env("DATABASE_URL")
    default_tid = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    default_slug = os.getenv("DEFAULT_TENANT_SLUG", "default")

    admin_user = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_DEFAULT_PASSWORD", "change_me_immediately")
    admin_email = os.getenv("ADMIN_DEFAULT_EMAIL", "admin@localhost")
    admin_display = os.getenv("ADMIN_DEFAULT_DISPLAY_NAME", "Administrator")
    force_update = os.getenv("ADMIN_FORCE_UPDATE", "false").lower() in {"1", "true", "yes"}

    engine = create_engine(database_url, pool_pre_ping=True)

    with engine.begin() as conn:
        # Ensure required extensions (idempotent)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
        except Exception:
            pass

        # Seed default tenant
        conn.execute(
            text(
                """
                INSERT INTO tenants (id, slug, name, created_at, updated_at)
                VALUES (:id, :slug, :name, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": default_tid, "slug": default_slug, "name": "Default Organization"},
        )

        # Seed admin user if not exists
        exists = conn.execute(text("SELECT 1 FROM admin_users WHERE username = :u"), {"u": admin_user}).first()
        if not exists:
            # Hash password via bcrypt
            salt = bcrypt.gensalt(rounds=12)
            pwd_hash = bcrypt.hashpw(admin_pass.encode("utf-8"), salt).decode("utf-8")
            conn.execute(
                text(
                    """
                    INSERT INTO admin_users (username, email, password_hash, role, is_active, display_name, created_at, updated_at)
                    VALUES (:u, :e, :ph, :role, true, :dn, NOW(), NOW())
                    """
                ),
                {"u": admin_user, "e": admin_email, "ph": pwd_hash, "role": "admin", "dn": admin_display},
            )
        elif force_update:
            salt = bcrypt.gensalt(rounds=12)
            pwd_hash = bcrypt.hashpw(admin_pass.encode("utf-8"), salt).decode("utf-8")
            conn.execute(
                text(
                    """
                    UPDATE admin_users
                    SET password_hash = :ph,
                        email = COALESCE(:e, email),
                        display_name = COALESCE(:dn, display_name),
                        updated_at = NOW()
                    WHERE username = :u
                    """
                ),
                {"u": admin_user, "e": admin_email, "ph": pwd_hash, "dn": admin_display},
            )

        # Ensure admin user is a member of default tenant (owner)
        admin_row = conn.execute(text("SELECT id FROM admin_users WHERE username = :u"), {"u": admin_user}).first()
        if admin_row:
            admin_id = int(admin_row[0])
            conn.execute(
                text(
                    """
                    INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                    VALUES (:tid, :uid, 'owner', NOW())
                    ON CONFLICT (tenant_id, user_id) DO NOTHING
                    """
                ),
                {"tid": default_tid, "uid": admin_id},
            )

        # Seed minimal RBAC permissions
        perms = [
            ("platform:admin", "Platform-wide superuser; short-circuit authorization"),
            ("tenant:manage", "Manage tenant lifecycle, billing, destructive ops"),
            ("user:manage", "Invite/remove users, assign roles within tenant"),
            ("data:read", "Read/search/use tenant data"),
            ("data:write", "Modify/ingest/configure tenant data"),
        ]
        for slug, desc in perms:
            conn.execute(
                text(
                    """
                    INSERT INTO permissions (slug, description, created_at)
                    VALUES (:slug, :desc, NOW())
                    ON CONFLICT (slug) DO NOTHING
                    """
                ),
                {"slug": slug, "desc": desc},
            )

        # Seed minimal RBAC roles (global definitions; tenant_id NULL for built-ins)
        roles = [
            ("SuperAdmin", "platform", None, True),
            ("TenantOwner", "tenant", None, True),
            ("TenantAdmin", "tenant", None, True),
            ("Member", "tenant", None, True),
        ]
        for name, scope, tid, built_in in roles:
            existing = conn.execute(
                text("SELECT id FROM roles WHERE name = :name AND tenant_id IS NULL"),
                {"name": name},
            ).first()
            if not existing:
                conn.execute(
                    text(
                        """
                        INSERT INTO roles (name, scope, tenant_id, built_in, created_at, updated_at)
                        VALUES (:name, :scope, :tid, :built_in, NOW(), NOW())
                        """
                    ),
                    {"name": name, "scope": scope, "tid": tid, "built_in": built_in},
                )

        # Ensure platform-level unique for roles with tenant_id NULL
        # (if role already exists, fetch its id; otherwise inserted above)
        rows = conn.execute(text("SELECT id, name FROM roles WHERE tenant_id IS NULL")).fetchall()
        role_ids = {row[1]: int(row[0]) for row in rows}

        # Map role -> permissions
        def role_perm(role_name: str, perm_slugs: list[str]):
            rid = role_ids.get(role_name)
            if not rid:
                return
            for slug in perm_slugs:
                pid_row = conn.execute(text("SELECT id FROM permissions WHERE slug = :s"), {"s": slug}).first()
                if not pid_row:
                    continue
                pid = int(pid_row[0])
                conn.execute(
                    text(
                        """
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (:rid, :pid)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"rid": rid, "pid": pid},
                )

        role_perm("SuperAdmin", ["platform:admin"])  # short-circuit role
        role_perm("TenantOwner", ["tenant:manage", "user:manage", "data:read", "data:write"])
        role_perm("TenantAdmin", ["user:manage", "data:read", "data:write"])
        role_perm("Member", ["data:read", "data:write"])

        # Assign SuperAdmin to seeded admin user (platform scope)
        if admin_row:
            superadmin_id = role_ids.get("SuperAdmin")
            if superadmin_id:
                conn.execute(
                    text(
                        """
                        INSERT INTO user_roles (user_id, role_id, tenant_id, assigned_at)
                        VALUES (:uid, :rid, NULL, NOW())
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"uid": admin_id, "rid": superadmin_id},
                )

    print("Seed complete: default tenant and admin user ensured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
