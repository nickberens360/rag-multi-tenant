# Minimal RBAC (v1) — Overview and Guidance

Goals
- Keep the smallest useful set of roles/permissions that enforces tenant isolation and least privilege.
- Make expansion easy without schema churn (add roles/permissions later, optional custom roles).

Roles (built-in)
- SuperAdmin (platform) — platform:admin short-circuit (allow-all, audited).
- TenantOwner (tenant) — tenant:manage, user:manage, data:read, data:write.
- TenantAdmin (tenant) — user:manage, data:read, data:write.
- Member (tenant) — data:read, data:write. (Viewer omitted for v1.)

Permission Slugs
- platform:admin — platform superuser, short-circuit.
- tenant:manage — tenant lifecycle, billing, destructive ops.
- user:manage — invite/remove users, assign roles in tenant.
- data:read — read/search/use data within tenant.
- data:write — modify/ingest/configure data within tenant.

Design Choices
- Scope at evaluation time: `authorize(user, perm, tenant_id)` enforces tenant boundary; default deny.
- Tokens carry minimal claims (is_platform_admin, role IDs). Server resolves permissions.
- Caching: cache effective permissions per (user_id, tenant_id) with short TTL + explicit invalidation on role changes.
- Safeguards: prevent removing the last TenantOwner; audit all role changes and impersonation.

 

FastAPI Enforcement Pattern (sketch)
```python
# backend/core/rbac.py
from fastapi import HTTPException, status

PLATFORM_ADMIN = "platform:admin"

def authorize(user_ctx, permission: str, tenant_id: str | None) -> None:
    # Short-circuit for platform admin
    if user_ctx.is_platform_admin:
        return

    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant scope required")

    # Resolve effective permissions for (user_id, tenant_id)
    effective_perms = user_ctx.get_effective_permissions(tenant_id)
    if permission not in effective_perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

# backend/dependencies.py
from fastapi import Depends

def require_perm(permission: str, tenant_from: str = "path"):
    def _dep(user_ctx = Depends(get_user_ctx), tenant_id = Depends(get_tenant_id_from(tenant_from))):
        authorize(user_ctx, permission, tenant_id)
    return _dep
```

Data Model (minimal, forwards-compatible)
- roles(id, name, scope: platform|tenant, tenant_id NULLABLE, built_in BOOL)
- permissions(id, slug)
- role_permissions(role_id, permission_id)
- user_roles(user_id, role_id, tenant_id) UNIQUE (user_id, role_id, tenant_id)

Operational Notes
- Seed built-ins and enforce idempotency.
- Use feature flag `enable_custom_roles` (off by default) to permit tenant-defined roles later.
- Log/audit role changes; add step-up auth (MFA) for `tenant:manage` and sensitive actions when available.

Testing Strategy
- Validate the role→permission matrix (see rbac_test_matrix.yaml).
- Route tests: deny without tenant scope; allow with correct role; deny cross-tenant.
