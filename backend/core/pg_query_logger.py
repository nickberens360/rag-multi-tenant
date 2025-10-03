"""
Postgres query logging service (RLS-aware).

Writes query logs to the Postgres query_logs table with tenant scoping via RLS.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text

from .config_v2 import AppConfig
from .db_session import get_db_session_sync
from .geolocation_service import get_geolocation_service
from .tenant_context import get_current_tenant_id


class PostgresQueryLogger:
    """Service for logging user queries and AI responses to Postgres (RLS)."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        # Defaults from config/settings
        self.anonymize_ips = AppConfig.ANONYMIZE_IPS
        self.excluded_ips = set(AppConfig.EXCLUDED_IPS or [])
        self.ip_salt = AppConfig.IP_HASH_SALT or ""

    # --- Public API ---
    def log_query(
        self,
        client_ip: str,
        question: str,
        response: str,
        model_used: str,
        query_type: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Log a query to Postgres with RLS tenant context."""
        try:
            # Respect analytics feature flag
            from .settings_manager import get_settings_manager

            if not get_settings_manager().is_feature_enabled("enable_analytics"):
                return

            # Process IP and optional geolocation
            processed_ip = self._process_ip_for_logging(client_ip)
            if processed_ip is None:
                return

            geo = {}
            try:
                gs = get_geolocation_service()
                if gs:
                    info = gs.get_location(client_ip)
                    if info:
                        geo = {
                            "location_city": info.get("city"),
                            "location_region": info.get("region"),
                            "location_country": info.get("country_name"),
                            "location_country_code": info.get("country_code"),
                        }
            except Exception as e:
                self.logger.debug("Geolocation lookup failed: %s", e)

            # Extract metadata
            md = metadata or {}
            vector_score = md.get("vector_search_score")
            sources_used = md.get("source_urls") or md.get("sources_used") or []
            followups = md.get("followup_questions") or md.get("follow_up_questions") or []
            cache_hit = bool(md.get("cache_hit", False))
            error_occurred = bool(md.get("error_occurred", False))
            error_message = md.get("error_message")

            response_time_ms = response_time * 1000 if response_time else None

            # Resolve tenant id from context (middleware set)
            tenant_id = get_current_tenant_id() or os.getenv(
                "DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"
            )

            # Determine a session identifier if provided
            session_id = None
            try:
                if md.get("session_id"):
                    session_id = str(md.get("session_id"))
                elif request_id:
                    session_id = str(request_id)
            except Exception:
                session_id = request_id

            with get_db_session_sync() as session:
                if session is None:
                    # No DB available; do not raise
                    return
                # Ensure RLS context if enabled
                try:
                    if os.getenv("ENABLE_RLS_ENFORCEMENT", "false").lower() == "true" and tenant_id:
                        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                except Exception:
                    pass

                # Insert query log
                session.execute(
                    text(
                        """
                        INSERT INTO query_logs (
                            tenant_id, session_id, user_query, system_response, query_type, response_time_ms,
                            llm_provider, llm_model, vector_search_score, sources_used, follow_up_questions,
                            cache_hit, error_occurred, error_message, client_ip, location_city, location_region,
                            location_country, location_country_code, timestamp
                        ) VALUES (
                            :tenant_id, :session_id, :user_query, :system_response, :query_type, :response_time_ms,
                            :llm_provider, :llm_model, :vector_search_score, CAST(:sources_used AS jsonb), CAST(:follow_up_questions AS jsonb),
                            :cache_hit, :error_occurred, :error_message, :client_ip, :location_city, :location_region,
                            :location_country, :location_country_code, :timestamp
                        )
                        """
                    ),
                    {
                        "tenant_id": str(tenant_id),
                        "session_id": session_id,
                        "user_query": question,
                        "system_response": response,
                        "query_type": query_type,
                        "response_time_ms": response_time_ms,
                        "llm_provider": self._infer_llm_provider(model_used),
                        "llm_model": model_used,
                        "vector_search_score": vector_score,
                        "sources_used": json.dumps(sources_used) if sources_used else None,
                        "follow_up_questions": json.dumps(followups) if followups else None,
                        "cache_hit": cache_hit,
                        "error_occurred": error_occurred,
                        "error_message": error_message,
                        "client_ip": processed_ip,
                        "location_city": geo.get("location_city"),
                        "location_region": geo.get("location_region"),
                        "location_country": geo.get("location_country"),
                        "location_country_code": geo.get("location_country_code"),
                        "timestamp": datetime.now(timezone.utc),
                    },
                )
                # Commit is handled by context manager
        except Exception as e:
            self.logger.error("Failed to log query to Postgres: %s", e)

    def log_streaming_query(
        self,
        client_ip: str,
        question: str,
        model_used: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        # No-op placeholder (we log final response only)
        return

    def update_streaming_response(
        self,
        cache_key: str,
        client_ip: str,
        question: str,
        actual_response: str,
        request_id: Optional[str] = None,
        model_used: Optional[str] = None,
        response_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            self.log_query(
                client_ip=client_ip,
                question=question,
                response=actual_response,
                model_used=model_used or "streaming_completion",
                query_type="text",
                response_time=response_time or 0.0,
                metadata={
                    **(metadata or {}),
                    "cache_key": cache_key,
                    "response_updated": datetime.now(timezone.utc).isoformat(),
                },
                request_id=request_id,
            )
            return True
        except Exception as e:
            self.logger.error("Failed to log streaming response completion (PG): %s", e)
            return False

    # --- Helpers ---
    def anonymize_ip(self, ip_address: str) -> str:
        if not self.anonymize_ips:
            return ip_address
        import hashlib

        salted_ip = f"{ip_address}{self.ip_salt}".encode("utf-8")
        return f"anon_{hashlib.sha256(salted_ip).hexdigest()[:16]}"

    def should_log_ip(self, client_ip: str) -> bool:
        return client_ip not in self.excluded_ips

    def _process_ip_for_logging(self, ip_address: str) -> Optional[str]:
        if ip_address in self.excluded_ips:
            return None
        return self.anonymize_ip(ip_address) if self.anonymize_ips else ip_address

    def _infer_llm_provider(self, model_name: Optional[str]) -> str:
        if not model_name:
            return "unknown"
        m = model_name.lower()
        if "claude" in m or "anthropic" in m:
            return "anthropic"
        if "gpt" in m or "openai" in m:
            return "openai"
        if "gemini" in m or "google" in m:
            return "google"
        if "llama" in m:
            return "meta"
        return "unknown"
