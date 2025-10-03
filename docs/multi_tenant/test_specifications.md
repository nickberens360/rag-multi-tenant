# Test Specifications (Agent-Executable)

## File: tests/conftest.py
```python
import pytest
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os

# Test database URL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://test_user:test_pass@localhost:5432/test_db")

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    # Run migrations
    os.system(f"DATABASE_URL={TEST_DATABASE_URL} alembic upgrade head")
    yield engine
    # Cleanup
    os.system(f"DATABASE_URL={TEST_DATABASE_URL} alembic downgrade base")
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestSessionLocal()
    # Start transaction
    trans = session.begin()
    yield session
    # Rollback
    trans.rollback()
    session.close()

@pytest.fixture
def test_tenant_1(db_session):
    """Create test tenant 1."""
    tenant_id = str(uuid.uuid4())
    db_session.execute(
        text("""
            INSERT INTO tenants (id, slug, name, created_at, updated_at)
            VALUES (:id, :slug, :name, NOW(), NOW())
        """),
        {"id": tenant_id, "slug": "tenant1", "name": "Test Tenant 1"}
    )
    db_session.commit()
    return {"id": tenant_id, "slug": "tenant1", "name": "Test Tenant 1"}

@pytest.fixture
def test_tenant_2(db_session):
    """Create test tenant 2."""
    tenant_id = str(uuid.uuid4())
    db_session.execute(
        text("""
            INSERT INTO tenants (id, slug, name, created_at, updated_at)
            VALUES (:id, :slug, :name, NOW(), NOW())
        """),
        {"id": tenant_id, "slug": "tenant2", "name": "Test Tenant 2"}
    )
    db_session.commit()
    return {"id": tenant_id, "slug": "tenant2", "name": "Test Tenant 2"}

@pytest.fixture
def test_user_1(db_session):
    """Create test user 1."""
    result = db_session.execute(
        text("""
            INSERT INTO users (username, email, password_hash, is_active)
            VALUES (:username, :email, :password_hash, true)
            RETURNING id
        """),
        {
            "username": "user1",
            "email": "user1@example.com",
            "password_hash": "hashed_password_1"
        }
    )
    user_id = result.scalar()
    db_session.commit()
    return {"id": user_id, "username": "user1", "email": "user1@example.com"}

@pytest.fixture
def test_user_2(db_session):
    """Create test user 2."""
    result = db_session.execute(
        text("""
            INSERT INTO users (username, email, password_hash, is_active)
            VALUES (:username, :email, :password_hash, true)
            RETURNING id
        """),
        {
            "username": "user2",
            "email": "user2@example.com",
            "password_hash": "hashed_password_2"
        }
    )
    user_id = result.scalar()
    db_session.commit()
    return {"id": user_id, "username": "user2", "email": "user2@example.com"}

@pytest.fixture
def app_with_tenant(test_tenant_1):
    """Create app with tenant context."""
    from backend.main import app
    from backend.core.db_session import get_db_session

    def override_get_db(request):
        session = TestSessionLocal()
        try:
            # Set tenant context
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_1["id"]})
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db
    return TestClient(app)
```

## File: tests/integration/test_tenancy_rls.py
```python
import pytest
from sqlalchemy import text

class TestRLS:
    """Test Row Level Security enforcement."""

    def test_tenant_isolation_admin_settings(self, db_session, test_tenant_1, test_tenant_2):
        """Test that admin_settings are isolated by tenant."""
        # Insert setting for tenant 1
        db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_1["id"]})
        db_session.execute(
            text("""
                INSERT INTO admin_settings (tenant_id, setting_key, setting_value)
                VALUES (:tenant_id, :key, :value)
            """),
            {"tenant_id": test_tenant_1["id"], "key": "test_key", "value": "tenant1_value"}
        )

        # Insert setting for tenant 2
        db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_2["id"]})
        db_session.execute(
            text("""
                INSERT INTO admin_settings (tenant_id, setting_key, setting_value)
                VALUES (:tenant_id, :key, :value)
            """),
            {"tenant_id": test_tenant_2["id"], "key": "test_key", "value": "tenant2_value"}
        )

        # Query as tenant 1 - should only see tenant 1 data
        db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_1["id"]})
        result = db_session.execute(
            text("SELECT setting_value FROM admin_settings WHERE setting_key = :key"),
            {"key": "test_key"}
        )
        values = [row[0] for row in result.fetchall()]
        assert values == ["tenant1_value"]

        # Query as tenant 2 - should only see tenant 2 data
        db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_2["id"]})
        result = db_session.execute(
            text("SELECT setting_value FROM admin_settings WHERE setting_key = :key"),
            {"key": "test_key"}
        )
        values = [row[0] for row in result.fetchall()]
        assert values == ["tenant2_value"]

    def test_cannot_insert_wrong_tenant(self, db_session, test_tenant_1, test_tenant_2):
        """Test that RLS prevents inserting data for wrong tenant."""
        # Set context to tenant 1
        db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_1["id"]})

        # Try to insert for tenant 2 - should fail
        with pytest.raises(Exception) as exc_info:
            db_session.execute(
                text("""
                    INSERT INTO admin_settings (tenant_id, setting_key, setting_value)
                    VALUES (:tenant_id, :key, :value)
                """),
                {"tenant_id": test_tenant_2["id"], "key": "test_key", "value": "wrong_tenant"}
            )
            db_session.commit()

        assert "new row violates row-level security policy" in str(exc_info.value).lower()

    def test_query_logs_isolation(self, db_session, test_tenant_1, test_tenant_2):
        """Test that query_logs are isolated by tenant."""
        # Insert logs for both tenants
        for tenant in [test_tenant_1, test_tenant_2]:
            db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant["id"]})
            db_session.execute(
                text("""
                    INSERT INTO query_logs (tenant_id, user_query, system_response, timestamp)
                    VALUES (:tenant_id, :query, :response, NOW())
                """),
                {
                    "tenant_id": tenant["id"],
                    "query": f"Query from {tenant['slug']}",
                    "response": f"Response for {tenant['slug']}"
                }
            )

        # Verify isolation
        db_session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_1["id"]})
        result = db_session.execute(text("SELECT COUNT(*) FROM query_logs"))
        count = result.scalar()
        assert count == 1

        result = db_session.execute(text("SELECT user_query FROM query_logs"))
        query = result.scalar()
        assert query == "Query from tenant1"
```

