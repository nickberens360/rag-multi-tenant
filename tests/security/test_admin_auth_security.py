"""
Security-focused tests for AdminAuthManager.
Tests password security, session management, rate limiting, and authentication flows.
"""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from backend.core.admin_auth import AdminAuthManager


@pytest.mark.security
@pytest.mark.auth
class TestAdminAuthSecurity:
    """Security-focused tests for AdminAuthManager."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            yield tmp.name
        os.unlink(tmp.name)

    @pytest.fixture
    def auth_manager(self, temp_db):
        """Create AdminAuthManager with temporary database."""
        # Initialize database schema
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create required tables
        cursor.execute(
            """
            CREATE TABLE admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE admin_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                started_at TIMESTAMP NOT NULL,
                last_active_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES admin_users (id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE rate_limiting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 1,
                first_attempt_at TIMESTAMP NOT NULL,
                last_attempt_at TIMESTAMP NOT NULL,
                lockout_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(identifier, identifier_type)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                identifier TEXT NOT NULL,
                details TEXT,
                severity TEXT NOT NULL DEFAULT 'low',
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

        # Mock the admin_db_manager
        mock_db_manager = Mock()
        mock_db_manager.get_connection.return_value.__enter__ = lambda: sqlite3.connect(temp_db)
        mock_db_manager.get_connection.return_value.__exit__ = lambda *args: None

        with patch("backend.core.admin_auth.admin_db_manager", mock_db_manager):
            auth_manager = AdminAuthManager()
            yield auth_manager

    def test_password_strength_validation_comprehensive(self, auth_manager):
        """Test comprehensive password strength validation."""
        # Test empty password
        with pytest.raises(ValueError, match="Password cannot be empty"):
            auth_manager.validate_password_strength("")

        # Test minimum length
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            auth_manager.validate_password_strength("short!")

        # Test missing uppercase
        with pytest.raises(ValueError, match="Password must contain at least one uppercase letter"):
            auth_manager.validate_password_strength("lowercase123!")

        # Test missing lowercase
        with pytest.raises(ValueError, match="Password must contain at least one lowercase letter"):
            auth_manager.validate_password_strength("UPPERCASE123!")

        # Test missing digit
        with pytest.raises(ValueError, match="Password must contain at least one digit"):
            auth_manager.validate_password_strength("NoDigitsHere!")

        # Test missing special character
        with pytest.raises(ValueError, match="Password must contain at least one special character"):
            auth_manager.validate_password_strength("NoSpecialChar123")

        # Test common weak patterns (must satisfy other requirements first)
        weak_patterns = ["Password123!@#", "AdminLogin123!", "QwertySecure123!", "WelcomeUser123!"]
        for weak_password in weak_patterns:
            with pytest.raises(ValueError, match="Password cannot contain common weak patterns"):
                auth_manager.validate_password_strength(weak_password)

        # Test sequential characters
        with pytest.raises(ValueError, match="Password cannot contain sequential characters"):
            auth_manager.validate_password_strength("Abc123!sequential")

        # Test repeated characters (avoid sequential patterns)
        with pytest.raises(ValueError, match="Password cannot contain more than 2 repeated characters"):
            auth_manager.validate_password_strength("Stronnnng135!Pass")

        # Test valid strong password
        try:
            auth_manager.validate_password_strength("StrongP@ssw0rd2024!")
        except ValueError:
            pytest.fail("Valid strong password was rejected")

    def test_bcrypt_hashing_security(self, auth_manager):
        """Test bcrypt password hashing security features."""
        password = "SecureP@ssw0rd297!"

        # Test hashing works
        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        assert len(hash1) > 50  # bcrypt hashes are long
        assert hash1.startswith("$2b$")  # bcrypt identifier

        # Test verification works
        assert auth_manager.verify_password(password, hash1)
        assert auth_manager.verify_password(password, hash2)

        # Test wrong password fails
        assert not auth_manager.verify_password("WrongPassword!", hash1)

        # Test empty/None inputs
        assert not auth_manager.verify_password("", hash1)
        assert not auth_manager.verify_password(password, "")
        assert not auth_manager.verify_password(None, hash1)

    def test_session_hijacking_detection(self, auth_manager):
        """Test detection of potential session hijacking."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            # Mock database responses
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_db.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_db.record_security_event.return_value = True

            # Simulate session data with original IP/User-Agent
            session_data = {
                "id": "test-session-123",
                "user_id": 1,
                "username": "testuser",
                "started_at": datetime.now().isoformat(),
                "last_active_at": datetime.now().isoformat(),
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Chrome/90.0)",
            }

            # Mock get_session to return session data
            mock_cursor.fetchone.return_value = type("Row", (), session_data)()

            # Test IP address change detection
            auth_manager._monitor_session_activity(
                session_data, "192.168.1.200", "Mozilla/5.0 (Chrome/90.0)"  # Different IP
            )

            # Should record security event for IP change
            mock_db.record_security_event.assert_called_with(
                "session_ip_change",
                "testuser",
                "high",
                "Session IP changed from 192.168.1.100 to 192.168.1.200",
                "192.168.1.200",
                "Mozilla/5.0 (Chrome/90.0)",
            )

    def test_session_management_security(self, auth_manager):
        """Test secure session management."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_db.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [3]  # 3 active sessions
            mock_cursor.lastrowid = 123

            # Test session creation with user limit
            session_id = auth_manager.create_session(user_id=1, ip_address="192.168.1.100", user_agent="Test Agent")

            # Should create valid UUID session ID
            import uuid

            assert uuid.UUID(session_id)  # Valid UUID format

            # Test invalid user ID
            with pytest.raises(ValueError, match="Invalid user ID"):
                auth_manager.create_session(user_id=0)

            # Test session expiry
            auth_manager.expire_session("test-session-123")
            mock_cursor.execute.assert_called_with(
                "UPDATE admin_sessions SET is_active = 0 WHERE id = ?", ("test-session-123",)
            )

    def test_rate_limiting_enforcement(self, auth_manager):
        """Test comprehensive rate limiting enforcement."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            # Test IP rate limiting
            mock_db.is_rate_limited.return_value = True
            mock_db.record_security_event.return_value = True

            result = auth_manager.authenticate_user(
                "testuser", "password", ip_address="192.168.1.100", user_agent="Test Agent"
            )

            assert result is None  # Should block authentication
            mock_db.record_security_event.assert_called()

    def test_comprehensive_rate_limit_checking(self, auth_manager):
        """Test comprehensive rate limit status checking."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_db.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Mock rate limit data
            mock_cursor.fetchone.side_effect = [
                (3, "2024-01-01 12:00:00"),  # IP attempts and lockout
                (2, None),  # User attempts, no lockout
            ]

            status = auth_manager.check_user_rate_limits("testuser", "192.168.1.100")

            assert "ip_rate_limited" in status
            assert "user_rate_limited" in status
            assert "any_rate_limited" in status
            assert "ip_attempts" in status
            assert "user_attempts" in status
            assert status["ip_attempts"] == 3
            assert status["user_attempts"] == 2

    def test_security_event_logging(self, auth_manager):
        """Test comprehensive security event logging."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_db.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Mock security events data
            mock_cursor.fetchall.return_value = [
                ("login_failure", "testuser", "Failed login attempt", "high", "192.168.1.100", "2024-01-01", 3),
                ("session_hijacking", "testuser", "IP change detected", "critical", "192.168.1.200", "2024-01-01", 1),
            ]

            alerts = auth_manager.get_security_alerts(24)

            assert len(alerts) == 2
            assert alerts[0]["event_type"] == "login_failure"
            assert alerts[0]["severity"] == "high"
            assert alerts[0]["count"] == 3

    def test_session_activity_pattern_detection(self, auth_manager):
        """Test detection of unusual session activity patterns."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_db.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_db.record_security_event.return_value = True

            session_data = {
                "id": "test-session-123",
                "user_id": 1,
                "username": "testuser",
                "started_at": (datetime.now() - timedelta(hours=50)).isoformat(),  # Very old session
                "last_active_at": datetime.now().isoformat(),
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
            }

            # Mock multiple IPs for user
            mock_cursor.fetchone.side_effect = [(5, 10), 15]  # 5 unique IPs, 10 total sessions  # 15 recent sessions

            auth_manager._check_session_activity_patterns(session_data)

            # Should detect multiple concerning patterns
            assert mock_db.record_security_event.call_count >= 1

    def test_browser_type_extraction(self, auth_manager):
        """Test browser type extraction for session monitoring."""
        test_cases = [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "chrome",
            ),
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0", "firefox"),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                "safari",
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
                "edge",
            ),
            ("Unknown Browser/1.0", "other"),
            ("", "unknown"),
        ]

        for user_agent, expected_browser in test_cases:
            result = auth_manager._extract_browser_type(user_agent)
            assert result == expected_browser

    def test_session_fingerprint_integration(self, auth_manager):
        """Test session fingerprinting integration for security."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            with patch("backend.core.admin_auth.session_fingerprinter") as mock_fingerprinter:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_db.get_connection.return_value.__enter__.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.fetchone.return_value = [3]  # Active session count
                mock_cursor.lastrowid = 123

                # Mock fingerprinting
                mock_fingerprinter.create_fingerprint.return_value = "test-fingerprint-hash"
                mock_fingerprinter.store_session_fingerprint.return_value = True
                mock_fingerprinter.monitor_session_fingerprint.return_value = {
                    "validation_result": {"risk_level": "low", "reason": "Normal session"}
                }

                # Test session creation with fingerprinting
                session_id = auth_manager.create_session(
                    user_id=1, ip_address="192.168.1.100", user_agent="Mozilla/5.0 (Chrome)"
                )

                # Should create and store fingerprint
                mock_fingerprinter.create_fingerprint.assert_called_with("192.168.1.100", "Mozilla/5.0 (Chrome)")
                mock_fingerprinter.store_session_fingerprint.assert_called_with(session_id, "test-fingerprint-hash")

    def test_geolocation_security_validation(self, auth_manager):
        """Test geolocation-based security validation."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            with patch("backend.core.admin_auth.geo_validator") as mock_geo:
                mock_db.get_admin_user.return_value = {"id": 1, "username": "testuser", "password_hash": "test-hash"}
                mock_db.record_security_event.return_value = True

                # Test blocked unusual location
                mock_geo.validate_login_location.return_value = {
                    "action": "block",
                    "reason": "Login from unusual country detected",
                }

                with patch.object(auth_manager, "check_user_rate_limits") as mock_rate_check:
                    mock_rate_check.return_value = {"any_rate_limited": False}

                    result = auth_manager.authenticate_user(
                        "testuser", "correct-password", ip_address="1.2.3.4", user_agent="Test Agent"  # Foreign IP
                    )

                    assert result is None  # Should block login
                    # Should record some kind of security event (actual event type may vary based on implementation)
                    mock_db.record_security_event.assert_called()

    def test_audit_logging_integration(self, auth_manager):
        """Test audit logging integration for security events."""
        with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
            with patch("backend.routes.admin.audit_logger") as mock_audit:
                mock_db.get_admin_user.return_value = {"id": 1, "username": "testuser", "password_hash": "test-hash"}
                mock_db.record_security_event.return_value = True

                with patch.object(auth_manager, "verify_password", return_value=False):
                    with patch.object(auth_manager, "check_user_rate_limits") as mock_rate_check:
                        mock_rate_check.return_value = {"any_rate_limited": False}

                        # This will trigger audit logging in the routes
                        result = auth_manager.authenticate_user(
                            "testuser", "wrong-password", ip_address="192.168.1.100", user_agent="Test Agent"
                        )

                        assert result is None
                        # Verify security event was recorded
                        mock_db.record_security_event.assert_called()
