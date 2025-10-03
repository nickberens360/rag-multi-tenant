# Admin Dashboard: Multi-Tenant Data Scoping Pattern

## Overview

This document describes the established pattern for implementing tenant-scoped data isolation in the admin dashboard. All operational views (Dashboard, Queries, Performance, Knowledge) follow this consistent pattern to ensure data is properly filtered by the current tenant context.

## Architecture

### Tenant Context Flow

```
User switches tenant in OrgSwitcher
    ↓
Tenant Store updates currentTenant
    ↓
Route changes to /{tenant}/...
    ↓
Component watchers detect tenant change
    ↓
Components refresh data via stores
    ↓
API calls include tenant in URL path
    ↓
Backend middleware extracts tenant from URL
    ↓
Backend queries filter by tenant_id
    ↓
Frontend receives tenant-scoped data
```

## Frontend Pattern

### 1. Component Setup

Every tenant-aware view component must:

1. Import required dependencies
2. Get tenant store reference
3. Extract reactive tenant ref
4. Create data refresh function
5. Add tenant watcher

#### Example Template

```vue
<script setup>
import { computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { useDataStore } from '@/stores/data' // Your specific store

// Get store instances
const tenantStore = useTenantStore()
const dataStore = useDataStore()

// Extract reactive tenant reference
const { currentTenant } = storeToRefs(tenantStore)

// Create refresh function
const refreshData = async () => {
  console.log('🔄 [ViewName] Refreshing data, currentTenant:', currentTenant.value)
  await dataStore.fetchData()
}

// Initialize on mount
onMounted(async () => {
  console.log('✅ [ViewName] Component mounted, currentTenant:', currentTenant.value)
  await refreshData()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [ViewName] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [ViewName] Tenant slug changed, refreshing data')
    refreshData()
  }
})
</script>
```

### 2. Key Principles

#### Watch the Slug, Not the Object

❌ **Wrong:**
```javascript
// Don't watch the entire object
watch(currentTenant, (newTenant, oldTenant) => {
  // May not trigger reliably
})
```

✅ **Correct:**
```javascript
// Watch the slug property specifically
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  if (newSlug && newSlug !== oldSlug) {
    refreshData()
  }
})
```

**Why:** Watching a primitive value (string) is more reliable than watching an object reference. The slug changes guarantee a watcher trigger.

#### Use Getter Functions, Not Direct Refs

❌ **Wrong:**
```javascript
const { currentTenant } = storeToRefs(tenantStore)
watch(currentTenant, ...) // Watching the ref directly
```

✅ **Correct:**
```javascript
const { currentTenant } = storeToRefs(tenantStore)
watch(() => currentTenant.value?.slug, ...) // Watching a getter
```

**Why:** Getter functions create computed dependencies that Vue's reactivity system tracks precisely.

#### Check Both Conditions

Always check both conditions in the watcher:

```javascript
if (newSlug && newSlug !== oldSlug) {
  refreshData()
}
```

- `newSlug` - Ensures we have a valid tenant
- `newSlug !== oldSlug` - Prevents unnecessary refreshes on initial load

### 3. Console Logging Strategy

Use consistent emoji prefixes for easy debugging:

- `🔄` - Data refresh operations
- `✅` - Component lifecycle events (mount, unmount)
- `👀` - Watcher triggers
- `⚠️` - Warnings or edge cases
- `❌` - Errors

Example:
```javascript
console.log('✅ [DashboardView] Component mounted, currentTenant:', currentTenant.value)
console.log('👀 [DashboardView] Tenant slug watcher fired:', { oldSlug, newSlug })
console.log('🔄 [DashboardView] Tenant slug changed, refreshing dashboard')
```

## Backend Pattern

### 1. Endpoint Setup

Every tenant-aware endpoint must:

1. Accept `Request` parameter
2. Extract tenant context from request state
3. Build dynamic SQL with tenant filter
4. Apply filter to all queries

#### Example Template

```python
from fastapi import Request

@router.get("/endpoint")
async def get_data(
    request: Request,
    pg_session: Session = Depends(get_db_session),
):
    """Get tenant-scoped data."""
    try:
        # Extract tenant context from middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)

        logger.info(f"Fetching data for tenant: {tenant_slug} (ID: {tenant_id})")

        # Build tenant filter
        tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""

        # Build params dict
        params = {"tenant_id": tenant_id} if tenant_id else {}

        # Query with filter
        result = pg_session.execute(
            text(f"""
                SELECT * FROM table
                WHERE 1=1 {tenant_filter}
                ORDER BY created_at DESC
            """),
            params
        ).fetchall()

        return result

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 2. SQL Filter Pattern

#### Dynamic Filter Construction

```python
# Build conditional filter
tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""