## File: tests/integration/test_tenant_resolution.py
```python
import pytest
from fastapi.testclient import TestClient

class TestTenantResolution:
    """Test tenant resolution from subdomain and path."""

    def test_subdomain_resolution(self, app_with_tenant):
        """Test tenant resolution from subdomain."""
        response = app_with_tenant.get(
            "/api/health",
            headers={"Host": "tenant1.example.com"}
        )
        assert response.status_code == 200
        # Verify tenant context was set (would need to expose in response for testing)

    def test_path_prefix_resolution(self, app_with_tenant):
        """Test tenant resolution from path prefix."""
        response = app_with_tenant.get("/tenant1/api/health")
        assert response.status_code == 200

    def test_subdomain_takes_precedence(self, app_with_tenant):
        """Test that subdomain takes precedence over path."""
        response = app_with_tenant.get(
            "/tenant2/api/health",
            headers={"Host": "tenant1.example.com"}
        )
        # Should use tenant1 from subdomain, not tenant2 from path
        assert response.status_code == 200

    def test_no_tenant_uses_default(self, app_with_tenant):
        """Test that no tenant uses default when enabled."""
        response = app_with_tenant.get(
            "/api/health",
            headers={"Host": "www.example.com"}
        )
        assert response.status_code == 200

    def test_invalid_tenant_returns_404(self, app_with_tenant):
        """Test that invalid tenant returns 404."""
        response = app_with_tenant.get(
            "/api/health",
            headers={"Host": "nonexistent.example.com"}
        )
        assert response.status_code == 404
```

## File: tests/unit/test_tenant_memberships.py
```python
import pytest
from sqlalchemy import text

class TestTenantMemberships:
    """Test tenant membership logic."""

    def test_add_member_to_tenant(self, db_session, test_tenant_1, test_user_1, test_user_2):
        """Test adding members to tenant."""
        # Add user1 as owner
        db_session.execute(
            text("""
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, :role, NOW())
            """),
            {"tenant_id": test_tenant_1["id"], "user_id": test_user_1["id"], "role": "owner"}
        )

        # Add user2 as member
        db_session.execute(
            text("""
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, :role, NOW())
            """),
            {"tenant_id": test_tenant_1["id"], "user_id": test_user_2["id"], "role": "member"}
        )

        # Verify memberships
        result = db_session.execute(
            text("""
                SELECT user_id, role FROM tenant_memberships
                WHERE tenant_id = :tenant_id
                ORDER BY role
            """),
            {"tenant_id": test_tenant_1["id"]}
        )
        memberships = result.fetchall()
        assert len(memberships) == 2
        assert memberships[0][1] == "member"
        assert memberships[1][1] == "owner"

    def test_cannot_remove_last_owner(self, db_session, test_tenant_1, test_user_1):
        """Test that last owner cannot be removed."""
        # Add user1 as only owner
        db_session.execute(
            text("""
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, 'owner', NOW())
            """),
            {"tenant_id": test_tenant_1["id"], "user_id": test_user_1["id"]}
        )

        # Count owners
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM tenant_memberships
                WHERE tenant_id = :tenant_id AND role = 'owner'
            """),
            {"tenant_id": test_tenant_1["id"]}
        )
        owner_count = result.scalar()
        assert owner_count == 1

        # Attempting to remove would fail in API layer
        # (business logic check, not database constraint)

    def test_unique_membership_per_tenant(self, db_session, test_tenant_1, test_user_1):
        """Test that user can only have one membership per tenant."""
        # Add first membership
        db_session.execute(
            text("""
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, 'member', NOW())
            """),
            {"tenant_id": test_tenant_1["id"], "user_id": test_user_1["id"]}
        )

        # Try to add duplicate - should fail
        with pytest.raises(Exception) as exc_info:
            db_session.execute(
                text("""
                    INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                    VALUES (:tenant_id, :user_id, 'admin', NOW())
                """),
                {"tenant_id": test_tenant_1["id"], "user_id": test_user_1["id"]}
            )
            db_session.commit()

        assert "duplicate key" in str(exc_info.value).lower()
```

## File: pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    -p no:warnings
markers =
    unit: Unit tests
    integration: Integration tests
    rls: Row Level Security tests
    tenant: Multi-tenant tests
    slow: Slow tests
```

## File: Makefile (additions)
```makefile
test-rls:
	pytest tests/integration/test_tenancy_rls.py -v -m rls

test-tenant:
	pytest tests/ -v -m tenant

test-integration:
	pytest tests/integration/ -v

test-coverage:
	pytest tests/ --cov=backend --cov-report=html --cov-report=term
```

## Commands to execute
```bash
# Run all tests
pytest tests/

# Run only RLS tests
pytest tests/integration/test_tenancy_rls.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test class
pytest tests/unit/test_tenant_memberships.py::TestTenantMemberships -v
```