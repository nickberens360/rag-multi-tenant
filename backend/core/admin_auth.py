"""
Admin authentication system for the main backend.
Migrated from admin/backend/auth.py with improvements.
"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import HTTPException, Request
from sqlalchemy import text

from .audit_logger import AuditAction, audit_logger
from .db_session import get_db_session_sync
from .geolocation_validator import GeolocationValidator
from .session_fingerprint import SessionFingerprinter
from .settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

# Initialize security services
session_fingerprinter = SessionFingerprinter()
geo_validator = GeolocationValidator()


class AdminAuthManager:
    """
    Manages admin authentication for the backend system.

    Purpose:
        Provides secure authentication mechanisms for admin users, including password hashing,
        verification, session management, and rate limiting for failed login attempts.

    Main Responsibilities:
        - Hashes and verifies admin passwords using bcrypt.
        - Manages admin sessions, including creation, expiry, and activity tracking.
        - Limits concurrent sessions per user and expires oldest sessions when necessary.
        - Implements rate limiting and lockout for repeated failed authentication attempts.
        - Tracks session metadata such as IP address and user agent for auditing.

    Security Considerations:
        - Enforces minimum password length and uses bcrypt with configurable rounds for hashing.
        - Sessions expire after a configurable period (default: 24 hours) to reduce risk of hijacking.
        - Limits the number of concurrent active sessions per user to mitigate session abuse.
        - Implements lockout after repeated failed login attempts to prevent brute-force attacks.
        - Stores session metadata for monitoring and forensic analysis.
        - Handles exceptions and logs errors for security auditing.
    """

    def __init__(self):

        self._bcrypt_rounds = 12
        # Session expiry time (24 hours default, but will use dynamic settings)
        self.session_expiry_hours = 24
        # Rate limiting now handled by database - no in-memory storage
        self._lockout_duration_minutes = 5  # 5 minutes lockout

    def get_dynamic_session_timeout_hours(self) -> int:
        """Get session timeout from security settings, with fallback to default."""
        try:
            settings_manager = get_settings_manager()
            security_settings = settings_manager.get_security_settings()
            # Convert seconds to hours
            return security_settings.session_timeout // 3600
        except Exception as e:
            logger.warning(f"Failed to get dynamic session timeout, using default: {e}")
            return self.session_expiry_hours

    def get_dynamic_max_login_attempts(self) -> int:
        """Get max login attempts from security settings."""
        try:
            settings_manager = get_settings_manager()
            security_settings = settings_manager.get_security_settings()
            return security_settings.max_login_attempts
        except Exception as e:
            logger.warning(f"Failed to get dynamic max login attempts, using default: {e}")
            return 5  # Default

    def get_dynamic_lockout_duration_minutes(self) -> int:
        """Get lockout duration from security settings."""
        try:
            settings_manager = get_settings_manager()
            security_settings = settings_manager.get_security_settings()
            # Convert seconds to minutes
            return security_settings.lockout_duration // 60
        except Exception as e:
            logger.warning(f"Failed to get dynamic lockout duration, using default: {e}")
            return self._lockout_duration_minutes

    def validate_password_strength(self, password: str) -> None:
        """Validate password strength with comprehensive checks."""
        if not password:
            raise ValueError("Password cannot be empty")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        has_upper = has_lower = has_digit = has_special = False
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        for char in password:
            if char.isupper():
                has_upper = True
            elif char.islower():
                has_lower = True
            elif char.isdigit():
                has_digit = True
            elif char in special_chars:
                has_special = True
            # Early exit if all conditions are met
            if has_upper and has_lower and has_digit and has_special:
                break

        if not has_upper:
            raise ValueError("Password must contain at least one uppercase letter")

        if not has_lower:
            raise ValueError("Password must contain at least one lowercase letter")

        if not has_digit:
            raise ValueError("Password must contain at least one digit")

        if not has_special:
            raise ValueError(f"Password must contain at least one special character: {special_chars}")

        # Check for common weak patterns
        weak_patterns = [
            "password",
            "123456",
            "qwerty",
            "admin",
            "user",
            "login",
            "welcome",
            "letmein",
            "monkey",
            "dragon",
            "master",
        ]
        lower_password = password.lower()
        for pattern in weak_patterns:
            if pattern in lower_password:
                raise ValueError(f"Password cannot contain common weak patterns like '{pattern}'")

        # Check for sequential characters
        if any(
            ord(password[i]) == ord(password[i + 1]) - 1 == ord(password[i + 2]) - 2 for i in range(len(password) - 2)
        ):
            raise ValueError("Password cannot contain sequential characters (e.g., abc, 123)")

        # Check for repeated characters (more than 2 in a row)
        if any(password[i] == password[i + 1] == password[i + 2] for i in range(len(password) - 2)):
            raise ValueError("Password cannot contain more than 2 repeated characters in a row")

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with validation."""
        # Validate password strength first
        self.validate_password_strength(password)

        try:
            password_bytes = password.encode("utf-8")
            salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode("utf-8")
        except Exception:
            logger.error("Bcrypt hashing failed", exc_info=True)
            raise ValueError("Failed to hash password")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash with rate limiting."""
        if not plain_password or not hashed_password:
            return False

        try:
            # Try bcrypt directly first (works for both old and new hashes)
            password_bytes = plain_password.encode("utf-8")
            hash_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            logger.error("Password verification failed", exc_info=True)
            return False

    def create_session(self, user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Create a new session for a user with validation."""
        if user_id <= 0:
            raise ValueError("Invalid user ID")

        # Clean up expired sessions before creating new one
        self.cleanup_expired_sessions()

        session_id = str(uuid.uuid4())
        now = datetime.now()

        try:
            # Serialize session writes to avoid DB lock contention
            with get_db_session_sync() as session:
                if session is None:
                    raise RuntimeError("Database not available")
                # Limit concurrent sessions per user (max 5)
                active_sessions = (
                    session.execute(
                        text("SELECT COUNT(*) FROM admin_sessions WHERE user_id = :uid AND is_active = true"),
                        {"uid": user_id},
                    ).scalar()
                    or 0
                )
                if active_sessions >= 5:
                    # Expire oldest session
                    oldest = session.execute(
                        text(
                            "SELECT id FROM admin_sessions WHERE user_id = :uid AND is_active = true ORDER BY started_at ASC LIMIT 1"
                        ),
                        {"uid": user_id},
                    ).first()
                    if oldest:
                        session.execute(
                            text("UPDATE admin_sessions SET is_active = false WHERE id = :id"), {"id": oldest[0]}
                        )

                session.execute(
                    text(
                        """
                        INSERT INTO admin_sessions (id, user_id, started_at, last_active_at, ip_address, user_agent, is_active)
                        VALUES (:id, :uid, :st, :la, :ip, :ua, true)
                        """
                    ),
                    {
                        "id": session_id,
                        "uid": user_id,
                        "st": now,
                        "la": now,
                        "ip": ip_address,
                        "ua": user_agent[:500] if user_agent else None,
                    },
                )

                # Create and store session fingerprint (skip in FAST_LOGIN_MODE)
                if os.getenv("FAST_LOGIN_MODE", "false").lower() not in {"1", "true", "yes"}:
                    fingerprint = session_fingerprinter.create_fingerprint(ip_address or "unknown", user_agent or "")
                    session_fingerprinter.store_session_fingerprint(session_id, fingerprint)

                logger.info(f"Created session {session_id} for user {user_id} with fingerprint")
                return session_id

        except Exception:
            logger.error(f"Error creating session for user {user_id}", exc_info=True)
            raise

    def get_session(
        self, session_id: str, request_ip: Optional[str] = None, request_user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """Get session data if valid and active with enhanced validation and suspicious activity monitoring."""
        if not session_id or not session_id.strip():
            return None

        try:
            # Validate UUID format
            uuid.UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id[:8]}...")
            return None

        try:
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        """
                        SELECT s.id, s.user_id, s.started_at, s.last_active_at, s.ip_address, s.user_agent,
                               u.username, u.email, u.role, u.is_active
                        FROM admin_sessions s
                        JOIN admin_users u ON s.user_id = u.id
                        WHERE s.id = :sid AND s.is_active = true AND u.is_active = true
                        """
                    ),
                    {"sid": session_id},
                ).first()

                if not row:
                    return None

                session_data = {
                    "id": row[0],
                    "user_id": row[1],
                    "started_at": row[2].isoformat() if row[2] else None,
                    "last_active_at": row[3].isoformat() if row[3] else None,
                    "ip_address": row[4],
                    "user_agent": row[5],
                    "username": row[6],
                    "email": row[7],
                    "role": row[8],
                    "user_active": row[9],
                }

                # Check if session is expired (normalize to timezone-aware UTC)
                last_active_dt = row[3]
                if last_active_dt is None:
                    return None
                if last_active_dt.tzinfo is None:
                    from datetime import timezone as _tz

                    last_active_dt = last_active_dt.replace(tzinfo=_tz.utc)
                session_timeout_hours = self.get_dynamic_session_timeout_hours()
                expiry_time = last_active_dt + timedelta(hours=session_timeout_hours)

                from datetime import timezone as _tz

                now_utc = datetime.now(_tz.utc)
                if now_utc > expiry_time:
                    # Expire the session
                    self.expire_session(session_id)
                    return None

                # Session monitoring - check for suspicious patterns
                self._monitor_session_activity(session_data, request_ip, request_user_agent)

                # Session fingerprint monitoring
                from .session_fingerprint import session_fingerprinter

                fingerprint_result = session_fingerprinter.monitor_session_fingerprint(
                    session_id, session_data["username"], request_ip or "unknown", request_user_agent or ""
                )

                # Log high-risk fingerprint changes
                if fingerprint_result.get("validation_result", {}).get("risk_level") == "high":
                    logger.warning(
                        f"High-risk session fingerprint change detected for user {session_data['username']}: {fingerprint_result}"
                    )
                    audit_logger.log_action(
                        AuditAction.SECURITY_SCAN,
                        session_data["username"],
                        details={"event": "possible_session_hijacking"},
                        ip_address=request_ip,
                        user_agent=request_user_agent or "",
                        success=False,
                        error_message=fingerprint_result.get("validation_result", {}).get("reason"),
                    )

                return session_data

        except Exception:
            logger.error(f"Error getting session {session_id[:8]}...", exc_info=True)
            return None

    def update_session_activity(self, session_id: str) -> None:
        """Update the last activity time for a session."""
        if not session_id:
            return

        try:
            with get_db_session_sync() as session:
                if session is not None:
                    session.execute(
                        text("UPDATE admin_sessions SET last_active_at = now() WHERE id = :id AND is_active = true"),
                        {"id": session_id},
                    )
        except Exception:
            logger.error(f"Error updating session activity {session_id[:8]}...", exc_info=True)

    def expire_session(self, session_id: str) -> None:
        """Expire a session safely."""
        if not session_id:
            return

        try:
            with get_db_session_sync() as session:
                if session is not None:
                    session.execute(
                        text("UPDATE admin_sessions SET is_active = false WHERE id = :id"), {"id": session_id}
                    )
                    logger.info(f"Expired session {session_id[:8]}...")
        except Exception:
            logger.error(f"Error expiring session {session_id[:8]}...", exc_info=True)

    def expire_user_sessions(self, user_id: int) -> None:
        """Expire all sessions for a user."""
        if user_id <= 0:
            return

        try:
            with get_db_session_sync() as session:
                if session is not None:
                    session.execute(
                        text("UPDATE admin_sessions SET is_active = false WHERE user_id = :uid"), {"uid": user_id}
                    )
                    logger.info(f"Expired all sessions for user {user_id}")
        except Exception:
            logger.error(f"Error expiring sessions for user {user_id}", exc_info=True)

    def authenticate_user(
        self, username: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """Authenticate a user and create a session with persistent rate limiting."""
        if not username or not password:
            return None

        username = username.strip().lower()
        client_ip = ip_address or "unknown"

        fast_mode = os.getenv("FAST_LOGIN_MODE", "false").lower() in {"1", "true", "yes"}

        if not fast_mode:
            # Comprehensive rate limit check
            rate_limit_status = self.check_user_rate_limits(username, client_ip)

            if rate_limit_status["any_rate_limited"]:
                limit_type = rate_limit_status["primary_limit_type"]
                attempts = rate_limit_status.get(f"{limit_type}_attempts", 0)
                lockout_until = rate_limit_status.get(f"{limit_type}_lockout_until")

                logger.warning(
                    f"{limit_type.upper()} rate limited authentication attempt for user {username} from {client_ip} ({attempts} attempts)"
                )
                audit_logger.log_action(
                    AuditAction.LOGIN_FAILED,
                    username,
                    details={
                        "reason": "rate_limited_login",
                        "limit_type": limit_type,
                        "attempts": attempts,
                        "lockout_until": str(lockout_until) if lockout_until else None,
                    },
                    ip_address=client_ip,
                    user_agent=user_agent or "",
                    success=False,
                    error_message="rate limited",
                )
                return None

        # Validate login location for security
        if not fast_mode:
            from .geolocation_validator import geo_validator

            try:
                location_validation = geo_validator.validate_login_location(username, client_ip, user_agent)
            except Exception as e:
                # Never fail login due to validator errors; log and allow with low risk
                logger.warning(f"Geolocation validation error for user {username}: {e}")
                location_validation = {
                    "is_unusual": False,
                    "reason": "geolocation_validator_error",
                    "risk_level": "low",
                    "action": "allow",
                }
        else:
            location_validation = {"is_unusual": False, "reason": "fast_mode", "risk_level": "low", "action": "allow"}

        if location_validation["action"] == "block":
            logger.warning(f"Blocked login from unusual location for user {username}: {location_validation['reason']}")
            audit_logger.log_action(
                AuditAction.LOGIN_FAILED,
                username,
                details={"reason": "blocked_unusual_location", "detail": location_validation.get("reason")},
                ip_address=client_ip,
                user_agent=user_agent or "",
                success=False,
                error_message="blocked by geolocation",
            )
            return None

        # Load user from Postgres
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        "SELECT id, username, email, password_hash, role, is_active, last_login_at FROM admin_users WHERE lower(username) = :un"
                    ),
                    {"un": username},
                ).first()
        except Exception:
            row = None

        if not row or not self.verify_password(password, row[3]):
            if not fast_mode:
                # Record failed attempt for both IP and username
                ip_locked = self.record_rate_limit_attempt(client_ip, "ip", self._lockout_duration_minutes)
                user_locked = self.record_rate_limit_attempt(username, "username", self._lockout_duration_minutes)

                # Log security event
                audit_logger.log_login(
                    username,
                    client_ip,
                    user_agent or "",
                    success=False,
                    error_message="invalid credentials",
                )

                if ip_locked or user_locked:
                    logger.warning(f"Locked out after failed authentication: user {username} from {client_ip}")
                    audit_logger.log_action(
                        AuditAction.LOGIN_FAILED,
                        username,
                        details={"reason": "account_lockout"},
                        ip_address=client_ip,
                        user_agent=user_agent or "",
                        success=False,
                        error_message="locked out",
                    )
                else:
                    logger.warning(f"Failed authentication attempt for user {username} from {client_ip}")

            return None

        # Reset failed attempts on successful login
        if not fast_mode:
            self.reset_user_rate_limits(username, client_ip)

        # Build user object from database row
        user = {
            "id": int(row[0]),
            "username": row[1],
            "email": row[2],
            "password_hash": row[3],
            "role": row[4],
            "is_active": bool(row[5]) if row[5] is not None else True,
            "last_login_at": row[6].isoformat() if row[6] else None,
        }

        # Check if user has 2FA enabled
        from .totp_service import totp_service

        totp_status = totp_service.get_2fa_status(int(row[0]))

        if totp_status["enabled"]:
            # User has 2FA enabled - return partial authentication result
            logger.info(f"2FA required for user {username}")
            return {"user": user, "requires_2fa": True, "message": "2FA verification required"}

        # Log successful login with location information
        if not fast_mode:
            audit_logger.log_login(username, client_ip, user_agent or "", success=True)

        try:
            # Update last login time (Postgres)
            with get_db_session_sync() as session:
                if session is not None:
                    session.execute(
                        text("UPDATE admin_users SET last_login_at = now() WHERE id = :id"),
                        {"id": int(row[0])},
                    )

            # Create session
            session_id = self.create_session(int(row[0]), ip_address, user_agent)

            logger.info(f"Successful authentication for user {username}")
            return {"user": user, "session_id": session_id}

        except Exception as e:
            logger.error(f"Error during authentication for user {username}", exc_info=True)
            audit_logger.log_action(
                AuditAction.LOGIN_FAILED,
                username,
                details={"reason": "authentication_error"},
                ip_address=client_ip,
                user_agent=user_agent or "",
                success=False,
                error_message=str(e),
            )
            return None

    def complete_2fa_authentication(
        self,
        username: str,
        totp_code: str,
        is_backup_code: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Dict]:
        """Complete authentication with 2FA verification."""
        username = username.strip().lower()
        client_ip = ip_address or "unknown"

        try:
            # Get user info (Postgres) - fetch all fields needed for user object
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        "SELECT id, username, email, password_hash, role, is_active, last_login_at FROM admin_users WHERE lower(username) = :un AND is_active = true"
                    ),
                    {"un": username},
                ).first()
            if not row:
                return None

            # Build user object from database row
            user = {
                "id": int(row[0]),
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],
                "role": row[4],
                "is_active": bool(row[5]) if row[5] is not None else True,
                "last_login_at": row[6].isoformat() if row[6] else None,
            }

            # Verify 2FA token
            from .totp_service import totp_service

            verification_result = totp_service.verify_2fa_token(int(row[0]), username, totp_code, is_backup_code)

            if not verification_result["success"]:
                logger.warning(f"2FA verification failed for user {username}: {verification_result.get('error')}")
                return None

            # Log successful 2FA completion
            event_type = "2fa_backup_login" if verification_result.get("backup_code_used") else "2fa_login_success"
            audit_logger.log_action(
                AuditAction.TOTP_VERIFY,
                username,
                details={"event_type": event_type},
                ip_address=client_ip,
                user_agent=user_agent or "",
            )

            # Update last login time
            with get_db_session_sync() as session:
                if session is not None:
                    session.execute(
                        text("UPDATE admin_users SET last_login_at = now() WHERE id = :id"), {"id": int(row[0])}
                    )

            # Create session
            session_id = self.create_session(int(row[0]), ip_address, user_agent)

            logger.info(f"Successful 2FA authentication completed for user {username}")
            return {"user": user, "session_id": session_id, "2fa_used": True}

        except Exception as e:
            logger.error(f"Error during 2FA completion for user {username}", exc_info=True)
            audit_logger.log_action(
                AuditAction.TOTP_VERIFY,
                username,
                details={"reason": "2fa_authentication_error"},
                ip_address=client_ip,
                user_agent=user_agent or "",
                success=False,
                error_message=str(e),
            )
            return None

    def create_admin_user(self, username: str, password: str, email: Optional[str] = None, role: str = "viewer") -> int:
        """Create a new admin user with validation."""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")

        # Password validation is now handled in hash_password method
        password_hash = self.hash_password(password)
        try:
            with get_db_session_sync() as session:
                if session is None:
                    raise RuntimeError("Database not available")
                row = session.execute(
                    text(
                        """
                        INSERT INTO admin_users (username, email, password_hash, role, is_active)
                        VALUES (:un, :em, :ph, :role, true)
                        RETURNING id
                        """
                    ),
                    {"un": username.lower(), "em": email, "ph": password_hash, "role": role},
                ).first()
                return int(row[0])
        except Exception as e:
            logger.error(f"Error creating admin user in Postgres: {e}")
            raise

    def get_session_from_request(self, request: Request) -> Optional[Dict]:
        """Extract and validate session from request."""
        # Get session ID from cookie only - no fallbacks
        session_id = request.cookies.get("admin_session")

        if not session_id:
            return None

        # Get request details for monitoring
        request_ip = request.client.host if request.client else None
        request_user_agent = request.headers.get("User-Agent")

        session = self.get_session(session_id, request_ip, request_user_agent)
        if session:
            # Update activity
            self.update_session_activity(session_id)

        return session

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions from the database."""
        try:
            session_timeout_hours = self.get_dynamic_session_timeout_hours()
            expiry_cutoff = datetime.now() - timedelta(hours=session_timeout_hours)

            with get_db_session_sync() as session:
                if session is None:
                    return
                res = session.execute(
                    text(
                        "UPDATE admin_sessions SET is_active = false WHERE last_active_at < :cutoff AND is_active = true"
                    ),
                    {"cutoff": expiry_cutoff},
                )
                expired_count = res.rowcount or 0
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception:
            logger.error("Error cleaning up expired sessions", exc_info=True)

    def is_rate_limited(self, identifier: str, identifier_type: str = "ip") -> bool:
        """Check if identifier is currently rate limited (Postgres)."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return False
                row = session.execute(
                    text("SELECT lockout_until FROM rate_limiting WHERE identifier = :id AND identifier_type = :t"),
                    {"id": identifier, "t": identifier_type},
                ).first()
                if not row or not row[0]:
                    return False
                return (
                    row[0] > datetime.now(row[0].tzinfo) if getattr(row[0], "tzinfo", None) else row[0] > datetime.now()
                )
        except Exception:
            logger.error("Error checking rate limit in Postgres", exc_info=True)
            return False

    def record_rate_limit_attempt(
        self, identifier: str, identifier_type: str, lockout_duration_minutes: Optional[int] = None
    ) -> bool:
        """Record a failed attempt; return True if lockout is active after update (Postgres)."""
        import random

        try:
            now = datetime.now()
            duration_min = lockout_duration_minutes or self.get_dynamic_lockout_duration_minutes()
            jitter_seconds = random.randint(0, 60)
            lockout_until = now + timedelta(minutes=duration_min, seconds=jitter_seconds)

            with get_db_session_sync() as session:
                if session is None:
                    return False
                row = session.execute(
                    text(
                        "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = :id AND identifier_type = :t"
                    ),
                    {"id": identifier, "t": identifier_type},
                ).first()

                max_attempts = self.get_dynamic_max_login_attempts()

                if row:
                    attempt_count, current_lockout = row[0] or 0, row[1]

                    # Still locked out
                    if current_lockout and (current_lockout > now):
                        return True

                    # Reset attempts if lockout expired over an hour ago
                    if current_lockout and (current_lockout < (now - timedelta(hours=1))):
                        attempt_count = 0

                    new_attempts = attempt_count + 1
                    should_lock = new_attempts >= max_attempts

                    session.execute(
                        text(
                            """
                            UPDATE rate_limiting
                            SET attempt_count = :ac, last_attempt_at = :la, lockout_until = :lu
                            WHERE identifier = :id AND identifier_type = :t
                            """
                        ),
                        {
                            "ac": new_attempts,
                            "la": now,
                            "lu": lockout_until if should_lock else None,
                            "id": identifier,
                            "t": identifier_type,
                        },
                    )
                    return should_lock
                else:
                    session.execute(
                        text(
                            """
                            INSERT INTO rate_limiting (identifier, identifier_type, attempt_count, first_attempt_at, last_attempt_at)
                            VALUES (:id, :t, 1, :ts, :ts)
                            """
                        ),
                        {"id": identifier, "t": identifier_type, "ts": now},
                    )
                    return False
        except Exception:
            logger.error("Error recording rate limit attempt in Postgres", exc_info=True)
            return False

    def check_user_rate_limits(self, username: str, ip_address: str) -> Dict[str, Any]:
        """
        Comprehensive rate limit check for both user and IP.

        Returns:
            Dict containing rate limit status and details
        """
        try:
            username = username.strip().lower()
            ip_rate_limited = self.is_rate_limited(ip_address, "ip")
            user_rate_limited = self.is_rate_limited(username, "username")

            # Get attempt counts and lockout info from Postgres
            with get_db_session_sync() as session:
                if session is None:
                    return {"ip_rate_limited": False, "user_rate_limited": False, "any_rate_limited": False}
                ip_info = session.execute(
                    text(
                        "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = :id AND identifier_type = 'ip'"
                    ),
                    {"id": ip_address},
                ).first()
                user_info = session.execute(
                    text(
                        "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = :id AND identifier_type = 'username'"
                    ),
                    {"id": username},
                ).first()

            return {
                "ip_rate_limited": ip_rate_limited,
                "user_rate_limited": user_rate_limited,
                "any_rate_limited": ip_rate_limited or user_rate_limited,
                "ip_attempts": ip_info[0] if ip_info else 0,
                "user_attempts": user_info[0] if user_info else 0,
                "ip_lockout_until": ip_info[1] if ip_info else None,
                "user_lockout_until": user_info[1] if user_info else None,
                "primary_limit_type": "user" if user_rate_limited else ("ip" if ip_rate_limited else None),
            }

        except Exception as e:
            logger.error("Error checking user rate limits", exc_info=True)
            return {"ip_rate_limited": False, "user_rate_limited": False, "any_rate_limited": False, "error": str(e)}

    def reset_user_rate_limits(self, username: str, ip_address: str) -> bool:
        """Reset rate limits for both user and IP after successful login."""
        try:
            username = username.strip().lower()
            ip_reset = self.reset_rate_limit(ip_address, "ip")
            user_reset = self.reset_rate_limit(username, "username")

            if ip_reset or user_reset:
                logger.info(f"Reset rate limits for user {username} and IP {ip_address}")

            return True

        except Exception:
            logger.error("Error resetting user rate limits", exc_info=True)
            return False

    def cleanup_old_sessions_and_rate_limits(self) -> None:
        """Clean up old sessions and rate limiting records."""
        self.cleanup_expired_sessions()
        self.cleanup_old_rate_limits()

    def reset_rate_limit(self, identifier: str, identifier_type: str) -> bool:
        """Reset rate limiting for an identifier (Postgres)."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return False
                res = session.execute(
                    text("DELETE FROM rate_limiting WHERE identifier = :id AND identifier_type = :t"),
                    {"id": identifier, "t": identifier_type},
                )
                return (res.rowcount or 0) > 0
        except Exception:
            logger.error("Error resetting rate limit in Postgres", exc_info=True)
            return False

    def cleanup_old_rate_limits(self, days_old: int = 7) -> int:
        """Clean up old rate limiting records from Postgres."""
        try:
            cutoff = datetime.now() - timedelta(days=days_old)
            with get_db_session_sync() as session:
                if session is None:
                    return 0
                res = session.execute(
                    text("DELETE FROM rate_limiting WHERE last_attempt_at < :cutoff"), {"cutoff": cutoff}
                )
                return int(res.rowcount or 0)
        except Exception:
            logger.error("Error cleaning up old rate limits in Postgres", exc_info=True)
            return 0

    def _monitor_session_activity(
        self, session_data: Dict, request_ip: Optional[str], request_user_agent: Optional[str]
    ) -> None:
        """Monitor session activity for suspicious patterns."""
        session_data["id"]
        username = session_data["username"]
        original_ip = session_data.get("ip_address")
        original_user_agent = session_data.get("user_agent")

        try:
            # Check for IP address changes (possible session hijacking)
            if original_ip and request_ip and original_ip != request_ip:
                logger.warning(f"Session IP change detected for user {username}: {original_ip} -> {request_ip}")
                audit_logger.log_action(
                    AuditAction.SECURITY_SCAN,
                    username,
                    details={"event": "session_ip_change", "from": original_ip, "to": request_ip},
                    ip_address=request_ip,
                    user_agent=request_user_agent or "",
                )

                # Consider terminating session if IP change is from completely different location
                # For now, just log and alert

            # Check for user agent changes (possible session hijacking)
            if original_user_agent and request_user_agent:
                # Simple check - just compare browser types, not exact versions
                original_browser = self._extract_browser_type(original_user_agent)
                request_browser = self._extract_browser_type(request_user_agent)

                if (
                    original_browser != request_browser
                    and original_browser != "unknown"
                    and request_browser != "unknown"
                ):
                    logger.warning(
                        f"Session user agent change detected for user {username}: {original_browser} -> {request_browser}"
                    )
                    audit_logger.log_action(
                        AuditAction.SECURITY_SCAN,
                        username,
                        details={"event": "session_user_agent_change", "from": original_browser, "to": request_browser},
                        ip_address=request_ip,
                        user_agent=request_user_agent or "",
                    )

            # Check for unusual session activity patterns
            self._check_session_activity_patterns(session_data)

        except Exception:
            logger.error("Error monitoring session activity", exc_info=True)

    def _extract_browser_type(self, user_agent: str) -> str:
        """Extract browser type from user agent string."""
        if not user_agent:
            return "unknown"

        user_agent_lower = user_agent.lower()

        if "chrome" in user_agent_lower and "edg" not in user_agent_lower:
            return "chrome"
        elif "firefox" in user_agent_lower:
            return "firefox"
        elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
            return "safari"
        elif "edg" in user_agent_lower:
            return "edge"
        elif "opera" in user_agent_lower:
            return "opera"
        else:
            return "other"

    def _check_session_activity_patterns(self, session_data: Dict) -> None:
        """Check for unusual session activity patterns."""
        session_data["id"]
        user_id = session_data["user_id"]
        username = session_data["username"]
        # Normalize timestamps to timezone-aware UTC
        from datetime import timezone as _tz

        started_at = datetime.fromisoformat(session_data["started_at"]) if session_data.get("started_at") else None
        if started_at is not None and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=_tz.utc)
        # Parse last_active_at to validate format, but activity check uses DB now()
        _ = datetime.fromisoformat(session_data["last_active_at"]) if session_data.get("last_active_at") else None

        try:
            with get_db_session_sync() as session:
                if session is None:
                    return
                row = session.execute(
                    text(
                        "SELECT COUNT(DISTINCT ip_address), COUNT(*) FROM admin_sessions WHERE user_id = :uid AND is_active = true"
                    ),
                    {"uid": user_id},
                ).first()
                ip_stats = row

                if ip_stats and ip_stats[0] > 2:  # More than 2 unique IPs
                    logger.warning(f"User {username} has active sessions from {ip_stats[0]} different IP addresses")
                    audit_logger.log_action(
                        AuditAction.SECURITY_SCAN if False else AuditAction.LOGOUT,
                        username,
                        details={
                            "event": "multiple_concurrent_ips",
                            "unique_ips": int(ip_stats[0]),
                            "total_sessions": int(ip_stats[1]),
                        },
                        ip_address=session_data.get("ip_address"),
                        user_agent=session_data.get("user_agent"),
                    )

                # Check for abnormally long session duration
                now_utc = datetime.now(_tz.utc)
                session_duration = 0.0
                if started_at is not None:
                    session_duration = (now_utc - started_at).total_seconds() / 3600  # Hours
                if session_duration > 48:  # More than 48 hours
                    logger.warning(f"Very long session detected for user {username}: {session_duration:.1f} hours")
                    audit_logger.log_action(
                        AuditAction.SESSION_EXPIRE,
                        username,
                        details={"event": "long_session_duration", "hours": round(session_duration, 1)},
                        ip_address=session_data.get("ip_address"),
                        user_agent=session_data.get("user_agent"),
                    )

                # Check for rapid session creation (possible brute force)
                row = session.execute(
                    text(
                        "SELECT COUNT(*) FROM admin_sessions WHERE user_id = :uid AND started_at > (now() - interval '1 hour')"
                    ),
                    {"uid": user_id},
                ).first()
                recent_sessions = int(row[0]) if row else 0

                if recent_sessions > 10:  # More than 10 sessions in the last hour
                    logger.warning(
                        f"Rapid session creation detected for user {username}: {recent_sessions} sessions in last hour"
                    )
                    audit_logger.log_action(
                        AuditAction.SESSION_CREATE,
                        username,
                        details={"event": "rapid_session_creation", "count_last_hour": recent_sessions},
                        ip_address=session_data.get("ip_address"),
                        user_agent=session_data.get("user_agent"),
                    )

        except Exception:
            logger.error("Error checking session activity patterns", exc_info=True)

    def _aggregate_security_alerts(self, raw_alerts: List[Dict]) -> List[Dict]:
        """Aggregate security alerts by event_type, identifier, severity, and ip_address.

        This helper method encapsulates the Python aggregation logic that mirrors
        the SQL GROUP BY behavior in the main query.

        Args:
            raw_alerts: List of raw security alert dictionaries

        Returns:
            List of aggregated security alerts, sorted by severity and count
        """
        aggregated: Dict[tuple, Dict] = {}
        for alert in raw_alerts:
            key = (alert.get("event_type"), alert.get("identifier"), alert.get("severity"), alert.get("ip_address"))
            item = aggregated.get(key)
            if item is None:
                aggregated[key] = {
                    "event_type": alert.get("event_type"),
                    "identifier": alert.get("identifier"),
                    "details": alert.get("details"),
                    "severity": alert.get("severity"),
                    "ip_address": alert.get("ip_address"),
                    "created_at": alert.get("created_at"),
                    "count": 1,
                }
            else:
                item["count"] += 1
                # Keep the most recent timestamp
                if alert.get("created_at") > item.get("created_at"):
                    item["created_at"] = alert.get("created_at")

        # Sort by severity (high to low) and then by created_at (most recent first)
        severity_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        result = sorted(
            aggregated.values(),
            key=lambda x: (severity_order.get(x.get("severity"), 1), x.get("created_at")),
            reverse=True,
        )
        return result[:50]

    def get_security_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent security events for monitoring dashboard (Postgres)."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return []
                rows = session.execute(
                    text(
                        """
                        SELECT event_type, identifier, COALESCE(details, ''), severity, ip_address,
                               MAX(created_at) AS created_at, COUNT(*) AS cnt
                        FROM security_events
                        WHERE created_at >= (now() - interval :hours)
                        GROUP BY event_type, identifier, severity, ip_address
                        ORDER BY cnt DESC, created_at DESC
                        LIMIT 50
                        """
                    ),
                    {"hours": f"{int(hours)} hours"},
                ).fetchall()
                return [
                    {
                        "event_type": r[0],
                        "identifier": r[1],
                        "details": r[2],
                        "severity": r[3],
                        "ip_address": r[4],
                        "created_at": r[5],
                        "count": r[6],
                    }
                    for r in rows
                ]
        except Exception:
            logger.error("Error fetching security alerts from Postgres", exc_info=True)
            return []


# Global auth manager instance
admin_auth_manager = AdminAuthManager()


def require_admin_auth(request: Request) -> Dict:
    """Dependency to require authentication for admin routes."""
    session = admin_auth_manager.get_session_from_request(request)
    if not session:
        logger.warning(f"Unauthenticated admin request from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_admin_role(request: Request) -> Dict:
    """Dependency to require admin role for routes with logging."""
    session = require_admin_auth(request)
    if session["role"] not in ["admin", "owner"]:
        logger.warning(f"Unauthorized admin access attempt by user {session.get('username', 'unknown')}")
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return session


def get_current_admin_user(request: Request) -> Optional[Dict]:
    """Get current admin user from request if authenticated, None otherwise."""
    try:
        return admin_auth_manager.get_session_from_request(request)
    except Exception:
        logger.error("Error getting current admin user", exc_info=True)
        return None
