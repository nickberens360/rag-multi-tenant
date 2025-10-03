# Implementation Code (Agent-Executable)

## File: backend/core/tenant_middleware.py
```python
from fastapi import Request, HTTPException
from typing import Optional
import uuid
import re

async def tenant_middleware(request: Request, call_next):
    """Extract tenant from subdomain or path prefix."""
    tenant_id = None
    tenant_slug = None

    # Extract from subdomain
    host = request.headers.get("host", "")
    subdomain_match = re.match(r"^([^.]+)\..*", host)
    if subdomain_match and subdomain_match.group(1) not in ["www", "api", "admin"]:
        tenant_slug = subdomain_match.group(1)

    # Extract from path (fallback)
    if not tenant_slug:
        path_match = re.match(r"^/([^/]+)/.*", request.url.path)
        if path_match:
            tenant_slug = path_match.group(1)

    # Resolve tenant_id from slug (TODO: cache this)
    if tenant_slug:
        from backend.core.db_session import get_db_session_sync
        with get_db_session_sync() as session:
            result = session.execute(
                "SELECT id FROM tenants WHERE slug = :slug AND deleted_at IS NULL",
                {"slug": tenant_slug}
            )
            row = result.fetchone()
            if row:
                tenant_id = row[0]

    # Store in request state
    request.state.tenant_id = tenant_id
    request.state.tenant_slug = tenant_slug

    # Proceed with request
    response = await call_next(request)
    return response
```

## File: backend/core/db_session.py
```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import Request, Depends
from contextlib import contextmanager
import os
from typing import Generator

# Create engine
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=bool(os.getenv("SQL_ECHO", "false").lower() == "true")
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

def get_db_session(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency for request-scoped session with tenant context."""
    session = SessionLocal()
    try:
        # Set tenant context for RLS
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@contextmanager
def get_db_session_sync():
    """Context manager for sync operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

## File: backend/routes/tenants.py
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import uuid
from backend.core.db_session import get_db_session
from backend.core.admin_auth import require_admin

router = APIRouter(prefix="/api/admin/tenants", tags=["tenants"])

@router.post("/")
async def create_tenant(
    data: Dict[str, Any],
    session: Session = Depends(get_db_session),
    admin = Depends(require_admin)
) -> Dict[str, Any]:
    """Create new tenant."""
    tenant_id = str(uuid.uuid4())
    session.execute(
        text("""
            INSERT INTO tenants (id, slug, name, created_at, updated_at)
            VALUES (:id, :slug, :name, NOW(), NOW())
        """),
        {"id": tenant_id, "slug": data["slug"], "name": data["name"]}
    )

    # Add creator as owner
    session.execute(
        text("""
            INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
            VALUES (:tenant_id, :user_id, 'owner', NOW())
        """),
        {"tenant_id": tenant_id, "user_id": admin["user_id"]}
    )

    return {"id": tenant_id, "slug": data["slug"], "name": data["name"]}

@router.get("/mine")
async def get_my_tenants(
    session: Session = Depends(get_db_session),
    admin = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get user's tenants."""
    result = session.execute(
        text("""
            SELECT t.id, t.slug, t.name, tm.role
            FROM tenants t
            JOIN tenant_memberships tm ON t.id = tm.tenant_id
            WHERE tm.user_id = :user_id AND t.deleted_at IS NULL
            ORDER BY t.name
        """),
        {"user_id": admin["user_id"]}
    )

    return [
        {"id": str(row[0]), "slug": row[1], "name": row[2], "role": row[3]}
        for row in result.fetchall()
    ]

@router.post("/{tenant_id}/members")
async def add_member(
    tenant_id: str,
    data: Dict[str, Any],
    request: Request,
    session: Session = Depends(get_db_session),
    admin = Depends(require_admin)
) -> Dict[str, str]:
    """Add member to tenant."""
    # Verify requester is admin/owner
    result = session.execute(
        text("""
            SELECT role FROM tenant_memberships
            WHERE tenant_id = :tenant_id AND user_id = :user_id
        """),
        {"tenant_id": tenant_id, "user_id": admin["user_id"]}
    )
    membership = result.fetchone()
    if not membership or membership[0] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Add new member
    session.execute(
        text("""
            INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
            VALUES (:tenant_id, :user_id, :role, NOW())
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = :role
        """),
        {
            "tenant_id": tenant_id,
            "user_id": data["user_id"],
            "role": data.get("role", "member")
        }
    )

    return {"status": "added"}

@router.delete("/{tenant_id}/members/{user_id}")
async def remove_member(
    tenant_id: str,
    user_id: int,
    session: Session = Depends(get_db_session),
    admin = Depends(require_admin)
) -> Dict[str, str]:
    """Remove member from tenant."""
    # Verify requester is admin/owner
    result = session.execute(
        text("""
            SELECT role FROM tenant_memberships
            WHERE tenant_id = :tenant_id AND user_id = :user_id
        """),
        {"tenant_id": tenant_id, "user_id": admin["user_id"]}
    )
    membership = result.fetchone()
    if not membership or membership[0] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Cannot remove last owner
    result = session.execute(
        text("""
            SELECT COUNT(*) FROM tenant_memberships
            WHERE tenant_id = :tenant_id AND role = 'owner'
        """),
        {"tenant_id": tenant_id}
    )
    owner_count = result.scalar()

    result = session.execute(
        text("""
            SELECT role FROM tenant_memberships
            WHERE tenant_id = :tenant_id AND user_id = :user_id
        """),
        {"tenant_id": tenant_id, "user_id": user_id}
    )
    target_role = result.scalar()

    if owner_count == 1 and target_role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove last owner")

    # Remove member
    session.execute(
        text("""
            DELETE FROM tenant_memberships
            WHERE tenant_id = :tenant_id AND user_id = :user_id
        """),
        {"tenant_id": tenant_id, "user_id": user_id}
    )

    return {"status": "removed"}
```

