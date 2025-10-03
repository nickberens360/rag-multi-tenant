"""
Unit tests for settings validation utilities.

Tests the advanced validation system including:
- Cross-field dependency validation
- Performance impact validation
- Security configuration validation
- AI model configuration validation
- Settings health checking
"""

from unittest.mock import Mock

import pytest

from backend.core.settings_manifest import ValidationSeverity
from backend.core.settings_schemas import (
    FeatureFlags,
    FollowUpSettings,
    QueryRoutingSettings,
    RagConfigurationSettings,
    ResponseSettings,
    SearchRetrievalSettings,
    SecuritySettings,
    SystemConfigurationSettings,
    SystemSettings,
)
from backend.core.settings_validation import (
    SettingsHealthChecker,
    SettingsValidator,
    get_settings_validation_report,
    validate_settings_configuration,
)


class TestSettingsValidator:
    """Test SettingsValidator functionality."""

    def create_default_system_settings(self) -> SystemSettings:
        """Create a default SystemSettings instance for testing."""
        return SystemSettings(
            followup=FollowUpSettings(),
            response=ResponseSettings(),
            routing=QueryRoutingSettings(),
            features=FeatureFlags(),
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(),
        )

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = SettingsValidator()
        assert validator.manifest is not None

        # Test with custom manifest
        mock_manifest = Mock()
        validator_with_manifest = SettingsValidator(manifest=mock_manifest)
        assert validator_with_manifest.manifest is mock_manifest

    def test_cross_field_dependencies_mmr_validation(self):
        """Test MMR configuration dependency validation."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create invalid MMR configuration
        rag_config = RagConfigurationSettings(
            rag_use_mmr=True,
            rag_mmr_k=10,  # Greater than fetch_k
            rag_mmr_fetch_k=5,
        )
        settings.rag_config = rag_config

        results = validator.validate_cross_field_dependencies(settings)

        # Should find MMR dependency error
        mmr_errors = [r for r in results if "MMR K cannot be greater" in r.message]
        assert len(mmr_errors) == 1
        assert mmr_errors[0].severity == ValidationSeverity.ERROR

    def test_cross_field_dependencies_caching_validation(self):
        """Test caching configuration consistency validation."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create inconsistent caching configuration
        settings.response.enable_caching = True
        settings.routing.enable_query_caching = False

        results = validator.validate_cross_field_dependencies(settings)

        # Should find caching inconsistency warning
        caching_warnings = [r for r in results if "query caching is disabled" in r.message]
        assert len(caching_warnings) == 1
        assert caching_warnings[0].severity == ValidationSeverity.WARNING

    def test_cross_field_dependencies_rate_limiting(self):
        """Test rate limiting configuration validation."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create potentially problematic rate limiting
        settings.security.enable_rate_limiting = True
        settings.security.rate_limit_requests = 1500  # High requests
        settings.security.rate_limit_window = 30  # Short window

        results = validator.validate_cross_field_dependencies(settings)

        # Should find rate limiting warning
        rate_warnings = [r for r in results if "High request rate" in r.message]
        assert len(rate_warnings) == 1
        assert rate_warnings[0].severity == ValidationSeverity.WARNING

    def test_cross_field_dependencies_followup_feature_flag(self):
        """Test follow-up settings vs feature flag consistency."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create inconsistent follow-up configuration
        settings.followup.enabled = True
        settings.features.enable_followup_questions = False

        results = validator.validate_cross_field_dependencies(settings)

        # Should find follow-up inconsistency error
        followup_errors = [r for r in results if "feature flag is disabled" in r.message]
        assert len(followup_errors) == 1
        assert followup_errors[0].severity == ValidationSeverity.ERROR

    def test_performance_impact_validation_context(self):
        """Test performance impact validation for context settings."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create performance-heavy context configuration
        settings.response.max_context_documents = 8  # High
        settings.response.max_context_length = 7000  # High

        results = validator.validate_performance_impact(settings)

        # Should find performance warning
        perf_warnings = [r for r in results if "may increase response time" in r.message]
        assert len(perf_warnings) == 1
        assert perf_warnings[0].severity == ValidationSeverity.WARNING

    def test_performance_impact_validation_caching(self):
        """Test performance impact validation for caching disabled."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create performance-impacting configuration
        settings.response.enable_caching = False
        settings.response.preferred_response_length = "comprehensive"

        results = validator.validate_performance_impact(settings)

        # Should find caching performance warning
        caching_warnings = [r for r in results if "Caching disabled" in r.message]
        assert len(caching_warnings) == 1
        assert caching_warnings[0].severity == ValidationSeverity.WARNING

    def test_performance_impact_validation_rag(self):
        """Test performance impact validation for RAG settings."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create performance-heavy RAG configuration
        rag_config = RagConfigurationSettings(
            rag_use_mmr=True,
            rag_mmr_fetch_k=75,  # High fetch count
        )
        settings.rag_config = rag_config

        results = validator.validate_performance_impact(settings)

        # Should find RAG performance warning
        rag_warnings = [r for r in results if "document retrieval time" in r.message]
        assert len(rag_warnings) == 1
        assert rag_warnings[0].severity == ValidationSeverity.WARNING

    def test_performance_impact_validation_search(self):
        """Test performance impact validation for search settings."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create search configuration that may timeout
        search_config = SearchRetrievalSettings(
            max_search_results=25,  # High results
            search_timeout_seconds=5,  # Low timeout
        )
        settings.search_retrieval = search_config

        results = validator.validate_performance_impact(settings)

        # Should find search timeout warning
        search_warnings = [r for r in results if "may cause timeouts" in r.message]
        assert len(search_warnings) == 1
        assert search_warnings[0].severity == ValidationSeverity.WARNING

    def test_security_configuration_validation_session_timeout(self):
        """Test security validation for session timeout."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create long session timeout
        settings.security.session_timeout_minutes = 2000  # More than 24 hours

        results = validator.validate_security_configuration(settings)

        # Should find security warning
        session_warnings = [r for r in results if "long session timeout" in r.message]
        assert len(session_warnings) == 1
        assert session_warnings[0].severity == ValidationSeverity.WARNING

    def test_security_configuration_validation_login_attempts(self):
        """Test security validation for login attempts."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create high login attempt limit
        settings.security.max_login_attempts = 15  # High limit

        results = validator.validate_security_configuration(settings)

        # Should find security warning
        login_warnings = [r for r in results if "High login attempt limit" in r.message]
        assert len(login_warnings) == 1
        assert login_warnings[0].severity == ValidationSeverity.WARNING

    def test_security_configuration_validation_rate_limiting(self):
        """Test security validation for rate limiting."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create high rate limit
        settings.security.enable_rate_limiting = True
        settings.security.rate_limit_requests = 750  # High limit

        results = validator.validate_security_configuration(settings)

        # Should find rate limit info
        rate_info = [r for r in results if "High rate limit" in r.message]
        assert len(rate_info) == 1
        assert rate_info[0].severity == ValidationSeverity.INFO

    def test_ai_model_configuration_validation_consistency(self):
        """Test AI model configuration consistency validation."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create inconsistent LLM configuration
        settings.system_config.response_llm = "claude"
        settings.response.response_llm = "gemini"  # Different

        results = validator.validate_ai_model_configuration(settings)

        # Should find LLM mismatch
        llm_warnings = [r for r in results if "Response LLM mismatch" in r.message]
        assert len(llm_warnings) == 1
        assert llm_warnings[0].severity == ValidationSeverity.WARNING

    def test_ai_model_configuration_validation_efficiency(self):
        """Test AI model configuration efficiency validation."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create inefficient model configuration
        settings.system_config.processing_llm = "claude"
        settings.system_config.response_llm = "claude"
        settings.system_config.processing_claude_model = "claude-3-5-sonnet-20241022"
        settings.system_config.response_claude_model = "claude-3-5-sonnet-20241022"

        results = validator.validate_ai_model_configuration(settings)

        # Should find efficiency suggestion
        efficiency_info = [r for r in results if "same model for processing" in r.message]
        assert len(efficiency_info) == 1
        assert efficiency_info[0].severity == ValidationSeverity.INFO

    def test_feature_flag_consistency_validation_analytics(self):
        """Test feature flag consistency validation for analytics."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create inconsistent analytics configuration
        settings.features.enable_analytics = True
        settings.security.enable_analytics = False

        results = validator.validate_feature_flag_consistency(settings)

        # Should find analytics inconsistency
        analytics_warnings = [r for r in results if "Analytics feature flag inconsistent" in r.message]
        assert len(analytics_warnings) == 1
        assert analytics_warnings[0].severity == ValidationSeverity.WARNING

    def test_feature_flag_consistency_validation_caching(self):
        """Test feature flag consistency validation for caching."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create inconsistent caching configuration
        settings.features.enable_caching = True
        settings.response.enable_caching = False

        results = validator.validate_feature_flag_consistency(settings)

        # Should find caching inconsistency
        caching_warnings = [r for r in results if "Caching feature flag inconsistent" in r.message]
        assert len(caching_warnings) == 1
        assert caching_warnings[0].severity == ValidationSeverity.WARNING

    def test_complete_settings_validation(self):
        """Test complete settings validation workflow."""
        validator = SettingsValidator()
        settings = self.create_default_system_settings()

        # Create some issues for comprehensive testing
        settings.followup.max_questions = 10  # Invalid
        settings.security.session_timeout_minutes = 2000  # Warning
        settings.response.enable_caching = False
        settings.response.preferred_response_length = "comprehensive"  # Performance warning

        results = validator.validate_complete_settings(settings)

        # Should have multiple types of validation results
        assert len(results) > 0

        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]

        assert len(errors) > 0
        assert len(warnings) > 0


class TestSettingsHealthChecker:
    """Test SettingsHealthChecker functionality."""

    def create_healthy_settings(self) -> SystemSettings:
        """Create healthy settings for testing."""
        return SystemSettings(
            followup=FollowUpSettings(),
            response=ResponseSettings(),
            routing=QueryRoutingSettings(),
            features=FeatureFlags(),
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(),
        )

    def create_unhealthy_settings(self) -> SystemSettings:
        """Create settings with multiple issues for testing."""
        settings = self.create_healthy_settings()

        # Add various issues
        settings.followup.max_questions = 10  # Invalid
        settings.security.max_login_attempts = 20  # Warning
        settings.response.max_context_documents = 8
        settings.response.max_context_length = 8000  # Performance warning

        return settings

    def test_health_checker_initialization(self):
        """Test health checker initialization."""
        checker = SettingsHealthChecker()
        assert checker.validator is not None

        # Test with custom validator
        mock_validator = Mock()
        checker_with_validator = SettingsHealthChecker(validator=mock_validator)
        assert checker_with_validator.validator is mock_validator

    def test_check_settings_health_healthy(self):
        """Test health check with healthy settings."""
        checker = SettingsHealthChecker()
        settings = self.create_healthy_settings()

        health_data = checker.check_settings_health(settings)

        assert "health_score" in health_data
        assert "overall_status" in health_data
        assert "total_issues" in health_data
        assert "issues_by_severity" in health_data
        assert "critical_issues" in health_data
        assert "recommendations" in health_data
        assert "validation_timestamp" in health_data

        # Healthy settings should have high score
        assert health_data["health_score"] >= 80
        assert health_data["overall_status"] in ["excellent", "good"]

    def test_check_settings_health_unhealthy(self):
        """Test health check with unhealthy settings."""
        checker = SettingsHealthChecker()
        settings = self.create_unhealthy_settings()

        health_data = checker.check_settings_health(settings)

        # Unhealthy settings should have lower score
        assert health_data["health_score"] < 90
        assert health_data["total_issues"] > 0
        assert len(health_data["recommendations"]) > 0

    def test_calculate_health_score_no_issues(self):
        """Test health score calculation with no issues."""
        checker = SettingsHealthChecker()

        score = checker._calculate_health_score([])
        assert score == 100.0

    def test_calculate_health_score_with_issues(self):
        """Test health score calculation with various issues."""
        checker = SettingsHealthChecker()

        from backend.core.settings_manifest import ValidationResult

        results = [
            ValidationResult(
                field_name="test1",
                severity=ValidationSeverity.CRITICAL,
                message="Critical issue",
            ),
            ValidationResult(
                field_name="test2",
                severity=ValidationSeverity.ERROR,
                message="Error issue",
            ),
            ValidationResult(
                field_name="test3",
                severity=ValidationSeverity.WARNING,
                message="Warning issue",
            ),
        ]

        score = checker._calculate_health_score(results)

        # Should be less than 100 due to issues
        assert score < 100
        assert score >= 0

    def test_group_issues_by_severity(self):
        """Test grouping issues by severity."""
        checker = SettingsHealthChecker()

        from backend.core.settings_manifest import ValidationResult

        results = [
            ValidationResult(
                field_name="test1",
                severity=ValidationSeverity.ERROR,
                message="Error 1",
            ),
            ValidationResult(
                field_name="test2",
                severity=ValidationSeverity.ERROR,
                message="Error 2",
            ),
            ValidationResult(
                field_name="test3",
                severity=ValidationSeverity.WARNING,
                message="Warning 1",
            ),
        ]

        grouped = checker._group_issues_by_severity(results)

        assert grouped["error"] == 2
        assert grouped["warning"] == 1
        assert grouped["critical"] == 0
        assert grouped["info"] == 0

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        checker = SettingsHealthChecker()

        from backend.core.settings_manifest import ValidationResult

        results = [
            ValidationResult(
                field_name="critical_field",
                severity=ValidationSeverity.CRITICAL,
                message="Critical issue",
                suggestion="Fix this immediately",
            ),
            ValidationResult(
                field_name="error_field",
                severity=ValidationSeverity.ERROR,
                message="Error issue",
                suggestion="Fix this error",
            ),
            ValidationResult(
                field_name="performance_field",
                severity=ValidationSeverity.WARNING,
                message="Performance issue detected",
                suggestion="Optimize performance",
            ),
        ]

        recommendations = checker._generate_recommendations(results)

        assert len(recommendations) > 0
        assert any("Fix this immediately" in rec for rec in recommendations)
        assert any("Fix this error" in rec for rec in recommendations)

    def test_get_overall_status(self):
        """Test overall status determination."""
        checker = SettingsHealthChecker()

        assert checker._get_overall_status(95) == "excellent"
        assert checker._get_overall_status(85) == "good"
        assert checker._get_overall_status(70) == "fair"
        assert checker._get_overall_status(50) == "poor"
        assert checker._get_overall_status(30) == "critical"

    def test_get_timestamp(self):
        """Test timestamp generation."""
        checker = SettingsHealthChecker()

        timestamp = checker._get_timestamp()
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_validate_settings_configuration(self):
        """Test validate_settings_configuration convenience function."""
        settings = SystemSettings(
            followup=FollowUpSettings(),
            response=ResponseSettings(),
            routing=QueryRoutingSettings(),
            features=FeatureFlags(),
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(),
        )

        result = validate_settings_configuration(settings)

        assert isinstance(result, dict)
        assert "health_score" in result
        assert "overall_status" in result

    def test_get_settings_validation_report(self):
        """Test get_settings_validation_report convenience function."""
        settings = SystemSettings(
            followup=FollowUpSettings(),
            response=ResponseSettings(),
            routing=QueryRoutingSettings(),
            features=FeatureFlags(),
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(),
        )

        report = get_settings_validation_report(settings)

        assert isinstance(report, str)
        assert "Settings Configuration Validation Report" in report
        assert "Overall Health Score" in report
        assert "Issues by Severity" in report

    def test_validation_report_with_issues(self):
        """Test validation report with actual issues."""
        settings = SystemSettings(
            followup=FollowUpSettings(max_questions=10),  # Invalid
            response=ResponseSettings(),
            routing=QueryRoutingSettings(),
            features=FeatureFlags(),
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(max_login_attempts=20),  # Warning
        )

        report = get_settings_validation_report(settings)

        assert "Total Issues Found:" in report
        assert "Top Recommendations:" in report or "Critical Issues:" in report


if __name__ == "__main__":
    pytest.main([__file__])
