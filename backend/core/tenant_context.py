"""
Per-request tenant context using contextvars.

This allows any code path (e.g., audit logging) to read the current
tenant context without threading Request objects through every call.
"""

from contextvars import ContextVar
from typing import Optional

tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
tenant_slug_var: ContextVar[Optional[str]] = ContextVar("tenant_slug", default=None)


def get_current_tenant_id() -> Optional[str]:
    return tenant_id_var.get(None)


def get_current_tenant_slug() -> Optional[str]:
    return tenant_slug_var.get(None)
