"""
Development-only debug endpoints.

Exposes current tenant resolution context for easier testing.
"""

import os

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _is_debug_enabled() -> bool:
    # Enabled if not production or explicit override via env
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env not in {"production", "prod"}:
        return True
    return os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() in {"1", "true", "yes"}


@router.get("/debug/tenant")
async def get_tenant_context(request: Request) -> dict:
    if not _is_debug_enabled():
        # Hide this endpoint in production unless explicitly enabled
        raise HTTPException(status_code=404, detail="Not found")

    tenant_id = getattr(request.state, "tenant_id", None)
    tenant_slug = getattr(request.state, "tenant_slug", None)

    return {
        "tenant_id": tenant_id,
        "tenant_slug": tenant_slug,
        "path": request.url.path,
        "host": request.headers.get("host"),
        "enable_multi_tenant": os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true",
        "enable_rls_enforcement": os.getenv("ENABLE_RLS_ENFORCEMENT", "false").lower() == "true",
    }


# Support path-prefix style for local/dev testing: /{tenant}/api/debug/tenant
@router.get("/{tenant}/api/debug/tenant")
async def get_tenant_context_prefixed(tenant: str, request: Request) -> dict:
    return await get_tenant_context(request)
