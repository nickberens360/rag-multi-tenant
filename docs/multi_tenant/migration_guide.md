# SQLite to Postgres Migration Guide (Agent-Executable)

## Migration Strategy

### Phase 1: Setup Postgres + Dual Write
```bash
# 1. Setup Postgres database
docker-compose up -d postgres
alembic upgrade head

# 2. Seed default tenant
psql $DATABASE_URL -c "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Organization', NOW(), NOW());"
```

### Phase 2: Data Migration Scripts

#### File: scripts/migrate_admin_data.py
```python
import sqlite3
import psycopg
import os
from datetime import datetime

def migrate_admin_data():
    """Migrate from admin_monitoring.db to Postgres."""
    sqlite_path = "backend/logs/admin_monitoring.db"
    postgres_url = os.getenv("DATABASE_URL")
    default_tenant_id = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")

    # Connect to both databases
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg.connect(postgres_url)

    try:
        # Migrate admin_users -> users (if not exists)
        migrate_users(sqlite_conn, postgres_conn)

        # Migrate admin_settings
        migrate_admin_settings(sqlite_conn, postgres_conn, default_tenant_id)

        # Migrate admin_sessions
        migrate_sessions(sqlite_conn, postgres_conn)

        postgres_conn.commit()
        print("Admin data migration completed")

    except Exception as e:
        postgres_conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_users(sqlite_conn, postgres_conn):
    """Migrate admin_users to users."""
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()

    sqlite_cursor.execute("SELECT * FROM admin_users")
    users = sqlite_cursor.fetchall()

    for user in users:
        postgres_cursor.execute("""
            INSERT INTO users (id, username, email, password_hash, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                updated_at = EXCLUDED.updated_at
        """, (
            user["id"],
            user["username"],
            user.get("email", f"{user['username']}@example.com"),
            user["password_hash"],
            user.get("is_active", True),
            user.get("created_at", datetime.now()),
            user.get("updated_at", datetime.now())
        ))

def migrate_admin_settings(sqlite_conn, postgres_conn, tenant_id):
    """Migrate admin_settings with tenant_id."""
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()

    sqlite_cursor.execute("SELECT * FROM admin_settings")
    settings = sqlite_cursor.fetchall()

    for setting in settings:
        postgres_cursor.execute("""
            INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at, updated_by)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                updated_at = EXCLUDED.updated_at,
                updated_by = EXCLUDED.updated_by
        """, (
            tenant_id,
            setting["setting_key"],
            setting["setting_value"],
            setting.get("updated_at", datetime.now()),
            setting.get("updated_by")
        ))

def migrate_sessions(sqlite_conn, postgres_conn):
    """Migrate admin_sessions."""
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()

    sqlite_cursor.execute("SELECT * FROM admin_sessions")
    sessions = sqlite_cursor.fetchall()

    for session in sessions:
        postgres_cursor.execute("""
            INSERT INTO sessions (id, user_id, session_data, expires_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                session_data = EXCLUDED.session_data,
                expires_at = EXCLUDED.expires_at,
                updated_at = EXCLUDED.updated_at
        """, (
            session["id"],
            session["user_id"],
            session.get("session_data", "{}"),
            session["expires_at"],
            session.get("created_at", datetime.now()),
            session.get("updated_at", datetime.now())
        ))

if __name__ == "__main__":
    migrate_admin_data()
```

