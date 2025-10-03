"""
Centralized settings manifest and validation system.

This module provides a unified registry and validation framework for all settings
without changing existing runtime behavior or schemas. It acts as a metadata layer
that describes the complete settings architecture.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type

from .settings_schemas import (
    CoreSettings,
    FeatureFlags,
    FollowUpSettings,
    KnowledgeSettings,
    QueryRoutingSettings,
    RagConfigurationSettings,
    ResponseSettings,
    SearchRetrievalSettings,
    SecuritySettings,
    SettingKeys,
    SystemConfigurationSettings,
    UXSettings,
)

logger = logging.getLogger(__name__)


class SettingCategory(Enum):
    """Categories for organizing settings by functional domain."""

    CORE = "core"
    USER_EXPERIENCE = "user_experience"
    FEATURES = "features"
    SYSTEM_CONFIG = "system_config"
    SECURITY = "security"
    AI_MODELS = "ai_models"
    KNOWLEDGE = "knowledge"
    SEARCH_RETRIEVAL = "search_retrieval"
    RESPONSE_GENERATION = "response_generation"
    QUERY_ROUTING = "query_routing"
    RAG_CONFIG = "rag_config"


class SettingType(Enum):
    """Types of individual settings."""

    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"


class ValidationSeverity(Enum):
    """Severity levels for validation results."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class FieldDescriptor:
    """Metadata descriptor for individual setting fields."""

    name: str
    field_type: SettingType
    default_value: Any
    description: str
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    is_required: bool = True
    is_user_configurable: bool = True
    is_runtime_configurable: bool = True
    deprecated: bool = False
    migration_notes: Optional[str] = None

    def validate_value(self, value: Any) -> List["ValidationResult"]:
        """Validate a field value against its rules."""
        results = []

        # Type validation
        type_valid, type_msg = self._validate_type(value)
        if not type_valid:
            results.append(
                ValidationResult(
                    field_name=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=type_msg,
                    current_value=value,
                    expected_type=self.field_type.value,
                )
            )
            return results  # Skip further validation if type is wrong

        # Rule-based validation
        for rule_name, rule_config in self.validation_rules.items():
            rule_valid, rule_msg = self._validate_rule(value, rule_name, rule_config)
            if not rule_valid:
                # Determine severity - only dict rule configs can have critical flag
                severity = ValidationSeverity.ERROR
                if isinstance(rule_config, dict) and rule_config.get("critical", False):
                    severity = ValidationSeverity.ERROR
                elif not isinstance(rule_config, dict):
                    severity = ValidationSeverity.WARNING
                else:
                    severity = ValidationSeverity.WARNING

                results.append(
                    ValidationResult(
                        field_name=self.name,
                        severity=severity,
                        message=rule_msg,
                        current_value=value,
                        rule_name=rule_name,
                    )
                )

        return results

    def _validate_type(self, value: Any) -> tuple[bool, str]:
        """Validate field type."""
        if self.field_type == SettingType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Expected boolean, got {type(value).__name__}"
        elif self.field_type == SettingType.INTEGER:
            if not isinstance(value, int):
                return False, f"Expected integer, got {type(value).__name__}"
        elif self.field_type == SettingType.FLOAT:
            if not isinstance(value, (int, float)):
                return False, f"Expected float, got {type(value).__name__}"
        elif self.field_type == SettingType.STRING:
            if not isinstance(value, str):
                return False, f"Expected string, got {type(value).__name__}"
        elif self.field_type == SettingType.LIST:
            if not isinstance(value, list):
                return False, f"Expected list, got {type(value).__name__}"
        elif self.field_type == SettingType.DICT:
            if not isinstance(value, dict):
                return False, f"Expected dict, got {type(value).__name__}"

        return True, ""

    def _validate_rule(self, value: Any, rule_name: str, rule_config: Any) -> tuple[bool, str]:
        """Validate specific rule."""
        if rule_name == "min_value" and isinstance(value, (int, float)):
            if value < rule_config:
                return False, f"Value {value} is below minimum {rule_config}"
        elif rule_name == "max_value" and isinstance(value, (int, float)):
            if value > rule_config:
                return False, f"Value {value} exceeds maximum {rule_config}"
        elif rule_name == "min_length" and isinstance(value, (str, list)):
            if len(value) < rule_config:
                return False, f"Length {len(value)} is below minimum {rule_config}"
        elif rule_name == "max_length" and isinstance(value, (str, list)):
            if len(value) > rule_config:
                return False, f"Length {len(value)} exceeds maximum {rule_config}"
        elif rule_name == "allowed_values" and isinstance(rule_config, list):
            if value not in rule_config:
                return False, f"Value '{value}' not in allowed values: {rule_config}"
        elif rule_name == "pattern" and isinstance(value, str):
            import re

            if not re.match(rule_config, value):
                return False, f"Value '{value}' does not match pattern '{rule_config}'"

        return True, ""


