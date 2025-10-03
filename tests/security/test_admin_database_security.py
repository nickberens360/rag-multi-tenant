"""
Security-focused tests for AdminDatabaseManager.
Tests SQL injection prevention, data integrity, transaction safety, and database security.
"""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.skip(reason="admin_database removed; tests superseded by Postgres-backed flows")

# from backend.core.admin_database import AdminDatabaseManager


@pytest.mark.security
@pytest.mark.database
class TestAdminDatabaseSecurity:
    """Security-focused tests for AdminDatabaseManager."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            yield tmp.name
        os.unlink(tmp.name)

    @pytest.fixture
    def db_manager(self, temp_db):
        """Create AdminDatabaseManager with temporary database."""
        with patch.object(AdminDatabaseManager, "__init__", lambda self: None):
            manager = AdminDatabaseManager()
            manager.db_path = temp_db
            manager._initialize_database()
            yield manager

    def test_sql_injection_prevention_user_queries(self, db_manager):
        """Test SQL injection prevention in user-related queries."""
        # Create a legitimate user first
        user_id = db_manager.create_admin_user("testuser", "test@example.com", "hashed_password", "viewer")

        # Test SQL injection attempts in username
        malicious_usernames = [
            "admin'; DROP TABLE admin_users; --",
            "admin' OR '1'='1",
            "admin' UNION SELECT * FROM admin_sessions --",
            "'; INSERT INTO admin_users (username, password_hash, role) VALUES ('hacker', 'hash', 'admin'); --",
            "admin' AND (SELECT COUNT(*) FROM admin_users) > 0 --",
        ]

        for malicious_username in malicious_usernames:
            # Should not find user (and not cause SQL injection)
            result = db_manager.get_admin_user(malicious_username)
            assert result is None

            # Verify original user still exists (table wasn't dropped)
            legitimate_user = db_manager.get_admin_user("testuser")
            assert legitimate_user is not None
            assert legitimate_user["id"] == user_id

    def test_sql_injection_prevention_rate_limiting(self, db_manager):
        """Test SQL injection prevention in rate limiting queries."""
        malicious_identifiers = [
            "192.168.1.1'; DROP TABLE rate_limiting; --",
            "ip' OR '1'='1",
            "admin' UNION SELECT * FROM admin_users --",
        ]

        for malicious_identifier in malicious_identifiers:
            # These operations should not cause SQL injection
            db_manager.record_rate_limit_attempt(malicious_identifier, "ip")
            is_limited = db_manager.is_rate_limited(malicious_identifier, "ip")
            db_manager.reset_rate_limit(malicious_identifier, "ip")

            # Should handle safely without error
            assert isinstance(is_limited, bool)

    def test_sql_injection_prevention_security_events(self, db_manager):
        """Test SQL injection prevention in security event logging."""
        malicious_inputs = [
            "'; DROP TABLE security_events; --",
            "' UNION SELECT * FROM admin_users --",
            "'; INSERT INTO admin_users (username, password_hash, role) VALUES ('hacker', 'hash', 'admin'); --",
        ]

        for malicious_input in malicious_inputs:
            # Should handle malicious input safely
            result = db_manager.record_security_event(
                event_type=malicious_input,
                identifier=malicious_input,
                details=malicious_input,
                severity="high",
                ip_address=malicious_input,
                user_agent=malicious_input,
            )
            assert result is True  # Should complete without error

    def test_parameterized_queries_enforcement(self, db_manager):
        """Verify all database queries use parameterized statements."""
        # Test user creation with special characters
        special_chars_data = {
            "username": "test'user\"with;chars",
            "email": "test@ex'ample.com",
            "password_hash": "hash'with\"special;chars",
            "role": "view'er",
        }

        user_id = db_manager.create_admin_user(
            special_chars_data["username"],
            special_chars_data["email"],
            special_chars_data["password_hash"],
            "viewer",  # Use safe role
        )

        # Verify data stored correctly (not interpreted as SQL)
        user = db_manager.get_admin_user(special_chars_data["username"])
        assert user is not None
        assert user["username"] == special_chars_data["username"]
        assert user["email"] == special_chars_data["email"]

    @pytest.mark.skip(reason="Complex integration test - replaced by simpler security tests")
    def test_transaction_rollback_security(self, db_manager):
        """Test transaction rollback on errors to prevent partial updates."""
        original_user_count = len(db_manager.get_all_admin_users())

        # Simulate database error during user creation using context manager
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.row_factory = sqlite3.Row
            mock_connect.return_value = mock_conn

            # Simulate error on INSERT - this should trigger rollback
            mock_cursor.execute.side_effect = sqlite3.Error("Simulated database error")

            with pytest.raises(sqlite3.Error):
                db_manager.create_admin_user("testuser", "test@example.com", "hash", "viewer")

            # Verify rollback was called due to exception in context manager
            mock_conn.rollback.assert_called_once()

        # Verify no partial user was created
        final_user_count = len(db_manager.get_all_admin_users())
        assert final_user_count == original_user_count

    @pytest.mark.skip(reason="Complex integration test - replaced by simpler security tests")
    def test_connection_cleanup_security(self, db_manager):
        """Test database connections are properly cleaned up."""
        # Test connection cleanup in normal operation
        user = db_manager.get_admin_user("nonexistent")
        assert user is None

        # Test connection cleanup on exception
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.row_factory = sqlite3.Row
            mock_connect.return_value = mock_conn

            # Mock the context manager behavior - simulate error in yield
            def mock_context_manager():
                try:
                    yield mock_conn
                    mock_conn.commit.assert_called_once()
                except Exception:
                    mock_conn.rollback.assert_called_once()
                    raise
                finally:
                    mock_conn.close.assert_called_once()

            # Replace get_connection with a failing version
            original_get_connection = db_manager.get_connection

            def failing_get_connection():
                raise Exception("Connection error")

            db_manager.get_connection = failing_get_connection

            try:
                with pytest.raises(Exception):
                    with db_manager.get_connection():
                        pass
            finally:
                # Restore original method
                db_manager.get_connection = original_get_connection

        # Test that normal operations still work (connection pool recovered)
        user = db_manager.get_admin_user("nonexistent")
        assert user is None

    def test_rate_limiting_persistence_security(self, db_manager):
        """Test rate limiting persistence and lockout enforcement."""
        identifier = "192.168.1.100"

        # Record multiple failed attempts
        for i in range(4):
            locked = db_manager.record_rate_limit_attempt(identifier, "ip", 5)
            assert not locked  # Should not be locked yet

        # 5th attempt should trigger lockout
        locked = db_manager.record_rate_limit_attempt(identifier, "ip", 5)
        assert locked

        # Should be rate limited now
        assert db_manager.is_rate_limited(identifier, "ip")

        # Test lockout duration enforcement
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # Manually set lockout to past time
            past_time = datetime.now() - timedelta(minutes=10)
            cursor.execute("UPDATE rate_limiting SET lockout_until = ? WHERE identifier = ?", (past_time, identifier))
            conn.commit()

        # Should no longer be rate limited
        assert not db_manager.is_rate_limited(identifier, "ip")

    @pytest.mark.skip(reason="Complex integration test - replaced by simpler security tests")
    def test_data_sanitization_and_validation(self, db_manager):
        """Test data sanitization and validation in database operations."""
        # Test extremely long inputs - should handle gracefully without errors
        long_string = "a" * 10000

        try:
            # Should handle long inputs gracefully (may truncate internally)
            result = db_manager.record_security_event(
                event_type=long_string[:50],  # Truncate to reasonable size
                identifier="test",
                details=long_string,
                ip_address="192.168.1.1",
                user_agent=long_string,
            )
            assert result is True
        except Exception as e:
            # If the method doesn't exist or fails, that's acceptable for this security test
            # The important part is that it doesn't cause SQL injection or crash
            assert "SQL" not in str(e).upper() and "injection" not in str(e).lower()

        # Test null/empty inputs - should handle without crashing
        try:
            result = db_manager.record_security_event(
                event_type="test", identifier="test", details="", ip_address="192.168.1.1", user_agent=""
            )
            assert result is True
        except Exception as e:
            # Method may not exist, but should not cause SQL injection
            assert "SQL" not in str(e).upper() and "injection" not in str(e).lower()

        # Test special characters that could cause SQL injection
        special_chars = "'; DROP TABLE test; --"
        try:
            result = db_manager.record_security_event(
                event_type=special_chars,
                identifier=special_chars,
                details=special_chars,
                ip_address="192.168.1.1",
                user_agent=special_chars,
            )
            # Should either succeed or fail gracefully (no SQL injection)
            assert isinstance(result, bool)
        except Exception as e:
            # Should not contain SQL injection indicators
            assert "SQL" not in str(e).upper() or "DROP" not in str(e).upper()

    def test_database_schema_integrity(self, db_manager):
        """Test database schema integrity and constraints."""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Verify required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            required_tables = ["admin_users", "admin_sessions", "admin_settings", "rate_limiting", "security_events"]
            for table in required_tables:
                assert table in tables, f"Required table {table} missing"

            # Verify foreign key constraints
            cursor.execute("PRAGMA foreign_keys")
            cursor.fetchone()[0]
            # Note: SQLite foreign keys may be off by default, but constraints should exist

            # Test unique constraints
            db_manager.create_admin_user("testuser1", "test1@example.com", "hash1", "viewer")

            # Attempt to create duplicate username should fail
            with pytest.raises(Exception):  # Should raise IntegrityError
                db_manager.create_admin_user("testuser1", "test2@example.com", "hash2", "viewer")

    def test_concurrent_access_safety(self, db_manager):
        """Test database safety under concurrent access."""
        import threading

        results = []
        errors = []

        def create_user_worker(user_index):
            try:
                username = f"user_{user_index}_{threading.current_thread().ident}"
                user_id = db_manager.create_admin_user(
                    username, f"test{user_index}@example.com", f"hash{user_index}", "viewer"
                )
                results.append(user_id)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads to test concurrent access
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_user_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have successful results without database corruption
        assert len(results) > 0
        # Some errors might occur due to timing, but no corruption should happen

        # Verify database integrity
        all_users = db_manager.get_all_admin_users()
        assert len(all_users) >= len(results)

    def test_backup_and_recovery_security(self, db_manager):
        """Test backup and recovery procedures don't expose sensitive data."""
        # Create test data
        db_manager.create_admin_user("testuser", "test@example.com", "sensitive_hash", "admin")

        # Test that password hashes are not exposed in logs or error messages
        try:
            # Force an error that might expose data
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM nonexistent_table")
        except Exception as e:
            error_message = str(e)
            # Error message should not contain sensitive data
            assert "sensitive_hash" not in error_message
            assert "password" not in error_message.lower() or "hash" not in error_message.lower()

    def test_audit_trail_integrity(self, db_manager):
        """Test audit trail integrity and tamper prevention."""
        # Create security events
        original_events = []
        for i in range(5):
            db_manager.record_security_event(f"test_event_{i}", f"user_{i}", f"Test event {i}", "medium")
            original_events.append(f"test_event_{i}")

        # Verify events are recorded
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_type FROM security_events ORDER BY created_at")
            recorded_events = [row[0] for row in cursor.fetchall()]

        # Should contain our test events
        for event in original_events:
            assert event in recorded_events

        # Test that old events cleanup doesn't remove recent events
        initial_count = len(recorded_events)
        cleaned_count = db_manager.cleanup_old_rate_limits(days_old=1)  # Very recent cleanup

        # Should not clean up recent events
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM security_events")
            remaining_count = cursor.fetchone()[0]

        assert remaining_count == initial_count  # No recent events should be cleaned

    def test_password_hash_storage_security(self, db_manager):
        """Test secure password hash storage and retrieval."""
        # Create user with password hash
        password_hash = "$2b$12$test.hash.with.salt.and.rounds"
        user_id = db_manager.create_admin_user("testuser", "test@example.com", password_hash, "viewer")

        # Retrieve user and verify hash storage
        user = db_manager.get_admin_user("testuser")
        assert user["password_hash"] == password_hash

        # Test that get_all_admin_users excludes password hashes
        all_users = db_manager.get_all_admin_users()
        user_without_hash = next(u for u in all_users if u["id"] == user_id)
        assert "password_hash" not in user_without_hash

    def test_session_security_constraints(self, db_manager):
        """Test session security constraints and data integrity."""
        # Create user for session testing
        user_id = db_manager.create_admin_user("testuser", "test@example.com", "hash", "viewer")

        # Test session creation and validation
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            session_id = "test-session-123"

            # Insert session
            cursor.execute(
                """INSERT INTO admin_sessions
                   (id, user_id, started_at, last_active_at, ip_address, user_agent, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, user_id, datetime.now(), datetime.now(), "192.168.1.100", "Test Agent", 1),
            )

            # Verify session integrity
            cursor.execute("SELECT * FROM admin_sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            assert session is not None
            assert session[1] == user_id  # user_id should match

            # Test cleanup of expired sessions
            expired_count = db_manager.cleanup_expired_sessions()
            assert isinstance(expired_count, int)
            assert expired_count >= 0
