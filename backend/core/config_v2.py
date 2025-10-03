"""
Centralized configuration management v2 with database-first approach.
This module provides configuration that:
1. Uses hardcoded defaults for non-secret settings
2. Checks database for overrides
3. Falls back to environment variables only for secrets

Backwards-compatibility notes:
- Many modules reference uppercase constants on AppConfig as class attributes
  (e.g., DEFAULT_SEARCH_K). To avoid breaking those imports when switching to
  this module, we initialize common constants at module load. Where practical,
  these values are sourced from DB settings (with safe defaults), otherwise we
  retain the original static defaults from the legacy config.
"""

import ipaddress
import logging
import os
import re
import secrets
from typing import List
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)


def sanitize_error_message(error: Exception, user_message: str = "An error occurred") -> str:
    """
    Sanitize error messages for production use.

    Args:
        error: The exception that occurred
        user_message: Safe message to show to users in production

    Returns:
        str: Sanitized error message
    """
    # In development or debug mode, show detailed errors
    if not AppConfig.IS_PRODUCTION or AppConfig.DEBUG_MODE:
        return str(error)

    # In production, return generic message and log actual error
    logger.error(f"Error sanitized for production: {str(error)}", exc_info=True)
    return user_message


class AppConfig:
    """Centralized configuration with database-first approach and hardcoded defaults."""

    # =====================================
    # ENVIRONMENT DETECTION (from env only)
    # =====================================
    # Sanitize ENVIRONMENT to tolerate inline comments in container env-files
    _raw_env = os.getenv("ENVIRONMENT", "development")
    ENVIRONMENT = _raw_env.split("#", 1)[0].strip().lower()
    IS_PRODUCTION = ENVIRONMENT in ("production", "prod")
    DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true" and not IS_PRODUCTION

    # =====================================
    # SECRETS (must come from environment)
    # =====================================
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional, for git integration
    ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD")
    ADMIN_DEFAULT_USERNAME = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")

    # =====================================
    # MULTI-TENANT CONFIGURATION
    # =====================================
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    DEFAULT_TENANT_ID = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    DEFAULT_TENANT_SLUG = os.getenv("DEFAULT_TENANT_SLUG", "default")
    ENABLE_MULTI_TENANT = os.getenv("ENABLE_MULTI_TENANT", "true").lower() == "true"
    ENABLE_RLS_ENFORCEMENT = os.getenv("ENABLE_RLS_ENFORCEMENT", "true").lower() == "true"
    TENANT_RESOLUTION_MODE = os.getenv("TENANT_RESOLUTION_MODE", "subdomain_then_path")

    # Redis for caching
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_TENANT_CACHE_TTL = int(os.getenv("REDIS_TENANT_CACHE_TTL", "300"))  # 5 minutes

    # Session configuration
    SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", None)
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "lax"

    # =====================================
    # DEPLOYMENT-SPECIFIC (from environment)
    # =====================================
    PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "https://nickberens-astro-production.up.railway.app")
    PUBLIC_GITHUB_USERNAME = os.getenv("PUBLIC_GITHUB_USERNAME", "nickberens360")
    PUBLIC_GITHUB_REPO = os.getenv("PUBLIC_GITHUB_REPO", "nickberens-astro")
    PUBLIC_GA_TRACKING_ID = os.getenv("PUBLIC_GA_TRACKING_ID", "G-YRSSE66Z31")

    # =====================================
    # HARDCODED DEFAULTS (overridable by database)
    # =====================================

    # LLM Configuration Defaults
    PRIMARY_LLM_DEFAULT = "claude"
    CLAUDE_MODEL_DEFAULT = "claude-3-5-sonnet-20241022"
    GEMINI_MODEL_DEFAULT = "gemini-1.5-flash"
    EMBEDDING_MODEL_DEFAULT = "models/embedding-001"

    # Search Configuration Defaults
    SEARCH_THRESHOLD_DEFAULT = 55
    MAX_RESULTS_DEFAULT = 15
    ILLUSTRATIONS_PATH_DEFAULT = "backend/knowledge/illustrations.json"

    # Performance Defaults
    REQUEST_TIMEOUT_DEFAULT = 60
    ENABLE_CACHING_DEFAULT = True
    CACHE_TTL_DEFAULT = 3600
    MAX_CACHE_SIZE_DEFAULT = 1000

    # RAG Configuration Defaults
    RAG_USE_MMR_DEFAULT = False
    RAG_USE_HEADING_SPLITTER_DEFAULT = False
    RAG_ENABLE_DELETE_DEFAULT = False
    RAG_SAFE_DELETE_DEFAULT = True
    RAG_SCORE_THRESHOLD_DEFAULT = 0.2
    RAG_MMR_K_DEFAULT = 4
    RAG_MMR_FETCH_K_DEFAULT = 20
    RAG_MMR_LAMBDA_MULT_DEFAULT = 0.5
    RAG_INDEX_DIRS_DEFAULT = ["backend/knowledge"]

    # Feature Flags Defaults
    ENABLE_HETEROGENEITY_FALLBACK_DEFAULT = False
    ENABLE_FOLLOWUP_PREGENERATION_DEFAULT = False
    FOLLOWUP_MODE_DEFAULT = "static"
    CACHE_FOLLOWUP_RESPONSES_DEFAULT = True

    # System Configuration Defaults
    LOG_LEVEL_DEFAULT = "INFO"
    RATE_LIMIT_DEFAULT = "5/minute"
    HOST_DEFAULT = "0.0.0.0"
    PORT_DEFAULT = 8000

    # Database Configuration Defaults
    ADMIN_DB_PATH_DEFAULT = "backend/logs/admin_monitoring.db"
    ADMIN_DB_TIMEOUT_SECONDS_DEFAULT = 10
    ADMIN_DB_BUSY_TIMEOUT_MS_DEFAULT = 15000
    SQLITE_JOURNAL_MODE_DEFAULT = "WAL"
    ADMIN_DB_CONNECT_RETRIES_DEFAULT = 7
    ADMIN_DB_CONNECT_RETRY_DELAY_MS_DEFAULT = 300

    # Search & Retrieval Defaults
    DEFAULT_SEARCH_K_DEFAULT = 8
    EXPANDED_SEARCH_K_DEFAULT = 12
    SEARCH_EXPANSION_MULTIPLIER_DEFAULT = 3
    DEFAULT_DISTANCE_THRESHOLD_DEFAULT = 0.5
    INCLUSIVE_DISTANCE_THRESHOLD_DEFAULT = 1.0
    BROAD_DISTANCE_THRESHOLD_DEFAULT = 1.2
    RETRIEVAL_SCORE_THRESHOLD_DEFAULT = 0.3
    LOW_SIMILARITY_THRESHOLD_DEFAULT = 0.7

    # Illustration & Fuzzy Defaults (legacy constants used across modules)
    DEFAULT_ILLUSTRATION_COUNT_DEFAULT = 10
    MAX_ILLUSTRATION_SEARCH_DEFAULT = 200
    SHORT_TERM_LENGTH_DEFAULT = 6
    MEDIUM_TERM_LENGTH_DEFAULT = 10
    SHORT_TERM_FUZZY_THRESHOLD_DEFAULT = 0.45
    MEDIUM_TERM_FUZZY_THRESHOLD_DEFAULT = 0.5
    LONG_TERM_FUZZY_THRESHOLD_DEFAULT = 0.55
    DEFAULT_FUZZY_THRESHOLD_DEFAULT = 0.7

    # Statistics defaults (used by routes/stats, routes/performance)
    DEFAULT_CACHE_HIT_RATE_DEFAULT = 0.85
    DEFAULT_TOTAL_SOURCES_DEFAULT = 15
    DEFAULT_TOTAL_TOPICS_DEFAULT = 8

    # =====================================
    # DYNAMIC PROPERTIES WITH DB OVERRIDE
    # =====================================

    @classmethod
    def get_primary_llm(cls) -> str:
        """Get primary LLM with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_system_config_settings()
            if settings and settings.primary_llm:
                return settings.primary_llm
        except Exception:
            pass
        return cls.PRIMARY_LLM_DEFAULT

    @classmethod
    def get_claude_model(cls) -> str:
        """Get Claude model with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_system_config_settings()
            if settings and settings.claude_model:
                return settings.claude_model
        except Exception:
            pass
        return cls.CLAUDE_MODEL_DEFAULT

    @classmethod
    def get_gemini_model(cls) -> str:
        """Get Gemini model with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_system_config_settings()
            if settings and settings.gemini_model:
                return settings.gemini_model
        except Exception:
            pass
        return cls.GEMINI_MODEL_DEFAULT

    @classmethod
    def get_embedding_model(cls) -> str:
        """Get embedding model with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_system_config_settings()
            if settings and settings.embedding_model:
                return settings.embedding_model
        except Exception:
            pass
        return cls.EMBEDDING_MODEL_DEFAULT

    @classmethod
    def get_search_threshold(cls) -> int:
        """Get search threshold with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_search_retrieval_settings()
            if settings:
                # Map semantic_similarity_threshold to search threshold (0-100)
                return int(settings.semantic_similarity_threshold * 100)
        except Exception:
            pass
        return cls.SEARCH_THRESHOLD_DEFAULT

    @classmethod
    def get_max_results(cls) -> int:
        """Get max results with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_search_retrieval_settings()
            if settings and settings.max_search_results:
                return settings.max_search_results
        except Exception:
            pass
        return cls.MAX_RESULTS_DEFAULT

    @classmethod
    def get_cache_ttl(cls) -> int:
        """Get cache TTL with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_response_settings()
            if settings and settings.cache_ttl_seconds:
                return settings.cache_ttl_seconds
        except Exception:
            pass
        return cls.CACHE_TTL_DEFAULT

    @classmethod
    def get_enable_caching(cls) -> bool:
        """Get caching enabled with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_response_settings()
            if settings is not None:
                return settings.enable_caching
        except Exception:
            pass
        return cls.ENABLE_CACHING_DEFAULT

    @classmethod
    def get_rate_limit(cls) -> str:
        """Get rate limit with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_system_config_settings()
            if settings and settings.rate_limit:
                return settings.rate_limit
        except Exception:
            pass
        return cls.RATE_LIMIT_DEFAULT

    @classmethod
    def get_rag_use_mmr(cls) -> bool:
        """Get RAG MMR usage with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_rag_config_settings()
            if settings is not None:
                return settings.rag_use_mmr
        except Exception:
            pass
        return cls.RAG_USE_MMR_DEFAULT

    @classmethod
    def get_rag_score_threshold(cls) -> float:
        """Get RAG score threshold with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_rag_config_settings()
            if settings is not None:
                return settings.rag_score_threshold
        except Exception:
            pass
        return cls.RAG_SCORE_THRESHOLD_DEFAULT

    @classmethod
    def get_rag_index_dirs(cls) -> List[str]:
        """Get RAG index directories with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_knowledge_settings()
            if settings and settings.index_directories:
                # Filter out public directory to avoid scanning static assets
                return [d for d in settings.index_directories if not str(d).strip().startswith("public")]
        except Exception:
            pass
        return cls.RAG_INDEX_DIRS_DEFAULT

    @classmethod
    def get_enable_heterogeneity_fallback(cls) -> bool:
        """Get heterogeneity fallback enabled with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_knowledge_settings()
            if settings is not None:
                return settings.enable_heterogeneity_fallback
        except Exception:
            pass
        return cls.ENABLE_HETEROGENEITY_FALLBACK_DEFAULT

    @classmethod
    def get_heterogeneity_include_patterns(cls) -> List[str]:
        """Get heterogeneity include patterns with database override."""
        try:
            from .settings_manager import get_settings_manager

            settings = get_settings_manager().get_knowledge_settings()
            if settings and settings.heterogeneity_fallback_include:
                return settings.heterogeneity_fallback_include
        except Exception:
            pass
        return []

    # =====================================
    # COMPATIBILITY PROPERTIES
    # =====================================
    # These provide backward compatibility with existing code
    # Note: These will be populated at module load time below

    # Server Configuration (hardcoded, rarely changes)
    LOG_LEVEL = LOG_LEVEL_DEFAULT
    HOST = HOST_DEFAULT
    PORT = PORT_DEFAULT

    # Static configuration (doesn't change at runtime)
    ILLUSTRATIONS_PATH = ILLUSTRATIONS_PATH_DEFAULT
    ADMIN_DB_PATH = ADMIN_DB_PATH_DEFAULT

    # CORS Configuration
    @staticmethod
    def _is_valid_origin(origin: str) -> bool:
        """Validate a single CORS origin URL."""
        if not origin or not isinstance(origin, str):
            return False

        # Allow wildcard only when not in production
        if origin == "*":
            env = os.getenv("ENVIRONMENT")
            if env is not None:
                is_prod = env.lower() in ["production", "prod"]
            else:
                is_prod = AppConfig.IS_PRODUCTION

            if not is_prod:
                logger.warning("Wildcard CORS origin allowed in development mode")
                return True
            logger.error("Wildcard CORS origin not allowed in production")
            return False

        # Basic URL validation
        try:
            parsed = urlparse(origin)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"Invalid CORS origin format: {origin}")
                return False

            # Only allow http/https
            if parsed.scheme not in ["http", "https"]:
                logger.warning(f"Invalid CORS origin scheme: {origin}")
                return False

            # Enforce HTTPS for public domains (allow HTTP for local/private networks)
            netloc_lower = parsed.netloc.lower()
            host = parsed.hostname or ""
            is_private_ip = False
            try:
                ip_obj = ipaddress.ip_address(host)
                is_private_ip = ip_obj.is_private or ip_obj.is_loopback
            except ValueError:
                # Not an IP address
                is_private_ip = False

            is_localhost = host.startswith("localhost") or host.startswith("127.0.0.1")
            if not is_localhost and not is_private_ip:
                if parsed.scheme != "https":
                    logger.warning(f"Non-HTTPS origin for production/public domain: {origin}")
                    return False

            # Domain format validation (stricter)
            domain_part = parsed.netloc.split(":")[0]
            domain_format_valid = re.match(
                r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                domain_part,
            ) is not None or domain_part in ["localhost", "127.0.0.1"]
            if not domain_format_valid:
                logger.warning(f"Invalid domain format: {domain_part}")
                return False

            # Block obviously malicious domains
            suspicious = ["malware", "phishing", "hack", "exploit", "evil"]
            if any(keyword in netloc_lower for keyword in suspicious):
                logger.error(f"Suspicious domain blocked: {origin}")
                return False

            return True

        except Exception as e:
            logger.warning(f"Error validating CORS origin {origin}: {e}")
            return False

    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get CORS origins with sensible defaults."""
        # Check for environment override
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            origins = []
            for origin in env_origins.split(","):
                origin = origin.strip()
                if AppConfig._is_valid_origin(origin):
                    origins.append(origin)
            if origins:
                return origins

        # Default origins based on environment
        production_origins = [
            "https://nickberens.me",
            "https://www.nickberens.me",
            "https://nickberens360.netlify.app",
            "https://development--nickberens360.netlify.app",
            "https://nickberens-astro.onrender.com",
            "https://nickberens-astro-production.up.railway.app",
            "https://nickberens-astro-development.up.railway.app",
        ]

        development_origins = [
            "http://localhost:4321",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003",
            "https://development--nickberens360.netlify.app",
        ]

        # Check environment dynamically for testing
        current_env = os.getenv("ENVIRONMENT", "development").split("#", 1)[0].strip().lower()
        is_production = current_env in ("production", "prod")

        if is_production:
            return production_origins
        else:
            return production_origins + development_origins

    # IP Anonymization Settings
    @classmethod
    def get_ip_hash_salt(cls) -> str:
        """Get IP hash salt with secure default generation."""
        salt = os.getenv("IP_HASH_SALT", "")

        if not salt:
            if cls.IS_PRODUCTION:
                raise ValueError(
                    "IP_HASH_SALT must be explicitly set in production environments. "
                    "Generate a secure salt using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            else:
                # Generate a secure random salt for development
                salt = secrets.token_urlsafe(32)
                logger.warning(
                    f"Using generated IP_HASH_SALT for development: {salt[:8]}... "
                    "Set IP_HASH_SALT environment variable for consistent hashing."
                )

        return salt

    @classmethod
    def get_admin_default_password(cls) -> str:
        """Get admin default password with secure default generation."""
        password = os.getenv("ADMIN_DEFAULT_PASSWORD", "")

        if not password:
            if cls.IS_PRODUCTION:
                raise ValueError(
                    "ADMIN_DEFAULT_PASSWORD must be explicitly set in production environments. "
                    "Generate a secure password using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            else:
                # Generate a secure random password for development
                password = secrets.token_urlsafe(32)
                logger.warning(
                    f"Using generated ADMIN_DEFAULT_PASSWORD for development: {password[:8]}... "
                    "Set ADMIN_DEFAULT_PASSWORD environment variable for consistent authentication."
                )

        return password

    @classmethod
    def get_excluded_ips(cls) -> List[str]:
        """Get excluded IPs from SecuritySettings if available, else env."""
        try:
            from .settings_manager import get_settings_manager

            sec = get_settings_manager().get_security_settings()
            if sec and getattr(sec, "excluded_ips", None):
                return list(sec.excluded_ips)
        except Exception:
            pass

        # Fallback to environment parsing
        excluded_ips_str = os.getenv("EXCLUDED_IPS", "")
        if not excluded_ips_str:
            return []
        excluded_ips: List[str] = []
        for ip in excluded_ips_str.split(","):
            ip = ip.strip()
            if ip:
                try:
                    ipaddress.ip_address(ip)
                    excluded_ips.append(ip)
                except ValueError:
                    logger.warning(f"Invalid IP address in EXCLUDED_IPS: {ip}")
        return excluded_ips

    # App Metadata
    APP_TITLE = "Nick Berens Portfolio API"
    APP_DESCRIPTION = """
Intelligent API for Nick Berens' Portfolio and Knowledge Base

This API provides AI-powered access to Nick's professional experience, skills, projects, and creative work using advanced RAG (Retrieval-Augmented Generation) technology.

Built with ❤️ by Nick Berens using FastAPI, Vue.js, and modern AI technologies.
    """
    APP_VERSION = "2.2.0"

    # Properties that need to be set at module load time for backward compatibility
    ENABLE_SMART_MODEL_SELECTION = True
    RETRIEVAL_SCORE_THRESHOLD = RETRIEVAL_SCORE_THRESHOLD_DEFAULT
    MAX_CACHE_SIZE = MAX_CACHE_SIZE_DEFAULT
    EXCLUDED_IPS = []
    IP_HASH_SALT = ""
    ANONYMIZE_IPS = True

    # Back-compat constants (initialized below)
    DEFAULT_SEARCH_K = DEFAULT_SEARCH_K_DEFAULT
    EXPANDED_SEARCH_K = EXPANDED_SEARCH_K_DEFAULT
    SEARCH_EXPANSION_MULTIPLIER = SEARCH_EXPANSION_MULTIPLIER_DEFAULT
    DEFAULT_DISTANCE_THRESHOLD = DEFAULT_DISTANCE_THRESHOLD_DEFAULT
    INCLUSIVE_DISTANCE_THRESHOLD = INCLUSIVE_DISTANCE_THRESHOLD_DEFAULT
    BROAD_DISTANCE_THRESHOLD = BROAD_DISTANCE_THRESHOLD_DEFAULT

    DEFAULT_ILLUSTRATION_COUNT = DEFAULT_ILLUSTRATION_COUNT_DEFAULT
    MAX_ILLUSTRATION_SEARCH = MAX_ILLUSTRATION_SEARCH_DEFAULT

    SHORT_TERM_LENGTH = SHORT_TERM_LENGTH_DEFAULT
    MEDIUM_TERM_LENGTH = MEDIUM_TERM_LENGTH_DEFAULT
    SHORT_TERM_FUZZY_THRESHOLD = SHORT_TERM_FUZZY_THRESHOLD_DEFAULT
    MEDIUM_TERM_FUZZY_THRESHOLD = MEDIUM_TERM_FUZZY_THRESHOLD_DEFAULT
    LONG_TERM_FUZZY_THRESHOLD = LONG_TERM_FUZZY_THRESHOLD_DEFAULT
    DEFAULT_FUZZY_THRESHOLD = DEFAULT_FUZZY_THRESHOLD_DEFAULT

    DEFAULT_CACHE_HIT_RATE = DEFAULT_CACHE_HIT_RATE_DEFAULT
    DEFAULT_TOTAL_SOURCES = DEFAULT_TOTAL_SOURCES_DEFAULT
    DEFAULT_TOTAL_TOPICS = DEFAULT_TOTAL_TOPICS_DEFAULT

    # Response context defaults (legacy constants used by some modules)
    DEFAULT_MAX_CONTEXT_LENGTH = 2000
    MAX_CONTEXT_DOCUMENTS = 3
    CONTEXT_FILL_RATIO = 0.7


# Initialize properties at module load time
def _init_backcompat_from_db() -> None:
    """Initialize legacy constants from DB settings where applicable."""
    try:
        from .settings_manager import get_settings_manager

        sm = get_settings_manager()

        # Response settings for context-related constants
        try:
            rs = sm.get_response_settings()
            if rs:
                AppConfig.DEFAULT_MAX_CONTEXT_LENGTH = int(getattr(rs, "max_context_length", 2000) or 2000)
                AppConfig.MAX_CONTEXT_DOCUMENTS = int(getattr(rs, "max_context_documents", 3) or 3)
                AppConfig.CONTEXT_FILL_RATIO = float(getattr(rs, "context_fill_ratio", 0.7) or 0.7)
        except Exception:
            pass

        # Security settings for anonymization and excluded IPs
        try:
            sec = sm.get_security_settings()
            if sec:
                AppConfig.ANONYMIZE_IPS = bool(getattr(sec, "anonymize_ips", True))
                if getattr(sec, "excluded_ips", None):
                    AppConfig.EXCLUDED_IPS = list(sec.excluded_ips)
        except Exception:
            pass

        # System configuration for cache sizing (optional)
        try:
            sc = sm.get_system_config_settings()
            if sc and getattr(sc, "max_cache_size", None):
                AppConfig.MAX_CACHE_SIZE = int(sc.max_cache_size)
        except Exception:
            pass

    except Exception:
        # Safe to ignore; defaults remain in place
        pass


# Initialize properties and back-compat constants at module load time
AppConfig.EXCLUDED_IPS = AppConfig.get_excluded_ips()
AppConfig.IP_HASH_SALT = AppConfig.get_ip_hash_salt()
AppConfig.ADMIN_DEFAULT_PASSWORD = AppConfig.get_admin_default_password()
_init_backcompat_from_db()

# NOTE: Static attribute assignments removed to enable dynamic configuration updates.
# All code should use AppConfig.get_*() methods instead of AppConfig.* attributes
# to ensure settings changes in the admin UI take effect immediately without restart.