@dataclass
class ValidationResult:
    """Result of a validation check."""

    field_name: str
    severity: ValidationSeverity
    message: str
    current_value: Any = None
    expected_type: Optional[str] = None
    rule_name: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class SettingsGroupDescriptor:
    """Metadata descriptor for a settings group/schema."""

    key: str
    name: str
    category: SettingCategory
    schema_class: Type
    description: str
    fields: Dict[str, FieldDescriptor] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    version: str = "1.0"
    is_legacy: bool = False
    migration_path: Optional[str] = None

    def validate_instance(self, instance: Any) -> List[ValidationResult]:
        """Validate a settings instance against this descriptor."""
        results = []

        if not isinstance(instance, self.schema_class):
            results.append(
                ValidationResult(
                    field_name="__root__",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Expected {self.schema_class.__name__}, got {type(instance).__name__}",
                    current_value=type(instance).__name__,
                )
            )
            return results

        # Validate each field
        instance_dict = instance.to_dict() if hasattr(instance, "to_dict") else instance.__dict__

        for field_name, field_descriptor in self.fields.items():
            if field_name in instance_dict:
                field_results = field_descriptor.validate_value(instance_dict[field_name])
                results.extend(field_results)
            elif field_descriptor.is_required:
                results.append(
                    ValidationResult(
                        field_name=field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Required field '{field_name}' is missing",
                    )
                )

        return results


