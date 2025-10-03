"""
Settings Manager service for unified DB-driven configuration.
Provides cached access to all runtime settings with fallback to defaults.
"""

import logging
import os
import time
from threading import Lock
from typing import Any, Dict, Optional, TypeVar

from sqlalchemy import text

from .db_session import get_db_session_sync
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
    SystemSettings,
    UXSettings,
)
from .tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SettingsCache:
    """Thread-safe settings cache with TTL."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl_seconds:
                    return entry["value"]
                else:
                    # Expired, remove from cache
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        with self._lock:
            self._cache[key] = {"value": value, "timestamp": time.time()}

    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate specific key or all cache."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get cache status information safely."""
        with self._lock:
            cache_keys = list(self._cache.keys())
            cache_size = len(cache_keys)
            return {"keys": cache_keys, "size": cache_size}


class SettingsManager:
    """Unified settings manager with caching and fallback to defaults."""

    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache = SettingsCache(cache_ttl_seconds)
        self._lock = Lock()

    def _cache_key(self, setting_key: str) -> str:
        """Compute a cache key that includes tenant in multi-tenant mode."""
        if os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true":
            tid = get_current_tenant_id() or os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
            return f"{tid}:{setting_key}"
        return setting_key

    def _get_setting_from_db(self, setting_key: str) -> Optional[str]:
        """Get setting value from Postgres admin_settings.

        Uses tenant_id when multi-tenant is enabled; otherwise defaults to DEFAULT_TENANT_ID.
        """
        try:
            tenant_id = get_current_tenant_id() or os.getenv(
                "DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"
            )
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text("SELECT setting_value FROM admin_settings WHERE tenant_id = :tid AND setting_key = :key"),
                    {"tid": tenant_id, "key": setting_key},
                ).fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting setting {setting_key} from DB: {e}")
            return None

    def _set_setting_in_db(self, setting_key: str, setting_value: str, updated_by: int) -> bool:
        """Set setting value in Postgres admin_settings.

        Uses tenant_id when multi-tenant is enabled; otherwise defaults to DEFAULT_TENANT_ID.
        """
        try:
            tenant_id = get_current_tenant_id() or os.getenv(
                "DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"
            )
            with get_db_session_sync() as session:
                if session is None:
                    return False
                session.execute(
                    text(
                        """
                        INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at, updated_by)
                        VALUES (:tid, :key, :val, now(), :uid)
                        ON CONFLICT (tenant_id, setting_key)
                        DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = now(), updated_by = EXCLUDED.updated_by
                        """
                    ),
                    {"tid": tenant_id, "key": setting_key, "val": setting_value, "uid": updated_by},
                )
            # Invalidate tenant-scoped cache key
            self.cache.invalidate(self._cache_key(setting_key))
            return True
        except Exception as e:
            logger.error(f"Error setting {setting_key} in DB: {e}")
            return False

    def get_followup_settings(self) -> FollowUpSettings:
        """Get follow-up settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.FOLLOWUP_SETTINGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.FOLLOWUP_SETTINGS)
        if settings_json:
            settings = FollowUpSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = FollowUpSettings()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.FOLLOWUP_SETTINGS), settings)
        return settings

    def set_followup_settings(self, settings: FollowUpSettings, updated_by: int) -> bool:
        """Set follow-up settings in database."""
        return self._set_setting_in_db(SettingKeys.FOLLOWUP_SETTINGS, settings.to_json(), updated_by)

    def get_response_settings(self) -> ResponseSettings:
        """Get response settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.RESPONSE_SETTINGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.RESPONSE_SETTINGS)
        if settings_json:
            settings = ResponseSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = ResponseSettings()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.RESPONSE_SETTINGS), settings)
        return settings

    def set_response_settings(self, settings: ResponseSettings, updated_by: int) -> bool:
        """Set response settings in database."""
        return self._set_setting_in_db(SettingKeys.RESPONSE_SETTINGS, settings.to_json(), updated_by)

    def get_routing_settings(self) -> QueryRoutingSettings:
        """Get query routing settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.ROUTING_SETTINGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.ROUTING_SETTINGS)
        if settings_json:
            settings = QueryRoutingSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = QueryRoutingSettings()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.ROUTING_SETTINGS), settings)
        return settings

    def set_routing_settings(self, settings: QueryRoutingSettings, updated_by: int) -> bool:
        """Set query routing settings in database."""
        return self._set_setting_in_db(SettingKeys.ROUTING_SETTINGS, settings.to_json(), updated_by)

    def get_feature_flags(self) -> FeatureFlags:
        """Get feature flags with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.FEATURE_FLAGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.FEATURE_FLAGS)
        if settings_json:
            settings = FeatureFlags.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = FeatureFlags()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.FEATURE_FLAGS), settings)
        return settings

    def set_feature_flags(self, settings: FeatureFlags, updated_by: int) -> bool:
        """Set feature flags in database."""
        return self._set_setting_in_db(SettingKeys.FEATURE_FLAGS, settings.to_json(), updated_by)

    def get_system_config_settings(self) -> SystemConfigurationSettings:
        """Get system configuration settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.SYSTEM_CONFIG_SETTINGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.SYSTEM_CONFIG_SETTINGS)
        if settings_json:
            settings = SystemConfigurationSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = SystemConfigurationSettings()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.SYSTEM_CONFIG_SETTINGS), settings)
        return settings

    def set_system_config_settings(self, settings: SystemConfigurationSettings, updated_by: int) -> bool:
        """Set system configuration settings in database."""
        return self._set_setting_in_db(SettingKeys.SYSTEM_CONFIG_SETTINGS, settings.to_json(), updated_by)

    def get_security_settings(self) -> SecuritySettings:
        """Get security settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.SECURITY_SETTINGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.SECURITY_SETTINGS)
        if settings_json:
            settings = SecuritySettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = SecuritySettings()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.SECURITY_SETTINGS), settings)
        return settings

    def set_security_settings(self, settings: SecuritySettings, updated_by: int) -> bool:
        """Set security settings in database."""
        return self._set_setting_in_db(SettingKeys.SECURITY_SETTINGS, settings.to_json(), updated_by)

    def get_rag_config_settings(self) -> RagConfigurationSettings:
        """Get RAG configuration settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.RAG_CONFIG_SETTINGS))
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.RAG_CONFIG_SETTINGS)
        if settings_json:
            settings = RagConfigurationSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = RagConfigurationSettings()

        # Cache the result
        self.cache.set(self._cache_key(SettingKeys.RAG_CONFIG_SETTINGS), settings)
        return settings

    def set_rag_config_settings(self, settings: RagConfigurationSettings, updated_by: int) -> bool:
        """Set RAG configuration settings in database."""
        # Validate settings before saving
        is_valid, errors = settings.validate()
        if not is_valid:
            logger.error(f"Invalid RAG configuration settings: {errors}")
            return False

        success = self._set_setting_in_db(SettingKeys.RAG_CONFIG_SETTINGS, settings.to_json(), updated_by)
        if success:
            # Invalidate cache so next get will fetch fresh data
            self.cache.invalidate(self._cache_key(SettingKeys.RAG_CONFIG_SETTINGS))
            logger.info("RAG configuration settings updated successfully")
        return success

    def get_core_settings(self) -> CoreSettings:
        """Get core settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.CORE_SETTINGS))
        if cached:
            return cached

        json_str = self._get_setting_from_db(SettingKeys.CORE_SETTINGS)
        if json_str:
            try:
                settings = CoreSettings.from_json(json_str)
                self.cache.set(self._cache_key(SettingKeys.CORE_SETTINGS), settings)
                return settings
            except Exception as e:
                logger.warning(f"Failed to parse core settings from DB: {e}")

        # Return defaults if no DB value or parse error
        defaults = CoreSettings()
        self.cache.set(self._cache_key(SettingKeys.CORE_SETTINGS), defaults)
        return defaults

    def set_core_settings(self, settings: CoreSettings, updated_by: int) -> bool:
        """Set core settings in database."""
        return self._set_setting_in_db(SettingKeys.CORE_SETTINGS, settings.to_json(), updated_by)

    def get_ux_settings(self) -> UXSettings:
        """Get UX settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.UX_SETTINGS))
        if cached:
            return cached

        json_str = self._get_setting_from_db(SettingKeys.UX_SETTINGS)
        if json_str:
            try:
                settings = UXSettings.from_json(json_str)
                self.cache.set(self._cache_key(SettingKeys.UX_SETTINGS), settings)
                return settings
            except Exception as e:
                logger.warning(f"Failed to parse UX settings from DB: {e}")

        # Return defaults if no DB value or parse error
        defaults = UXSettings()
        self.cache.set(self._cache_key(SettingKeys.UX_SETTINGS), defaults)
        return defaults

    def set_ux_settings(self, settings: UXSettings, updated_by: int) -> bool:
        """Set UX settings in database."""
        return self._set_setting_in_db(SettingKeys.UX_SETTINGS, settings.to_json(), updated_by)

    def get_search_retrieval_settings(self) -> SearchRetrievalSettings:
        """Get search retrieval settings with caching."""
        cached = self.cache.get(self._cache_key(SettingKeys.SEARCH_RETRIEVAL_SETTINGS))
        if cached:
            return cached

        json_str = self._get_setting_from_db(SettingKeys.SEARCH_RETRIEVAL_SETTINGS)
        if json_str:
            try:
                settings = SearchRetrievalSettings.from_json(json_str)
                self.cache.set(self._cache_key(SettingKeys.SEARCH_RETRIEVAL_SETTINGS), settings)
                return settings
            except Exception as e:
                logger.warning(f"Failed to parse search retrieval settings from DB: {e}")

        # Return defaults if no DB value or parse error
        defaults = SearchRetrievalSettings()
        self.cache.set(self._cache_key(SettingKeys.SEARCH_RETRIEVAL_SETTINGS), defaults)
        return defaults

    def set_search_retrieval_settings(self, settings: SearchRetrievalSettings, updated_by: int) -> bool:
        """Set search retrieval settings in database."""
        return self._set_setting_in_db(SettingKeys.SEARCH_RETRIEVAL_SETTINGS, settings.to_json(), updated_by)

    def get_all_settings(self) -> SystemSettings:
        """Get all settings as unified SystemSettings object."""
        return SystemSettings(
            followup=self.get_followup_settings(),
            response=self.get_response_settings(),
            routing=self.get_routing_settings(),
            features=self.get_feature_flags(),
            system_config=self.get_system_config_settings(),
            security=self.get_security_settings(),
        )

    def invalidate_cache(self, setting_key: Optional[str] = None) -> None:
        """Invalidate specific setting cache or all caches."""
        self.cache.invalidate(setting_key)

    def warmup_cache(self) -> None:
        """Warmup cache by loading all settings."""
        try:
            logger.info("Warming up settings cache...")
            self.get_followup_settings()
            self.get_response_settings()
            self.get_routing_settings()
            self.get_feature_flags()
            self.get_system_config_settings()
            self.get_security_settings()
            self.get_rag_config_settings()
            logger.info("Settings cache warmed up successfully")
        except Exception as e:
            logger.error(f"Error warming up settings cache: {e}")

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status for monitoring."""
        cache_status = self.cache.get_status()
        cache_keys = cache_status["keys"]
        cache_size = cache_status["size"]

        # Check which settings are cached
        cached_settings = {}
        for key in [
            SettingKeys.FOLLOWUP_SETTINGS,
            SettingKeys.RESPONSE_SETTINGS,
            SettingKeys.ROUTING_SETTINGS,
            SettingKeys.FEATURE_FLAGS,
            SettingKeys.SYSTEM_CONFIG_SETTINGS,
            SettingKeys.SECURITY_SETTINGS,
            SettingKeys.RAG_CONFIG_SETTINGS,
            SettingKeys.KNOWLEDGE_SETTINGS,
        ]:
            cached_settings[key] = key in cache_keys

        return {
            "cache_size": cache_size,
            "cached_keys": cache_keys,
            "cached_settings": cached_settings,
            "ttl_seconds": self.cache.ttl_seconds,
        }

    # Convenience methods for backward compatibility
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        # Handle consolidated settings that moved to other schemas
        if feature_name == "enable_analytics":
            security_settings = self.get_security_settings()
            return security_settings.enable_analytics
        elif feature_name == "enable_rate_limiting":
            security_settings = self.get_security_settings()
            return security_settings.enable_rate_limiting
        elif feature_name == "enable_followup_questions":
            # Follow-up questions are controlled by FollowUpSettings.enabled
            # Keep this mapping here so callers using the old feature flag continue to work
            followup_settings = self.get_followup_settings()
            return followup_settings.enabled
        elif feature_name == "enable_smart_routing":
            routing_settings = self.get_routing_settings()
            return routing_settings.enable_smart_routing
        elif feature_name in ["enable_caching", "enable_response_caching"]:
            response_settings = self.get_response_settings()
            return response_settings.enable_caching

        # Check remaining flags in FeatureFlags schema
        features = self.get_feature_flags()
        return getattr(features, feature_name, False)

    # === NEW LLM CONFIGURATION METHODS ===

    def get_response_llm(self) -> str:
        """Get the response LLM type (what users see in chat)."""
        response_settings = self.get_response_settings()
        return response_settings.response_llm

    def get_processing_llm(self) -> str:
        """Get the processing LLM type (background operations)."""
        system_config = self.get_system_config_settings()
        return system_config.processing_llm

    def get_response_model_name(self) -> str:
        """Get the specific model name for response generation."""
        system_config = self.get_system_config_settings()
        return system_config.get_response_model_name()

    def get_processing_model_name(self) -> str:
        """Get the specific model name for background processing."""
        system_config = self.get_system_config_settings()
        return system_config.get_processing_model_name()

    def is_response_smart_selection_enabled(self) -> bool:
        """Check if smart selection is enabled for response models."""
        response_settings = self.get_response_settings()
        return response_settings.enable_smart_selection

    def get_effective_primary_llm(self) -> str:
        """Get the effective primary LLM for backward compatibility."""
        system_config = self.get_system_config_settings()
        return system_config.effective_primary_llm

    # === Knowledge Settings ===
    def get_knowledge_settings(self) -> KnowledgeSettings:
        cached = self.cache.get(self._cache_key(SettingKeys.KNOWLEDGE_SETTINGS))
        if cached:
            return cached
        json_str = self._get_setting_from_db(SettingKeys.KNOWLEDGE_SETTINGS)
        if json_str:
            settings = KnowledgeSettings.from_json(json_str)
        else:
            settings = KnowledgeSettings()
        self.cache.set(self._cache_key(SettingKeys.KNOWLEDGE_SETTINGS), settings)
        return settings

    def set_knowledge_settings(self, settings: KnowledgeSettings, updated_by: int) -> bool:
        ok = self._set_setting_in_db(SettingKeys.KNOWLEDGE_SETTINGS, settings.to_json(), updated_by)
        if ok:
            self.cache.invalidate(self._cache_key(SettingKeys.KNOWLEDGE_SETTINGS))
        return ok


# Global settings manager instance
settings_manager = SettingsManager()


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    return settings_manager