#### File: scripts/migrate_query_logs.py
```python
import sqlite3
import psycopg
import os
import json
from datetime import datetime

def migrate_query_logs():
    """Migrate from rag_monitoring.db to Postgres."""
    sqlite_path = "backend/logs/rag_monitoring.db"
    postgres_url = os.getenv("DATABASE_URL")
    default_tenant_id = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg.connect(postgres_url)

    try:
        # Migrate query_logs
        migrate_logs(sqlite_conn, postgres_conn, default_tenant_id)

        # Migrate content_gaps if exists
        try:
            migrate_content_gaps(sqlite_conn, postgres_conn, default_tenant_id)
        except sqlite3.OperationalError:
            print("content_gaps table not found in SQLite, skipping")

        postgres_conn.commit()
        print("Query logs migration completed")

    except Exception as e:
        postgres_conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_logs(sqlite_conn, postgres_conn, tenant_id):
    """Migrate query_logs with tenant_id."""
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()

    sqlite_cursor.execute("SELECT * FROM query_logs ORDER BY timestamp")
    logs = sqlite_cursor.fetchall()

    batch_size = 1000
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i + batch_size]

        values = []
        for log in batch:
            # Parse sources_used if it's JSON string
            sources_used = log.get("sources_used")
            if sources_used and isinstance(sources_used, str):
                try:
                    sources_used = json.loads(sources_used)
                except json.JSONDecodeError:
                    pass

            # Parse follow_up_questions if it's JSON string
            follow_up_questions = log.get("follow_up_questions")
            if follow_up_questions and isinstance(follow_up_questions, str):
                try:
                    follow_up_questions = json.loads(follow_up_questions)
                except json.JSONDecodeError:
                    pass

            values.append((
                tenant_id,
                log["user_query"],
                log.get("system_response"),
                log.get("query_type"),
                log.get("response_time_ms"),
                log.get("llm_provider"),
                log.get("llm_model"),
                log.get("vector_search_score"),
                json.dumps(sources_used) if sources_used else None,
                json.dumps(follow_up_questions) if follow_up_questions else None,
                log.get("cache_hit", False),
                log.get("error_occurred", False),
                log.get("error_message"),
                log.get("timestamp", datetime.now()),
                log.get("client_ip"),
                log.get("location_city"),
                log.get("location_region"),
                log.get("location_country"),
                log.get("location_country_code")
            ))

        postgres_cursor.executemany("""
            INSERT INTO query_logs (
                tenant_id, user_query, system_response, query_type, response_time_ms,
                llm_provider, llm_model, vector_search_score, sources_used,
                follow_up_questions, cache_hit, error_occurred, error_message,
                timestamp, client_ip, location_city, location_region,
                location_country, location_country_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, values)

        print(f"Migrated {len(batch)} query logs")

def migrate_content_gaps(sqlite_conn, postgres_conn, tenant_id):
    """Migrate content_gaps with tenant_id."""
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()

    sqlite_cursor.execute("SELECT * FROM content_gaps")
    gaps = sqlite_cursor.fetchall()

    for gap in gaps:
        postgres_cursor.execute("""
            INSERT INTO content_gaps (
                tenant_id, query_pattern, occurrence_count, avg_similarity_score,
                first_seen, last_seen, resolved, notes, sample_query_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            tenant_id,
            gap["query_pattern"],
            gap.get("occurrence_count", 1),
            gap.get("avg_similarity_score"),
            gap.get("first_seen", datetime.now()),
            gap.get("last_seen", datetime.now()),
            gap.get("resolved", False),
            gap.get("notes"),
            gap.get("sample_query_id")
        ))

if __name__ == "__main__":
    migrate_query_logs()
```

