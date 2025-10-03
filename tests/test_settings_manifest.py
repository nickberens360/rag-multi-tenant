"""
Unit tests for settings manifest and validation system.

Tests the centralized settings manifest functionality including:
- Field descriptor validation
- Settings group validation
- Manifest registration and retrieval
- Cross-field validation logic
"""

import pytest

from backend.core.settings_manifest import (
    FieldDescriptor,
    SettingCategory,
    SettingsGroupDescriptor,
    SettingsManifest,
    SettingType,
    ValidationResult,
    ValidationSeverity,
    get_settings_manifest,
)
from backend.core.settings_schemas import CoreSettings, FeatureFlags, FollowUpSettings, ResponseSettings, SettingKeys


class TestFieldDescriptor:
    """Test FieldDescriptor validation logic."""

    def test_boolean_field_validation(self):
        """Test boolean field validation."""
        field = FieldDescriptor(
            name="test_bool",
            field_type=SettingType.BOOLEAN,
            default_value=True,
            description="Test boolean field",
        )

        # Valid boolean
        results = field.validate_value(True)
        assert len(results) == 0

        results = field.validate_value(False)
        assert len(results) == 0

        # Invalid type
        results = field.validate_value("true")
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "Expected boolean" in results[0].message

    def test_integer_field_validation(self):
        """Test integer field validation with range rules."""
        field = FieldDescriptor(
            name="test_int",
            field_type=SettingType.INTEGER,
            default_value=10,
            description="Test integer field",
            validation_rules={"min_value": 1, "max_value": 100},
        )

        # Valid integer within range
        results = field.validate_value(50)
        assert len(results) == 0

        # Valid edge cases
        results = field.validate_value(1)
        assert len(results) == 0

        results = field.validate_value(100)
        assert len(results) == 0

        # Invalid type
        results = field.validate_value("10")
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR

        # Invalid range
        results = field.validate_value(0)
        assert len(results) == 1
        assert "below minimum" in results[0].message

        results = field.validate_value(101)
        assert len(results) == 1
        assert "exceeds maximum" in results[0].message

    def test_float_field_validation(self):
        """Test float field validation with range rules."""
        field = FieldDescriptor(
            name="test_float",
            field_type=SettingType.FLOAT,
            default_value=0.5,
            description="Test float field",
            validation_rules={"min_value": 0.0, "max_value": 1.0},
        )

        # Valid float
        results = field.validate_value(0.7)
        assert len(results) == 0

        # Valid integer (should be accepted for float)
        results = field.validate_value(1)
        assert len(results) == 0

        # Invalid range
        results = field.validate_value(-0.1)
        assert len(results) == 1
        assert "below minimum" in results[0].message

        results = field.validate_value(1.1)
        assert len(results) == 1
        assert "exceeds maximum" in results[0].message

    def test_string_field_validation(self):
        """Test string field validation with length and pattern rules."""
        field = FieldDescriptor(
            name="test_string",
            field_type=SettingType.STRING,
            default_value="test",
            description="Test string field",
            validation_rules={
                "min_length": 2,
                "max_length": 10,
                "allowed_values": ["test", "example", "demo"],
            },
        )

        # Valid string
        results = field.validate_value("test")
        assert len(results) == 0

        # Invalid length
        results = field.validate_value("x")
        assert len(results) >= 1
        assert any("below minimum" in r.message for r in results)

        results = field.validate_value("this_is_too_long")
        assert len(results) >= 1
        assert any("exceeds maximum" in r.message for r in results)

        # Invalid value
        results = field.validate_value("invalid")
        assert len(results) >= 1
        assert any("not in allowed values" in r.message for r in results)

    def test_pattern_validation(self):
        """Test regex pattern validation for strings."""
        field = FieldDescriptor(
            name="version",
            field_type=SettingType.STRING,
            default_value="1.0",
            description="Version string",
            validation_rules={"pattern": r"^\d+\.\d+(\.\d+)?$"},
        )

        # Valid patterns
        results = field.validate_value("1.0")
        assert len(results) == 0

        results = field.validate_value("2.1.3")
        assert len(results) == 0

        # Invalid pattern
        results = field.validate_value("invalid_version")
        assert len(results) == 1
        assert "does not match pattern" in results[0].message

    def test_list_field_validation(self):
        """Test list field validation."""
        field = FieldDescriptor(
            name="test_list",
            field_type=SettingType.LIST,
            default_value=[],
            description="Test list field",
            validation_rules={"min_length": 1, "max_length": 5},
        )

        # Valid list
        results = field.validate_value(["item1", "item2"])
        assert len(results) == 0

        # Invalid type
        results = field.validate_value("not_a_list")
        assert len(results) == 1
        assert "Expected list" in results[0].message

        # Invalid length
        results = field.validate_value([])
        assert len(results) == 1
        assert "below minimum" in results[0].message


