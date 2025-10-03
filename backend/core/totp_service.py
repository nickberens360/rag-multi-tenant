"""
TOTP (Time-based One-Time Password) service for two-factor authentication.
Provides secure 2FA implementation without external dependencies.
"""

import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time
from typing import Any, Dict, Optional
from urllib.parse import quote

from sqlalchemy import text

from .audit_logger import AuditAction, audit_logger
from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class TOTPService:
    """
    Time-based One-Time Password service for 2FA.

    Features:
    - TOTP code generation and validation
    - Secret key management
    - QR code URL generation
    - Backup code generation
    - 2FA enrollment and verification
    """

    def __init__(self):
        """Initialize TOTP service."""
        self.issuer = "Admin Dashboard"
        self.digits = 6
        self.period = 30  # 30 second validity window
        self.window = 1  # Allow 1 period before/after for clock drift

    def generate_secret(self) -> str:
        """Generate a new TOTP secret key."""
        # Generate 20 bytes (160 bits) of random data
        secret_bytes = secrets.token_bytes(20)
        # Encode as base32 for TOTP compatibility
        return base64.b32encode(secret_bytes).decode("ascii").rstrip("=")

    def generate_backup_codes(self, count: int = 8) -> list:
        """Generate backup codes for 2FA recovery."""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes

    def generate_qr_url(self, username: str, secret: str) -> str:
        """Generate QR code URL for TOTP setup."""
        # Format: otpauth://totp/Issuer:Username?secret=SECRET&issuer=ISSUER
        account_name = f"{self.issuer}:{username}"
        params = f"secret={secret}&issuer={quote(self.issuer)}&digits={self.digits}&period={self.period}"
        return f"otpauth://totp/{quote(account_name)}?{params}"

    def _hotp(self, secret: str, counter: int) -> int:
        """Generate HOTP value (RFC 4226)."""
        # Convert secret from base32
        key = base64.b32decode(secret + "=" * (8 - len(secret) % 8))

        # Convert counter to bytes
        counter_bytes = struct.pack(">Q", counter)

        # Generate HMAC-SHA1
        mac = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        # Dynamic truncation
        offset = mac[-1] & 0x0F
        binary = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF

        # Generate digits
        return binary % (10**self.digits)

    def generate_totp(self, secret: str, timestamp: Optional[int] = None) -> str:
        """Generate TOTP code for given secret and timestamp."""
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate time counter
        counter = timestamp // self.period

        # Generate HOTP
        hotp_value = self._hotp(secret, counter)

        # Format with leading zeros
        return f"{hotp_value:0{self.digits}d}"

    def verify_totp(self, secret: str, token: str, timestamp: Optional[int] = None) -> bool:
        """Verify TOTP token with time window tolerance."""
        if not token or len(token) != self.digits or not token.isdigit():
            return False

        if timestamp is None:
            timestamp = int(time.time())

        # Check current time and surrounding windows for clock drift
        for i in range(-self.window, self.window + 1):
            test_time = timestamp + (i * self.period)
            expected_token = self.generate_totp(secret, test_time)

            if hmac.compare_digest(token, expected_token):
                return True

        return False

    def enable_2fa_for_user(self, user_id: int, username: str) -> Dict[str, Any]:
        """Enable 2FA for a user and return setup information."""
        try:
            # Generate new secret and backup codes
            secret = self.generate_secret()
            backup_codes = self.generate_backup_codes()

            # Store in Postgres
            with get_db_session_sync() as session:
                if session is None:
                    return {"success": False, "error": "Database unavailable"}
                row = session.execute(text("SELECT 1 FROM user_2fa WHERE user_id = :uid"), {"uid": user_id}).first()
                if row:
                    session.execute(
                        text(
                            "UPDATE user_2fa SET secret = :sec, backup_codes = :codes, used_backup_codes = NULL, is_enabled = false, created_at = now(), verified_at = NULL WHERE user_id = :uid"
                        ),
                        {"sec": secret, "codes": ",".join(backup_codes), "uid": user_id},
                    )
                else:
                    session.execute(
                        text(
                            "INSERT INTO user_2fa (user_id, secret, backup_codes, is_enabled, created_at) VALUES (:uid, :sec, :codes, false, now())"
                        ),
                        {"uid": user_id, "sec": secret, "codes": ",".join(backup_codes)},
                    )

            # Generate QR code URL
            qr_url = self.generate_qr_url(username, secret)

            # Audit event
            audit_logger.log_action(
                AuditAction.TOTP_ENABLE,
                username,
                details={"event": "2fa_setup_initiated"},
            )

            return {
                "secret": secret,
                "qr_url": qr_url,
                "backup_codes": backup_codes,
                "manual_entry_key": secret,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error enabling 2FA for user {user_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def verify_and_enable_2fa(self, user_id: int, username: str, token: str) -> Dict[str, Any]:
        """Verify setup token and enable 2FA for user."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return {"success": False, "error": "Database unavailable"}
                row = session.execute(
                    text("SELECT secret, is_enabled FROM user_2fa WHERE user_id = :uid"), {"uid": user_id}
                ).first()

                if not row:
                    return {"success": False, "error": "2FA not set up for this user"}

                secret, is_enabled = row

                if is_enabled:
                    return {"success": False, "error": "2FA already enabled"}

                # Verify the token
                if not self.verify_totp(secret, token):
                    audit_logger.log_action(
                        AuditAction.TOTP_VERIFY,
                        username,
                        details={"event": "2fa_verification_failed_setup"},
                        success=False,
                        error_message="Invalid verification code",
                    )
                    return {"success": False, "error": "Invalid verification code"}

                # Enable 2FA
                session.execute(
                    text("UPDATE user_2fa SET is_enabled = true, verified_at = now() WHERE user_id = :uid"),
                    {"uid": user_id},
                )

                # Log successful setup
                audit_logger.log_action(
                    AuditAction.TOTP_ENABLE,
                    username,
                    details={"event": "2fa_enabled"},
                )

                return {"success": True, "message": "2FA enabled successfully"}

        except Exception as e:
            logger.error(f"Error verifying 2FA setup for user {user_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def verify_2fa_token(self, user_id: int, username: str, token: str, is_backup_code: bool = False) -> Dict[str, Any]:
        """Verify 2FA token for authentication."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return {"success": False, "error": "Database unavailable"}
                row = session.execute(
                    text(
                        "SELECT secret, backup_codes, is_enabled, used_backup_codes FROM user_2fa WHERE user_id = :uid"
                    ),
                    {"uid": user_id},
                ).first()

                if not row:
                    return {"success": False, "error": "2FA not set up"}

                secret, backup_codes_str, is_enabled, used_backup_codes_str = row

                if not is_enabled:
                    return {"success": False, "error": "2FA not enabled"}

                if is_backup_code:
                    # Verify backup code
                    backup_codes = backup_codes_str.split(",") if backup_codes_str else []
                    used_codes = used_backup_codes_str.split(",") if used_backup_codes_str else []

                    if token not in backup_codes:
                        audit_logger.log_action(
                            AuditAction.TOTP_VERIFY,
                            username,
                            details={"event": "invalid_backup_code"},
                            success=False,
                            error_message="invalid backup code",
                        )
                        return {"success": False, "error": "Invalid backup code"}

                    if token in used_codes:
                        audit_logger.log_action(
                            AuditAction.TOTP_VERIFY,
                            username,
                            details={"event": "reused_backup_code"},
                            success=False,
                            error_message="reused backup code",
                        )
                        return {"success": False, "error": "Backup code already used"}

                    # Mark backup code as used
                    used_codes.append(token)
                    session.execute(
                        text("UPDATE user_2fa SET used_backup_codes = :codes WHERE user_id = :uid"),
                        {"codes": ",".join(used_codes), "uid": user_id},
                    )

                    audit_logger.log_action(
                        AuditAction.BACKUP_CODE_USE,
                        username,
                        details={"event": "backup_code_used"},
                    )

                    return {"success": True, "message": "Backup code verified", "backup_code_used": True}

                else:
                    # Verify TOTP token
                    if not self.verify_totp(secret, token):
                        audit_logger.log_action(
                            AuditAction.TOTP_VERIFY,
                            username,
                            details={"event": "2fa_verification_failed"},
                            success=False,
                            error_message="invalid 2FA code",
                        )
                        return {"success": False, "error": "Invalid 2FA code"}

                    return {"success": True, "message": "2FA token verified"}

        except Exception as e:
            logger.error(f"Error verifying 2FA token for user {user_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def disable_2fa_for_user(self, user_id: int, username: str) -> Dict[str, Any]:
        """Disable 2FA for a user."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return {"success": False, "error": "Database unavailable"}
                row = session.execute(
                    text("SELECT is_enabled FROM user_2fa WHERE user_id = :uid"), {"uid": user_id}
                ).first()

                if not row or not row[0]:
                    return {"success": False, "error": "2FA not enabled"}

                # Disable 2FA
                session.execute(text("DELETE FROM user_2fa WHERE user_id = :uid"), {"uid": user_id})

                audit_logger.log_action(AuditAction.TOTP_DISABLE, username, details={"event": "2fa_disabled"})

                return {"success": True, "message": "2FA disabled successfully"}

        except Exception as e:
            logger.error(f"Error disabling 2FA for user {user_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_2fa_status(self, user_id: int) -> Dict[str, Any]:
        """Get 2FA status for a user."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return {"enabled": False, "setup_started": False}
                row = session.execute(
                    text(
                        "SELECT is_enabled, created_at, verified_at, backup_codes, used_backup_codes FROM user_2fa WHERE user_id = :uid"
                    ),
                    {"uid": user_id},
                ).first()

                if not row:
                    return {"enabled": False, "setup_started": False}

                is_enabled, created_at, verified_at, backup_codes_str, used_backup_codes_str = row

                # Count remaining backup codes
                backup_codes = backup_codes_str.split(",") if backup_codes_str else []
                used_codes = used_backup_codes_str.split(",") if used_backup_codes_str else []
                remaining_codes = len(backup_codes) - len([c for c in used_codes if c])

                return {
                    "enabled": bool(is_enabled),
                    "setup_started": True,
                    "created_at": created_at,
                    "verified_at": verified_at,
                    "backup_codes_remaining": remaining_codes,
                }

        except Exception as e:
            logger.error(f"Error getting 2FA status for user {user_id}: {str(e)}", exc_info=True)
            return {"enabled": False, "setup_started": False, "error": str(e)}


# Global instance
totp_service = TOTPService()