#### File: scripts/migrate_followup_data.py
```python
import sqlite3
import psycopg
import os
import json

def migrate_followup_data():
    """Migrate followup categories and questions."""
    sqlite_path = "backend/logs/admin_monitoring.db"  # Assuming followup data is here
    postgres_url = os.getenv("DATABASE_URL")
    default_tenant_id = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg.connect(postgres_url)

    try:
        # Check if tables exist
        sqlite_cursor = sqlite_conn.cursor()

        # Migrate followup_categories
        try:
            sqlite_cursor.execute("SELECT * FROM followup_categories")
            categories = sqlite_cursor.fetchall()
            migrate_categories(postgres_conn, categories, default_tenant_id)
        except sqlite3.OperationalError:
            print("followup_categories table not found, creating defaults")
            create_default_categories(postgres_conn, default_tenant_id)

        # Migrate followup_questions
        try:
            sqlite_cursor.execute("SELECT * FROM followup_questions")
            questions = sqlite_cursor.fetchall()
            migrate_questions(postgres_conn, questions, default_tenant_id)
        except sqlite3.OperationalError:
            print("followup_questions table not found, skipping")

        postgres_conn.commit()
        print("Followup data migration completed")

    except Exception as e:
        postgres_conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_categories(postgres_conn, categories, tenant_id):
    """Migrate followup categories."""
    postgres_cursor = postgres_conn.cursor()

    for category in categories:
        postgres_cursor.execute("""
            INSERT INTO followup_categories (
                tenant_id, name, display_name, description, icon, sort_order,
                is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                description = EXCLUDED.description,
                icon = EXCLUDED.icon,
                sort_order = EXCLUDED.sort_order,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at
        """, (
            tenant_id,
            category["name"],
            category["display_name"],
            category.get("description"),
            category.get("icon", "help-circle"),
            category.get("sort_order", 0),
            category.get("is_active", True),
            category.get("created_at", "NOW()"),
            category.get("updated_at", "NOW()")
        ))

def create_default_categories(postgres_conn, tenant_id):
    """Create default followup categories."""
    postgres_cursor = postgres_conn.cursor()

    default_categories = [
        ("technical", "Technical Questions", "Programming and development topics", "code", 1),
        ("experience", "Experience & Background", "Professional experience inquiries", "briefcase", 2),
        ("projects", "Projects & Portfolio", "Questions about specific projects", "folder", 3),
        ("general", "General Questions", "Miscellaneous topics", "help-circle", 4)
    ]

    for name, display_name, description, icon, sort_order in default_categories:
        postgres_cursor.execute("""
            INSERT INTO followup_categories (
                tenant_id, name, display_name, description, icon, sort_order,
                is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, true, NOW(), NOW())
        """, (tenant_id, name, display_name, description, icon, sort_order))

def migrate_questions(postgres_conn, questions, tenant_id):
    """Migrate followup questions."""
    postgres_cursor = postgres_conn.cursor()

    for question in questions:
        postgres_cursor.execute("""
            INSERT INTO followup_questions (
                tenant_id, category_id, question_text, sort_order, is_active,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            tenant_id,
            question["category_id"],
            question["question_text"],
            question.get("sort_order", 0),
            question.get("is_active", True),
            question.get("created_at", "NOW()"),
            question.get("updated_at", "NOW()")
        ))

if __name__ == "__main__":
    migrate_followup_data()
```

### Phase 3: Validation Scripts