class TestSettingsGroupDescriptor:
    """Test SettingsGroupDescriptor functionality."""

    def test_group_descriptor_creation(self):
        """Test creating a settings group descriptor."""
        fields = {
            "enabled": FieldDescriptor(
                name="enabled",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable feature",
            )
        }

        group = SettingsGroupDescriptor(
            key="test_group",
            name="Test Group",
            category=SettingCategory.FEATURES,
            schema_class=FeatureFlags,
            description="Test settings group",
            fields=fields,
        )

        assert group.key == "test_group"
        assert group.name == "Test Group"
        assert group.category == SettingCategory.FEATURES
        assert group.schema_class == FeatureFlags
        assert len(group.fields) == 1

    def test_validate_instance_with_valid_data(self):
        """Test validating a valid settings instance."""
        fields = {
            "enabled": FieldDescriptor(
                name="enabled",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable feature",
            )
        }

        group = SettingsGroupDescriptor(
            key="test_group",
            name="Test Group",
            category=SettingCategory.FEATURES,
            schema_class=FeatureFlags,
            description="Test settings group",
            fields=fields,
        )

        # Create valid instance
        instance = FeatureFlags(enable_debug_mode=True)
        results = group.validate_instance(instance)

        # Should have no errors (some fields may be missing but not required)
        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0

    def test_validate_instance_with_wrong_type(self):
        """Test validating an instance of wrong type."""
        fields = {
            "enabled": FieldDescriptor(
                name="enabled",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable feature",
            )
        }

        group = SettingsGroupDescriptor(
            key="test_group",
            name="Test Group",
            category=SettingCategory.FEATURES,
            schema_class=FeatureFlags,
            description="Test settings group",
            fields=fields,
        )

        # Wrong type instance
        instance = "not_a_settings_object"
        results = group.validate_instance(instance)

        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.CRITICAL
        assert "Expected FeatureFlags" in results[0].message


class TestSettingsManifest:
    """Test SettingsManifest functionality."""

    def test_manifest_initialization(self):
        """Test that manifest initializes with all expected groups."""
        manifest = SettingsManifest()
        groups = manifest.get_all_groups()

        # Should have all the main settings groups
        expected_keys = [
            SettingKeys.CORE_SETTINGS,
            SettingKeys.FEATURE_FLAGS,
            SettingKeys.FOLLOWUP_SETTINGS,
            SettingKeys.RESPONSE_SETTINGS,
            SettingKeys.ROUTING_SETTINGS,
            SettingKeys.SYSTEM_CONFIG_SETTINGS,
            SettingKeys.SECURITY_SETTINGS,
            SettingKeys.RAG_CONFIG_SETTINGS,
            SettingKeys.UX_SETTINGS,
            SettingKeys.SEARCH_RETRIEVAL_SETTINGS,
            SettingKeys.KNOWLEDGE_SETTINGS,
        ]

        for key in expected_keys:
            assert key in groups, f"Missing settings group: {key}"

        # Verify each group has proper metadata
        for group in groups.values():
            assert group.key
            assert group.name
            assert group.category
            assert group.schema_class
            assert group.description
            assert isinstance(group.fields, dict)

    def test_get_group(self):
        """Test retrieving a specific settings group."""
        manifest = SettingsManifest()

        core_group = manifest.get_group(SettingKeys.CORE_SETTINGS)
        assert core_group is not None
        assert core_group.key == SettingKeys.CORE_SETTINGS
        assert core_group.schema_class == CoreSettings

        # Non-existent group
        invalid_group = manifest.get_group("non_existent")
        assert invalid_group is None

    def test_get_groups_by_category(self):
        """Test retrieving groups by category."""
        manifest = SettingsManifest()

        feature_groups = manifest.get_groups_by_category(SettingCategory.FEATURES)
        assert len(feature_groups) > 0

        # Check that all returned groups have the correct category
        for group in feature_groups:
            assert group.category == SettingCategory.FEATURES

        # Test empty category
        manifest.get_groups_by_category(SettingCategory.AI_MODELS)
        # This category might be empty or have groups depending on implementation

    def test_get_all_categories(self):
        """Test retrieving all categories."""
        manifest = SettingsManifest()

        categories = manifest.get_all_categories()
        assert len(categories) > 0

        # Should include major categories
        expected_categories = [
            SettingCategory.CORE,
            SettingCategory.FEATURES,
            SettingCategory.RESPONSE_GENERATION,
            SettingCategory.SECURITY,
            SettingCategory.SYSTEM_CONFIG,
        ]

        for category in expected_categories:
            assert category in categories

    def test_validate_all_groups(self):
        """Test validating multiple settings groups."""
        manifest = SettingsManifest()

        # Create valid settings instances
        settings_instances = {
            SettingKeys.CORE_SETTINGS: CoreSettings(),
            SettingKeys.FEATURE_FLAGS: FeatureFlags(),
            SettingKeys.FOLLOWUP_SETTINGS: FollowUpSettings(),
            SettingKeys.RESPONSE_SETTINGS: ResponseSettings(),
        }

        results = manifest.validate_all_groups(settings_instances)

        # Should have minimal errors for default instances
        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0

    def test_validate_with_unknown_group(self):
        """Test validation with unknown settings group."""
        manifest = SettingsManifest()

        settings_instances = {
            "unknown_group": CoreSettings(),
        }

        results = manifest.validate_all_groups(settings_instances)
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.WARNING
        assert "Unknown settings group" in results[0].message

    def test_get_validation_summary(self):
        """Test validation result summary generation."""
        manifest = SettingsManifest()

        # Create some validation results
        results = [
            ValidationResult(
                field_name="test1",
                severity=ValidationSeverity.ERROR,
                message="Test error",
            ),
            ValidationResult(
                field_name="test2",
                severity=ValidationSeverity.WARNING,
                message="Test warning",
            ),
            ValidationResult(
                field_name="test3",
                severity=ValidationSeverity.INFO,
                message="Test info",
            ),
        ]

        summary = manifest.get_validation_summary(results)

        assert summary["total_issues"] == 3
        assert summary["errors"] == 1
        assert summary["warnings"] == 1
        assert summary["info"] == 1
        assert summary["critical"] == 0
        assert summary["is_valid"] == False  # Has errors

    def test_get_deprecated_fields(self):
        """Test retrieving deprecated fields."""
        manifest = SettingsManifest()

        deprecated = manifest.get_deprecated_fields()

        # Should be a list of tuples (group_key, field_name, migration_notes)
        assert isinstance(deprecated, list)

        # Check format of each item
        for item in deprecated:
            assert isinstance(item, tuple)
            assert len(item) == 3
            group_key, field_name, migration_notes = item
            assert isinstance(group_key, str)
            assert isinstance(field_name, str)
            assert isinstance(migration_notes, str)

    def test_get_manifest_info(self):
        """Test getting manifest summary information."""
        manifest = SettingsManifest()

        info = manifest.get_manifest_info()

        assert "total_groups" in info
        assert "total_fields" in info
        assert "categories" in info
        assert "groups" in info
        assert "deprecated_fields" in info

        assert info["total_groups"] > 0
        assert info["total_fields"] > 0
        assert len(info["categories"]) > 0
        assert len(info["groups"]) > 0

    def test_global_manifest_instance(self):
        """Test global manifest instance."""
        manifest1 = get_settings_manifest()
        manifest2 = get_settings_manifest()

        # Should return the same instance
        assert manifest1 is manifest2

        # Should be properly initialized
        groups = manifest1.get_all_groups()
        assert len(groups) > 0


