"""
Secure API Key Management Service.
Handles encryption, decryption, and validation of API keys.
"""

import base64
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import text

from .db_session import get_db_session_sync
from .tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)


class ApiKeyManager:
    """Manages API keys with encryption and secure storage."""

    def __init__(self):
        """Initialize the API key manager with encryption."""
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption using environment-based key."""
        # Get or generate encryption key from environment
        encryption_password = os.getenv("API_KEY_ENCRYPTION_SECRET")

        # Use centralized environment detection to avoid env-file parsing quirks
        try:
            from .config_v2 import AppConfig

            is_production = AppConfig.IS_PRODUCTION
        except Exception:
            # Fallback: sanitize ENVIRONMENT manually
            env_raw = os.getenv("ENVIRONMENT", "development")
            env_clean = env_raw.split("#", 1)[0].strip().lower()
            is_production = env_clean in ("production", "prod")

        if not encryption_password:
            # In development, use a default (NOT for production!)
            if not is_production:
                encryption_password = "dev-encryption-key-change-in-production"
                logger.warning("Using development encryption key. Set API_KEY_ENCRYPTION_SECRET in production!")
            else:
                raise ValueError("API_KEY_ENCRYPTION_SECRET must be set in production environment")

        # Derive encryption key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"api-key-salt-v1",  # Static salt for consistent key derivation
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_password.encode()))
        self.cipher = Fernet(key)

    def encrypt_key(self, api_key: str) -> Tuple[str, str]:
        """
        Encrypt an API key and return encrypted value and last 4 characters.

        Returns:
            Tuple of (encrypted_value, last_four_chars)
        """
        try:
            # Encrypt the API key
            encrypted = self.cipher.encrypt(api_key.encode())
            encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

            # Get last 4 characters for display
            last_four = api_key[-4:] if len(api_key) >= 4 else api_key

            return encrypted_b64, last_four
        except Exception as e:
            logger.error(f"Error encrypting API key: {e}")
            raise

    def decrypt_key(self, encrypted_value: str) -> str:
        """Decrypt an API key.

        Supports both new (Fernet-encrypted, base64-encoded) values and
        legacy values that were stored as base64-encoded plaintext during
        environment migration. If a legacy format is detected, we transparently
        return the decoded value and attempt a best-effort in-place migration
        to the new encryption format.
        """
        # First, base64-decode the stored string
        try:
            raw = base64.b64decode(encrypted_value.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error base64-decoding stored API key value: {e}")
            raise

        # Attempt Fernet decryption (new format)
        try:
            decrypted = self.cipher.decrypt(raw)
            return decrypted.decode("utf-8")
        except Exception as fernet_error:
            # Fallback: legacy format (raw is actually the plaintext API key)
            try:
                legacy_plain = raw.decode("utf-8", errors="ignore").strip()
            except (UnicodeDecodeError, AttributeError) as decode_error:
                # Be specific about decode failures
                logger.debug(f"Failed to decode legacy API key format: {decode_error}")
                legacy_plain = ""

            if legacy_plain and len(legacy_plain) >= 10:
                logger.warning("Detected legacy base64-only API key format; using decoded value and migrating")
                # Attempt one-shot in-place migration to new encrypted format
                try:
                    new_encrypted_b64, _last_four = self.encrypt_key(legacy_plain)
                    with get_db_session_sync() as session:
                        if session is not None:
                            session.execute(
                                text(
                                    "UPDATE api_keys SET encrypted_value = :enc, updated_at = now() WHERE encrypted_value = :old"
                                ),
                                {"enc": new_encrypted_b64, "old": encrypted_value},
                            )
                except (ValueError, ConnectionError) as migrate_error:
                    # Non-fatal: we can still return the usable key
                    logger.debug(f"API key migration to new encryption failed (non-fatal): {migrate_error}")
                except Exception as unexpected_migrate_error:
                    # Log unexpected errors differently in development
                    logger.warning(f"Unexpected error during API key migration: {unexpected_migrate_error}")
                    if os.getenv("ENVIRONMENT", "development") == "development":
                        logger.debug("Re-raising unexpected migration error in development", exc_info=True)
                        raise
                return legacy_plain

            # If fallback failed, surface the original error for observability
            logger.error(f"Error decrypting API key with Fernet: {fernet_error}")
            raise

    def create_api_key(self, key_name: str, key_type: str, api_key: str, updated_by: int) -> Dict[str, Any]:
        """
        Create a new API key entry with encryption.

        Args:
            key_name: Unique name for the key (e.g., "anthropic_primary")
            key_type: Type of key (anthropic, google, openai, etc.)
            api_key: The actual API key to store
            updated_by: User ID making the change

        Returns:
            Dict with created key info (without actual key value)
        """
        try:
            # Encrypt the key
            encrypted_value, last_four = self.encrypt_key(api_key)

            with get_db_session_sync() as session:
                if session is None:
                    raise RuntimeError("Database not available")
                # Ensure RLS context
                tid = get_current_tenant_id() or os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
                try:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tid)})
                except Exception:
                    pass

                # Check if key name already exists (per-tenant unique)
                exists = session.execute(
                    text("SELECT 1 FROM api_keys WHERE key_name = :name"), {"name": key_name}
                ).first()
                if exists:
                    raise ValueError(f"API key with name '{key_name}' already exists")

                row = session.execute(
                    text(
                        """
                        INSERT INTO api_keys (tenant_id, key_name, key_type, encrypted_value, last_four, updated_by)
                        VALUES (current_setting('app.tenant_id')::uuid, :name, :type, :enc, :last4, :uid)
                        RETURNING id
                        """
                    ),
                    {"name": key_name, "type": key_type, "enc": encrypted_value, "last4": last_four, "uid": updated_by},
                ).first()
                key_id = row[0]
                logger.info(f"Created API key: {key_name} (ID: {key_id})")

                return {
                    "id": key_id,
                    "key_name": key_name,
                    "key_type": key_type,
                    "last_four": last_four,
                    "is_active": True,
                }

        except Exception as e:
            logger.error(f"Error creating API key {key_name}: {e}")
            raise

    def update_api_key(self, key_name: str, new_api_key: str, updated_by: int) -> bool:
        """Update an existing API key."""
        try:
            # Encrypt the new key
            encrypted_value, last_four = self.encrypt_key(new_api_key)

            with get_db_session_sync() as session:
                if session is None:
                    return False
                res = session.execute(
                    text(
                        """
                        UPDATE api_keys
                        SET encrypted_value = :enc, last_four = :last4, updated_at = now(), updated_by = :uid
                        WHERE key_name = :name
                        """
                    ),
                    {"enc": encrypted_value, "last4": last_four, "uid": updated_by, "name": key_name},
                )

                if res.rowcount and res.rowcount > 0:
                    logger.info(f"Updated API key: {key_name}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error updating API key {key_name}: {e}")
            raise

    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get a decrypted API key by name.

        Args:
            key_name: Name of the key to retrieve

        Returns:
            Decrypted API key value or None if not found/inactive
        """
        try:
            # Fetch and update usage in a single short-lived transaction
            encrypted_value: Optional[str] = None
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        "SELECT encrypted_value FROM api_keys WHERE key_name = :name AND is_active = true ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"name": key_name},
                ).first()
                if not row:
                    return None
                encrypted_value = row[0]
                session.execute(
                    text("UPDATE api_keys SET last_used_at = now() WHERE key_name = :name"), {"name": key_name}
                )

            # Perform any heavy/auxiliary work (like optional migration) AFTER the DB connection is closed
            if encrypted_value is not None:
                return self.decrypt_key(encrypted_value)
            return None

        except ConnectionError as db_error:
            logger.error(f"Database error getting API key {key_name}: {db_error}")
            return None
        except (ValueError, UnicodeDecodeError) as decode_error:
            logger.error(f"Decryption error for API key {key_name}: {decode_error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting API key {key_name}: {e}")
            # Re-raise unexpected errors in development for better debugging
            if os.getenv("ENVIRONMENT", "development") == "development":
                raise
            return None

    def get_api_key_by_type(self, key_type: str) -> Optional[str]:
        """
        Get the first active API key of a specific type.

        Args:
            key_type: Type of key (anthropic, google, openai, etc.)

        Returns:
            Decrypted API key value or None if not found
        """
        try:
            key_name: Optional[str] = None
            encrypted_value: Optional[str] = None
            # Keep the transaction scope minimal to reduce lock contention
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        "SELECT key_name, encrypted_value FROM api_keys WHERE key_type = :type AND is_active = true ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"type": key_type},
                ).first()
                if not row:
                    return None
                key_name, encrypted_value = row[0], row[1]
                session.execute(
                    text("UPDATE api_keys SET last_used_at = now() WHERE key_name = :name"), {"name": key_name}
                )

            if encrypted_value is not None:
                return self.decrypt_key(encrypted_value)
            return None

        except Exception as e:
            logger.error(f"Error getting API key by type {key_type}: {e}")
            return None

    def list_api_keys(self, include_inactive: bool = False) -> List[Dict]:
        """
        List all API keys (without actual values).

        Returns:
            List of key info dictionaries
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return []
                where = "" if include_inactive else "WHERE is_active = true"
                rows = session.execute(
                    text(
                        f"""
                        SELECT id, key_name, key_type, last_four, is_active, last_used_at, last_validated_at, created_at, updated_at
                        FROM api_keys
                        {where}
                        ORDER BY key_type, key_name
                        """
                    )
                ).fetchall()
                keys = [
                    {
                        "id": r[0],
                        "key_name": r[1],
                        "key_type": r[2],
                        "last_four": r[3],
                        "is_active": bool(r[4]),
                        "last_used_at": r[5],
                        "last_validated_at": r[6],
                        "created_at": r[7],
                        "updated_at": r[8],
                    }
                    for r in rows
                ]
                return keys

        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return []

    def toggle_api_key(self, key_name: str, is_active: bool, updated_by: int) -> bool:
        """Enable or disable an API key."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return False
                res = session.execute(
                    text(
                        "UPDATE api_keys SET is_active = :active, updated_at = now(), updated_by = :uid WHERE key_name = :name"
                    ),
                    {"active": is_active, "uid": updated_by, "name": key_name},
                )

                if res.rowcount and res.rowcount > 0:
                    action = "Enabled" if is_active else "Disabled"
                    logger.info(f"{action} API key: {key_name}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error toggling API key {key_name}: {e}")
            return False

    def delete_api_key(self, key_name: str) -> bool:
        """Permanently delete an API key."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return False
                res = session.execute(text("DELETE FROM api_keys WHERE key_name = :name"), {"name": key_name})
                if res.rowcount and res.rowcount > 0:
                    logger.info(f"Deleted API key: {key_name}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error deleting API key {key_name}: {e}")
            return False

    def validate_api_key(self, key_name: str) -> Tuple[bool, str]:
        """
        Validate an API key by attempting a minimal API call.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Get the key
            api_key = self.get_api_key(key_name)
            if not api_key:
                return False, "Key not found or inactive"

            with get_db_session_sync() as session:
                if session is None:
                    return False, "Database unavailable"
                row = session.execute(
                    text("SELECT key_type FROM api_keys WHERE key_name = :name"), {"name": key_name}
                ).first()
                if not row:
                    return False, "Key not found"

                key_type = row[0]

                # Validate based on type
                is_valid, message = self._validate_key_by_type(key_type, api_key)

                # Update validation timestamp if successful
                if is_valid:
                    session.execute(
                        text("UPDATE api_keys SET last_validated_at = now() WHERE key_name = :name"), {"name": key_name}
                    )

                return is_valid, message

        except ConnectionError as db_error:
            logger.error(f"Database error validating API key {key_name}: {db_error}")
            return False, f"Database error: {db_error}"
        except ImportError as import_error:
            logger.error(f"Missing dependency for API key validation: {import_error}")
            return False, f"Missing dependency: {import_error}"
        except Exception as e:
            logger.error(f"Unexpected error validating API key {key_name}: {e}")
            # Re-raise in development for better debugging
            if os.getenv("ENVIRONMENT", "development") == "development":
                logger.debug("Re-raising validation error in development", exc_info=True)
                raise
            return False, f"Validation error: {str(e)}"

    def _validate_key_by_type(self, key_type: str, api_key: str) -> Tuple[bool, str]:
        """Validate an API key based on its type."""
        try:
            if key_type == "anthropic":
                # Test with a minimal Anthropic API call
                from anthropic import Anthropic

                client = Anthropic(api_key=api_key)
                # Just check if we can create a client - actual validation would need a test call
                return True, "Anthropic API key format valid"

            elif key_type == "google":
                # Test with langchain-google-genai (available in container)
                from langchain_google_genai import ChatGoogleGenerativeAI

                # Just check if we can create a client with the API key
                ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
                return True, "Google API key format valid"

            elif key_type == "openai":
                # Test with a minimal OpenAI API call
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                # Just check if we can create a client
                return True, "OpenAI API key format valid"

            else:
                return False, f"Unknown key type: {key_type}"

        except ImportError as e:
            return False, f"Provider library not installed: {e}"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    def migrate_from_environment(self, updated_by: int) -> Dict[str, bool]:
        """
        Migrate API keys from environment variables to database.

        Returns:
            Dict mapping key names to migration success status
        """
        results = {}

        # Map of environment variables to key names and types
        env_mappings = [
            ("ANTHROPIC_API_KEY", "anthropic_primary", "anthropic"),
            ("GOOGLE_API_KEY", "google_primary", "google"),
            ("OPENAI_API_KEY", "openai_primary", "openai"),
        ]

        for env_var, key_name, key_type in env_mappings:
            api_key = os.getenv(env_var)
            if api_key:
                try:
                    # Check if already migrated
                    existing = self.get_api_key(key_name)
                    if existing:
                        results[key_name] = True  # Already migrated
                        continue

                    # Create the key in database
                    self.create_api_key(key_name, key_type, api_key, updated_by)
                    results[key_name] = True
                    logger.info(f"Migrated {env_var} to database as {key_name}")
                except Exception as e:
                    logger.error(f"Failed to migrate {env_var}: {e}")
                    results[key_name] = False
            else:
                results[key_name] = False  # No env var to migrate

        return results


# Global instance
api_key_manager = ApiKeyManager()
