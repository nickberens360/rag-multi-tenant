"""
Admin diagnostics router for configuration presence reporting.

This router provides endpoints to check the configuration status of both
environment-only and admin-managed settings without exposing sensitive values.
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..core.admin_auth import require_admin_auth
from ..core.config_validation import get_configuration_health_summary, get_current_timestamp, validate_critical_settings
from ..core.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["Admin Diagnostics"])


def _is_sensitive_setting(setting_name: str) -> bool:
    """
    Check if a setting contains sensitive information that should never be logged or exposed.

    Returns True for API keys, passwords, secrets, and other sensitive data.
    """
    sensitive_patterns = [
        "api_key",
        "password",
        "secret",
        "token",
        "key",
        "salt",
        "credentials",
        "auth",
        "private",
        "cert",
        "oauth",
    ]
    setting_lower = setting_name.lower()
    return any(pattern in setting_lower for pattern in sensitive_patterns)


def _sanitize_setting_value(setting_name: str, value: Any) -> Any:
    """
    Sanitize setting values to prevent accidental exposure of sensitive data.

    Returns None for sensitive settings, actual value for safe settings.
    """
    if _is_sensitive_setting(setting_name):
        return None

    # Only allow specific safe settings to show values
    safe_value_settings = ["ENVIRONMENT", "DEBUG_MODE", "PRIMARY_LLM", "PERFORMANCE_MODE"]
    if setting_name in safe_value_settings:
        return value

    return None


@router.get("/config-status", summary="Get configuration status overview")
async def get_config_status(
    user_session=Depends(require_admin_auth),
) -> JSONResponse:
    """
    Get comprehensive configuration status overview.

    Returns presence/absence status for both env-only and admin-managed settings
    without exposing any sensitive values.

    **Response Structure:**
    - env_only: Environment variables that must remain secrets
    - admin_managed: Settings that can be overridden via admin UI
    - database_settings: Admin-manageable setting categories from database
    - summary: Overall configuration health statistics
    """
    try:
        # Environment-only settings (secrets and deployment-specific)
        env_only_settings = _check_env_only_settings()

        # Admin-managed environment settings (can be overridden via UI)
        admin_managed_env = _check_admin_managed_env_settings()

        # Database setting categories
        database_settings = _check_database_settings()

        # Generate summary statistics
        summary = _generate_summary(env_only_settings, admin_managed_env, database_settings)

        return JSONResponse(
            content={
                "env_only": env_only_settings,
                "admin_managed_env": admin_managed_env,
                "database_settings": database_settings,
                "summary": summary,
                "timestamp": get_current_timestamp(),
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving configuration status: {e}")
        return JSONResponse(content={"error": "Failed to retrieve configuration status"}, status_code=500)


@router.get("/env-only-status", summary="Get environment-only settings status")
async def get_env_only_status(
    user_session=Depends(require_admin_auth),
) -> JSONResponse:
    """
    Get status of environment-only settings (secrets, deployment config).

    Reports presence/absence without exposing values for security-sensitive settings
    that must remain as environment variables.
    """
    try:
        env_only_settings = _check_env_only_settings()

        return JSONResponse(
            content={
                "env_only_settings": env_only_settings,
                "summary": {
                    "total_settings": len(env_only_settings),
                    "configured": sum(1 for s in env_only_settings.values() if s["present"]),
                    "missing": sum(1 for s in env_only_settings.values() if not s["present"]),
                },
                "timestamp": get_current_timestamp(),
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving env-only settings status: {e}")
        return JSONResponse(content={"error": "Failed to retrieve env-only settings status"}, status_code=500)


@router.get("/admin-managed-status", summary="Get admin-managed settings status")
async def get_admin_managed_status(
    user_session=Depends(require_admin_auth),
) -> JSONResponse:
    """
    Get status of admin-managed settings.

    Reports configuration status for settings that can be overridden via the admin UI,
    including both environment variables and database-stored settings.
    """
    try:
        # Admin-managed environment settings
        admin_managed_env = _check_admin_managed_env_settings()

        # Database setting categories
        database_settings = _check_database_settings()

        return JSONResponse(
            content={
                "admin_managed_env": admin_managed_env,
                "database_settings": database_settings,
                "summary": {
                    "env_settings": {
                        "total": len(admin_managed_env),
                        "configured": sum(1 for s in admin_managed_env.values() if s["present"]),
                        "missing": sum(1 for s in admin_managed_env.values() if not s["present"]),
                    },
                    "database_categories": {
                        "total": len(database_settings),
                        "configured": sum(1 for s in database_settings.values() if s["configured"]),
                        "using_defaults": sum(1 for s in database_settings.values() if not s["configured"]),
                    },
                },
                "timestamp": get_current_timestamp(),
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving admin-managed settings status: {e}")
        return JSONResponse(content={"error": "Failed to retrieve admin-managed settings status"}, status_code=500)


@router.get("/config-validation", summary="Validate configuration health and completeness")
async def get_config_validation(
    user_session=Depends(require_admin_auth),
) -> JSONResponse:
    """
    Validate system configuration health and completeness.

    Performs comprehensive validation of:
    - Critical environment variables
    - Feature flag consistency
    - Database settings health
    - Overall system configuration status

    Returns actionable recommendations for configuration improvements.
    """
    try:
        health_summary = get_configuration_health_summary()

        return JSONResponse(
            content={
                "validation_results": health_summary,
                "timestamp": get_current_timestamp(),
            }
        )
    except Exception as e:
        logger.error(f"Error performing configuration validation: {e}")
        return JSONResponse(content={"error": "Failed to perform configuration validation"}, status_code=500)


@router.get("/critical-settings-check", summary="Check critical settings for system operation")
async def get_critical_settings_check(
    user_session=Depends(require_admin_auth),
) -> JSONResponse:
    """
    Quick check of critical settings required for basic system operation.

    Returns only the most important configuration issues that could prevent
    the system from functioning properly.
    """
    try:
        critical_validation = validate_critical_settings()

        # Simplified response focusing on critical issues
        response_data = {
            "status": critical_validation["overall_status"],
            "critical_missing": critical_validation["critical_missing"],
            "critical_count": len(critical_validation["critical_missing"]),
            "recommendations": critical_validation["recommendations"],
            "timestamp": get_current_timestamp(),
        }

        # Set appropriate HTTP status based on critical issues
        status_code = 200
        if critical_validation["overall_status"] == "critical":
            status_code = 503  # Service Unavailable for critical config issues

        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.error(f"Error checking critical settings: {e}")
        return JSONResponse(content={"error": "Failed to check critical settings"}, status_code=500)


def _check_env_only_settings() -> Dict[str, Dict[str, Any]]:
    """Check presence of environment-only settings (secrets and deployment-specific)."""
    # Based on Phase 1 inventory: 27 ENV-ONLY settings
    env_only_vars = [
        # Core environment
        "ENVIRONMENT",
        "DEBUG_MODE",
        # API Keys and secrets
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GITHUB_TOKEN",
        "API_KEY_ENCRYPTION_SECRET",
        # Admin credentials
        "ADMIN_DEFAULT_PASSWORD",
        "ADMIN_DEFAULT_USERNAME",
        "ADMIN_DEFAULT_EMAIL",
        # Deployment-specific
        "PUBLIC_API_URL",
        "PUBLIC_GITHUB_USERNAME",
        "PUBLIC_GITHUB_REPO",
        "PUBLIC_GA_TRACKING_ID",
        "CORS_ORIGINS",
        # Railway deployment
        "RAILWAY_ENVIRONMENT_NAME",
        "RAILWAY_RUN_UID",
        "RAILWAY_VOLUME_MOUNT_PATH",
        "RAILWAY_VOLUME_NAME",
        # Security
        "IP_HASH_SALT",
        # Development flags
        "TESTING",
        "SKIP_INDEXING",
        "FORCE_REBUILD_DATA",
        "UNIFIED_PERSIST_DIR",
        "DISABLE_RATE_LIMITING",
        "FORCE_DISABLE_MAINTENANCE",
        "FAST_LOGIN_MODE",
    ]

    result = {}
    for var in env_only_vars:
        value = os.getenv(var)
        result[var] = {
            "present": value is not None,
            "classification": "env-only",
            "description": _get_setting_description(var),
        }

        # Add additional context for some settings (with security validation)
        if var in ["ENVIRONMENT", "DEBUG_MODE"]:
            # These are safe to expose with defaults
            result[var]["current_value"] = value if value else ("development" if var == "ENVIRONMENT" else "false")
        else:
            # Use security validation for all other settings
            sanitized_value = _sanitize_setting_value(var, value)
            if sanitized_value is not None:
                result[var]["current_value"] = sanitized_value

    return result


def _check_admin_managed_env_settings() -> Dict[str, Dict[str, Any]]:
    """Check presence of admin-managed environment settings (can be overridden via UI)."""
    # Based on Phase 1 inventory: 55 ADMIN-MANAGED settings
    admin_managed_vars = [
        # LLM Configuration
        "PRIMARY_LLM",
        "CLAUDE_MODEL",
        "GEMINI_MODEL",
        "EMBEDDING_MODEL",
        "REQUEST_TIMEOUT",
        # Rate limiting and caching
        "RATE_LIMIT",
        "ENABLE_CACHING",
        "CACHE_TTL_SECONDS",
        "MAX_CACHE_SIZE",
        # Search and retrieval
        "SEARCH_THRESHOLD",
        "MAX_RESULTS",
        "MAX_CONTEXT_LENGTH",
        "MAX_CONTEXT_DOCUMENTS",
        "DEFAULT_MAX_CONTEXT_LENGTH",
        "CONTEXT_FILL_RATIO",
        "RETRIEVAL_SCORE_THRESHOLD",
        # RAG configuration
        "RAG_USE_MMR",
        "RAG_USE_HEADING_SPLITTER",
        "RAG_ENABLE_DELETE",
        "RAG_SAFE_DELETE",
        "RAG_SCORE_THRESHOLD",
        "RAG_MMR_K",
        "RAG_MMR_FETCH_K",
        "RAG_MMR_LAMBDA_MULT",
        "RAG_INDEX_DIRS",
        # Knowledge base
        "ENABLE_HETEROGENEITY_FALLBACK",
        "HETEROGENEITY_FALLBACK_INCLUDE",
        "KNOWLEDGE_SYNC_AUTO_RECONCILE",
        "KNOWLEDGE_SYNC_INTERVAL_SECONDS",
        # Performance settings
        "ENABLE_SMART_MODEL_SELECTION",
        "ENABLE_FAST_QUERY_CLASSIFIER",
        "ENABLE_FAST_CONTENT_CLASSIFIER",
        "ENABLE_LIGHTWEIGHT_CONTEXT",
        "ENABLE_AGGRESSIVE_CACHING",
        "CONTENT_CLASSIFICATION_MODE",
        "ENABLE_STARTUP_LLM_CLASSIFICATION",
        "QUERY_ANALYSIS_TIMEOUT_MS",
        "CONTENT_PROCESSING_TIMEOUT_MS",
        "QUERY_CACHE_SIZE",
        "CONTENT_CACHE_SIZE",
        "PERFORMANCE_MODE",
        # Database settings
        "SQLITE_JOURNAL_MODE",
        "ADMIN_DB_TIMEOUT_SECONDS",
        "ADMIN_DB_BUSY_TIMEOUT_MS",
        "ADMIN_DB_CONNECT_RETRIES",
        "ADMIN_DB_CONNECT_RETRY_DELAY_MS",
        "ADMIN_DB_WRITE_RETRIES",
        "ADMIN_DB_WRITE_RETRY_DELAY_MS",
        "ADMIN_DB_AUDIT_TIMEOUT_SECONDS",
        "SEC_EVENTS_DB_TIMEOUT_SECONDS",
        "SEC_EVENTS_DB_BUSY_TIMEOUT_MS",
        # Feature flags
        "ENABLE_AB_TESTING",
        "AB_TEST_FAST_CLASSIFIER",
        "FAST_CLASSIFIER_ROLLOUT_PERCENT",
        "CHROMA_AUTO_RESET_ON_CONFIG_ERROR",
        # Security (non-sensitive)
        "EXCLUDED_IPS",
    ]

    result = {}
    for var in admin_managed_vars:
        value = os.getenv(var)
        result[var] = {
            "present": value is not None,
            "classification": "admin-managed",
            "override_available": True,
            "description": _get_setting_description(var),
        }

    return result


def _check_database_settings() -> Dict[str, Dict[str, Any]]:
    """Check status of database-stored setting categories."""
    try:
        settings_manager = get_settings_manager()

        # Setting categories from Phase 1 inventory
        categories = {
            "followup_settings": {
                "class": "FollowUpSettings",
                "fields": 9,
                "description": "Follow-up question configuration",
            },
            "response_settings": {
                "class": "ResponseSettings",
                "fields": 17,
                "description": "Response generation and caching",
            },
            "routing_settings": {
                "class": "QueryRoutingSettings",
                "fields": 6,
                "description": "Query routing configuration",
            },
            "feature_flags": {"class": "FeatureFlags", "fields": 12, "description": "Feature toggles"},
            "system_config_settings": {
                "class": "SystemConfigurationSettings",
                "fields": 10,
                "description": "System configuration",
            },
            "security_settings": {"class": "SecuritySettings", "fields": 11, "description": "Security settings"},
            "rag_config_settings": {
                "class": "RagConfigurationSettings",
                "fields": 12,
                "description": "RAG configuration",
            },
            "core_settings": {"class": "CoreSettings", "fields": 8, "description": "Core app metadata"},
            "ux_settings": {"class": "UXSettings", "fields": 8, "description": "UI/UX preferences"},
            "search_retrieval_settings": {
                "class": "SearchRetrievalSettings",
                "fields": 9,
                "description": "Search and retrieval",
            },
            "knowledge_settings": {"class": "KnowledgeSettings", "fields": 6, "description": "Knowledge base indexing"},
            "system_settings": {
                "class": "SystemSettings",
                "fields": 0,  # Future unified settings
                "description": "Unified settings storage (future)",
            },
        }

        result = {}
        for category, info in categories.items():
            try:
                # Check if settings exist in database
                method_name = f"get_{category}"
                if hasattr(settings_manager, method_name):
                    try:
                        settings_method = getattr(settings_manager, method_name)
                        settings_obj = settings_method()
                        configured = settings_obj is not None
                    except Exception as method_error:
                        logger.warning(f"Error executing {method_name}(): {method_error}")
                        configured = False
                else:
                    configured = False

                result[category] = {
                    "configured": configured,
                    "class_name": info["class"],
                    "field_count": info["fields"],
                    "description": info["description"],
                    "classification": "admin-managed",
                }
            except Exception as e:
                logger.warning(f"Error checking {category}: {e}")
                result[category] = {
                    "configured": False,
                    "class_name": info["class"],
                    "field_count": info["fields"],
                    "description": info["description"],
                    "classification": "admin-managed",
                    "error": str(e),
                }

        return result
    except Exception as e:
        logger.error(f"Error checking database settings: {e}")
        return {}


def _generate_summary(
    env_only: Dict[str, Dict[str, Any]],
    admin_managed_env: Dict[str, Dict[str, Any]],
    database_settings: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate configuration summary statistics."""
    total_env_only = len(env_only)
    configured_env_only = sum(1 for s in env_only.values() if s["present"])

    total_admin_env = len(admin_managed_env)
    configured_admin_env = sum(1 for s in admin_managed_env.values() if s["present"])

    total_db_categories = len(database_settings)
    configured_db_categories = sum(1 for s in database_settings.values() if s["configured"])

    return {
        "env_only": {
            "total": total_env_only,
            "configured": configured_env_only,
            "missing": total_env_only - configured_env_only,
            "percentage_configured": (
                round((configured_env_only / total_env_only) * 100, 1) if total_env_only > 0 else 0
            ),
        },
        "admin_managed_env": {
            "total": total_admin_env,
            "configured": configured_admin_env,
            "missing": total_admin_env - configured_admin_env,
            "percentage_configured": (
                round((configured_admin_env / total_admin_env) * 100, 1) if total_admin_env > 0 else 0
            ),
        },
        "database_settings": {
            "total_categories": total_db_categories,
            "configured_categories": configured_db_categories,
            "using_defaults": total_db_categories - configured_db_categories,
            "percentage_configured": (
                round((configured_db_categories / total_db_categories) * 100, 1) if total_db_categories > 0 else 0
            ),
        },
        "overall": {
            "total_settings": total_env_only + total_admin_env + total_db_categories,
            "total_configured": configured_env_only + configured_admin_env + configured_db_categories,
        },
    }