class SettingsManifest:
    """
    Centralized manifest of all settings in the system.

    Provides metadata, validation, and introspection capabilities
    without changing runtime behavior.
    """

    def __init__(self):
        self._groups: Dict[str, SettingsGroupDescriptor] = {}
        self._initialize_manifest()

    def _initialize_manifest(self) -> None:
        """Initialize the manifest with all known settings groups."""
        # Core Settings
        self._register_core_settings()
        # Feature Flags
        self._register_feature_flags()
        # Follow-up Settings
        self._register_followup_settings()
        # Response Settings
        self._register_response_settings()
        # Query Routing Settings
        self._register_routing_settings()
        # System Configuration Settings
        self._register_system_config_settings()
        # Security Settings
        self._register_security_settings()
        # RAG Configuration Settings
        self._register_rag_config_settings()
        # UX Settings
        self._register_ux_settings()
        # Search Retrieval Settings
        self._register_search_retrieval_settings()
        # Knowledge Settings
        self._register_knowledge_settings()

    def _register_core_settings(self) -> None:
        """Register CoreSettings metadata."""
        fields = {
            "system_name": FieldDescriptor(
                name="system_name",
                field_type=SettingType.STRING,
                default_value="Nick Berens AI Assistant",
                description="Display name for the AI assistant",
                validation_rules={"min_length": 1, "max_length": 100},
            ),
            "version": FieldDescriptor(
                name="version",
                field_type=SettingType.STRING,
                default_value="2.0",
                description="System version identifier",
                validation_rules={"pattern": r"^\d+\.\d+(\.\d+)?$"},
            ),
            "default_model": FieldDescriptor(
                name="default_model",
                field_type=SettingType.STRING,
                default_value="claude-3-sonnet",
                description="Default LLM model for processing",
                validation_rules={
                    "allowed_values": [
                        "claude-3-sonnet",
                        "claude-3-opus",
                        "claude-3-haiku",
                        "gemini-pro",
                        "gemini-1.5-pro",
                    ]
                },
            ),
            "anthropic_api_key_configured": FieldDescriptor(
                name="anthropic_api_key_configured",
                field_type=SettingType.BOOLEAN,
                default_value=False,
                description="Whether Anthropic API key is configured",
                is_user_configurable=False,
            ),
            "google_api_key_configured": FieldDescriptor(
                name="google_api_key_configured",
                field_type=SettingType.BOOLEAN,
                default_value=False,
                description="Whether Google API key is configured",
                is_user_configurable=False,
            ),
        }

        self._groups[SettingKeys.CORE_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.CORE_SETTINGS,
            name="Core Settings",
            category=SettingCategory.CORE,
            schema_class=CoreSettings,
            description="Core system configuration and identification",
            fields=fields,
        )

    def _register_feature_flags(self) -> None:
        """Register FeatureFlags metadata."""
        boolean_features = [
            ("enable_debug_mode", "Enable debug mode for development"),
            ("enable_maintenance_mode", "Enable maintenance mode"),
            ("enable_api_versioning", "Enable API versioning support"),
            ("enable_followup_questions", "Enable follow-up question generation"),
            ("enable_smart_routing", "Enable intelligent query routing"),
            ("enable_caching", "Enable general caching"),
            ("enable_response_caching", "Enable response caching"),
            ("enable_analytics", "Enable analytics and monitoring"),
            ("enable_rate_limiting", "Enable rate limiting protection"),
            ("enable_illustrations", "Enable illustration support"),
            ("enable_geolocation", "Enable geolocation features"),
            ("enable_query_preprocessing", "Enable query preprocessing"),
        ]

        fields = {}
        for field_name, description in boolean_features:
            fields[field_name] = FieldDescriptor(
                name=field_name,
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description=description,
            )

        # Special cases for debug and maintenance mode
        fields["enable_debug_mode"].default_value = False
        fields["enable_maintenance_mode"].default_value = False
        fields["enable_api_versioning"].default_value = False

        self._groups[SettingKeys.FEATURE_FLAGS] = SettingsGroupDescriptor(
            key=SettingKeys.FEATURE_FLAGS,
            name="Feature Flags",
            category=SettingCategory.FEATURES,
            schema_class=FeatureFlags,
            description="Feature toggles for enabling/disabling system capabilities",
            fields=fields,
        )

    def _register_followup_settings(self) -> None:
        """Register FollowUpSettings metadata."""
        fields = {
            "enabled": FieldDescriptor(
                name="enabled",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Whether follow-up questions are enabled",
            ),
            "service_type": FieldDescriptor(
                name="service_type",
                field_type=SettingType.STRING,
                default_value="static",
                description="Type of follow-up service",
                validation_rules={"allowed_values": ["static", "dynamic", "contextual"]},
            ),
            "max_questions": FieldDescriptor(
                name="max_questions",
                field_type=SettingType.INTEGER,
                default_value=1,
                description="Maximum number of follow-up questions to generate",
                validation_rules={"min_value": 1, "max_value": 5},
            ),
            "relevance_threshold": FieldDescriptor(
                name="relevance_threshold",
                field_type=SettingType.FLOAT,
                default_value=0.7,
                description="Threshold for follow-up question relevance",
                validation_rules={"min_value": 0.1, "max_value": 1.0},
            ),
            "include_technical": FieldDescriptor(
                name="include_technical",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Include technical follow-up questions",
            ),
            "include_personal": FieldDescriptor(
                name="include_personal",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Include personal follow-up questions",
            ),
            "include_creative": FieldDescriptor(
                name="include_creative",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Include creative follow-up questions",
            ),
            "question_style": FieldDescriptor(
                name="question_style",
                field_type=SettingType.STRING,
                default_value="conversational",
                description="Style of follow-up questions",
                validation_rules={"allowed_values": ["formal", "conversational", "exploratory"]},
            ),
            "custom_questions": FieldDescriptor(
                name="custom_questions",
                field_type=SettingType.DICT,
                default_value={},
                description="Custom questions by category",
                is_user_configurable=True,
            ),
        }

        self._groups[SettingKeys.FOLLOWUP_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.FOLLOWUP_SETTINGS,
            name="Follow-up Settings",
            category=SettingCategory.RESPONSE_GENERATION,
            schema_class=FollowUpSettings,
            description="Configuration for follow-up question generation",
            fields=fields,
        )

    def _register_response_settings(self) -> None:
        """Register ResponseSettings metadata."""
        fields = {
            "max_context_length": FieldDescriptor(
                name="max_context_length",
                field_type=SettingType.INTEGER,
                default_value=2000,
                description="Maximum context length for responses",
                validation_rules={"min_value": 100, "max_value": 10000},
            ),
            "max_context_documents": FieldDescriptor(
                name="max_context_documents",
                field_type=SettingType.INTEGER,
                default_value=3,
                description="Maximum number of context documents",
                validation_rules={"min_value": 1, "max_value": 10},
            ),
            "context_fill_ratio": FieldDescriptor(
                name="context_fill_ratio",
                field_type=SettingType.FLOAT,
                default_value=0.7,
                description="Ratio of context to fill",
                validation_rules={"min_value": 0.1, "max_value": 1.0},
            ),
            "enable_caching": FieldDescriptor(
                name="enable_caching",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable general caching",
            ),
            "enable_response_caching": FieldDescriptor(
                name="enable_response_caching",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable response-specific caching",
            ),
            "cache_ttl_seconds": FieldDescriptor(
                name="cache_ttl_seconds",
                field_type=SettingType.INTEGER,
                default_value=3600,
                description="Cache TTL in seconds",
                validation_rules={"min_value": 60, "max_value": 86400},
            ),
            "preferred_response_length": FieldDescriptor(
                name="preferred_response_length",
                field_type=SettingType.STRING,
                default_value="medium",
                description="Preferred response length",
                validation_rules={"allowed_values": ["brief", "medium", "detailed", "comprehensive"]},
            ),
            "response_style": FieldDescriptor(
                name="response_style",
                field_type=SettingType.STRING,
                default_value="conversational",
                description="Response style preference",
                validation_rules={"allowed_values": ["professional", "conversational", "technical", "casual"]},
            ),
            "include_sources": FieldDescriptor(
                name="include_sources",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Include source references in responses",
            ),
            "source_format": FieldDescriptor(
                name="source_format",
                field_type=SettingType.STRING,
                default_value="numbered",
                description="Format for source references",
                validation_rules={"allowed_values": ["numbered", "bulleted", "inline"]},
            ),
            "max_sources": FieldDescriptor(
                name="max_sources",
                field_type=SettingType.INTEGER,
                default_value=5,
                description="Maximum number of sources to include",
                validation_rules={"min_value": 0, "max_value": 20},
            ),
            "response_llm": FieldDescriptor(
                name="response_llm",
                field_type=SettingType.STRING,
                default_value="claude",
                description="LLM for response generation",
                validation_rules={"allowed_values": ["claude", "gemini"]},
            ),
            "enable_smart_selection": FieldDescriptor(
                name="enable_smart_selection",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable complexity-based model switching",
            ),
        }

        self._groups[SettingKeys.RESPONSE_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.RESPONSE_SETTINGS,
            name="Response Settings",
            category=SettingCategory.RESPONSE_GENERATION,
            schema_class=ResponseSettings,
            description="Configuration for response generation and caching",
            fields=fields,
        )

    def _register_routing_settings(self) -> None:
        """Register QueryRoutingSettings metadata."""
        fields = {
            "enable_smart_routing": FieldDescriptor(
                name="enable_smart_routing",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable intelligent query routing",
            ),
            "confidence_threshold": FieldDescriptor(
                name="confidence_threshold",
                field_type=SettingType.FLOAT,
                default_value=0.75,
                description="Confidence threshold for routing decisions",
                validation_rules={"min_value": 0.0, "max_value": 1.0},
            ),
            "fallback_strategy": FieldDescriptor(
                name="fallback_strategy",
                field_type=SettingType.STRING,
                default_value="comprehensive_search",
                description="Strategy when routing confidence is low",
                validation_rules={
                    "allowed_values": [
                        "comprehensive_search",
                        "semantic_similarity",
                        "keyword_matching",
                        "default_response",
                    ]
                },
            ),
            "enable_query_caching": FieldDescriptor(
                name="enable_query_caching",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable query result caching",
            ),
            "enable_parallel_processing": FieldDescriptor(
                name="enable_parallel_processing",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable parallel query processing",
            ),
            "max_retries": FieldDescriptor(
                name="max_retries",
                field_type=SettingType.INTEGER,
                default_value=3,
                description="Maximum retry attempts for failed queries",
                validation_rules={"min_value": 0, "max_value": 10},
            ),
        }

        self._groups[SettingKeys.ROUTING_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.ROUTING_SETTINGS,
            name="Query Routing Settings",
            category=SettingCategory.QUERY_ROUTING,
            schema_class=QueryRoutingSettings,
            description="Configuration for query routing and processing",
            fields=fields,
        )

    def _register_system_config_settings(self) -> None:
        """Register SystemConfigurationSettings metadata."""
        fields = {
            "primary_llm": FieldDescriptor(
                name="primary_llm",
                field_type=SettingType.STRING,
                default_value="claude",
                description="Primary LLM (legacy - use response_llm)",
                validation_rules={"allowed_values": ["claude", "gemini"]},
                deprecated=True,
                migration_notes="Use response_llm instead",
            ),
            "response_llm": FieldDescriptor(
                name="response_llm",
                field_type=SettingType.STRING,
                default_value="claude",
                description="LLM for user-facing responses",
                validation_rules={"allowed_values": ["claude", "gemini"]},
            ),
            "processing_llm": FieldDescriptor(
                name="processing_llm",
                field_type=SettingType.STRING,
                default_value="claude_haiku",
                description="LLM for background processing",
                validation_rules={"allowed_values": ["claude_haiku", "claude", "gemini"]},
            ),
            "enable_smart_model_selection": FieldDescriptor(
                name="enable_smart_model_selection",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable intelligent model selection",
            ),
            "system_cache_ttl_seconds": FieldDescriptor(
                name="system_cache_ttl_seconds",
                field_type=SettingType.INTEGER,
                default_value=3600,
                description="System cache TTL in seconds",
                validation_rules={"min_value": 60, "max_value": 86400},
            ),
            "max_cache_size": FieldDescriptor(
                name="max_cache_size",
                field_type=SettingType.INTEGER,
                default_value=1000,
                description="Maximum cache size",
                validation_rules={"min_value": 10, "max_value": 10000},
            ),
            "rate_limit": FieldDescriptor(
                name="rate_limit",
                field_type=SettingType.STRING,
                default_value="100/minute",
                description="Rate limit specification",
                validation_rules={"pattern": r"^\d+/(minute|hour|day)$"},
            ),
        }

        self._groups[SettingKeys.SYSTEM_CONFIG_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.SYSTEM_CONFIG_SETTINGS,
            name="System Configuration",
            category=SettingCategory.SYSTEM_CONFIG,
            schema_class=SystemConfigurationSettings,
            description="Core system configuration settings",
            fields=fields,
        )

    def _register_security_settings(self) -> None:
        """Register SecuritySettings metadata."""
        fields = {
            "enable_analytics": FieldDescriptor(
                name="enable_analytics",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable analytics and monitoring",
            ),
            "enable_rate_limiting": FieldDescriptor(
                name="enable_rate_limiting",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable rate limiting protection",
            ),
            "rate_limit_requests": FieldDescriptor(
                name="rate_limit_requests",
                field_type=SettingType.INTEGER,
                default_value=100,
                description="Number of requests allowed in rate limit window",
                validation_rules={"min_value": 1, "max_value": 10000},
            ),
            "rate_limit_window": FieldDescriptor(
                name="rate_limit_window",
                field_type=SettingType.INTEGER,
                default_value=60,
                description="Rate limit window in seconds",
                validation_rules={"min_value": 1, "max_value": 3600},
            ),
            "session_timeout_minutes": FieldDescriptor(
                name="session_timeout_minutes",
                field_type=SettingType.INTEGER,
                default_value=480,
                description="Session timeout in minutes",
                validation_rules={"min_value": 30, "max_value": 1440},
            ),
            "max_login_attempts": FieldDescriptor(
                name="max_login_attempts",
                field_type=SettingType.INTEGER,
                default_value=5,
                description="Maximum login attempts before lockout",
                validation_rules={"min_value": 1, "max_value": 100},
            ),
        }

        self._groups[SettingKeys.SECURITY_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.SECURITY_SETTINGS,
            name="Security Settings",
            category=SettingCategory.SECURITY,
            schema_class=SecuritySettings,
            description="Security, privacy, and protection settings",
            fields=fields,
        )

    def _register_rag_config_settings(self) -> None:
        """Register RagConfigurationSettings metadata."""
        fields = {
            "rag_score_threshold": FieldDescriptor(
                name="rag_score_threshold",
                field_type=SettingType.FLOAT,
                default_value=0.2,
                description="Minimum score threshold for RAG results",
                validation_rules={"min_value": 0.0, "max_value": 1.0},
            ),
            "rag_use_mmr": FieldDescriptor(
                name="rag_use_mmr",
                field_type=SettingType.BOOLEAN,
                default_value=False,
                description="Use Maximal Marginal Relevance for diversity",
            ),
            "rag_mmr_k": FieldDescriptor(
                name="rag_mmr_k",
                field_type=SettingType.INTEGER,
                default_value=4,
                description="Number of documents to return with MMR",
                validation_rules={"min_value": 1, "max_value": 20},
            ),
            "rag_mmr_fetch_k": FieldDescriptor(
                name="rag_mmr_fetch_k",
                field_type=SettingType.INTEGER,
                default_value=20,
                description="Number of documents to fetch for MMR",
                validation_rules={"min_value": 10, "max_value": 100},
            ),
            "rag_mmr_lambda_mult": FieldDescriptor(
                name="rag_mmr_lambda_mult",
                field_type=SettingType.FLOAT,
                default_value=0.5,
                description="Lambda multiplier for MMR diversity",
                validation_rules={"min_value": 0.0, "max_value": 1.0},
            ),
        }

        self._groups[SettingKeys.RAG_CONFIG_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.RAG_CONFIG_SETTINGS,
            name="RAG Configuration",
            category=SettingCategory.RAG_CONFIG,
            schema_class=RagConfigurationSettings,
            description="Retrieval Augmented Generation configuration",
            fields=fields,
        )

    def _register_ux_settings(self) -> None:
        """Register UXSettings metadata."""
        fields = {
            "enable_animations": FieldDescriptor(
                name="enable_animations",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable UI animations",
            ),
            "theme_preference": FieldDescriptor(
                name="theme_preference",
                field_type=SettingType.STRING,
                default_value="auto",
                description="UI theme preference",
                validation_rules={"allowed_values": ["auto", "light", "dark"]},
            ),
            "compact_mode": FieldDescriptor(
                name="compact_mode",
                field_type=SettingType.BOOLEAN,
                default_value=False,
                description="Enable compact UI mode",
            ),
            "response_streaming": FieldDescriptor(
                name="response_streaming",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable streaming responses",
            ),
        }

        self._groups[SettingKeys.UX_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.UX_SETTINGS,
            name="UX Settings",
            category=SettingCategory.USER_EXPERIENCE,
            schema_class=UXSettings,
            description="User experience and interface customization",
            fields=fields,
        )

    def _register_search_retrieval_settings(self) -> None:
        """Register SearchRetrievalSettings metadata."""
        fields = {
            "semantic_similarity_threshold": FieldDescriptor(
                name="semantic_similarity_threshold",
                field_type=SettingType.FLOAT,
                default_value=0.55,
                description="Threshold for semantic similarity search",
                validation_rules={"min_value": 0.0, "max_value": 1.0},
            ),
            "max_search_results": FieldDescriptor(
                name="max_search_results",
                field_type=SettingType.INTEGER,
                default_value=10,
                description="Maximum number of search results",
                validation_rules={"min_value": 1, "max_value": 100},
            ),
            "search_timeout_seconds": FieldDescriptor(
                name="search_timeout_seconds",
                field_type=SettingType.INTEGER,
                default_value=30,
                description="Search timeout in seconds",
                validation_rules={"min_value": 5, "max_value": 120},
            ),
            "enable_fuzzy_matching": FieldDescriptor(
                name="enable_fuzzy_matching",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Enable fuzzy string matching",
            ),
        }

        self._groups[SettingKeys.SEARCH_RETRIEVAL_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.SEARCH_RETRIEVAL_SETTINGS,
            name="Search & Retrieval",
            category=SettingCategory.SEARCH_RETRIEVAL,
            schema_class=SearchRetrievalSettings,
            description="Search and document retrieval configuration",
            fields=fields,
        )

    def _register_knowledge_settings(self) -> None:
        """Register KnowledgeSettings metadata."""
        fields = {
            "index_on_startup": FieldDescriptor(
                name="index_on_startup",
                field_type=SettingType.BOOLEAN,
                default_value=True,
                description="Index knowledge base on startup",
            ),
            "background_sync_interval_seconds": FieldDescriptor(
                name="background_sync_interval_seconds",
                field_type=SettingType.INTEGER,
                default_value=0,
                description="Background sync interval (0 disables)",
                validation_rules={"min_value": 0, "max_value": 86400},
            ),
            "auto_reindex_deltas": FieldDescriptor(
                name="auto_reindex_deltas",
                field_type=SettingType.BOOLEAN,
                default_value=False,
                description="Automatically reindex when changes detected",
            ),
            "index_directories": FieldDescriptor(
                name="index_directories",
                field_type=SettingType.LIST,
                default_value=["backend/knowledge", "public"],
                description="Directories to index for knowledge",
            ),
        }

        self._groups[SettingKeys.KNOWLEDGE_SETTINGS] = SettingsGroupDescriptor(
            key=SettingKeys.KNOWLEDGE_SETTINGS,
            name="Knowledge Settings",
            category=SettingCategory.KNOWLEDGE,
            schema_class=KnowledgeSettings,
            description="Knowledge indexing and synchronization configuration",
            fields=fields,
        )

    # Public interface methods

    def get_all_groups(self) -> Dict[str, SettingsGroupDescriptor]:
        """Get all registered settings groups."""
        return self._groups.copy()

    def get_group(self, key: str) -> Optional[SettingsGroupDescriptor]:
        """Get a specific settings group by key."""
        return self._groups.get(key)

    def get_groups_by_category(self, category: SettingCategory) -> List[SettingsGroupDescriptor]:
        """Get all settings groups in a specific category."""
        return [group for group in self._groups.values() if group.category == category]

    def get_all_categories(self) -> Set[SettingCategory]:
        """Get all categories that have registered groups."""
        return {group.category for group in self._groups.values()}

    def validate_all_groups(self, settings_instances: Dict[str, Any]) -> List[ValidationResult]:
        """Validate all provided settings instances against their descriptors."""
        results = []

        for group_key, instance in settings_instances.items():
            group_descriptor = self.get_group(group_key)
            if group_descriptor:
                group_results = group_descriptor.validate_instance(instance)
                results.extend(group_results)
            else:
                results.append(
                    ValidationResult(
                        field_name=group_key,
                        severity=ValidationSeverity.WARNING,
                        message=f"Unknown settings group: {group_key}",
                    )
                )

        return results

    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate a summary of validation results."""
        summary = {
            "total_issues": len(results),
            "critical": len([r for r in results if r.severity == ValidationSeverity.CRITICAL]),
            "errors": len([r for r in results if r.severity == ValidationSeverity.ERROR]),
            "warnings": len([r for r in results if r.severity == ValidationSeverity.WARNING]),
            "info": len([r for r in results if r.severity == ValidationSeverity.INFO]),
            "is_valid": len(
                [r for r in results if r.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]
            )
            == 0,
        }

        return summary

    def get_deprecated_fields(self) -> List[tuple[str, str, str]]:
        """Get all deprecated fields across all groups."""
        deprecated = []
        for group_key, group in self._groups.items():
            for field_name, field_desc in group.fields.items():
                if field_desc.deprecated:
                    deprecated.append((group_key, field_name, field_desc.migration_notes or "No migration notes"))
        return deprecated

    def get_manifest_info(self) -> Dict[str, Any]:
        """Get summary information about the manifest."""
        total_fields = sum(len(group.fields) for group in self._groups.values())
        categories = self.get_all_categories()

        return {
            "total_groups": len(self._groups),
            "total_fields": total_fields,
            "categories": [cat.value for cat in categories],
            "groups": list(self._groups.keys()),
            "deprecated_fields": len(self.get_deprecated_fields()),
        }


# Global manifest instance
settings_manifest = SettingsManifest()


def get_settings_manifest() -> SettingsManifest:
    """Get the global settings manifest instance."""
    return settings_manifest
