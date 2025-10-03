"""
Performance optimization configuration and feature flags.

This module provides centralized control over performance optimizations
with easy rollback capabilities for production safety.
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PerformanceConfig:
    """Centralized performance optimization configuration."""

    # Feature flags for performance optimizations
    ENABLE_FAST_QUERY_CLASSIFIER = os.getenv("ENABLE_FAST_QUERY_CLASSIFIER", "true").lower() == "true"
    ENABLE_FAST_CONTENT_CLASSIFIER = (
        os.getenv("ENABLE_FAST_CONTENT_CLASSIFIER", "false").lower() == "true"
    )  # Disabled in hybrid mode
    ENABLE_LIGHTWEIGHT_CONTEXT = os.getenv("ENABLE_LIGHTWEIGHT_CONTEXT", "true").lower() == "true"
    ENABLE_AGGRESSIVE_CACHING = os.getenv("ENABLE_AGGRESSIVE_CACHING", "true").lower() == "true"

    # Hybrid mode configuration
    CONTENT_CLASSIFICATION_MODE = os.getenv("CONTENT_CLASSIFICATION_MODE", "hybrid")  # "fast", "startup_llm", "hybrid"
    ENABLE_STARTUP_LLM_CLASSIFICATION = os.getenv("ENABLE_STARTUP_LLM_CLASSIFICATION", "true").lower() == "true"

    # Performance thresholds
    QUERY_ANALYSIS_TIMEOUT_MS = int(os.getenv("QUERY_ANALYSIS_TIMEOUT_MS", "100"))  # 100ms max
    CONTENT_PROCESSING_TIMEOUT_MS = int(os.getenv("CONTENT_PROCESSING_TIMEOUT_MS", "50"))  # 50ms max
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "8000"))  # Token limit

    # Cache configuration
    QUERY_CACHE_SIZE = int(os.getenv("QUERY_CACHE_SIZE", "1000"))
    CONTENT_CACHE_SIZE = int(os.getenv("CONTENT_CACHE_SIZE", "500"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour

    @classmethod
    def get_performance_settings(cls) -> Dict[str, Any]:
        """Get all performance settings as a dictionary."""
        return {
            "fast_query_classifier": cls.ENABLE_FAST_QUERY_CLASSIFIER,
            "fast_content_classifier": cls.ENABLE_FAST_CONTENT_CLASSIFIER,
            "lightweight_context": cls.ENABLE_LIGHTWEIGHT_CONTEXT,
            "aggressive_caching": cls.ENABLE_AGGRESSIVE_CACHING,
            "content_classification_mode": cls.CONTENT_CLASSIFICATION_MODE,
            "startup_llm_classification": cls.ENABLE_STARTUP_LLM_CLASSIFICATION,
            "query_analysis_timeout_ms": cls.QUERY_ANALYSIS_TIMEOUT_MS,
            "content_processing_timeout_ms": cls.CONTENT_PROCESSING_TIMEOUT_MS,
            "max_context_length": cls.MAX_CONTEXT_LENGTH,
            "query_cache_size": cls.QUERY_CACHE_SIZE,
            "content_cache_size": cls.CONTENT_CACHE_SIZE,
            "cache_ttl_seconds": cls.CACHE_TTL_SECONDS,
        }

    @classmethod
    def log_performance_config(cls):
        """Log current performance configuration."""
        settings = cls.get_performance_settings()
        logger.info("Performance optimization settings:")
        for key, value in settings.items():
            logger.info(f"  {key}: {value}")

    @classmethod
    def is_optimization_enabled(cls, optimization_name: str) -> bool:
        """Check if a specific optimization is enabled."""
        optimization_flags = {
            "fast_query_classifier": cls.ENABLE_FAST_QUERY_CLASSIFIER,
            "fast_content_classifier": cls.ENABLE_FAST_CONTENT_CLASSIFIER,
            "lightweight_context": cls.ENABLE_LIGHTWEIGHT_CONTEXT,
            "aggressive_caching": cls.ENABLE_AGGRESSIVE_CACHING,
        }
        return optimization_flags.get(optimization_name, False)


# Environment-based feature toggles for easy production control
class FeatureFlags:
    """Feature flags for gradual rollout and A/B testing."""

    # Performance optimization rollout flags
    PERFORMANCE_MODE = os.getenv("PERFORMANCE_MODE", "optimized")  # "optimized", "legacy", "hybrid"

    # Rollout percentage (0-100) for gradual deployment
    FAST_CLASSIFIER_ROLLOUT_PERCENT = int(os.getenv("FAST_CLASSIFIER_ROLLOUT_PERCENT", "100"))

    # A/B testing flags
    ENABLE_AB_TESTING = os.getenv("ENABLE_AB_TESTING", "false").lower() == "true"
    AB_TEST_FAST_CLASSIFIER = os.getenv("AB_TEST_FAST_CLASSIFIER", "false").lower() == "true"

    @classmethod
    def should_use_fast_classifier(cls, user_id: str = None) -> bool:
        """Determine if fast classifier should be used for a given user/session."""
        if cls.PERFORMANCE_MODE == "legacy":
            return False
        elif cls.PERFORMANCE_MODE == "optimized":
            return True
        elif cls.PERFORMANCE_MODE == "hybrid":
            # Use rollout percentage for gradual deployment
            if user_id:
                # Deterministic based on user ID hash
                import hashlib

                hash_value = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
                return (hash_value % 100) < cls.FAST_CLASSIFIER_ROLLOUT_PERCENT
            else:
                # Random rollout for anonymous users
                import random

                return random.randint(1, 100) <= cls.FAST_CLASSIFIER_ROLLOUT_PERCENT

        return PerformanceConfig.ENABLE_FAST_QUERY_CLASSIFIER

    @classmethod
    def log_feature_flags(cls):
        """Log current feature flag configuration."""
        logger.info("Feature flags configuration:")
        logger.info(f"  Performance mode: {cls.PERFORMANCE_MODE}")
        logger.info(f"  Fast classifier rollout: {cls.FAST_CLASSIFIER_ROLLOUT_PERCENT}%")
        logger.info(f"  A/B testing enabled: {cls.ENABLE_AB_TESTING}")


# Performance monitoring and alerting
class PerformanceMonitor:
    """Monitor performance metrics and alert on degradation."""

    def __init__(self):
        self.metrics = {
            "query_analysis_times": [],
            "content_processing_times": [],
            "total_response_times": [],
            "llm_call_counts": [],
        }

    def record_query_analysis_time(self, duration_ms: float):
        """Record query analysis time."""
        self.metrics["query_analysis_times"].append(duration_ms)

        # Alert if analysis takes too long
        if duration_ms > PerformanceConfig.QUERY_ANALYSIS_TIMEOUT_MS:
            logger.warning(
                f"Query analysis took {duration_ms:.1f}ms (threshold: {PerformanceConfig.QUERY_ANALYSIS_TIMEOUT_MS}ms)"
            )

    def record_llm_call_count(self, count: int):
        """Record number of LLM calls per query."""
        self.metrics["llm_call_counts"].append(count)

        # Alert if too many LLM calls (target: 1 per query)
        if count > 1:
            logger.warning(f"Query used {count} LLM calls (target: 1)")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        if not any(self.metrics.values()):
            return {"status": "no_data"}

        summary = {}

        for metric_name, values in self.metrics.items():
            if values:
                summary[metric_name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }

        return summary

    def check_performance_targets(self) -> Dict[str, bool]:
        """Check if performance targets are being met."""
        targets = {}

        # Query analysis should be < 100ms average
        if self.metrics["query_analysis_times"]:
            avg_analysis_time = sum(self.metrics["query_analysis_times"]) / len(self.metrics["query_analysis_times"])
            targets["query_analysis_fast"] = avg_analysis_time < PerformanceConfig.QUERY_ANALYSIS_TIMEOUT_MS

        # LLM calls should average 1 per query
        if self.metrics["llm_call_counts"]:
            avg_llm_calls = sum(self.metrics["llm_call_counts"]) / len(self.metrics["llm_call_counts"])
            targets["single_llm_call"] = avg_llm_calls <= 1.1  # Allow small variance

        return targets


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
