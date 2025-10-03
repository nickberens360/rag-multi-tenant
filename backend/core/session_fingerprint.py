"""
Session fingerprinting service to detect session hijacking and suspicious activity.
Creates unique fingerprints based on browser and network characteristics.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .audit_logger import AuditAction, audit_logger
from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class SessionFingerprinter:
    """
    Creates and validates session fingerprints to detect hijacking.

    Features:
    - Browser fingerprinting based on User-Agent
    - Network fingerprinting based on IP characteristics
    - Fingerprint validation and change detection
    - Risk assessment for fingerprint changes
    - Session hijacking alerts
    """

    def __init__(self):
        """Initialize session fingerprinter."""
        self.suspicious_changes = [
            "user_agent_family_change",
            "operating_system_change",
            "ip_network_change",
            "timezone_change",
            "screen_resolution_change",
        ]

    def create_fingerprint(
        self, ip_address: str, user_agent: str, additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a session fingerprint from request characteristics.

        Args:
            ip_address: Client IP address
            user_agent: User agent string
            additional_headers: Optional additional headers for fingerprinting

        Returns:
            Dict containing fingerprint data
        """
        try:
            # Parse user agent for key characteristics
            ua_info = self._parse_user_agent(user_agent)

            # Analyze IP address
            ip_info = self._analyze_ip(ip_address)

            # Extract additional characteristics
            extras = self._extract_additional_characteristics(additional_headers or {})

            # Create fingerprint components
            fingerprint_data = {
                "browser_family": ua_info["browser_family"],
                "browser_version_major": ua_info["version_major"],
                "os_family": ua_info["os_family"],
                "os_version": ua_info["os_version"],
                "ip_network": ip_info["network_class"],
                "ip_type": ip_info["ip_type"],
                "accept_language": extras.get("accept_language"),
                "accept_encoding": extras.get("accept_encoding"),
                "created_at": datetime.now().isoformat(),
            }

            # Generate hash fingerprint
            fingerprint_hash = self._generate_fingerprint_hash(fingerprint_data)

            return {
                "fingerprint_hash": fingerprint_hash,
                "fingerprint_data": fingerprint_data,
                "risk_level": "low",  # New fingerprints start as low risk
            }

        except Exception as e:
            logger.error(f"Error creating session fingerprint: {str(e)}", exc_info=True)
            return {"fingerprint_hash": "error", "fingerprint_data": {}, "risk_level": "high", "error": str(e)}

    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """Parse user agent string for key characteristics."""
        if not user_agent:
            return {
                "browser_family": "unknown",
                "version_major": "unknown",
                "os_family": "unknown",
                "os_version": "unknown",
            }

        ua_lower = user_agent.lower()

        # Browser detection
        browser_family = "unknown"
        version_major = "unknown"

        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser_family = "Chrome"
            # Extract version
            if "chrome/" in ua_lower:
                try:
                    version_part = ua_lower.split("chrome/")[1].split()[0]
                    version_major = version_part.split(".")[0]
                except (IndexError, ValueError):
                    pass
        elif "firefox" in ua_lower:
            browser_family = "Firefox"
            if "firefox/" in ua_lower:
                try:
                    version_part = ua_lower.split("firefox/")[1].split()[0]
                    version_major = version_part.split(".")[0]
                except (IndexError, ValueError):
                    pass
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser_family = "Safari"
        elif "edg" in ua_lower:
            browser_family = "Edge"

        # OS detection
        os_family = "unknown"
        os_version = "unknown"

        if "windows nt" in ua_lower:
            os_family = "Windows"
            if "windows nt 10.0" in ua_lower:
                os_version = "10"
            elif "windows nt 6.3" in ua_lower:
                os_version = "8.1"
            elif "windows nt 6.1" in ua_lower:
                os_version = "7"
        elif "mac os x" in ua_lower or "macos" in ua_lower:
            os_family = "macOS"
        elif "linux" in ua_lower:
            os_family = "Linux"
        elif "android" in ua_lower:
            os_family = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            os_family = "iOS"

        return {
            "browser_family": browser_family,
            "version_major": version_major,
            "os_family": os_family,
            "os_version": os_version,
        }

    def _analyze_ip(self, ip_address: str) -> Dict[str, str]:
        """Analyze IP address characteristics."""
        if not ip_address or ip_address == "unknown":
            return {"network_class": "unknown", "ip_type": "unknown"}

        try:
            import ipaddress

            ip = ipaddress.ip_address(ip_address)

            if ip.is_private:
                network_class = "private"
                ip_type = "private"
            elif ip.is_loopback:
                network_class = "loopback"
                ip_type = "loopback"
            else:
                # Classify by first octet for IPv4
                if isinstance(ip, ipaddress.IPv4Address):
                    first_octet = int(str(ip).split(".")[0])
                    if 1 <= first_octet <= 126:
                        network_class = "class_a"
                    elif 128 <= first_octet <= 191:
                        network_class = "class_b"
                    elif 192 <= first_octet <= 223:
                        network_class = "class_c"
                    else:
                        network_class = "other"
                else:
                    network_class = "ipv6"

                ip_type = "public"

            return {"network_class": network_class, "ip_type": ip_type}

        except ValueError:
            return {"network_class": "invalid", "ip_type": "invalid"}

    def _extract_additional_characteristics(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Extract additional characteristics from headers."""
        characteristics = {}

        # Language preferences
        accept_language = headers.get("accept-language", headers.get("Accept-Language", ""))
        if accept_language:
            # Take first language preference
            characteristics["accept_language"] = accept_language.split(",")[0].split(";")[0].strip()

        # Encoding preferences
        accept_encoding = headers.get("accept-encoding", headers.get("Accept-Encoding", ""))
        if accept_encoding:
            characteristics["accept_encoding"] = accept_encoding

        return characteristics

    def _generate_fingerprint_hash(self, fingerprint_data: Dict[str, Any]) -> str:
        """Generate a hash from fingerprint data."""
        # Create stable string representation
        stable_data = {
            "browser_family": fingerprint_data.get("browser_family", ""),
            "browser_version_major": fingerprint_data.get("browser_version_major", ""),
            "os_family": fingerprint_data.get("os_family", ""),
            "os_version": fingerprint_data.get("os_version", ""),
            "ip_network": fingerprint_data.get("ip_network", ""),
            "ip_type": fingerprint_data.get("ip_type", ""),
            "accept_language": fingerprint_data.get("accept_language", ""),
            "accept_encoding": fingerprint_data.get("accept_encoding", ""),
        }

        # Sort keys for consistent hashing
        stable_json = json.dumps(stable_data, sort_keys=True)

        # Generate SHA-256 hash
        return hashlib.sha256(stable_json.encode()).hexdigest()[:16]  # First 16 chars for brevity

    def validate_fingerprint(
        self, current_fingerprint: Dict[str, Any], stored_fingerprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate current fingerprint against stored fingerprint.

        Returns:
            Dict containing validation results and risk assessment
        """
        if not stored_fingerprint or not current_fingerprint:
            return {
                "is_valid": True,
                "risk_level": "low",
                "changes": [],
                "reason": "No previous fingerprint to compare",
            }

        current_data = current_fingerprint.get("fingerprint_data", {})
        stored_data = stored_fingerprint.get("fingerprint_data", {})

        changes = []
        risk_level = "low"

        # Check for specific changes
        if current_data.get("browser_family") != stored_data.get("browser_family"):
            changes.append("browser_family_change")

        if current_data.get("os_family") != stored_data.get("os_family"):
            changes.append("operating_system_change")

        if current_data.get("ip_network") != stored_data.get("ip_network"):
            changes.append("ip_network_change")

        if current_data.get("accept_language") != stored_data.get("accept_language"):
            changes.append("language_change")

        # Assess risk level based on changes
        suspicious_change_count = sum(1 for change in changes if change in self.suspicious_changes)

        if suspicious_change_count >= 2:
            risk_level = "high"
        elif suspicious_change_count == 1:
            risk_level = "medium"
        elif len(changes) > 0:
            risk_level = "low"

        # Fingerprint hash comparison
        hash_match = current_fingerprint.get("fingerprint_hash") == stored_fingerprint.get("fingerprint_hash")

        return {
            "is_valid": risk_level != "high",
            "risk_level": risk_level,
            "changes": changes,
            "hash_match": hash_match,
            "reason": self._generate_validation_reason(changes, risk_level),
        }

    def _generate_validation_reason(self, changes: List[str], risk_level: str) -> str:
        """Generate human-readable reason for validation result."""
        if not changes:
            return "Session fingerprint unchanged"

        change_descriptions = {
            "browser_family_change": "browser changed",
            "operating_system_change": "operating system changed",
            "ip_network_change": "network changed",
            "language_change": "language preferences changed",
        }

        change_list = [change_descriptions.get(change, change) for change in changes[:3]]
        reason = f"Session changes detected: {', '.join(change_list)}"

        if len(changes) > 3:
            reason += f" and {len(changes) - 3} more"

        if risk_level == "high":
            reason += " - possible session hijacking"
        elif risk_level == "medium":
            reason += " - suspicious activity"

        return reason

    def store_session_fingerprint(self, session_id: str, fingerprint: Dict[str, Any]) -> bool:
        """Store session fingerprint in database."""
        try:
            # Short-circuit during local debugging to avoid DB contention
            if os.getenv("FAST_LOGIN_MODE", "false").lower() in {"1", "true", "yes"}:
                return True
            fingerprint_json = json.dumps(fingerprint)

            with get_db_session_sync() as session:
                if session is not None:
                    session.execute(
                        text(
                            """
                            INSERT INTO security_events (event_type, identifier, details, severity, created_at)
                            VALUES ('session_fingerprint_stored', :id, :details, 'low', now())
                            """
                        ),
                        {"id": session_id, "details": fingerprint_json},
                    )

            return True

        except Exception as e:
            logger.error(f"Error storing session fingerprint: {str(e)}", exc_info=True)
            return False

    def get_session_fingerprint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored session fingerprint."""
        try:
            if os.getenv("FAST_LOGIN_MODE", "false").lower() in {"1", "true", "yes"}:
                return None
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        """
                        SELECT details FROM security_events
                        WHERE event_type = 'session_fingerprint_stored' AND identifier = :id
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {"id": session_id},
                ).first()
                if row and row[0]:
                    return json.loads(row[0])
                return None

        except Exception as e:
            logger.error(f"Error retrieving session fingerprint: {str(e)}", exc_info=True)
            return None

    def monitor_session_fingerprint(
        self,
        session_id: str,
        username: str,
        ip_address: str,
        user_agent: str,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Monitor session fingerprint for changes and detect potential hijacking.

        Returns:
            Dict containing monitoring results and actions taken
        """
        try:
            if os.getenv("FAST_LOGIN_MODE", "false").lower() in {"1", "true", "yes"}:
                return {
                    "session_id": session_id,
                    "current_fingerprint": {},
                    "validation_result": {"risk_level": "low", "reason": "fast_mode", "is_valid": True},
                    "action_taken": "skipped",
                }
            # Create current fingerprint
            current_fingerprint = self.create_fingerprint(ip_address, user_agent, additional_headers)

            # Get stored fingerprint
            stored_fingerprint = self.get_session_fingerprint(session_id)

            # Validate fingerprint
            validation_result = self.validate_fingerprint(current_fingerprint, stored_fingerprint)

            # Log if suspicious
            if validation_result["risk_level"] in ["medium", "high"]:
                audit_logger.log_action(
                    AuditAction.SECURITY_SCAN,
                    username,
                    details={
                        "event": f"session_fingerprint_{validation_result['risk_level']}_risk",
                        "reason": validation_result["reason"],
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                logger.warning(
                    f"Suspicious session fingerprint change for user {username}: {validation_result['reason']}"
                )

            # Update stored fingerprint if this is a new session or low-risk change
            if not stored_fingerprint or validation_result["risk_level"] == "low":
                self.store_session_fingerprint(session_id, current_fingerprint)

            return {
                "session_id": session_id,
                "current_fingerprint": current_fingerprint,
                "validation_result": validation_result,
                "action_taken": "fingerprint_updated" if validation_result["risk_level"] == "low" else "alert_logged",
            }

        except Exception as e:
            logger.error(f"Error monitoring session fingerprint: {str(e)}", exc_info=True)
            return {"session_id": session_id, "error": str(e), "action_taken": "error_logged"}


# Global instance
session_fingerprinter = SessionFingerprinter()