class TestRealSettingsValidation:
    """Test validation with real settings instances."""

    def test_core_settings_validation(self):
        """Test validation of CoreSettings instance."""
        manifest = SettingsManifest()
        core_group = manifest.get_group(SettingKeys.CORE_SETTINGS)

        # Valid instance
        settings = CoreSettings(
            system_name="Test System",
            version="1.0.0",
            default_model="claude-3-sonnet",
        )

        results = core_group.validate_instance(settings)
        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0

    def test_followup_settings_validation(self):
        """Test validation of FollowUpSettings instance."""
        manifest = SettingsManifest()
        followup_group = manifest.get_group(SettingKeys.FOLLOWUP_SETTINGS)

        # Valid instance
        settings = FollowUpSettings(
            enabled=True,
            service_type="dynamic",
            max_questions=3,
            relevance_threshold=0.8,
        )

        results = followup_group.validate_instance(settings)
        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0

    def test_response_settings_validation(self):
        """Test validation of ResponseSettings instance."""
        manifest = SettingsManifest()
        response_group = manifest.get_group(SettingKeys.RESPONSE_SETTINGS)

        # Valid instance
        settings = ResponseSettings(
            max_context_length=3000,
            max_context_documents=5,
            preferred_response_length="detailed",
            response_style="professional",
        )

        results = response_group.validate_instance(settings)
        critical_errors = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) == 0

    def test_invalid_settings_validation(self):
        """Test validation with invalid settings values."""
        manifest = SettingsManifest()
        followup_group = manifest.get_group(SettingKeys.FOLLOWUP_SETTINGS)

        # Create settings with invalid values
        settings = FollowUpSettings(
            max_questions=10,  # Exceeds max of 5
            relevance_threshold=1.5,  # Exceeds max of 1.0
            service_type="invalid_type",  # Not in allowed values
        )

        results = followup_group.validate_instance(settings)

        # Should have validation errors
        errors = [r for r in results if r.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]]
        assert len(errors) > 0

        # Check specific error messages
        error_messages = [r.message for r in errors]
        assert any("exceeds maximum" in msg for msg in error_messages)
        assert any("not in allowed values" in msg for msg in error_messages)


if __name__ == "__main__":
    pytest.main([__file__])
