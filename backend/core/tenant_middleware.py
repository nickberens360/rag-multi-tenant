import logging
import os
import re
import time
from typing import Optional

from fastapi import Request
from sqlalchemy import text

from .tenant_context import tenant_id_var, tenant_slug_var

logger = logging.getLogger(__name__)


async def tenant_middleware(request: Request, call_next):
    """Extract tenant from subdomain or path prefix and set contextvars.

    Precedence: subdomain > path prefix. Falls back to defaults when disabled or unresolved.
    """
    tenant_id: Optional[str] = None
    tenant_slug: Optional[str] = None

    # If multi-tenant is disabled, use default values
    if os.getenv("ENABLE_MULTI_TENANT", "false").lower() != "true":
        tenant_id = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        tenant_slug = os.getenv("DEFAULT_TENANT_SLUG", "default")
    else:
        # PRIORITY 1: Check X-Tenant-Slug header (set by frontend for API calls)
        tenant_slug = request.headers.get("X-Tenant-Slug")
        if tenant_slug:
            logger.debug(f"Tenant resolved from X-Tenant-Slug header: {tenant_slug}")

        # PRIORITY 2: Try subdomain
        if not tenant_slug:
            host = request.headers.get("host", "")
            subdomain_match = re.match(r"^([^.]+)\..*", host)
            if subdomain_match and subdomain_match.group(1) not in ["www", "api", "admin", "localhost"]:
                tenant_slug = subdomain_match.group(1)
                logger.debug(f"Tenant resolved from subdomain: {tenant_slug}")

        # PRIORITY 3: Fallback to path prefix e.g., /{tenant}/...
        if not tenant_slug:
            path_match = re.match(r"^/([^/]+)/.*", request.url.path or "")
            if path_match and path_match.group(1) not in ["api", "admin", "assets", "static"]:
                tenant_slug = path_match.group(1)
                logger.debug(f"Tenant resolved from path prefix: {tenant_slug}")

        # Resolve slug -> id via cache/DB
        if tenant_slug:
            tenant_id = _get_tenant_id_from_cache(tenant_slug)
            if tenant_id is None:
                try:
                    from backend.core.db_session import get_db_session_sync

                    with get_db_session_sync() as session:
                        if session is not None:
                            result = session.execute(
                                text("SELECT id FROM tenants WHERE slug = :slug AND deleted_at IS NULL"),
                                {"slug": tenant_slug},
                            )
                            row = result.fetchone()
                            if row:
                                # Ensure tenant_id is a string for consistent context and JSON safety
                                tenant_id = str(row[0])
                                _set_tenant_cache(tenant_slug, tenant_id)
                except Exception as e:
                    logger.warning("Failed to resolve tenant from database: %s", e)

    # Ensure defaults if unresolved
    if not tenant_id:
        # Use env if non-empty, else stable default UUID
        tenant_id = os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001"
    if not tenant_slug:
        # Use env if non-empty, else default slug
        tenant_slug = os.getenv("DEFAULT_TENANT_SLUG") or "default"

    # Store on request and contextvars
    request.state.tenant_id = tenant_id
    request.state.tenant_slug = tenant_slug

    token_id = tenant_id_var.set(tenant_id)
    token_slug = tenant_slug_var.set(tenant_slug)
    try:
        response = await call_next(request)
        return response
    finally:
        # Always restore previous context to avoid leaking across requests
        try:
            tenant_id_var.reset(token_id)
            tenant_slug_var.reset(token_slug)
        except Exception:
            pass


# --- Simple in-memory cache for slug -> tenant_id with TTL ---
_TENANT_CACHE: dict[str, tuple[str, float]] = {}


def _get_cache_ttl_seconds() -> int:
    try:
        return int(os.getenv("TENANT_CACHE_TTL_SECONDS", os.getenv("REDIS_TENANT_CACHE_TTL", "300")))
    except Exception:
        return 300


def _get_tenant_id_from_cache(slug: str) -> Optional[str]:
    try:
        # Try Redis first if available
        tid = _redis_get(slug)
        if tid:
            return tid
        entry = _TENANT_CACHE.get(slug)
        if not entry:
            return None
        tid, expires_at = entry
        if time.time() < expires_at:
            return tid
        _TENANT_CACHE.pop(slug, None)
        return None
    except Exception:
        return None


def _set_tenant_cache(slug: str, tenant_id: str) -> None:
    try:
        ttl = _get_cache_ttl_seconds()
        _redis_set(slug, tenant_id, ttl)
        _TENANT_CACHE[slug] = (tenant_id, time.time() + ttl)
    except Exception:
        pass


# --- Optional Redis backend ---
_REDIS_CLIENT: Optional[object] = None


def _get_redis_client() -> Optional[object]:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    try:
        import redis  # type: ignore

        url = os.getenv("REDIS_URL")
        if not url:
            return None
        client = redis.from_url(url, decode_responses=True)
        client.ping()
        _REDIS_CLIENT = client
        return _REDIS_CLIENT
    except Exception:
        return None


def _redis_get(key: str) -> Optional[str]:
    try:
        client = _get_redis_client()
        if not client:
            return None
        return client.get(f"tenant_slug:{key}")
    except Exception:
        return None


def _redis_set(key: str, value: str, ttl: int) -> None:
    try:
        client = _get_redis_client()
        if not client:
            return
        client.setex(f"tenant_slug:{key}", ttl, value)
    except Exception:
        pass
