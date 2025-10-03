"""
Configuration validation utilities for system health checks.

This module provides functionality to validate configuration completeness,
detect missing critical settings, and report configuration health status.
"""

import logging
import os
from typing import Any, Dict, List, Tuple

from .settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class ConfigurationValidator:
    """Validates system configuration completeness and health."""

    def __init__(self):
        self.settings_manager = get_settings_manager()

    def validate_critical_settings(self) -> Dict[str, Any]:
        """
        Validate critical system settings required for basic operation.

        Returns:
            Dictionary with validation results including:
            - critical_missing: List of missing critical settings
            - warnings: List of non-critical but recommended settings
            - overall_status: 'healthy', 'degraded', or 'critical'
            - recommendations: List of recommended actions
        """
        critical_missing = []
        warnings = []
        recommendations = []

        # Critical environment variables required for basic operation
        critical_env_vars = [
            ("ANTHROPIC_API_KEY", "Claude API access required for AI functionality"),
            ("ADMIN_DEFAULT_PASSWORD", "Admin authentication required for management"),
        ]

        # Recommended environment variables for full functionality
        recommended_env_vars = [
            ("GOOGLE_API_KEY", "Gemini API access for multi-model support"),
            ("PUBLIC_API_URL", "Public API URL for proper CORS and redirects"),
            ("IP_HASH_SALT", "IP anonymization for privacy compliance"),
        ]

        # Check critical environment variables
        for var_name, description in critical_env_vars:
            if not os.getenv(var_name):
                critical_missing.append(
                    {
                        "setting": var_name,
                        "type": "environment_variable",
                        "description": description,
                        "severity": "critical",
                    }
                )

        # Check recommended environment variables
        for var_name, description in recommended_env_vars:
            if not os.getenv(var_name):
                warnings.append(
                    {
                        "setting": var_name,
                        "type": "environment_variable",
                        "description": description,
                        "severity": "warning",
                    }
                )

        # Check database settings health
        db_status = self._validate_database_settings()
        if db_status["has_issues"]:
            warnings.extend(db_status["issues"])

        # Generate recommendations
        if critical_missing:
            recommendations.append("Set missing critical environment variables immediately")
        if warnings:
            recommendations.append("Consider configuring recommended settings for optimal operation")
        if not critical_missing and not warnings:
            recommendations.append("Configuration is optimal")

        # Determine overall status
        if critical_missing:
            overall_status = "critical"
        elif warnings:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "critical_missing": critical_missing,
            "warnings": warnings,
            "overall_status": overall_status,
            "recommendations": recommendations,
            "validation_timestamp": self._get_timestamp(),
        }

    def validate_feature_flags_consistency(self) -> Dict[str, Any]:
        """
        Validate feature flag consistency and detect potential conflicts.

        Returns:
            Dictionary with feature flag validation results.
        """
        issues = []
        recommendations = []

        try:
            feature_flags = self.settings_manager.get_feature_flags()
            if not feature_flags:
                issues.append(
                    {
                        "issue": "Feature flags not configured",
                        "severity": "warning",
                        "description": "System using default feature flag values",
                    }
                )
                recommendations.append("Configure feature flags in admin UI for customized behavior")
                return {
                    "issues": issues,
                    "recommendations": recommendations,
                    "overall_status": "degraded",
                    "validation_timestamp": self._get_timestamp(),
                }

            # Check for potentially conflicting flag combinations
            if feature_flags.enable_maintenance_mode and feature_flags.enable_analytics:
                issues.append(
                    {
                        "issue": "Maintenance mode with analytics enabled",
                        "severity": "info",
                        "description": "Analytics might record maintenance mode events",
                    }
                )

            if not feature_flags.enable_rate_limiting and os.getenv("ENVIRONMENT") == "production":
                issues.append(
                    {
                        "issue": "Rate limiting disabled in production",
                        "severity": "warning",
                        "description": "Production systems should have rate limiting enabled",
                    }
                )
                recommendations.append("Enable rate limiting for production deployment")

            # Check admin features
            if feature_flags.enable_admin_diagnostics and not feature_flags.enable_analytics:
                recommendations.append("Consider enabling analytics for comprehensive admin insights")

        except Exception as e:
            logger.error(f"Error validating feature flags: {e}")
            issues.append(
                {
                    "issue": "Feature flag validation failed",
                    "severity": "error",
                    "description": f"Unable to validate feature flags: {e}",
                }
            )

        overall_status = "healthy"
        if any(issue["severity"] in ["error", "critical"] for issue in issues):
            overall_status = "critical"
        elif any(issue["severity"] == "warning" for issue in issues):
            overall_status = "degraded"

        return {
            "issues": issues,
            "recommendations": recommendations,
            "overall_status": overall_status,
            "validation_timestamp": self._get_timestamp(),
        }

    def get_configuration_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive configuration health summary combining all validation results.

        Returns:
            Complete health summary with overall system status.
        """
        critical_validation = self.validate_critical_settings()
        feature_flag_validation = self.validate_feature_flags_consistency()

        # Determine overall system health
        statuses = [critical_validation["overall_status"], feature_flag_validation["overall_status"]]
        if "critical" in statuses:
            overall_health = "critical"
        elif "degraded" in statuses:
            overall_health = "degraded"
        else:
            overall_health = "healthy"

        # Combine all issues and recommendations
        all_issues = critical_validation["critical_missing"] + critical_validation["warnings"]
        all_issues.extend(feature_flag_validation["issues"])

        all_recommendations = critical_validation["recommendations"] + feature_flag_validation["recommendations"]
        # Remove duplicate recommendations while preserving order
        all_recommendations = list(dict.fromkeys(all_recommendations))

        return {
            "overall_health": overall_health,
            "critical_settings": critical_validation,
            "feature_flags": feature_flag_validation,
            "summary": {
                "total_issues": len(all_issues),
                "critical_issues": len([i for i in all_issues if i.get("severity") == "critical"]),
                "warnings": len([i for i in all_issues if i.get("severity") == "warning"]),
                "recommendations_count": len(all_recommendations),
            },
            "recommendations": all_recommendations,
            "validation_timestamp": self._get_timestamp(),
        }

    def _validate_database_settings(self) -> Dict[str, Any]:
        """Validate database-stored settings health."""
        issues = []
        has_issues = False

        try:
            # Check if essential admin settings are configured
            core_settings = self.settings_manager.get_core_settings()
            if not core_settings:
                issues.append(
                    {
                        "setting": "core_settings",
                        "type": "database_setting",
                        "description": "Core application settings not configured",
                        "severity": "warning",
                    }
                )
                has_issues = True

            # Check response settings for performance optimization
            response_settings = self.settings_manager.get_response_settings()
            if response_settings and not response_settings.enable_caching:
                issues.append(
                    {
                        "setting": "response_caching",
                        "type": "database_setting",
                        "description": "Response caching disabled - may impact performance",
                        "severity": "info",
                    }
                )

        except Exception as e:
            logger.error(f"Error validating database settings: {e}")
            issues.append(
                {
                    "setting": "database_access",
                    "type": "database_setting",
                    "description": f"Unable to access database settings: {e}",
                    "severity": "error",
                }
            )
            has_issues = True

        return {
            "has_issues": has_issues,
            "issues": issues,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return get_current_timestamp()


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Convenience functions for easy access
def validate_critical_settings() -> Dict[str, Any]:
    """Validate critical system settings."""
    validator = ConfigurationValidator()
    return validator.validate_critical_settings()


def validate_feature_flags_consistency() -> Dict[str, Any]:
    """Validate feature flag consistency."""
    validator = ConfigurationValidator()
    return validator.validate_feature_flags_consistency()


def get_configuration_health_summary() -> Dict[str, Any]:
    """Get comprehensive configuration health summary."""
    validator = ConfigurationValidator()
    return validator.get_configuration_health_summary()


def is_system_healthy() -> Tuple[bool, List[str]]:
    """
    Quick health check function.

    Returns:
        Tuple of (is_healthy: bool, critical_issues: List[str])
    """
    try:
        summary = get_configuration_health_summary()
        is_healthy = summary["overall_health"] != "critical"
        critical_issues = [
            issue.get("description", "Unknown critical issue")
            for issue in summary["critical_settings"]["critical_missing"]
        ]
        return is_healthy, critical_issues
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return False, [f"Health check failed: {e}"]