## File: backend/routes/invitations.py
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
import uuid
import secrets
from datetime import datetime, timedelta
from backend.core.db_session import get_db_session
from backend.core.admin_auth import require_admin

router = APIRouter(prefix="/api/admin/invitations", tags=["invitations"])

@router.post("/")
async def create_invitation(
    data: Dict[str, Any],
    session: Session = Depends(get_db_session),
    admin = Depends(require_admin)
) -> Dict[str, Any]:
    """Create tenant invitation."""
    # Verify requester can invite
    tenant_id = data["tenant_id"]
    result = session.execute(
        text("""
            SELECT role FROM tenant_memberships
            WHERE tenant_id = :tenant_id AND user_id = :user_id
        """),
        {"tenant_id": tenant_id, "user_id": admin["user_id"]}
    )
    membership = result.fetchone()
    if not membership or membership[0] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Cannot invite to this tenant")

    # Create invitation
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    result = session.execute(
        text("""
            INSERT INTO invitations (tenant_id, email, inviter_user_id, token, status, expires_at, created_at)
            VALUES (:tenant_id, :email, :inviter, :token, 'pending', :expires_at, NOW())
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "email": data["email"],
            "inviter": admin["user_id"],
            "token": token,
            "expires_at": expires_at
        }
    )
    invitation_id = result.scalar()

    return {
        "id": invitation_id,
        "token": token,
        "tenant_id": tenant_id,
        "email": data["email"],
        "expires_at": expires_at.isoformat()
    }

@router.post("/accept")
async def accept_invitation(
    data: Dict[str, Any],
    session: Session = Depends(get_db_session),
    admin = Depends(require_admin)
) -> Dict[str, str]:
    """Accept tenant invitation."""
    # Find valid invitation
    result = session.execute(
        text("""
            SELECT i.id, i.tenant_id, i.email, t.name
            FROM invitations i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.token = :token
              AND i.status = 'pending'
              AND i.expires_at > NOW()
              AND t.deleted_at IS NULL
        """),
        {"token": data["token"]}
    )
    invitation = result.fetchone()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    invitation_id, tenant_id, email, tenant_name = invitation

    # Verify email matches
    if email != admin.get("email", ""):
        raise HTTPException(status_code=403, detail="Invitation email mismatch")

    # Add user to tenant
    session.execute(
        text("""
            INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
            VALUES (:tenant_id, :user_id, 'member', NOW())
            ON CONFLICT (tenant_id, user_id) DO NOTHING
        """),
        {"tenant_id": tenant_id, "user_id": admin["user_id"]}
    )

    # Mark invitation as accepted
    session.execute(
        text("""
            UPDATE invitations
            SET status = 'accepted'
            WHERE id = :id
        """),
        {"id": invitation_id}
    )

    return {
        "status": "accepted",
        "tenant_id": str(tenant_id),
        "tenant_name": tenant_name
    }
```

## File: backend/core/app_factory.py (additions)
```python
# Add after existing middleware
from backend.core.tenant_middleware import tenant_middleware
app.middleware("http")(tenant_middleware)

# Add after existing routers
from backend.routes import tenants, invitations
app.include_router(tenants.router)
app.include_router(invitations.router)
```

## File: src/composables/useTenant.ts
```typescript
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export interface Tenant {
  id: string
  slug: string
  name: string
  role: string
}

export function useTenant() {
  const route = useRoute()
  const router = useRouter()

  const currentTenant = ref<Tenant | null>(null)
  const userTenants = ref<Tenant[]>([])

  // Parse tenant from URL
  const tenantSlug = computed(() => {
    // Check subdomain
    const subdomain = window.location.hostname.split('.')[0]
    if (subdomain && !['www', 'localhost', 'api', 'admin'].includes(subdomain)) {
      return subdomain
    }

    // Check path prefix
    const pathMatch = route.path.match(/^\/([^\/]+)/)
    if (pathMatch) {
      return pathMatch[1]
    }

    return null
  })

  // Fetch user's tenants
  async function fetchUserTenants() {
    const response = await fetch('/api/admin/tenants/mine', {
      credentials: 'include'
    })
    if (response.ok) {
      userTenants.value = await response.json()

      // Set current tenant if slug matches
      if (tenantSlug.value) {
        currentTenant.value = userTenants.value.find(
          t => t.slug === tenantSlug.value
        ) || null
      }
    }
  }

  // Switch tenant
  async function switchTenant(tenant: Tenant) {
    if (window.location.hostname.includes('localhost')) {
      // Use path prefix in dev
      await router.push(`/${tenant.slug}`)
    } else {
      // Use subdomain in prod
      window.location.href = `https://${tenant.slug}.${window.location.hostname.split('.').slice(1).join('.')}`
    }
  }

  // Watch for route changes
  watch(() => route.path, () => {
    if (tenantSlug.value && userTenants.value.length > 0) {
      currentTenant.value = userTenants.value.find(
        t => t.slug === tenantSlug.value
      ) || null
    }
  })

  return {
    currentTenant,
    userTenants,
    tenantSlug,
    fetchUserTenants,
    switchTenant
  }
}
```

## File: src/components/OrgSwitcher.vue
```vue
<template>
  <v-menu>
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" variant="outlined">
        <v-icon start>$account-group</v-icon>
        {{ currentTenant?.name || 'Select Organization' }}
        <v-icon end>$chevron-down</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
        v-for="tenant in userTenants"
        :key="tenant.id"
        @click="switchTenant(tenant)"
        :active="tenant.id === currentTenant?.id"
      >
        <v-list-item-title>{{ tenant.name }}</v-list-item-title>
        <v-list-item-subtitle>{{ tenant.role }}</v-list-item-subtitle>
      </v-list-item>
      <v-divider />
      <v-list-item @click="createTenant">
        <v-list-item-title>
          <v-icon start>$plus</v-icon>
          Create Organization
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useTenant } from '@/composables/useTenant'

const { currentTenant, userTenants, fetchUserTenants, switchTenant } = useTenant()

onMounted(() => {
  fetchUserTenants()
})

function createTenant() {
  // TODO: Open create tenant dialog
  console.log('Create tenant')
}
</script>
```