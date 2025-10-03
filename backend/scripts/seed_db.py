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

    print("Seed complete: default tenant and admin user ensured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
