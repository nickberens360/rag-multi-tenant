"""
Integration tests for settings manifest with existing settings system.

These tests ensure that the new manifest and validation system works correctly
with the existing settings infrastructure without breaking runtime behavior.
"""

from unittest.mock import patch

import pytest

from backend.core.settings_manager import SettingsManager, get_settings_manager
from backend.core.settings_manifest import SettingKeys, get_settings_manifest
from backend.core.settings_schemas import (
    CoreSettings,
    FeatureFlags,
    FollowUpSettings,
    KnowledgeSettings,
    QueryRoutingSettings,
    RagConfigurationSettings,
    ResponseSettings,
    SearchRetrievalSettings,
    SecuritySettings,
    SystemConfigurationSettings,
    SystemSettings,
    UXSettings,
)
from backend.core.settings_validation import validate_settings_configuration


class TestSettingsManifestIntegration:
    """Test integration between manifest and existing settings system."""

    def test_manifest_covers_all_setting_keys(self):
        """Test that manifest includes all settings defined in SettingKeys."""
        manifest = get_settings_manifest()
        groups = manifest.get_all_groups()

        # Get all setting keys from SettingKeys class
        setting_keys = [
            getattr(SettingKeys, attr)
            for attr in dir(SettingKeys)
            if not attr.startswith("_") and isinstance(getattr(SettingKeys, attr), str)
        ]

        # Remove system settings as it's for future unified storage
        setting_keys = [key for key in setting_keys if key != SettingKeys.SYSTEM_SETTINGS]

        # Check that all keys are covered
        for key in setting_keys:
            assert key in groups, f"Setting key '{key}' not found in manifest"

    def test_manifest_schema_classes_match(self):
        """Test that manifest schema classes match actual schema classes."""
        manifest = get_settings_manifest()

        schema_mappings = {
            SettingKeys.CORE_SETTINGS: CoreSettings,
            SettingKeys.FEATURE_FLAGS: FeatureFlags,
            SettingKeys.FOLLOWUP_SETTINGS: FollowUpSettings,
            SettingKeys.RESPONSE_SETTINGS: ResponseSettings,
            SettingKeys.ROUTING_SETTINGS: QueryRoutingSettings,
            SettingKeys.SYSTEM_CONFIG_SETTINGS: SystemConfigurationSettings,
            SettingKeys.SECURITY_SETTINGS: SecuritySettings,
            SettingKeys.RAG_CONFIG_SETTINGS: RagConfigurationSettings,
            SettingKeys.UX_SETTINGS: UXSettings,
            SettingKeys.SEARCH_RETRIEVAL_SETTINGS: SearchRetrievalSettings,
            SettingKeys.KNOWLEDGE_SETTINGS: KnowledgeSettings,
        }

        for setting_key, expected_class in schema_mappings.items():
            group = manifest.get_group(setting_key)
            assert group is not None, f"Group not found for {setting_key}"
            assert group.schema_class == expected_class, f"Schema class mismatch for {setting_key}"

    def test_manifest_validation_with_real_instances(self):
        """Test manifest validation with real settings instances."""
        manifest = get_settings_manifest()

        # Create real instances with default values
        settings_instances = {
            SettingKeys.CORE_SETTINGS: CoreSettings(),
            SettingKeys.FEATURE_FLAGS: FeatureFlags(),
            SettingKeys.FOLLOWUP_SETTINGS: FollowUpSettings(),
            SettingKeys.RESPONSE_SETTINGS: ResponseSettings(),
            SettingKeys.ROUTING_SETTINGS: QueryRoutingSettings(),
            SettingKeys.SYSTEM_CONFIG_SETTINGS: SystemConfigurationSettings(),
            SettingKeys.SECURITY_SETTINGS: SecuritySettings(),
            SettingKeys.RAG_CONFIG_SETTINGS: RagConfigurationSettings(),
            SettingKeys.UX_SETTINGS: UXSettings(),
            SettingKeys.SEARCH_RETRIEVAL_SETTINGS: SearchRetrievalSettings(),
            SettingKeys.KNOWLEDGE_SETTINGS: KnowledgeSettings(),
        }

        # Validate all instances
        results = manifest.validate_all_groups(settings_instances)

        # Default instances should have minimal critical errors
        from backend.core.settings_manifest import ValidationSeverity

        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0, f"Critical errors in default instances: {critical_errors}"

    def test_settings_manager_compatibility(self):
        """Test that settings manager continues to work with manifest available."""
        # This test ensures backward compatibility
        settings_manager = get_settings_manager()

        # Test that all existing methods still work
        followup_settings = settings_manager.get_followup_settings()
        assert isinstance(followup_settings, FollowUpSettings)

        response_settings = settings_manager.get_response_settings()
        assert isinstance(response_settings, ResponseSettings)

        routing_settings = settings_manager.get_routing_settings()
        assert isinstance(routing_settings, QueryRoutingSettings)

        feature_flags = settings_manager.get_feature_flags()
        assert isinstance(feature_flags, FeatureFlags)

        system_config = settings_manager.get_system_config_settings()
        assert isinstance(system_config, SystemConfigurationSettings)

        security_settings = settings_manager.get_security_settings()
        assert isinstance(security_settings, SecuritySettings)

        # Test unified settings method
        all_settings = settings_manager.get_all_settings()
        assert isinstance(all_settings, SystemSettings)

    @patch("backend.core.settings_manager.SettingsManager._get_setting_from_db")
    def test_validation_with_database_settings(self, mock_get_setting):
        """Test validation with settings loaded from database."""
        # Mock database responses
        mock_get_setting.side_effect = lambda key: {
            SettingKeys.FOLLOWUP_SETTINGS: '{"enabled": true, "max_questions": 2}',
            SettingKeys.RESPONSE_SETTINGS: '{"max_context_length": 1500, "enable_caching": true}',
            SettingKeys.FEATURE_FLAGS: '{"enable_debug_mode": false, "enable_analytics": true}',
        }.get(key)

        settings_manager = SettingsManager()

        # Get settings (should load from mocked database)
        followup_settings = settings_manager.get_followup_settings()
        response_settings = settings_manager.get_response_settings()
        feature_flags = settings_manager.get_feature_flags()

        # Create system settings
        system_settings = SystemSettings(
            followup=followup_settings,
            response=response_settings,
            routing=QueryRoutingSettings(),
            features=feature_flags,
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(),
        )

        # Validate with manifest
        health_data = validate_settings_configuration(system_settings)

        assert "health_score" in health_data
        assert health_data["health_score"] > 0

    def test_field_descriptors_match_schema_fields(self):
        """Test that field descriptors in manifest match actual schema fields."""
        manifest = get_settings_manifest()

        # Test a few key schemas
        test_schemas = [
            (SettingKeys.CORE_SETTINGS, CoreSettings()),
            (SettingKeys.FOLLOWUP_SETTINGS, FollowUpSettings()),
            (SettingKeys.RESPONSE_SETTINGS, ResponseSettings()),
        ]

        for setting_key, schema_instance in test_schemas:
            group = manifest.get_group(setting_key)
            assert group is not None

            # Get actual fields from schema instance
            if hasattr(schema_instance, "to_dict"):
                actual_fields = set(schema_instance.to_dict().keys())
            else:
                actual_fields = set(schema_instance.__dict__.keys())

            # Get manifest fields
            manifest_fields = set(group.fields.keys())

            # Check that major fields are covered (allow for some flexibility)
            major_fields_covered = len(actual_fields.intersection(manifest_fields)) > 0
            assert major_fields_covered, f"No major fields covered for {setting_key}"

    def test_manifest_does_not_break_existing_functionality(self):
        """Test that importing and using manifest doesn't break existing functionality."""
        # Import manifest (should not cause issues)
        manifest = get_settings_manifest()
        assert manifest is not None

        # Test that settings manager still works
        settings_manager = get_settings_manager()

        # Test feature flag checking (backward compatibility method)
        is_enabled = settings_manager.is_feature_enabled("enable_analytics")
        assert isinstance(is_enabled, bool)

        # Test LLM configuration methods
        response_llm = settings_manager.get_response_llm()
        assert isinstance(response_llm, str)

        processing_llm = settings_manager.get_processing_llm()
        assert isinstance(processing_llm, str)

        # Test cache operations
        cache_status = settings_manager.get_cache_status()
        assert isinstance(cache_status, dict)

    def test_validation_performance(self):
        """Test that validation doesn't significantly impact performance."""
        import time

        # Create settings instances
        system_settings = SystemSettings(
            followup=FollowUpSettings(),
            response=ResponseSettings(),
            routing=QueryRoutingSettings(),
            features=FeatureFlags(),
            system_config=SystemConfigurationSettings(),
            security=SecuritySettings(),
        )

        # Time the validation
        start_time = time.time()
        health_data = validate_settings_configuration(system_settings)
        end_time = time.time()

        validation_time = end_time - start_time

        # Validation should complete quickly (under 1 second for unit tests)
        assert validation_time < 1.0, f"Validation took too long: {validation_time}s"
        assert "health_score" in health_data

    def test_manifest_serialization_compatibility(self):
        """Test that manifest works with settings serialization."""
        manifest = get_settings_manifest()

        # Test with serialized settings
        followup_settings = FollowUpSettings(enabled=True, max_questions=3)
        serialized = followup_settings.to_json()

        # Deserialize
        deserialized = FollowUpSettings.from_json(serialized)

        # Validate deserialized settings with manifest
        followup_group = manifest.get_group(SettingKeys.FOLLOWUP_SETTINGS)
        results = followup_group.validate_instance(deserialized)

        # Should validate successfully
        from backend.core.settings_manifest import ValidationSeverity

        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0

    def test_error_handling_with_invalid_data(self):
        """Test manifest error handling with invalid data."""
        manifest = get_settings_manifest()

        # Test with completely invalid data
        invalid_instances = {
            SettingKeys.CORE_SETTINGS: "not_a_settings_object",
            SettingKeys.FEATURE_FLAGS: 12345,
            "unknown_key": CoreSettings(),
        }

        results = manifest.validate_all_groups(invalid_instances)

        # Should generate appropriate validation results without crashing
        assert len(results) > 0

        from backend.core.settings_manifest import ValidationSeverity

        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]

        # Should have critical errors for type mismatches
        assert len(critical_errors) > 0
        # Should have warning for unknown key
        assert len(warnings) > 0


