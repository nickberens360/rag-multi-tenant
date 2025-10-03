"""
Pytest configuration for security tests.
Provides fixtures and configuration for admin security testing.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# Security test markers
def pytest_configure(config):
    """Configure custom markers for security tests."""
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "auth: mark test as authentication related")
    config.addinivalue_line("markers", "database: mark test as database security related")
    config.addinivalue_line("markers", "api: mark test as API security related")
    config.addinivalue_line("markers", "integration: mark test as security integration test")
    config.addinivalue_line("markers", "production: mark test as production security test")
    config.addinivalue_line("markers", "critical: mark test as critical security test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture(scope="session")
def security_test_config():
    """Configuration for security tests."""
    return {
        "test_timeout": 30,
        "max_test_users": 10,
        "rate_limit_threshold": 5,
        "session_timeout_minutes": 30,
        "password_min_length": 12,
    }


@pytest.fixture
def temp_admin_db():
    """Create a temporary admin database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    original_env = os.environ.copy()

    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "testing",
        "ADMIN_DB_PATH": ":memory:",
        "RATE_LIMIT": "100/minute",
        "SESSION_TIMEOUT_HOURS": "1",
    }

    os.environ.update(test_env)

    yield test_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def security_headers():
    """Standard security headers for testing."""
    return {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
        "User-Agent": "SecurityTestClient/1.0",
    }


@pytest.fixture
def malicious_payloads():
    """Common malicious payloads for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE admin_users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM admin_users --",
            "admin'; INSERT INTO admin_users (username, password_hash, role) VALUES ('hacker', 'hash', 'admin'); --",
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "{{7*7}}",
            "${7*7}",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ],
        "command_injection": ["; ls -la", "| cat /etc/passwd", "$(whoami)", "`id`", "&& rm -rf /"],
        "ldap_injection": ["*)(uid=*))(|(uid=*", "*)(|(password=*))", "admin)(&(password=*)", "*)((|userPassword=*)"],
        "nosql_injection": [{"$ne": None}, {"$gt": ""}, {"$where": "function() { return true; }"}, {"$regex": ".*"}],
    }


@pytest.fixture
def test_users():
    """Test user data for security testing."""
    return {
        "admin": {
            "username": "test_admin",
            "email": "admin@securitytest.com",
            "password": "SecureAdminP@ss123!",
            "role": "admin",
        },
        "viewer": {
            "username": "test_viewer",
            "email": "viewer@securitytest.com",
            "password": "SecureViewerP@ss123!",
            "role": "viewer",
        },
        "malicious": {
            "username": "'; DROP TABLE users; --",
            "email": "<script>alert('xss')</script>@evil.com",
            "password": "EvilP@ss123!",
            "role": "admin",
        },
    }


@pytest.fixture
def rate_limit_config():
    """Rate limiting configuration for testing."""
    return {
        "login_attempts": 5,
        "lockout_duration_minutes": 5,
        "ip_rate_limit": "50/minute",
        "user_rate_limit": "10/minute",
        "api_rate_limit": "100/minute",
    }


class SecurityTestHelper:
    """Helper class for security testing utilities."""

    @staticmethod
    def is_sql_injection_safe(response_text: str) -> bool:
        """Check if response is safe from SQL injection."""
        dangerous_patterns = [
            "sqlite_master",
            "information_schema",
            "pg_tables",
            "show tables",
            "describe",
            "mysql.user",
        ]
        response_lower = response_text.lower()
        return not any(pattern in response_lower for pattern in dangerous_patterns)

    @staticmethod
    def is_xss_safe(response_text: str) -> bool:
        """Check if response is safe from XSS."""
        dangerous_patterns = ["<script>", "javascript:", "onerror=", "onload=", "eval(", "setTimeout("]
        return not any(pattern in response_text for pattern in dangerous_patterns)

    @staticmethod
    def check_security_headers(headers: dict) -> dict:
        """Check security headers in response."""
        security_checks = {
            "content_type_safe": "application/json" in headers.get("content-type", ""),
            "no_server_header": "server" not in [h.lower() for h in headers.keys()],
            "no_x_powered_by": "x-powered-by" not in [h.lower() for h in headers.keys()],
        }
        return security_checks

    @staticmethod
    def generate_long_string(length: int = 10000, char: str = "A") -> str:
        """Generate long string for buffer overflow testing."""
        return char * length

    @staticmethod
    def generate_unicode_attacks() -> list:
        """Generate Unicode-based attack strings."""
        return [
            "\u0000",  # Null byte
            "\ufeff",  # BOM
            "\u202e",  # Right-to-left override
            "\u200b",  # Zero-width space
            "../../etc/passwd\u0000.jpg",  # Null byte injection
        ]


@pytest.fixture
def security_helper():
    """Security testing helper fixture."""
    return SecurityTestHelper()


# Custom assertions for security testing
def assert_no_sql_injection(response_text: str):
    """Assert that response doesn't contain SQL injection artifacts."""
    assert SecurityTestHelper.is_sql_injection_safe(response_text), "Response may contain SQL injection artifacts"


def assert_no_xss(response_text: str):
    """Assert that response doesn't contain XSS vulnerabilities."""
    assert SecurityTestHelper.is_xss_safe(response_text), "Response may contain XSS vulnerabilities"


def assert_secure_headers(headers: dict):
    """Assert that response has secure headers."""
    checks = SecurityTestHelper.check_security_headers(headers)
    assert all(checks.values()), f"Security header checks failed: {checks}"


# Make custom assertions available globally
pytest.assert_no_sql_injection = assert_no_sql_injection
pytest.assert_no_xss = assert_no_xss
pytest.assert_secure_headers = assert_secure_headers