def _get_setting_description(setting_name: str) -> str:
    """Get human-readable description for setting."""
    descriptions = {
        # Environment
        "ENVIRONMENT": "Core environment detection (development/production)",
        "DEBUG_MODE": "Debug mode toggle",
        # API Keys
        "ANTHROPIC_API_KEY": "Claude API authentication key",
        "GOOGLE_API_KEY": "Google/Gemini API authentication key",
        "GITHUB_TOKEN": "GitHub API token for repository access",
        "API_KEY_ENCRYPTION_SECRET": "Secret for encrypting stored API keys",
        # Admin
        "ADMIN_DEFAULT_PASSWORD": "Default admin password",
        "ADMIN_DEFAULT_USERNAME": "Default admin username",
        "ADMIN_DEFAULT_EMAIL": "Default admin email address",
        # Deployment
        "PUBLIC_API_URL": "Public API base URL",
        "PUBLIC_GITHUB_USERNAME": "GitHub username for public display",
        "PUBLIC_GITHUB_REPO": "GitHub repository name",
        "PUBLIC_GA_TRACKING_ID": "Google Analytics tracking ID",
        "CORS_ORIGINS": "Allowed CORS origins",
        # Railway
        "RAILWAY_ENVIRONMENT_NAME": "Railway environment name",
        "RAILWAY_RUN_UID": "Railway run unique identifier",
        "RAILWAY_VOLUME_MOUNT_PATH": "Railway volume mount path",
        "RAILWAY_VOLUME_NAME": "Railway volume name",
        # Security
        "IP_HASH_SALT": "Salt for IP address hashing/anonymization",
        # Development
        "TESTING": "Test environment flag",
        "SKIP_INDEXING": "Skip knowledge base indexing on startup",
        "FORCE_REBUILD_DATA": "Force rebuild of vector indices",
        "UNIFIED_PERSIST_DIR": "ChromaDB persistence directory",
        "DISABLE_RATE_LIMITING": "Disable rate limiting (dev only)",
        "FORCE_DISABLE_MAINTENANCE": "Force disable maintenance mode",
        "FAST_LOGIN_MODE": "Fast login for development",
        # LLM
        "PRIMARY_LLM": "Primary LLM provider (claude/gemini)",
        "CLAUDE_MODEL": "Claude model version",
        "GEMINI_MODEL": "Gemini model version",
        "EMBEDDING_MODEL": "Embedding model for vector search",
        "REQUEST_TIMEOUT": "LLM request timeout in seconds",
        # Performance
        "RATE_LIMIT": "API rate limit configuration",
        "ENABLE_CACHING": "Enable response caching",
        "CACHE_TTL_SECONDS": "Cache time-to-live in seconds",
        "MAX_CACHE_SIZE": "Maximum cache size",
    }

    return descriptions.get(setting_name, f"Configuration setting: {setting_name}")
