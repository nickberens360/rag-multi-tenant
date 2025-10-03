"""
Settings schema definitions for DB-driven runtime configuration.
All settings that can be modified via admin interface are defined here.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class FollowUpSettings:
    """Configuration for follow-up question generation."""

    enabled: bool = True
    service_type: str = "static"  # static, dynamic, contextual
    max_questions: int = 1
    # New: threshold (0.1..1.0) to bias follow-up generation relevance
    relevance_threshold: float = 0.7
    include_technical: bool = True
    include_personal: bool = True
    include_creative: bool = True
    question_style: str = "conversational"  # formal, conversational, exploratory
    custom_questions: Dict[str, List[str]] = field(default_factory=dict)  # Custom questions by category

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FollowUpSettings":
        """Create from dictionary with validation."""
        # Validate and set defaults for missing keys
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Type validation
        if not isinstance(validated_data["enabled"], bool):
            validated_data["enabled"] = str(validated_data["enabled"]).lower() == "true"

        if not isinstance(validated_data["max_questions"], int):
            try:
                validated_data["max_questions"] = int(validated_data["max_questions"])
            except (ValueError, TypeError):
                validated_data["max_questions"] = defaults.max_questions

        # Ensure max_questions is within reasonable bounds
        validated_data["max_questions"] = max(1, min(5, validated_data["max_questions"]))

        # Validate relevance_threshold
        if not isinstance(validated_data.get("relevance_threshold"), (int, float)):
            try:
                validated_data["relevance_threshold"] = float(validated_data.get("relevance_threshold"))
            except (ValueError, TypeError):
                validated_data["relevance_threshold"] = defaults.relevance_threshold
        # Bound to 0.1..1.0
        validated_data["relevance_threshold"] = max(0.1, min(1.0, float(validated_data["relevance_threshold"])))

        # Validate service_type
        valid_service_types = ["static", "dynamic", "contextual"]
        if validated_data["service_type"] not in valid_service_types:
            validated_data["service_type"] = defaults.service_type

        # Validate question_style
        valid_styles = ["formal", "conversational", "exploratory"]
        if validated_data["question_style"] not in valid_styles:
            validated_data["question_style"] = defaults.question_style

        # Validate custom_questions
        if "custom_questions" in validated_data and validated_data["custom_questions"]:
            custom_questions = validated_data["custom_questions"]
            if not isinstance(custom_questions, dict):
                validated_data["custom_questions"] = {}
            else:
                # Validate categories and questions
                valid_categories = ["technical", "personal", "creative"]
                cleaned_questions = {}
                for category, questions in custom_questions.items():
                    if category in valid_categories and isinstance(questions, list):
                        # Filter and validate individual questions
                        valid_questions = []
                        for q in questions:
                            if isinstance(q, str) and q.strip() and len(q.strip()) <= 200:
                                valid_questions.append(q.strip())
                        if valid_questions:
                            cleaned_questions[category] = valid_questions[:20]  # Max 20 questions per category
                validated_data["custom_questions"] = cleaned_questions
        else:
            validated_data["custom_questions"] = {}

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "FollowUpSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse follow-up settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class ResponseSettings:
    """Configuration for response generation and caching behavior."""

    # Context settings
    max_context_length: int = 2000
    max_context_documents: int = 3
    context_fill_ratio: float = 0.7

    # Caching settings (consolidated from multiple schemas)
    enable_caching: bool = True  # General caching toggle
    enable_response_caching: bool = True  # Specific response caching
    cache_ttl_seconds: int = 3600  # Unified cache TTL
    response_cache_ttl_seconds: int = 3600  # Legacy field for backward compatibility

    # Response generation settings
    preferred_response_length: str = "medium"  # brief, medium, detailed, comprehensive
    response_style: str = "conversational"  # professional, conversational, technical, casual
    include_sources: bool = True
    source_format: str = "numbered"  # numbered, bulleted, inline
    max_sources: int = 5
    enable_markdown: bool = True
    enable_code_highlighting: bool = True

    # Response model selection (moved from system settings)
    response_llm: str = "claude"  # claude, gemini
    response_claude_model: str = "claude-3-5-sonnet-20241022"
    response_gemini_model: str = "gemini-1.5-flash"
    enable_smart_selection: bool = True  # Allow complexity-based model switching

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate max_context_length
        if not isinstance(validated_data["max_context_length"], int):
            try:
                validated_data["max_context_length"] = int(validated_data["max_context_length"])
            except (ValueError, TypeError):
                validated_data["max_context_length"] = defaults.max_context_length

        # Ensure within bounds
        validated_data["max_context_length"] = max(100, min(10000, validated_data["max_context_length"]))

        # Validate max_context_documents
        if not isinstance(validated_data["max_context_documents"], int):
            try:
                validated_data["max_context_documents"] = int(validated_data["max_context_documents"])
            except (ValueError, TypeError):
                validated_data["max_context_documents"] = defaults.max_context_documents

        validated_data["max_context_documents"] = max(1, min(10, validated_data["max_context_documents"]))

        # Validate context_fill_ratio
        if not isinstance(validated_data["context_fill_ratio"], float):
            try:
                validated_data["context_fill_ratio"] = float(validated_data["context_fill_ratio"])
            except (ValueError, TypeError):
                validated_data["context_fill_ratio"] = defaults.context_fill_ratio

        validated_data["context_fill_ratio"] = max(0.1, min(1.0, validated_data["context_fill_ratio"]))

        # Validate boolean fields
        for bool_field in [
            "enable_caching",
            "enable_response_caching",
            "include_sources",
            "enable_markdown",
            "enable_code_highlighting",
            "enable_smart_selection",
        ]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate cache TTL seconds (unified and legacy fields)
        for ttl_field in ["cache_ttl_seconds", "response_cache_ttl_seconds"]:
            if not isinstance(validated_data[ttl_field], int):
                try:
                    validated_data[ttl_field] = int(validated_data[ttl_field])
                except (ValueError, TypeError):
                    validated_data[ttl_field] = getattr(defaults, ttl_field)
            validated_data[ttl_field] = max(60, min(86400, validated_data[ttl_field]))

        # Validate response LLM settings
        valid_llms = ["claude", "gemini"]
        if validated_data["response_llm"] not in valid_llms:
            validated_data["response_llm"] = "claude"

        # Validate model selections
        valid_claude_models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        if validated_data["response_claude_model"] not in valid_claude_models:
            validated_data["response_claude_model"] = defaults.response_claude_model

        valid_gemini_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if validated_data["response_gemini_model"] not in valid_gemini_models:
            validated_data["response_gemini_model"] = defaults.response_gemini_model

        # Validate response length preference
        valid_lengths = ["brief", "medium", "detailed", "comprehensive"]
        if validated_data["preferred_response_length"] not in valid_lengths:
            validated_data["preferred_response_length"] = "medium"

        # Validate response style preference
        valid_styles = ["professional", "conversational", "technical", "casual"]
        if validated_data["response_style"] not in valid_styles:
            validated_data["response_style"] = "conversational"

        # Validate source format preference
        valid_formats = ["numbered", "bulleted", "inline"]
        if validated_data["source_format"] not in valid_formats:
            validated_data["source_format"] = "numbered"

        # Validate max_sources
        if not isinstance(validated_data["max_sources"], int):
            try:
                validated_data["max_sources"] = int(validated_data["max_sources"])
            except (ValueError, TypeError):
                validated_data["max_sources"] = defaults.max_sources

        validated_data["max_sources"] = max(0, min(20, validated_data["max_sources"]))

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ResponseSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse response settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class QueryRoutingSettings:
    """Configuration for query routing and processing."""

    # Smart routing configuration
    enable_smart_routing: bool = True
    confidence_threshold: float = 0.75
    fallback_strategy: str = (
        "comprehensive_search"  # comprehensive_search, semantic_similarity, keyword_matching, default_response
    )

    # Caching configuration
    enable_query_caching: bool = True
    query_cache_ttl_seconds: int = 300  # 5 minutes
    enable_caching: bool = True  # Legacy alias for enable_query_caching
    cache_ttl_seconds: int = 300  # Legacy alias for query_cache_ttl_seconds

    # Processing configuration
    enable_parallel_processing: bool = True
    max_retries: int = 3

    # Search configuration
    enable_fuzzy_matching: bool = True
    similarity_threshold: float = 0.5
    fuzzy_threshold: float = 0.6
    max_search_results: int = 10

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QueryRoutingSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate boolean fields
        for bool_field in [
            "enable_smart_routing",
            "enable_fuzzy_matching",
            "enable_query_caching",
            "enable_parallel_processing",
            "enable_caching",
        ]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate fallback_strategy
        valid_strategies = ["comprehensive_search", "semantic_similarity", "keyword_matching", "default_response"]
        if validated_data["fallback_strategy"] not in valid_strategies:
            validated_data["fallback_strategy"] = "comprehensive_search"

        # Validate confidence_threshold
        if not isinstance(validated_data["confidence_threshold"], (int, float)):
            try:
                validated_data["confidence_threshold"] = float(validated_data["confidence_threshold"])
            except (ValueError, TypeError):
                validated_data["confidence_threshold"] = defaults.confidence_threshold
        validated_data["confidence_threshold"] = max(0.0, min(1.0, validated_data["confidence_threshold"]))

        # Validate similarity_threshold
        if not isinstance(validated_data["similarity_threshold"], (int, float)):
            try:
                validated_data["similarity_threshold"] = float(validated_data["similarity_threshold"])
            except (ValueError, TypeError):
                validated_data["similarity_threshold"] = defaults.similarity_threshold
        validated_data["similarity_threshold"] = max(0.0, min(1.0, validated_data["similarity_threshold"]))

        # Validate fuzzy_threshold
        if not isinstance(validated_data["fuzzy_threshold"], (int, float)):
            try:
                validated_data["fuzzy_threshold"] = float(validated_data["fuzzy_threshold"])
            except (ValueError, TypeError):
                validated_data["fuzzy_threshold"] = defaults.fuzzy_threshold
        validated_data["fuzzy_threshold"] = max(0.0, min(1.0, validated_data["fuzzy_threshold"]))

        # Validate query_cache_ttl_seconds
        if not isinstance(validated_data["query_cache_ttl_seconds"], int):
            try:
                validated_data["query_cache_ttl_seconds"] = int(validated_data["query_cache_ttl_seconds"])
            except (ValueError, TypeError):
                validated_data["query_cache_ttl_seconds"] = defaults.query_cache_ttl_seconds
        validated_data["query_cache_ttl_seconds"] = max(60, min(3600, validated_data["query_cache_ttl_seconds"]))

        # Validate cache_ttl_seconds (legacy alias)
        if not isinstance(validated_data["cache_ttl_seconds"], int):
            try:
                validated_data["cache_ttl_seconds"] = int(validated_data["cache_ttl_seconds"])
            except (ValueError, TypeError):
                validated_data["cache_ttl_seconds"] = defaults.cache_ttl_seconds
        validated_data["cache_ttl_seconds"] = max(60, min(3600, validated_data["cache_ttl_seconds"]))

        # Validate max_retries
        if not isinstance(validated_data["max_retries"], int):
            try:
                validated_data["max_retries"] = int(validated_data["max_retries"])
            except (ValueError, TypeError):
                validated_data["max_retries"] = defaults.max_retries
        validated_data["max_retries"] = max(0, min(10, validated_data["max_retries"]))

        # Validate max_search_results
        if not isinstance(validated_data["max_search_results"], int):
            try:
                validated_data["max_search_results"] = int(validated_data["max_search_results"])
            except (ValueError, TypeError):
                validated_data["max_search_results"] = defaults.max_search_results
        validated_data["max_search_results"] = max(1, min(100, validated_data["max_search_results"]))

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "QueryRoutingSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse query routing settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class FeatureFlags:
    """Feature flags for enabling/disabling system features."""

    # System-wide feature flags (duplicates removed)
    enable_debug_mode: bool = False
    enable_maintenance_mode: bool = False
    enable_api_versioning: bool = False

    # Admin features
    enable_admin_diagnostics: bool = False

    # Back-compat flags expected by tests/legacy callers (mapped elsewhere at runtime)
    enable_followup_questions: bool = True
    enable_smart_routing: bool = True
    enable_caching: bool = True
    enable_response_caching: bool = True
    enable_analytics: bool = True
    enable_rate_limiting: bool = True

    # User Experience flags
    enable_illustrations: bool = True
    enable_geolocation: bool = True
    enable_query_preprocessing: bool = True

    # Note: The following have been moved to their appropriate schemas:
    # - enable_analytics -> SecuritySettings (monitoring)
    # - enable_rate_limiting -> SecuritySettings (security)
    # - enable_smart_routing -> QueryRoutingSettings (routing)
    # - enable_caching/enable_response_caching -> ResponseSettings (caching)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FeatureFlags":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Identify field types from defaults
        defaults_dict = asdict(defaults)

        for field_name, default_value in defaults_dict.items():
            current_value = validated_data[field_name]

            if isinstance(default_value, bool):
                # Validate boolean fields
                if not isinstance(current_value, bool):
                    validated_data[field_name] = str(current_value).lower() == "true"
            elif isinstance(default_value, int):
                # Validate integer fields
                if not isinstance(current_value, int):
                    try:
                        validated_data[field_name] = int(current_value)
                    except (ValueError, TypeError):
                        validated_data[field_name] = default_value

            elif isinstance(default_value, float):
                # Validate float fields
                if not isinstance(current_value, (int, float)):
                    try:
                        validated_data[field_name] = float(current_value)
                    except (ValueError, TypeError):
                        validated_data[field_name] = default_value
                else:
                    validated_data[field_name] = float(current_value)

            elif isinstance(default_value, str):
                # Validate string fields
                if not isinstance(current_value, str):
                    validated_data[field_name] = str(current_value)

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "FeatureFlags":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse feature flags from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class SystemConfigurationSettings:
    """Configuration for core system settings."""

    # LLM Configuration (Legacy - use response_llm instead)
    primary_llm: str = "claude"  # claude, gemini (DEPRECATED: maps to response_llm)
    claude_model: str = "claude-3-5-sonnet-20241022"
    gemini_model: str = "gemini-1.5-flash"
    embedding_model: str = "models/embedding-001"

    # User-Facing Response LLM (what chatbot uses to respond)
    response_llm: str = "claude"  # claude, gemini
    response_claude_model: str = "claude-3-5-sonnet-20241022"
    response_gemini_model: str = "gemini-1.5-flash"

    # Background Processing LLM (indexing, reformulation, etc.)
    processing_llm: str = "claude_haiku"  # claude_haiku, claude, gemini
    processing_claude_model: str = "claude-3-haiku-20240307"
    processing_gemini_model: str = "gemini-1.5-flash"

    # Smart Selection Settings
    enable_response_smart_selection: bool = True  # Allow complexity-based switching within response model family

    # Performance Settings
    system_cache_ttl_seconds: int = 3600
    max_cache_size: int = 1000
    rate_limit: str = "100/minute"

    # Cache & Performance
    enable_smart_model_selection: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def _migrate_legacy_llm_settings(
        cls, validated_data: dict, defaults: "SystemConfigurationSettings", original_data: dict
    ) -> None:
        """
        Migrate legacy LLM settings to new structure for backward compatibility.

        If new LLM fields are missing from database, populate them from legacy primary_llm.
        """
        # Check if this is a legacy configuration (missing new fields in original data)
        new_fields = [
            "response_llm",
            "processing_llm",
            "response_claude_model",
            "response_gemini_model",
            "processing_claude_model",
            "processing_gemini_model",
        ]

        is_legacy = any(field not in original_data for field in new_fields)

        if is_legacy:
            logger.info("Migrating legacy LLM configuration to new structure")

            # Populate new fields from legacy primary_llm
            legacy_primary = validated_data.get("primary_llm", defaults.primary_llm)

            # Response LLM inherits from primary_llm
            if "response_llm" not in original_data:
                validated_data["response_llm"] = legacy_primary
                logger.info(f"Migrated response_llm to: {legacy_primary}")

            # Processing LLM defaults to fast model for background operations
            if "processing_llm" not in validated_data:
                validated_data["processing_llm"] = "claude_haiku"  # Always fast for background

            # Response model variants inherit from legacy models
            if "response_claude_model" not in validated_data:
                validated_data["response_claude_model"] = validated_data.get("claude_model", defaults.claude_model)

            if "response_gemini_model" not in validated_data:
                validated_data["response_gemini_model"] = validated_data.get("gemini_model", defaults.gemini_model)

            # Processing model variants use optimized defaults
            if "processing_claude_model" not in validated_data:
                validated_data["processing_claude_model"] = "claude-3-haiku-20240307"  # Fast model

            if "processing_gemini_model" not in validated_data:
                validated_data["processing_gemini_model"] = validated_data.get("gemini_model", defaults.gemini_model)

            # Smart selection setting inherits from enable_smart_model_selection
            if "enable_response_smart_selection" not in validated_data:
                validated_data["enable_response_smart_selection"] = validated_data.get(
                    "enable_smart_model_selection", defaults.enable_smart_model_selection
                )

    # === CONVENIENCE METHODS FOR BACKWARD COMPATIBILITY ===

    def get_response_model_name(self) -> str:
        """Get the specific model name for the response LLM."""
        if self.response_llm == "claude":
            return self.response_claude_model
        elif self.response_llm == "gemini":
            return self.response_gemini_model
        else:
            # Fallback to legacy if response_llm is invalid
            return self.claude_model if self.primary_llm == "claude" else self.gemini_model

    def get_processing_model_name(self) -> str:
        """Get the specific model name for the processing LLM."""
        if self.processing_llm == "claude" or self.processing_llm == "claude_haiku":
            return self.processing_claude_model
        elif self.processing_llm == "gemini":
            return self.processing_gemini_model
        else:
            # Default to fast Claude model
            return "claude-3-haiku-20240307"

    @property
    def effective_primary_llm(self) -> str:
        """Get the effective primary LLM (response_llm with fallback to primary_llm for compatibility)."""
        return self.response_llm if hasattr(self, "response_llm") else self.primary_llm

    @classmethod
    def from_dict(cls, data: dict) -> "SystemConfigurationSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate primary_llm
        valid_llms = ["claude", "gemini"]
        if validated_data["primary_llm"] not in valid_llms:
            validated_data["primary_llm"] = defaults.primary_llm

        # Validate Claude model
        valid_claude_models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        if validated_data["claude_model"] not in valid_claude_models:
            validated_data["claude_model"] = defaults.claude_model

        # Validate Gemini model
        valid_gemini_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if validated_data["gemini_model"] not in valid_gemini_models:
            validated_data["gemini_model"] = defaults.gemini_model

        # === NEW LLM CONFIGURATION VALIDATION ===

        # Backward compatibility: if new fields missing, populate from legacy fields
        cls._migrate_legacy_llm_settings(validated_data, defaults, data)

        # Validate response_llm
        valid_response_llms = ["claude", "gemini"]
        if validated_data["response_llm"] not in valid_response_llms:
            validated_data["response_llm"] = defaults.response_llm

        # Validate processing_llm
        valid_processing_llms = ["claude_haiku", "claude", "gemini"]
        if validated_data["processing_llm"] not in valid_processing_llms:
            validated_data["processing_llm"] = defaults.processing_llm

        # Validate response model variants
        if validated_data["response_claude_model"] not in valid_claude_models:
            validated_data["response_claude_model"] = defaults.response_claude_model

        if validated_data["response_gemini_model"] not in valid_gemini_models:
            validated_data["response_gemini_model"] = defaults.response_gemini_model

        # Validate processing model variants
        if validated_data["processing_claude_model"] not in valid_claude_models:
            validated_data["processing_claude_model"] = defaults.processing_claude_model

        if validated_data["processing_gemini_model"] not in valid_gemini_models:
            validated_data["processing_gemini_model"] = defaults.processing_gemini_model

        # Validate numeric fields with bounds
        numeric_validations = {
            "system_cache_ttl_seconds": (60, 86400),  # 1 minute to 1 day
            "max_cache_size": (10, 10000),  # 10 to 10k entries
        }

        for field, (min_val, max_val) in numeric_validations.items():
            if not isinstance(validated_data[field], int):
                try:
                    validated_data[field] = int(validated_data[field])
                except (ValueError, TypeError):
                    validated_data[field] = getattr(defaults, field)
            validated_data[field] = max(min_val, min(max_val, validated_data[field]))

        # Validate boolean fields
        for bool_field in ["enable_smart_model_selection", "enable_response_smart_selection"]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate rate_limit format
        import re

        rate_pattern = r"^\d+/(minute|hour|day)$"
        if not isinstance(validated_data["rate_limit"], str) or not re.match(
            rate_pattern, validated_data["rate_limit"]
        ):
            validated_data["rate_limit"] = defaults.rate_limit

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SystemConfigurationSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse system configuration settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class SecuritySettings:
    """Configuration for security, privacy, and monitoring settings."""

    # IP Management
    excluded_ips: List[str] = field(default_factory=list)
    anonymize_ips: bool = True

    # Analytics & Monitoring (consolidated from FeatureFlags)
    enable_analytics: bool = True
    enable_query_logging: bool = True
    query_log_retention_days: int = 30
    enable_audit_logging: bool = True

    # Quality Monitoring
    low_similarity_threshold: float = 0.7  # Quality alert threshold for monitoring

    # Authentication & Sessions
    session_timeout_minutes: int = 480  # 8 hours
    enable_session_fingerprinting: bool = True

    # Rate Limiting & Protection (consolidated from FeatureFlags)
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    max_requests_per_minute: int = 100  # Legacy field for backward compatibility
    enable_input_validation: bool = True

    # Authentication Security
    enable_api_keys: bool = False
    require_https: bool = True
    session_timeout: int = 86400  # seconds (24 hours)
    max_login_attempts: int = 5
    lockout_duration: int = 300  # seconds (5 minutes)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SecuritySettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate IP addresses
        if isinstance(validated_data["excluded_ips"], list):
            import ipaddress

            valid_ips = []
            for ip in validated_data["excluded_ips"]:
                if isinstance(ip, str) and ip.strip():
                    try:
                        ipaddress.ip_address(ip.strip())
                        valid_ips.append(ip.strip())
                    except ValueError:
                        logger.warning(f"Invalid IP address ignored: {ip}")
            validated_data["excluded_ips"] = valid_ips[:50]  # Max 50 IPs
        else:
            validated_data["excluded_ips"] = []

        # Validate numeric fields with bounds
        numeric_validations = {
            "query_log_retention_days": (1, 365),  # 1 day to 1 year
            "session_timeout_minutes": (30, 1440),  # 30 minutes to 24 hours
            "max_requests_per_minute": (1, 1000),  # 1 to 1000 requests per minute
            "rate_limit_requests": (1, 10000),  # 1 to 10,000 requests
            "rate_limit_window": (1, 3600),  # 1 second to 1 hour
            "session_timeout": (300, 604800),  # 5 minutes to 7 days
            "max_login_attempts": (1, 100),  # 1 to 100 attempts
            "lockout_duration": (60, 86400),  # 1 minute to 1 day
        }

        for field, (min_val, max_val) in numeric_validations.items():
            if not isinstance(validated_data[field], int):
                try:
                    validated_data[field] = int(validated_data[field])
                except (ValueError, TypeError):
                    validated_data[field] = getattr(defaults, field)
            validated_data[field] = max(min_val, min(max_val, validated_data[field]))

        # Validate low_similarity_threshold
        if not isinstance(validated_data["low_similarity_threshold"], float):
            try:
                validated_data["low_similarity_threshold"] = float(validated_data["low_similarity_threshold"])
            except (ValueError, TypeError):
                validated_data["low_similarity_threshold"] = defaults.low_similarity_threshold
        validated_data["low_similarity_threshold"] = max(0.0, min(1.0, validated_data["low_similarity_threshold"]))

        # Validate boolean fields
        bool_fields = [
            "anonymize_ips",
            "enable_analytics",
            "enable_query_logging",
            "enable_session_fingerprinting",
            "enable_audit_logging",
            "enable_rate_limiting",
            "enable_input_validation",
            "enable_api_keys",
            "require_https",
        ]
        for bool_field in bool_fields:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SecuritySettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse security settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class SystemSettings:
    """Unified container for all DB-driven runtime settings."""

    followup: "FollowUpSettings" = field(default_factory=lambda: None)  # Import from config.py
    response: ResponseSettings = field(default_factory=ResponseSettings)
    routing: QueryRoutingSettings = field(default_factory=QueryRoutingSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    system_config: SystemConfigurationSettings = field(default_factory=SystemConfigurationSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {}
        if self.followup:
            result["followup"] = self.followup.to_dict()
        result["response"] = self.response.to_dict()
        result["routing"] = self.routing.to_dict()
        result["features"] = self.features.to_dict()
        result["system_config"] = self.system_config.to_dict()
        result["security"] = self.security.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SystemSettings":
        """Create from dictionary with validation."""
        # Import here to avoid circular import

        followup_data = data.get("followup", {})
        response_data = data.get("response", {})
        routing_data = data.get("routing", {})
        features_data = data.get("features", {})
        system_config_data = data.get("system_config", {})
        security_data = data.get("security", {})

        return cls(
            followup=FollowUpSettings.from_dict(followup_data) if followup_data else FollowUpSettings(),
            response=ResponseSettings.from_dict(response_data),
            routing=QueryRoutingSettings.from_dict(routing_data),
            features=FeatureFlags.from_dict(features_data),
            system_config=SystemConfigurationSettings.from_dict(system_config_data),
            security=SecuritySettings.from_dict(security_data),
        )

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SystemSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse system settings from JSON: {e}")
            return cls()  # Return defaults on error


# Setting key constants
@dataclass
class RagConfigurationSettings:
    """Configuration settings for RAG (Retrieval Augmented Generation) system."""

    # Feature Toggles (Boolean)
    rag_use_mmr: bool = False
    rag_use_heading_splitter: bool = True
    rag_enable_delete: bool = False
    rag_safe_delete: bool = True

    # Numeric Settings
    rag_score_threshold: float = 0.2
    rag_low_similarity_threshold: float = 0.7
    rag_fuzzy_threshold: float = 0.7
    rag_confidence_threshold: float = 0.75
    rag_relevance_threshold: float = 0.7
    rag_mmr_k: int = 4
    rag_mmr_fetch_k: int = 20
    rag_mmr_lambda_mult: float = 0.5

    # String Settings
    rag_index_dirs: str = "backend/knowledge,public"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RagConfigurationSettings":
        """Create from dictionary with validation."""
        # Validate and set defaults for missing keys
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Boolean validation
        for bool_field in ["rag_use_mmr", "rag_use_heading_splitter", "rag_enable_delete", "rag_safe_delete"]:
            if bool_field in validated_data and not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Float validation with range checking
        if "rag_score_threshold" in validated_data:
            try:
                val = float(validated_data["rag_score_threshold"])
                validated_data["rag_score_threshold"] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                validated_data["rag_score_threshold"] = defaults.rag_score_threshold

        if "rag_mmr_lambda_mult" in validated_data:
            try:
                val = float(validated_data["rag_mmr_lambda_mult"])
                validated_data["rag_mmr_lambda_mult"] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                validated_data["rag_mmr_lambda_mult"] = defaults.rag_mmr_lambda_mult

        if "rag_low_similarity_threshold" in validated_data:
            try:
                val = float(validated_data["rag_low_similarity_threshold"])
                validated_data["rag_low_similarity_threshold"] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                validated_data["rag_low_similarity_threshold"] = defaults.rag_low_similarity_threshold

        if "rag_fuzzy_threshold" in validated_data:
            try:
                val = float(validated_data["rag_fuzzy_threshold"])
                validated_data["rag_fuzzy_threshold"] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                validated_data["rag_fuzzy_threshold"] = defaults.rag_fuzzy_threshold

        if "rag_confidence_threshold" in validated_data:
            try:
                val = float(validated_data["rag_confidence_threshold"])
                validated_data["rag_confidence_threshold"] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                validated_data["rag_confidence_threshold"] = defaults.rag_confidence_threshold

        if "rag_relevance_threshold" in validated_data:
            try:
                val = float(validated_data["rag_relevance_threshold"])
                validated_data["rag_relevance_threshold"] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                validated_data["rag_relevance_threshold"] = defaults.rag_relevance_threshold

        # Integer validation with range checking
        if "rag_mmr_k" in validated_data:
            try:
                val = int(validated_data["rag_mmr_k"])
                validated_data["rag_mmr_k"] = max(1, min(20, val))
            except (ValueError, TypeError):
                validated_data["rag_mmr_k"] = defaults.rag_mmr_k

        if "rag_mmr_fetch_k" in validated_data:
            try:
                val = int(validated_data["rag_mmr_fetch_k"])
                validated_data["rag_mmr_fetch_k"] = max(10, min(100, val))
            except (ValueError, TypeError):
                validated_data["rag_mmr_fetch_k"] = defaults.rag_mmr_fetch_k

        # String validation
        if "rag_index_dirs" in validated_data:
            if not validated_data["rag_index_dirs"] or not isinstance(validated_data["rag_index_dirs"], str):
                validated_data["rag_index_dirs"] = defaults.rag_index_dirs
            else:
                # Clean up the directory string
                validated_data["rag_index_dirs"] = validated_data["rag_index_dirs"].strip()

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "RagConfigurationSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse RAG configuration JSON: {e}")
            return cls()  # Return defaults on parse error

    def validate(self) -> tuple[bool, list[str]]:
        """Validate all settings and return (is_valid, error_messages)."""
        errors = []

        # Range validations
        if not (0.0 <= self.rag_score_threshold <= 1.0):
            errors.append("Score threshold must be between 0.0 and 1.0")

        if not (0.0 <= self.rag_low_similarity_threshold <= 1.0):
            errors.append("Low similarity threshold must be between 0.0 and 1.0")

        if not (0.0 <= self.rag_fuzzy_threshold <= 1.0):
            errors.append("Fuzzy threshold must be between 0.0 and 1.0")

        if not (0.0 <= self.rag_confidence_threshold <= 1.0):
            errors.append("Confidence threshold must be between 0.0 and 1.0")

        if not (0.0 <= self.rag_relevance_threshold <= 1.0):
            errors.append("Relevance threshold must be between 0.0 and 1.0")

        if not (1 <= self.rag_mmr_k <= 20):
            errors.append("MMR K must be between 1 and 20")

        if not (10 <= self.rag_mmr_fetch_k <= 100):
            errors.append("MMR Fetch K must be between 10 and 100")

        if not (0.0 <= self.rag_mmr_lambda_mult <= 1.0):
            errors.append("MMR Lambda multiplier must be between 0.0 and 1.0")

        # String validation
        if not self.rag_index_dirs or not self.rag_index_dirs.strip():
            errors.append("Index directories cannot be empty")

        # Logical validation
        if self.rag_mmr_k > self.rag_mmr_fetch_k:
            errors.append("MMR K cannot be greater than MMR Fetch K")

        return len(errors) == 0, errors


@dataclass
class CoreSettings:
    """Core system configuration and LLM model settings."""

    # System identification
    system_name: str = "Nick Berens AI Assistant"
    version: str = "2.0"

    # LLM Configuration
    default_model: str = "claude-3-sonnet"
    anthropic_api_key_configured: bool = False  # Read-only status
    google_api_key_configured: bool = False  # Read-only status

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CoreSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate strings
        for str_field in ["system_name", "version", "default_model"]:
            if not isinstance(validated_data[str_field], str):
                validated_data[str_field] = str(validated_data[str_field])
            validated_data[str_field] = validated_data[str_field].strip()
            if not validated_data[str_field]:
                validated_data[str_field] = getattr(defaults, str_field)

        # Validate boolean fields (read-only status fields)
        for bool_field in ["anthropic_api_key_configured", "google_api_key_configured"]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate default_model is in acceptable list
        valid_models = ["claude-3-sonnet", "claude-3-opus", "claude-3-haiku", "gemini-pro", "gemini-1.5-pro"]
        if validated_data["default_model"] not in valid_models:
            validated_data["default_model"] = "claude-3-sonnet"

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "CoreSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse core settings JSON: {e}")
            return cls()


@dataclass
class UXSettings:
    """User experience and interface customization settings."""

    # UI Preferences
    enable_animations: bool = True
    theme_preference: str = "auto"  # auto, light, dark
    compact_mode: bool = False

    # Response Behavior
    response_streaming: bool = True
    show_typing_indicators: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UXSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate boolean fields
        for bool_field in ["enable_animations", "compact_mode", "response_streaming", "show_typing_indicators"]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate theme_preference
        valid_themes = ["auto", "light", "dark"]
        if validated_data["theme_preference"] not in valid_themes:
            validated_data["theme_preference"] = "auto"

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "UXSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse UX settings JSON: {e}")
            return cls()


@dataclass
class SearchRetrievalSettings:
    """Search and document retrieval configuration settings."""

    # Search Configuration
    semantic_similarity_threshold: float = 0.55
    max_search_results: int = 10
    search_timeout_seconds: int = 30

    # Advanced Features
    enable_fuzzy_matching: bool = True
    enable_metadata_boosting: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SearchRetrievalSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate boolean fields
        for bool_field in ["enable_fuzzy_matching", "enable_metadata_boosting"]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate semantic_similarity_threshold
        if not isinstance(validated_data["semantic_similarity_threshold"], (int, float)):
            try:
                validated_data["semantic_similarity_threshold"] = float(validated_data["semantic_similarity_threshold"])
            except (ValueError, TypeError):
                validated_data["semantic_similarity_threshold"] = defaults.semantic_similarity_threshold
        validated_data["semantic_similarity_threshold"] = max(
            0.0, min(1.0, validated_data["semantic_similarity_threshold"])
        )

        # Validate max_search_results
        if not isinstance(validated_data["max_search_results"], int):
            try:
                validated_data["max_search_results"] = int(validated_data["max_search_results"])
            except (ValueError, TypeError):
                validated_data["max_search_results"] = defaults.max_search_results
        validated_data["max_search_results"] = max(1, min(100, validated_data["max_search_results"]))

        # Validate search_timeout_seconds
        if not isinstance(validated_data["search_timeout_seconds"], int):
            try:
                validated_data["search_timeout_seconds"] = int(validated_data["search_timeout_seconds"])
            except (ValueError, TypeError):
                validated_data["search_timeout_seconds"] = defaults.search_timeout_seconds
        validated_data["search_timeout_seconds"] = max(5, min(120, validated_data["search_timeout_seconds"]))

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SearchRetrievalSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse search retrieval settings JSON: {e}")
            return cls()


class SettingKeys:
    """Constants for setting keys used in database."""

    FOLLOWUP_SETTINGS = "followup_settings"
    RESPONSE_SETTINGS = "response_settings"
    ROUTING_SETTINGS = "routing_settings"
    FEATURE_FLAGS = "feature_flags"
    SYSTEM_CONFIG_SETTINGS = "system_config_settings"
    SECURITY_SETTINGS = "security_settings"
    RAG_CONFIG_SETTINGS = "rag_config_settings"
    CORE_SETTINGS = "core_settings"
    UX_SETTINGS = "ux_settings"
    SEARCH_RETRIEVAL_SETTINGS = "search_retrieval_settings"
    SYSTEM_SETTINGS = "system_settings"  # For unified storage (future use)
    KNOWLEDGE_SETTINGS = "knowledge_settings"


@dataclass
class KnowledgeSettings:
    """Configuration for knowledge indexing and synchronization."""

    index_on_startup: bool = True
    background_sync_interval_seconds: int = 0  # 0 disables
    auto_reindex_deltas: bool = False
    enable_heterogeneity_fallback: bool = False
    heterogeneity_fallback_include: List[str] = field(default_factory=list)
    index_directories: List[str] = field(default_factory=lambda: ["backend/knowledge", "public"])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeSettings":
        defaults = cls()
        validated = {}
        for k, v in asdict(defaults).items():
            validated[k] = data.get(k, v)

        # Normalize types and bounds
        validated["index_on_startup"] = bool(validated.get("index_on_startup", defaults.index_on_startup))
        try:
            ival = int(validated.get("background_sync_interval_seconds", defaults.background_sync_interval_seconds))
        except Exception:
            ival = defaults.background_sync_interval_seconds
        validated["background_sync_interval_seconds"] = max(0, min(86400, ival))

        validated["auto_reindex_deltas"] = bool(validated.get("auto_reindex_deltas", defaults.auto_reindex_deltas))
        validated["enable_heterogeneity_fallback"] = bool(
            validated.get("enable_heterogeneity_fallback", defaults.enable_heterogeneity_fallback)
        )

        includes = validated.get("heterogeneity_fallback_include") or []
        if not isinstance(includes, list):
            includes = [str(includes)]
        validated["heterogeneity_fallback_include"] = [str(x).strip() for x in includes if str(x).strip()]

        dirs = validated.get("index_directories") or []
        if not isinstance(dirs, list):
            dirs = [str(dirs)]
        validated["index_directories"] = [str(x).strip() for x in dirs if str(x).strip()]
        if not validated["index_directories"]:
            validated["index_directories"] = list(defaults.index_directories)

        return cls(**validated)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "KnowledgeSettings":
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to parse knowledge settings JSON: {e}")
            return cls()
