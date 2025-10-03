"""
Settings validation utilities and advanced validation logic.

This module provides additional validation capabilities that complement
the settings manifest, including cross-field validation, consistency checks,
and integration validation.
"""

import logging
from typing import Any, Dict, List, Optional

from .settings_manifest import SettingsManifest, ValidationResult, ValidationSeverity, get_settings_manifest
from .settings_schemas import SystemSettings

logger = logging.getLogger(__name__)


class SettingsValidator:
    """
    Advanced settings validator with cross-field and consistency validation.

    Provides validation beyond individual field rules, including:
    - Cross-field dependencies
    - Logical consistency checks
    - Performance impact validation
    - Security configuration validation
    """

    def __init__(self, manifest: Optional[SettingsManifest] = None):
        self.manifest = manifest or get_settings_manifest()

    def validate_cross_field_dependencies(self, settings: SystemSettings) -> List[ValidationResult]:
        """Validate dependencies between different settings fields."""
        results = []

        # Validate MMR configuration consistency
        if hasattr(settings, "rag_config"):
            rag = settings.rag_config
            if rag.rag_use_mmr and rag.rag_mmr_k > rag.rag_mmr_fetch_k:
                results.append(
                    ValidationResult(
                        field_name="rag_mmr_k",
                        severity=ValidationSeverity.ERROR,
                        message="MMR K cannot be greater than MMR Fetch K",
                        current_value=rag.rag_mmr_k,
                        suggestion=f"Set rag_mmr_k to be <= {rag.rag_mmr_fetch_k}",
                    )
                )

        # Validate caching consistency
        if hasattr(settings, "response") and hasattr(settings, "routing"):
            response = settings.response
            routing = settings.routing

            if response.enable_caching and not routing.enable_query_caching:
                results.append(
                    ValidationResult(
                        field_name="enable_query_caching",
                        severity=ValidationSeverity.WARNING,
                        message="Response caching is enabled but query caching is disabled",
                        suggestion="Consider enabling query caching for better performance",
                    )
                )

        # Validate rate limiting consistency
        if hasattr(settings, "security") and hasattr(settings, "system_config"):
            security = settings.security
            settings.system_config

            if security.enable_rate_limiting:
                # Check if rate limit values are consistent
                if security.rate_limit_requests > 1000 and security.rate_limit_window < 60:
                    results.append(
                        ValidationResult(
                            field_name="rate_limit_window",
                            severity=ValidationSeverity.WARNING,
                            message="High request rate with short window may cause performance issues",
                            current_value=security.rate_limit_window,
                            suggestion="Consider increasing rate_limit_window or reducing rate_limit_requests",
                        )
                    )

        # Validate follow-up question configuration
        if hasattr(settings, "followup") and hasattr(settings, "features"):
            followup = settings.followup
            features = settings.features

            if followup.enabled and not features.enable_followup_questions:
                results.append(
                    ValidationResult(
                        field_name="enable_followup_questions",
                        severity=ValidationSeverity.ERROR,
                        message="Follow-up settings are enabled but feature flag is disabled",
                        suggestion="Enable the feature flag or disable follow-up settings",
                    )
                )

        return results

    def validate_performance_impact(self, settings: SystemSettings) -> List[ValidationResult]:
        """Validate settings for potential performance impact."""
        results = []

        # Check for performance-heavy configurations
        if hasattr(settings, "response"):
            response = settings.response

            if response.max_context_documents > 5 and response.max_context_length > 5000:
                total_context = response.max_context_documents * response.max_context_length
                results.append(
                    ValidationResult(
                        field_name="max_context_documents",
                        severity=ValidationSeverity.WARNING,
                        message=f"High context load ({response.max_context_documents} docs × {response.max_context_length} chars = {total_context:,} total) may increase response time by 2-5 seconds",
                        current_value=response.max_context_documents,
                        suggestion="Consider reducing max_context_documents to ≤5 or max_context_length to ≤3000 for optimal performance",
                    )
                )

            if not response.enable_caching and response.preferred_response_length == "comprehensive":
                results.append(
                    ValidationResult(
                        field_name="enable_caching",
                        severity=ValidationSeverity.WARNING,
                        message="Caching disabled with comprehensive responses may add 3-8 seconds per repeated query due to full LLM processing",
                        suggestion="Enable caching to reduce comprehensive response time from ~10s to ~2s for cached queries",
                    )
                )

        # Check RAG configuration for performance
        if hasattr(settings, "rag_config"):
            rag = settings.rag_config

            if rag.rag_use_mmr and rag.rag_mmr_fetch_k > 50:
                estimated_latency = (rag.rag_mmr_fetch_k - 20) * 0.1  # Rough estimate
                results.append(
                    ValidationResult(
                        field_name="rag_mmr_fetch_k",
                        severity=ValidationSeverity.WARNING,
                        message=f"High MMR fetch count ({rag.rag_mmr_fetch_k}) may add ~{estimated_latency:.1f}s to document retrieval time",
                        current_value=rag.rag_mmr_fetch_k,
                        suggestion="Consider reducing rag_mmr_fetch_k to 20-40 for optimal retrieval speed (typically <2s)",
                    )
                )

        # Check search settings for performance
        if hasattr(settings, "search_retrieval"):
            search = settings.search_retrieval

            if search.max_search_results > 20 and search.search_timeout_seconds < 10:
                results.append(
                    ValidationResult(
                        field_name="search_timeout_seconds",
                        severity=ValidationSeverity.WARNING,
                        message="High max results with low timeout may cause timeouts",
                        current_value=search.search_timeout_seconds,
                        suggestion="Increase search_timeout_seconds or reduce max_search_results",
                    )
                )

        return results

    def validate_security_configuration(self, settings: SystemSettings) -> List[ValidationResult]:
        """Validate security-related configuration settings."""
        results = []

        if hasattr(settings, "security"):
            security = settings.security

            # Check session timeout
            if security.session_timeout_minutes > 1440:  # More than 24 hours
                results.append(
                    ValidationResult(
                        field_name="session_timeout_minutes",
                        severity=ValidationSeverity.WARNING,
                        message="Very long session timeout may pose security risks",
                        current_value=security.session_timeout_minutes,
                        suggestion="Consider reducing session timeout for better security",
                    )
                )

            # Check login attempt limits
            if security.max_login_attempts > 10:
                results.append(
                    ValidationResult(
                        field_name="max_login_attempts",
                        severity=ValidationSeverity.WARNING,
                        message="High login attempt limit may allow brute force attacks",
                        current_value=security.max_login_attempts,
                        suggestion="Consider reducing max_login_attempts",
                    )
                )

            # Check rate limiting configuration
            if security.enable_rate_limiting and security.rate_limit_requests > 500:
                results.append(
                    ValidationResult(
                        field_name="rate_limit_requests",
                        severity=ValidationSeverity.INFO,
                        message="High rate limit - ensure this is intentional",
                        current_value=security.rate_limit_requests,
                    )
                )

        return results

    def validate_ai_model_configuration(self, settings: SystemSettings) -> List[ValidationResult]:
        """Validate AI model configuration for consistency and best practices."""
        results = []

        if hasattr(settings, "system_config") and hasattr(settings, "response"):
            system_config = settings.system_config
            response = settings.response

            # Check model consistency
            if system_config.response_llm != response.response_llm:
                results.append(
                    ValidationResult(
                        field_name="response_llm",
                        severity=ValidationSeverity.WARNING,
                        message="Response LLM mismatch between system config and response settings",
                        suggestion="Ensure consistent LLM configuration across settings",
                    )
                )

            # Check processing vs response model efficiency
            if (
                system_config.processing_llm == "claude"
                and system_config.response_llm == "claude"
                and system_config.processing_claude_model == system_config.response_claude_model
            ):
                results.append(
                    ValidationResult(
                        field_name="processing_llm",
                        severity=ValidationSeverity.INFO,
                        message="Using same model for processing and response - consider using faster model for processing",
                        suggestion="Use claude_haiku for processing to improve performance",
                    )
                )

        return results

    def validate_feature_flag_consistency(self, settings: SystemSettings) -> List[ValidationResult]:
        """Validate feature flag consistency across different settings."""
        results = []

        if not hasattr(settings, "features"):
            return results

        features = settings.features

        # Check analytics configuration
        if hasattr(settings, "security"):
            security = settings.security
            if features.enable_analytics != security.enable_analytics:
                results.append(
                    ValidationResult(
                        field_name="enable_analytics",
                        severity=ValidationSeverity.WARNING,
                        message="Analytics feature flag inconsistent between feature flags and security settings",
                        suggestion="Ensure consistent analytics configuration",
                    )
                )

        # Check caching configuration
        if hasattr(settings, "response") and hasattr(settings, "routing"):
            response = settings.response
            settings.routing

            if features.enable_caching != response.enable_caching:
                results.append(
                    ValidationResult(
                        field_name="enable_caching",
                        severity=ValidationSeverity.WARNING,
                        message="Caching feature flag inconsistent with response settings",
                        suggestion="Ensure consistent caching configuration",
                    )
                )

        return results

    def validate_complete_settings(self, settings: SystemSettings) -> List[ValidationResult]:
        """Run complete validation including all checks."""
        results = []

        # Basic field validation using manifest
        if hasattr(settings, "to_dict"):
            settings_dict = {
                "followup": settings.followup,
                "response": settings.response,
                "routing": settings.routing,
                "features": settings.features,
                "system_config": settings.system_config,
                "security": settings.security,
            }
            results.extend(self.manifest.validate_all_groups(settings_dict))

        # Advanced validation
        results.extend(self.validate_cross_field_dependencies(settings))
        results.extend(self.validate_performance_impact(settings))
        results.extend(self.validate_security_configuration(settings))
        results.extend(self.validate_ai_model_configuration(settings))
        results.extend(self.validate_feature_flag_consistency(settings))

        return results