# Build base params
params = {"tenant_id": tenant_id} if tenant_id else {}

# Add additional params
params["start_date"] = start_date
params["end_date"] = end_date
```

#### Apply to All Queries

Ensure EVERY query in the endpoint includes the tenant filter:

```python
# Query 1: Count
total = pg_session.execute(
    text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start {tenant_filter}"),
    params
).scalar()

# Query 2: Average
avg_time = pg_session.execute(
    text(f"SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= :start {tenant_filter}"),
    params
).scalar()

# Query 3: Errors
errors = pg_session.execute(
    text(f"SELECT COUNT(*) FROM query_logs WHERE error_occurred = true {tenant_filter}"),
    params
).scalar()
```

### 3. Middleware Integration

The tenant middleware automatically extracts tenant context from the URL path:

```
URL: /test-org/api/admin/queries
     ↓
Middleware extracts: tenant_slug = "test-org"
     ↓
Middleware queries DB: tenant_id = "9939c528-c4bd-4041-bf7c-10ca09c20263"
     ↓
Sets: request.state.tenant_id, request.state.tenant_slug
```

**No additional configuration needed** - just access `request.state.tenant_id` in your endpoint.

## Real-World Examples

### Example 1: QueriesView (Simple)

**Frontend:**
```vue
<script setup>
import { onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useQueriesStore } from '@/stores/queries'
import { useTenantStore } from '@/stores/tenant'

const queriesStore = useQueriesStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

const refreshQueries = async () => {
  console.log('🔄 [QueriesView] Refreshing queries, currentTenant:', currentTenant.value)
  await queriesStore.fetchQueries()
}

onMounted(async () => {
  console.log('✅ [QueriesView] Component mounted, currentTenant:', currentTenant.value)
  await refreshQueries()
})

watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [QueriesView] Tenant slug watcher fired:', { oldSlug, newSlug })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [QueriesView] Tenant slug changed, refreshing queries')
    refreshQueries()
  }
})
</script>
```

**Backend:**
```python
@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pg_session: Session = Depends(get_db_session),
):
    # Get tenant context
    tenant_id = getattr(request.state, "tenant_id", None)

    # Build filter
    where_conditions = []
    params = {}

    if tenant_id:
        where_conditions.append("tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id

    # Query
    rows = pg_session.execute(
        text(f"""
            SELECT * FROM query_logs
            WHERE {' AND '.join(where_conditions) if where_conditions else '1=1'}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset}
    ).fetchall()

    return {"queries": rows, "total": len(rows)}
```

### Example 2: DashboardView (Complex - Multiple Stores)

**Frontend:**
```vue
<script setup>
import { onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAdminStore } from '@/stores/admin'
import { useQueriesStore } from '@/stores/queries'
import { usePerformanceStore } from '@/stores/performance'
import { useTenantStore } from '@/stores/tenant'

const adminStore = useAdminStore()
const queriesStore = useQueriesStore()
const performanceStore = usePerformanceStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Refresh all dashboard data
const refreshDashboard = async () => {
  console.log('🔄 [DashboardView] Refreshing dashboard data, currentTenant:', currentTenant.value)
  await Promise.all([
    adminStore.fetchStats(),
    queriesStore.fetchQueries({ limit: 10 }),
    performanceStore.refreshData()
  ])
}

onMounted(async () => {
  console.log('✅ [DashboardView] Component mounted, currentTenant:', currentTenant.value)
  await refreshDashboard()
})

watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [DashboardView] Tenant slug watcher fired:', { oldSlug, newSlug })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [DashboardView] Tenant slug changed, refreshing dashboard')
    refreshDashboard()
  }
})
</script>
```

### Example 3: Stats Endpoint (Multiple Queries)

**Backend:**
```python
@router.get("/stats/overview", response_model=OverviewStats)
async def get_stats_overview(
    request: Request,
    days: float = Query(7, ge=0.1, le=90),
    pg_session: Session = Depends(get_db_session),
):
    # Get tenant context
    tenant_id = getattr(request.state, "tenant_id", None)
    tenant_slug = getattr(request.state, "tenant_slug", None)

    logger.info(f"Filtering admin stats for tenant: {tenant_slug} (ID: {tenant_id})")

    # Build filter and params
    tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""
    params_base = {"start": start_date, "end": end_date}
    if tenant_id:
        params_base["tenant_id"] = tenant_id

    # Query 1: Total queries
    total_queries = pg_session.execute(
        text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end {tenant_filter}"),
        params_base,
    ).scalar() or 0

    # Query 2: Avg response time
    avg_response_time = pg_session.execute(
        text(f"SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end AND response_time_ms IS NOT NULL {tenant_filter}"),
        params_base,
    ).scalar() or 0.0

    # Query 3: Error rate
    total = pg_session.execute(
        text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end {tenant_filter}"),
        params_base,
    ).scalar() or 0

    errors = pg_session.execute(
        text(f"SELECT COUNT(*) FROM query_logs WHERE timestamp >= :start AND timestamp <= :end AND error_occurred = true {tenant_filter}"),
        params_base,
    ).scalar() or 0

    error_rate = (errors / total) if total > 0 else 0.0

    return OverviewStats(
        total_queries=total_queries,
        avg_response_time_ms=round(avg_response_time, 1),
        error_rate=round(error_rate, 3),
    )
```

## Common Pitfalls

### ❌ Pitfall 1: Forgetting to Filter ALL Queries

**Problem:**
```python
# Query 1: Filtered ✓
total = pg_session.execute(
    text(f"SELECT COUNT(*) FROM query_logs WHERE 1=1 {tenant_filter}"),
    params
).scalar()

# Query 2: NOT filtered ✗
avg_time = pg_session.execute(
    text("SELECT AVG(response_time_ms) FROM query_logs"),  # Missing filter!
    {}
).scalar()
```

**Solution:** Add tenant filter to EVERY query in the endpoint.

### ❌ Pitfall 2: Using Wrong Path Format in Filter

**Problem:**
```python
# Wrong - paths are relative
marker = f"/tenants/{tenant_slug}/"
```

**Solution:**
```python
# Correct - no leading slash
marker = f"tenants/{tenant_slug}/"
```

### ❌ Pitfall 3: Not Handling None tenant_id

**Problem:**
```python
# Fails if tenant_id is None
params = {"tenant_id": tenant_id}
```

**Solution:**
```python
# Conditional parameter inclusion
params = {"tenant_id": tenant_id} if tenant_id else {}
```

### ❌ Pitfall 4: Watching Object Instead of Property

**Problem:**
```javascript
watch(currentTenant, (newVal, oldVal) => {
  // May not trigger reliably
})
```

**Solution:**
```javascript
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  if (newSlug && newSlug !== oldSlug) {
    refreshData()
  }
})
```

## Testing Tenant Isolation

### Database Verification

```sql
-- Check query counts per tenant
SELECT
    t.name as tenant_name,
    COUNT(q.id) as query_count
FROM tenants t
LEFT JOIN query_logs q ON t.id = q.tenant_id::uuid
GROUP BY t.name
ORDER BY query_count DESC;
```

### API Testing

```bash
# Test test-org endpoint
curl -s "http://localhost:8000/test-org/api/admin/queries?limit=5" \
  -H "Cookie: session_id=test" | jq '.queries | length'

# Test default endpoint
curl -s "http://localhost:8000/default/api/admin/queries?limit=5" \
  -H "Cookie: session_id=test" | jq '.queries | length'

# Results should differ if data is properly scoped
```

### Frontend Verification

1. Open browser console (F12)
2. Navigate to tenant-scoped view
3. Switch tenants using OrgSwitcher
4. Look for console messages:
   - `👀 [ViewName] Tenant slug watcher fired`
   - `🔄 [ViewName] Tenant slug changed, refreshing data`
5. Verify data updates in the UI

## Implementation Checklist

When adding tenant scoping to a new view:

### Frontend Checklist

- [ ] Import `watch` from Vue
- [ ] Import `storeToRefs` from Pinia
- [ ] Import `useTenantStore` from stores
- [ ] Extract `currentTenant` ref with `storeToRefs`
- [ ] Create `refreshData()` function
- [ ] Call `refreshData()` in `onMounted`
- [ ] Add tenant slug watcher with proper condition check
- [ ] Add console logging with emoji prefixes
- [ ] Test tenant switching in browser

### Backend Checklist

- [ ] Add `Request` parameter to endpoint
- [ ] Extract `tenant_id` and `tenant_slug` from `request.state`
- [ ] Add debug logging with tenant info
- [ ] Build `tenant_filter` string conditionally
- [ ] Build `params` dict conditionally
- [ ] Apply filter to ALL SQL queries in endpoint
- [ ] Test with curl for both tenants
- [ ] Verify counts match database

## Implemented Views

| View | Frontend Scoped | Backend Scoped | Verified |
|------|----------------|----------------|----------|
| DashboardView | ✅ | ✅ | ✅ |
| QueriesView | ✅ | ✅ | ✅ |
| PerformanceView | ✅ | ✅ | ✅ |
| Knowledge/SourcesView | ✅ | ✅ | ✅ |
| Knowledge/DocumentsView | ✅ | ✅ | ✅ |
| Knowledge/ConsistencyView | ✅ | ✅ | ✅ |
| UsersView | ✅ | ✅ | ✅ |
| SessionsView | ❌ | ❌ | ❌ |

## Settings Views

All settings views use the tenant-aware `SettingsManager` backend service which automatically scopes settings by tenant using `get_current_tenant_id()`.

| Settings View | Frontend Watcher | Backend Scoped | Verified |
|---------------|-----------------|----------------|----------|
| CoreSettings | ✅ | ✅ | ⏳ |
| FeatureSettings | ✅ | ✅ | ⏳ |
| FollowupSettings | ✅ | ✅ | ⏳ |
| KnowledgeSettings | ✅ | ✅ | ⏳ |
| ResponseSettings | ✅ | ✅ | ⏳ |
| SecuritySettings | ✅ | ✅ | ⏳ |
| TaxonomySettings | ✅ | ✅ | ⏳ |
| UXSettings | ✅ | ✅ | ⏳ |
| WelcomeSettings | ✅ | ✅ | ⏳ |
| ApiKeysSettings | ✅ | ✅ | ⏳ |
| RagConfigSettings | ✅ | ✅ | ⏳ |
| RoutingSettings | ✅ | ✅ | ⏳ |
| SearchRetrievalSettings | ✅ | ✅ | ⏳ |
| SystemSettings | ✅ | ✅ | ⏳ |

### Example 4: UsersView (Tenant Memberships JOIN)

**Frontend:**
```vue
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useUsersStore } from '@/stores/users'
import { useTenantStore } from '@/stores/tenant'

const usersStore = useUsersStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

const refreshUsers = async () => {
  console.log('🔄 [UsersView] Refreshing users, currentTenant:', currentTenant.value)
  await usersStore.fetchUsers()
}

onMounted(async () => {
  console.log('✅ [UsersView] Component mounted, currentTenant:', currentTenant.value)
  await refreshUsers()
})

watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [UsersView] Tenant slug watcher fired:', { oldSlug, newSlug })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [UsersView] Tenant slug changed, refreshing users')
    refreshUsers()
  }
})
</script>
```

**Backend:**
```python
@router.get("/users", response_model=List[AdminUser])
async def get_admin_users(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_role),
    db: Session = Depends(get_db_session),
):
    # Get tenant context
    tenant_id = getattr(request.state, "tenant_id", None)
    tenant_slug = getattr(request.state, "tenant_slug", None)

    logger.info(f"Fetching users for tenant: {tenant_slug} (ID: {tenant_id})")

    # Query users that are members of the current tenant
    # Using JOIN with tenant_memberships for tenant isolation
    rows = db.execute(
        text("""
            SELECT DISTINCT
                u.id, u.username, u.email, u.role, u.is_active,
                u.created_at, u.last_login_at, u.updated_at
            FROM admin_users u
            JOIN tenant_memberships tm ON u.id = tm.user_id
            WHERE tm.tenant_id = :tenant_id
            ORDER BY u.username
        """),
        {"tenant_id": tenant_id},
    ).fetchall()

    users = [AdminUser(...) for r in rows]

    logger.info(f"Found {len(users)} users for tenant {tenant_slug}")
    return users
```

**Key difference:** UsersView uses a JOIN pattern with `tenant_memberships` table instead of a direct tenant_id column, allowing users to belong to multiple tenants with different roles per tenant.

## Next Steps

For views not yet implemented:

1. **SessionsView** - Filter sessions by tenant (if applicable)

## References

- Tenant Store: `admin/frontend/src/stores/tenant.js`
- Tenant Middleware: `backend/core/tenant_middleware.py`
- Example Implementations:
  - `admin/frontend/src/views/DashboardView.vue`
  - `admin/frontend/src/views/QueriesView.vue`
  - `admin/frontend/src/views/PerformanceView.vue`
  - `admin/frontend/src/views/UsersView.vue`
  - `backend/routes/queries.py`
  - `backend/routes/stats.py`
  - `backend/routes/performance.py`
  - `backend/routes/admin.py` (users endpoint)