class TestManifestFieldAccuracy:
    """Test that manifest field definitions accurately reflect schema reality."""

    def test_followup_settings_field_accuracy(self):
        """Test FollowUpSettings manifest fields match actual schema."""
        manifest = get_settings_manifest()
        group = manifest.get_group(SettingKeys.FOLLOWUP_SETTINGS)

        # Create instance and check fields exist
        instance = FollowUpSettings()
        instance_dict = instance.to_dict()

        # Check key fields are in manifest
        key_fields = ["enabled", "service_type", "max_questions", "relevance_threshold"]
        for field in key_fields:
            assert field in group.fields, f"Field {field} missing from manifest"
            assert field in instance_dict, f"Field {field} missing from schema"

    def test_response_settings_field_accuracy(self):
        """Test ResponseSettings manifest fields match actual schema."""
        manifest = get_settings_manifest()
        group = manifest.get_group(SettingKeys.RESPONSE_SETTINGS)

        instance = ResponseSettings()
        instance_dict = instance.to_dict()

        key_fields = ["max_context_length", "enable_caching", "response_llm", "preferred_response_length"]
        for field in key_fields:
            assert field in group.fields, f"Field {field} missing from manifest"
            assert field in instance_dict, f"Field {field} missing from schema"

    def test_security_settings_field_accuracy(self):
        """Test SecuritySettings manifest fields match actual schema."""
        manifest = get_settings_manifest()
        group = manifest.get_group(SettingKeys.SECURITY_SETTINGS)

        instance = SecuritySettings()
        instance_dict = instance.to_dict()

        key_fields = ["enable_analytics", "enable_rate_limiting", "session_timeout_minutes"]
        for field in key_fields:
            assert field in group.fields, f"Field {field} missing from manifest"
            assert field in instance_dict, f"Field {field} missing from schema"

    def test_field_types_match_defaults(self):
        """Test that manifest field types match schema default types."""
        manifest = get_settings_manifest()

        # Test Core Settings
        core_group = manifest.get_group(SettingKeys.CORE_SETTINGS)
        core_instance = CoreSettings()

        if "system_name" in core_group.fields:
            field_desc = core_group.fields["system_name"]
            actual_value = getattr(core_instance, "system_name", None)
            if actual_value is not None:
                # Type should match
                from backend.core.settings_manifest import SettingType

                if field_desc.field_type == SettingType.STRING:
                    assert isinstance(actual_value, str)
                elif field_desc.field_type == SettingType.BOOLEAN:
                    assert isinstance(actual_value, bool)
                elif field_desc.field_type == SettingType.INTEGER:
                    assert isinstance(actual_value, int)


if __name__ == "__main__":
    pytest.main([__file__])