#### File: scripts/validate_migration.py
```python
import sqlite3
import psycopg
import os

def validate_migration():
    """Validate that migration was successful."""
    sqlite_admin = "backend/logs/admin_monitoring.db"
    sqlite_query = "backend/logs/rag_monitoring.db"
    postgres_url = os.getenv("DATABASE_URL")

    print("=== Migration Validation Report ===")

    # Count records in SQLite
    sqlite_counts = get_sqlite_counts(sqlite_admin, sqlite_query)
    print(f"SQLite record counts: {sqlite_counts}")

    # Count records in Postgres
    postgres_counts = get_postgres_counts(postgres_url)
    print(f"Postgres record counts: {postgres_counts}")

    # Compare counts
    validation_passed = True
    for table, sqlite_count in sqlite_counts.items():
        postgres_count = postgres_counts.get(table, 0)
        if postgres_count < sqlite_count:
            print(f"❌ {table}: PostgreSQL has {postgres_count}, SQLite has {sqlite_count}")
            validation_passed = False
        else:
            print(f"✅ {table}: Migration complete ({postgres_count} records)")

    # Test RLS
    if test_rls(postgres_url):
        print("✅ RLS is working correctly")
    else:
        print("❌ RLS test failed")
        validation_passed = False

    if validation_passed:
        print("\n✅ Migration validation PASSED")
    else:
        print("\n❌ Migration validation FAILED")

    return validation_passed

def get_sqlite_counts(admin_db, query_db):
    """Get record counts from SQLite databases."""
    counts = {}

    # Admin DB
    conn = sqlite3.connect(admin_db)
    cursor = conn.cursor()

    tables = ["admin_users", "admin_settings", "admin_sessions"]
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0

    conn.close()

    # Query DB
    conn = sqlite3.connect(query_db)
    cursor = conn.cursor()

    tables = ["query_logs", "content_gaps"]
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0

    conn.close()
    return counts

def get_postgres_counts(postgres_url):
    """Get record counts from PostgreSQL."""
    counts = {}
    conn = psycopg.connect(postgres_url)
    cursor = conn.cursor()

    tables = {
        "admin_users": "users",
        "admin_settings": "admin_settings",
        "admin_sessions": "sessions",
        "query_logs": "query_logs",
        "content_gaps": "content_gaps"
    }

    for sqlite_table, postgres_table in tables.items():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {postgres_table}")
            counts[sqlite_table] = cursor.fetchone()[0]
        except Exception:
            counts[sqlite_table] = 0

    conn.close()
    return counts

def test_rls(postgres_url):
    """Test that RLS is working."""
    conn = psycopg.connect(postgres_url)
    cursor = conn.cursor()

    try:
        # Test with valid tenant
        default_tenant_id = os.getenv("DEFAULT_TENANT_ID")
        cursor.execute(f"SET LOCAL app.tenant_id = '{default_tenant_id}'")
        cursor.execute("SELECT COUNT(*) FROM admin_settings")
        count_with_tenant = cursor.fetchone()[0]

        # Test without tenant (should return 0 if RLS working)
        cursor.execute("RESET app.tenant_id")
        cursor.execute("SELECT COUNT(*) FROM admin_settings")
        count_without_tenant = cursor.fetchone()[0]

        conn.close()

        # If RLS is working, count without tenant should be 0 or less than with tenant
        return count_without_tenant == 0 or count_without_tenant < count_with_tenant

    except Exception as e:
        print(f"RLS test error: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    validate_migration()
```

## Migration Commands

### Complete Migration Script
```bash
#!/bin/bash
# File: scripts/run_migration.sh

set -e

echo "Starting SQLite to PostgreSQL migration..."

# 1. Setup Postgres
echo "Setting up PostgreSQL..."
docker-compose up -d postgres
sleep 10
alembic upgrade head

# 2. Seed default tenant
echo "Seeding default tenant..."
psql $DATABASE_URL -c "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES ('$DEFAULT_TENANT_ID', 'default', 'Default Organization', NOW(), NOW()) ON CONFLICT DO NOTHING;"

# 3. Run migrations
echo "Migrating admin data..."
python scripts/migrate_admin_data.py

echo "Migrating query logs..."
python scripts/migrate_query_logs.py

echo "Migrating followup data..."
python scripts/migrate_followup_data.py

# 4. Validate migration
echo "Validating migration..."
python scripts/validate_migration.py

echo "Migration completed successfully!"
```

### Rollback Script
```bash
#!/bin/bash
# File: scripts/rollback_migration.sh

echo "Rolling back to SQLite..."

# Switch database configuration
export USE_SQLITE=true
export DATABASE_URL=""

# Restart services
docker-compose restart backend
echo "Rolled back to SQLite successfully"
```

## Post-Migration Checklist

```bash
# Verify all services are using Postgres
railway logs | grep -i "connected to"

# Check RLS is enforced
psql $DATABASE_URL -c "SELECT COUNT(*) FROM admin_settings;" # Should be 0
psql $DATABASE_URL -c "SET LOCAL app.tenant_id = '$DEFAULT_TENANT_ID'; SELECT COUNT(*) FROM admin_settings;" # Should be > 0

# Test tenant endpoints
curl -H "Host: default.yourapp.com" "https://yourapp.com/api/health"

# Backup SQLite files (after successful migration)
mkdir -p backups/sqlite_backup_$(date +%Y%m%d)
cp backend/logs/*.db backups/sqlite_backup_$(date +%Y%m%d)/

# Update CLAUDE.md to reflect new database
sed -i 's/SQLite/PostgreSQL/g' CLAUDE.md
```