class SettingsHealthChecker:
    """
    Settings health checker for monitoring configuration health.

    Provides methods to check the overall health of settings configuration
    and identify potential issues before they impact runtime.
    """

    def __init__(self, validator: Optional[SettingsValidator] = None):
        self.validator = validator or SettingsValidator()

    def check_settings_health(self, settings: SystemSettings) -> Dict[str, Any]:
        """Perform comprehensive health check on settings."""
        validation_results = self.validator.validate_complete_settings(settings)

        health_score = self._calculate_health_score(validation_results)
        issues_by_severity = self._group_issues_by_severity(validation_results)
        recommendations = self._generate_recommendations(validation_results)

        return {
            "health_score": health_score,
            "overall_status": self._get_overall_status(health_score),
            "total_issues": len(validation_results),
            "issues_by_severity": issues_by_severity,
            "critical_issues": [r for r in validation_results if r.severity == ValidationSeverity.CRITICAL],
            "recommendations": recommendations,
            "validation_timestamp": self._get_timestamp(),
        }

    def _calculate_health_score(self, results: List[ValidationResult]) -> float:
        """Calculate health score (0-100) based on validation results."""
        if not results:
            return 100.0

        # Weight different severities
        weights = {
            ValidationSeverity.CRITICAL: 25,
            ValidationSeverity.ERROR: 10,
            ValidationSeverity.WARNING: 3,
            ValidationSeverity.INFO: 1,
        }

        total_penalty = sum(weights.get(result.severity, 0) for result in results)

        # Maximum possible penalty (assuming 20 issues of each type)
        max_penalty = sum(weights.values()) * 20

        health_score = max(0, 100 - (total_penalty / max_penalty * 100))
        return round(health_score, 1)

    def _group_issues_by_severity(self, results: List[ValidationResult]) -> Dict[str, int]:
        """Group validation issues by severity."""
        counts = {severity.value: 0 for severity in ValidationSeverity}

        for result in results:
            counts[result.severity.value] += 1

        return counts

    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Generate top recommendations based on validation results."""
        recommendations = []

        # Prioritize critical and error issues
        critical_errors = [r for r in results if r.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]

        for result in critical_errors[:5]:  # Top 5 critical issues
            if result.suggestion:
                recommendations.append(f"{result.field_name}: {result.suggestion}")
            else:
                recommendations.append(f"{result.field_name}: {result.message}")

        # Add performance recommendations
        performance_warnings = [
            r for r in results if r.severity == ValidationSeverity.WARNING and "performance" in r.message.lower()
        ]

        for result in performance_warnings[:3]:  # Top 3 performance warnings
            if result.suggestion:
                recommendations.append(f"Performance: {result.suggestion}")

        return recommendations

    def _get_overall_status(self, health_score: float) -> str:
        """Get overall status based on health score."""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "fair"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"

    def _get_timestamp(self) -> str:
        """Get current timestamp for validation."""
        from datetime import datetime

        return datetime.utcnow().isoformat()


def validate_settings_configuration(settings: SystemSettings) -> Dict[str, Any]:
    """
    Convenience function for validating settings configuration.

    Args:
        settings: SystemSettings instance to validate

    Returns:
        Dictionary containing validation results and health information
    """
    health_checker = SettingsHealthChecker()
    return health_checker.check_settings_health(settings)


def get_settings_validation_report(settings: SystemSettings) -> str:
    """
    Generate a human-readable validation report.

    Args:
        settings: SystemSettings instance to validate

    Returns:
        Formatted string report of validation results
    """
    health_data = validate_settings_configuration(settings)

    report_lines = [
        "Settings Configuration Validation Report",
        "=" * 40,
        f"Overall Health Score: {health_data['health_score']}/100 ({health_data['overall_status'].upper()})",
        f"Total Issues Found: {health_data['total_issues']}",
        "",
        "Issues by Severity:",
    ]

    for severity, count in health_data["issues_by_severity"].items():
        report_lines.append(f"  {severity.capitalize()}: {count}")

    if health_data["critical_issues"]:
        report_lines.extend(
            [
                "",
                "Critical Issues:",
            ]
        )
        for issue in health_data["critical_issues"]:
            report_lines.append(f"  - {issue.field_name}: {issue.message}")

    if health_data["recommendations"]:
        report_lines.extend(
            [
                "",
                "Top Recommendations:",
            ]
        )
        for i, recommendation in enumerate(health_data["recommendations"][:5], 1):
            report_lines.append(f"  {i}. {recommendation}")

    return "\n".join(report_lines)
