"""
IP Geolocation validation service for detecting unusual login locations.
Provides basic geolocation checking without external API dependencies.
"""

import ipaddress
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import text

from .audit_logger import AuditAction, audit_logger
from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class GeolocationValidator:
    """
    Validates IP addresses for unusual login locations.

    Features:
    - Basic geolocation validation using IP ranges
    - Login location history tracking
    - Unusual location detection
    - Security event logging
    """

    def __init__(self):
        """Initialize the geolocation validator."""
        self._known_ranges = self._load_known_ranges()

    def _load_known_ranges(self) -> Dict:
        """Load known IP ranges for basic geolocation."""
        # Basic IP range mappings for common cloud providers and geographic regions
        # In production, this could be expanded with a proper GeoIP database
        return {
            "cloud_providers": {
                "aws": [
                    "3.0.0.0/8",
                    "13.0.0.0/8",
                    "15.0.0.0/8",
                    "18.0.0.0/8",
                    "52.0.0.0/8",
                    "54.0.0.0/8",
                    "35.0.0.0/8",
                ],
                "gcp": ["34.0.0.0/8", "35.0.0.0/8", "130.211.0.0/16", "104.196.0.0/14"],
                "azure": ["13.0.0.0/8", "40.0.0.0/8", "52.0.0.0/8", "104.0.0.0/8"],
            },
            "local_networks": ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"],
            "tor_exit_nodes": [
                # This would be populated with known Tor exit node ranges
                # For now, just a placeholder
            ],
        }

    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP address is private/local."""
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private or ip.is_loopback
        except ValueError:
            return False

    def _classify_ip(self, ip_address: str) -> Dict[str, Any]:
        """Classify IP address by type and origin."""
        if self._is_private_ip(ip_address):
            return {"type": "private", "provider": "local", "risk_level": "low", "description": "Private/Local network"}

        try:
            ip = ipaddress.ip_address(ip_address)

            # Check cloud providers
            for provider, ranges in self._known_ranges["cloud_providers"].items():
                for range_str in ranges:
                    try:
                        if ip in ipaddress.ip_network(range_str, strict=False):
                            return {
                                "type": "cloud",
                                "provider": provider.upper(),
                                "risk_level": "medium",
                                "description": f"{provider.upper()} cloud infrastructure",
                            }
                    except ValueError:
                        continue

            # Default classification for public IPs
            return {
                "type": "public",
                "provider": "unknown",
                "risk_level": "medium",
                "description": "Public internet address",
            }

        except ValueError:
            return {
                "type": "invalid",
                "provider": "unknown",
                "risk_level": "high",
                "description": "Invalid IP address format",
            }

    def validate_login_location(
        self, username: str, ip_address: str, user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate login location and detect unusual activity.

        Args:
            username: Username attempting login
            ip_address: IP address of login attempt
            user_agent: User agent string

        Returns:
            Dict containing validation results and risk assessment
        """
        if not ip_address or ip_address == "unknown":
            return {
                "is_unusual": False,
                "risk_level": "low",
                "reason": "Unknown IP address - likely local development",
                "action": "allow",
            }

        # Classify the IP address
        ip_info = self._classify_ip(ip_address)

        # Get login history for this user
        login_history = self._get_user_login_history(username)

        # Analyze if this location is unusual
        is_unusual, risk_factors = self._analyze_location_risk(ip_address, ip_info, login_history)

        # Determine action based on risk level
        risk_level = self._calculate_risk_level(ip_info, risk_factors, is_unusual)
        action = self._determine_action(risk_level, is_unusual)

        result = {
            "is_unusual": is_unusual,
            "risk_level": risk_level,
            "ip_info": ip_info,
            "risk_factors": risk_factors,
            "action": action,
            "reason": self._generate_reason(is_unusual, risk_factors, ip_info),
        }

        # Log security event if unusual
        if is_unusual or risk_level == "high":
            audit_logger.log_action(
                AuditAction.SECURITY_SCAN,
                username,
                details={
                    "event": "unusual_login_location" if is_unusual else "high_risk_login",
                    "reason": result["reason"],
                },
                ip_address=ip_address,
                user_agent=user_agent or "",
            )

        # Record this login location
        self._record_login_location(username, ip_address, ip_info)

        return result

    def _get_user_login_history(self, username: str, days: int = 30) -> list:
        """Get recent login history for a user."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return []
                rows = session.execute(
                    text(
                        """
                        SELECT s.ip_address,
                               MAX(s.started_at) AS last_seen,
                               COUNT(*) AS login_count
                        FROM admin_sessions s
                        JOIN admin_users u ON s.user_id = u.id
                        WHERE u.username = :un
                          AND s.started_at > (now() - make_interval(days => :days))
                          AND s.ip_address IS NOT NULL
                        GROUP BY s.ip_address
                        ORDER BY last_seen DESC
                        LIMIT 50
                        """
                    ),
                    {"un": username, "days": int(days)},
                ).fetchall()

                return [
                    {"ip": row[0], "last_seen": row[1].isoformat() if row[1] else None, "count": row[2]} for row in rows
                ]

        except Exception as e:
            logger.error(f"Error getting login history for {username}: {str(e)}")
            return []

    def _analyze_location_risk(self, ip_address: str, ip_info: Dict, login_history: list) -> Tuple[bool, list]:
        """Analyze if this login location poses a risk."""
        risk_factors = []
        is_unusual = False

        # Check if IP has been used before
        known_ips = [entry["ip"] for entry in login_history]
        if ip_address not in known_ips:
            is_unusual = True
            risk_factors.append("new_ip_address")

        # Check if it's been a long time since last use
        for entry in login_history:
            if entry["ip"] == ip_address:
                try:
                    last_seen = datetime.fromisoformat(entry["last_seen"]) if entry["last_seen"] else None
                except Exception:
                    last_seen = None
                if last_seen is not None:
                    # Normalize to timezone-aware UTC for safe arithmetic
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    days_ago = (now_utc - last_seen).days
                    if days_ago > 90:
                        risk_factors.append("long_time_since_last_use")
                break

        # Check for rapid location changes
        if len(login_history) > 0:
            recent_ips = [entry["ip"] for entry in login_history[:5]]
            unique_recent_ips = set(recent_ips)
            if len(unique_recent_ips) > 3:
                risk_factors.append("frequent_ip_changes")

        # Check IP reputation
        if ip_info["risk_level"] == "high":
            risk_factors.append("high_risk_ip")
            is_unusual = True

        # Check for cloud/VPN usage if user typically uses direct connections
        if ip_info["type"] == "cloud":
            direct_connections = [
                entry for entry in login_history if not self._classify_ip(entry["ip"])["type"] == "cloud"
            ]
            if len(direct_connections) > len(login_history) * 0.8:  # 80% direct connections
                risk_factors.append("unusual_cloud_usage")

        return is_unusual, risk_factors

    def _calculate_risk_level(self, ip_info: Dict, risk_factors: list, is_unusual: bool) -> str:
        """Calculate overall risk level."""
        if "high_risk_ip" in risk_factors or ip_info["risk_level"] == "high":
            return "high"

        risk_score = 0
        risk_score += len(risk_factors)
        risk_score += 2 if is_unusual else 0
        risk_score += 1 if ip_info["type"] == "cloud" else 0

        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"

    def _determine_action(self, risk_level: str, is_unusual: bool) -> str:
        """Determine what action to take."""
        if risk_level == "high":
            return "block"  # In production, might require additional verification
        elif risk_level == "medium" and is_unusual:
            return "warn"  # Log and potentially notify user
        else:
            return "allow"

    def _generate_reason(self, is_unusual: bool, risk_factors: list, ip_info: Dict) -> str:
        """Generate human-readable reason for the decision."""
        if not is_unusual and not risk_factors:
            return "Normal login from known location"

        reasons = []
        if is_unusual:
            reasons.append("new location")

        if "frequent_ip_changes" in risk_factors:
            reasons.append("frequent location changes")
        if "long_time_since_last_use" in risk_factors:
            reasons.append("long time since last use from this location")
        if "high_risk_ip" in risk_factors:
            reasons.append("high-risk IP address")
        if "unusual_cloud_usage" in risk_factors:
            reasons.append("unusual cloud/VPN usage pattern")

        return f"Login from {ip_info['description']}: {', '.join(reasons)}"

    def _record_login_location(self, username: str, ip_address: str, ip_info: Dict) -> None:
        """Record this login location for future reference."""
        try:
            location_data = {
                "ip": ip_address,
                "type": ip_info["type"],
                "provider": ip_info["provider"],
                "classification": ip_info["description"],
                # Record timestamps as ISO8601 UTC to avoid naive/aware mixing
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            audit_logger.log_action(
                AuditAction.SECURITY_SCAN,
                username,
                details={"event": "login_location_recorded", **location_data},
                ip_address=ip_address,
            )

        except Exception as e:
            logger.error(f"Error recording login location: {str(e)}")

    def get_user_location_summary(self, username: str, days: int = 30) -> Dict:
        """Get summary of user's login locations."""
        try:
            login_history = self._get_user_login_history(username, days)

            if not login_history:
                return {"total_locations": 0, "locations": []}

            locations = []
            for entry in login_history:
                ip_info = self._classify_ip(entry["ip"])
                locations.append(
                    {
                        "ip": entry["ip"],
                        "type": ip_info["type"],
                        "provider": ip_info["provider"],
                        "description": ip_info["description"],
                        "last_seen": entry["last_seen"],
                        "login_count": entry["count"],
                    }
                )

            return {
                "total_locations": len(locations),
                "locations": locations,
                "unique_types": list(set([loc["type"] for loc in locations])),
                "risk_assessment": self._assess_location_pattern(locations),
            }

        except Exception as e:
            logger.error(f"Error getting location summary for {username}: {str(e)}")
            return {"total_locations": 0, "locations": [], "error": str(e)}

    def _assess_location_pattern(self, locations: list) -> Dict:
        """Assess overall risk pattern of user's locations."""
        if not locations:
            return {"risk_level": "unknown", "notes": "No location data available"}

        # Analyze patterns
        cloud_usage = sum(1 for loc in locations if loc["type"] == "cloud")
        private_usage = sum(1 for loc in locations if loc["type"] == "private")
        total = len(locations)

        notes = []
        risk_level = "low"

        if cloud_usage / total > 0.5:
            notes.append("Frequent cloud/VPN usage")
            risk_level = "medium"

        if total > 10:
            notes.append("Many different locations")
            risk_level = "medium"

        if private_usage / total > 0.8:
            notes.append("Primarily local network usage")

        return {
            "risk_level": risk_level,
            "notes": "; ".join(notes) if notes else "Normal usage pattern",
            "cloud_usage_percent": round((cloud_usage / total) * 100, 1),
            "private_usage_percent": round((private_usage / total) * 100, 1),
        }


# Global instance
geo_validator = GeolocationValidator()
