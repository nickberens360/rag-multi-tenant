# Tenant Store Refactoring - Corrected Implementation Plan (Simplified POC)

## TL;DR

**Problem**: Page refresh with tenant in URL causes stale/missing data due to component watcher race conditions.

**Solution**: Centralize tenant data in Pinia store, remove component watchers, use computed getters.

**Approach**:
- **Phase 1 (POC)**: Store data WITHOUT caching - prove architecture works
- **Phase 2**: Add TTL-based caching (5 min) for performance
- **Phase 3**: Expand to more data types and optimizations

**Key Changes from Original Plan**:
- ✅ No caching in POC (simpler, faster to implement)
- ✅ Fixed API signatures (no tenant params, use context)
- ✅ Removed duplicate watchers (single source of truth)
- ✅ Only store small, frequently-used data (knowledgeSources, knowledgeStats)

## Overview
Refactor the Pinia tenant store from "thin" (ID/name/role only) to a "hybrid thick" store that holds commonly-used tenant data. This solves the page refresh issue where data doesn't load correctly when a tenant query parameter is in the URL.

**NOTE**: This is a **proof of concept without caching**. We'll add TTL-based caching in Phase 2 after validating the architecture works.

## Problem Statement
**Current Issue**: When the page refreshes with `?tenant=test-org` in URL, components' watchers don't fire reliably, causing stale or missing data.

**Root Cause**:
- Tenant store watcher fires synchronously when URL changes
- Component watchers may execute before store initialization completes
- Each component independently fetches data, creating race conditions

## Solution Architecture

### Core Principle: Centralized Data Storage (No Caching Yet)
Store **only** data that is:
1. ✅ Small in size (< 100KB)
2. ✅ Frequently accessed across multiple views
3. ✅ Currently causing refresh issues

Do **NOT** store:
- ❌ Large datasets (1000s of query logs, documents)
- ❌ View-specific data used only in one place
- ❌ Data that changes very frequently

## Phase 1: Core Implementation

### Step 1: Update Tenant Store Structure

File: `/admin/frontend/src/stores/tenant.js`

#### 1.1 Add Tenant Data State (No Caching)

```javascript
// Tenant Data State - ONLY commonly-used, small datasets
const tenantData = ref({
  knowledgeSources: [],    // Used in: SourcesView, IndexedDocsView, Dashboard
  knowledgeStats: null,    // Used in: IndexedDocsView, Dashboard
  // Future additions (if needed):
  // performanceMetrics: null,
  // sessions: [],
})

// Loading states per data type
const dataLoading = ref({
  knowledgeSources: false,
  knowledgeStats: false,
})

// Error states per data type
const dataErrors = ref({
  knowledgeSources: null,
  knowledgeStats: null,
})
```

#### 1.2 Add Computed Getters

```javascript
// Data Getters - automatically reactive when currentTenant changes
const currentTenantKnowledgeSources = computed(() =>
  hasTenant.value ? tenantData.value.knowledgeSources : []
)

const currentTenantKnowledgeStats = computed(() =>
  hasTenant.value ? tenantData.value.knowledgeStats : null
)

// Loading state getters
const isLoadingKnowledgeSources = computed(() =>
  dataLoading.value.knowledgeSources
)

const isLoadingKnowledgeStats = computed(() =>
  dataLoading.value.knowledgeStats
)

// Check if critical data is ready
const isCriticalDataReady = computed(() => {
  if (!hasTenant.value) return false
  return !dataLoading.value.knowledgeSources &&
         !dataLoading.value.knowledgeStats
})
```

#### 1.3 Add Data Loading Functions

**CRITICAL**: API methods do NOT take tenant parameters. Tenant context is set via `adminAPI.setCurrentTenant(slug)`.

```javascript
const loadKnowledgeSources = async (force = false) => {
  // Guard: no tenant selected
  if (!currentTenant.value?.slug) {
    console.debug('No tenant selected, skipping knowledge sources load')
    return
  }

  // Guard: already loading (unless forced)
  if (dataLoading.value.knowledgeSources && !force) {
    console.debug('Knowledge sources already loading, skipping')
    return
  }

  dataLoading.value.knowledgeSources = true
  dataErrors.value.knowledgeSources = null

  try {
    console.debug(`Loading knowledge sources for tenant: ${currentTenant.value.slug}`)

    // NO tenant parameter - context already set via setCurrentTenant()
    const data = await adminAPI.getKnowledgeSources()

    tenantData.value.knowledgeSources = data || []

    console.debug(`✅ Loaded ${tenantData.value.knowledgeSources.length} knowledge sources`)
  } catch (err) {
    console.error('Failed to load knowledge sources:', err)
    dataErrors.value.knowledgeSources = adminAPI.formatError(err)
    tenantData.value.knowledgeSources = []
  } finally {
    dataLoading.value.knowledgeSources = false
  }
}

const loadKnowledgeStats = async (force = false) => {
  if (!currentTenant.value?.slug) return
  if (dataLoading.value.knowledgeStats && !force) return

  dataLoading.value.knowledgeStats = true
  dataErrors.value.knowledgeStats = null

  try {
    console.debug(`Loading knowledge stats for tenant: ${currentTenant.value.slug}`)

    // NO tenant parameter - context already set
    const data = await adminAPI.getKnowledgeStats()

    tenantData.value.knowledgeStats = data || null

    console.debug('✅ Loaded knowledge stats:', data)
  } catch (err) {
    console.error('Failed to load knowledge stats:', err)
    dataErrors.value.knowledgeStats = adminAPI.formatError(err)
    tenantData.value.knowledgeStats = null
  } finally {
    dataLoading.value.knowledgeStats = false
  }
}
```

#### 1.4 Add Composite Loading Functions

```javascript
// Load all tenant data (no caching, always fresh)
const loadTenantData = async (force = false) => {
  if (!currentTenant.value?.slug) {
    console.debug('No tenant to load data for')
    return
  }

  console.log(`Loading data for tenant: ${currentTenant.value.name}`)

  // Load in parallel for speed
  await Promise.all([
    loadKnowledgeSources(force),
    loadKnowledgeStats(force),
  ])

  console.log('✅ Tenant data loaded')
}

// Clear all tenant data
const clearTenantData = () => {
  tenantData.value = {
    knowledgeSources: [],
    knowledgeStats: null,
  }

  // Reset error states
  Object.keys(dataErrors.value).forEach(key => {
    dataErrors.value[key] = null
  })

  console.debug('Cleared all tenant data')
}
```

#### 1.5 Update switchTenant Function

**CRITICAL CHANGE**: Remove the `tenantId` watcher entirely. Only use `switchTenant()` to change tenants.

```javascript
const switchTenant = async (tenant) => {
  // Guard: no change
  if (!tenant || currentTenant.value?.id === tenant.id) {
    console.debug('Tenant switch skipped - same tenant or null')
    return
  }

  const previousTenant = currentTenant.value
  console.log(`🔄 Switching from ${previousTenant?.name || 'none'} to ${tenant.name}`)

  try {
    // Step 1: Clear previous tenant's data immediately
    clearTenantData()

    // Step 2: Update API service tenant context
    adminAPI.setCurrentTenant(tenant.slug)

    // Step 3: Update current tenant state (triggers reactivity)
    currentTenant.value = tenant

    // Step 4: Load data for new tenant
    // Don't await - let it load in background, components will show loading states
    loadTenantData().catch(err => {
      console.error('Error loading tenant data:', err)
    })

    // Step 5: Handle routing (navigate to tenant-prefixed URL)
    const slugs = (userTenants.value || []).map(t => t.slug)
    const cur = route.fullPath || '/'
    const parts = cur.split('/')
    let rest = cur

    // Strip existing tenant prefix if present
    if (parts.length > 1 && slugs.includes(parts[1])) {
      rest = cur.slice(parts[1].length + 1)
      if (!rest.startsWith('/')) rest = '/' + rest
    }

    const newPath = `/${tenant.slug}${rest === '' ? '/' : rest}`
    if (newPath !== cur) {
      await router.replace(newPath)
    }

    console.log(`✅ Switched to tenant: ${tenant.name} (${tenant.slug})`)
    return { success: true, previousTenant, newTenant: tenant }

  } catch (err) {
    console.error('Failed to switch tenant:', err)
    error.value = adminAPI.formatError(err)

    // Revert on error
    if (previousTenant) {
      adminAPI.setCurrentTenant(previousTenant.slug)
      currentTenant.value = previousTenant
      // Reload previous tenant data
      loadTenantData().catch(console.error)
    }

    return { success: false, error: err }
  }
}
```

#### 1.6 Remove Duplicate Watcher

**REMOVE THIS WATCHER** (lines 175-183 in current tenant.js):

```javascript
// ❌ DELETE THIS - causes double loading
watch(tenantSlug, (newSlug, oldSlug) => {
  if (newSlug && newSlug !== oldSlug && Array.isArray(userTenants.value) && userTenants.value.length) {
    const matched = userTenants.value.find(t => t.slug === newSlug)
    if (matched && currentTenant.value?.id !== matched.id) {
      currentTenant.value = matched
      adminAPI.setCurrentTenant(matched.slug)
    }
  }
})
```

**REPLACE WITH** this single watcher that delegates to `switchTenant()`:

```javascript
// Keep currentTenant in sync with URL - but delegate to switchTenant
watch(tenantSlug, async (newSlug, oldSlug) => {
  if (newSlug && newSlug !== oldSlug && initialized.value) {
    console.log('Tenant slug in URL changed:', oldSlug, '->', newSlug)
    const matched = userTenants.value.find(t => t.slug === newSlug)
    if (matched && currentTenant.value?.id !== matched.id) {
      await switchTenant(matched)
    }
  }
})
```

#### 1.7 Update Initialize Function

```javascript
const initialize = async () => {
  if (initialized.value) {
    console.debug('Tenant store already initialized')
    return
  }

  console.log('🚀 Initializing tenant store...')

  // Step 1: Fetch user's tenants
  await fetchUserTenants()

  // Step 2: If we have a current tenant after URL parsing, load its data
  if (currentTenant.value) {
    console.log('Current tenant detected on init:', currentTenant.value.name)
    await loadTenantData()
  } else {
    console.log('No tenant in URL on init')
  }

  console.log('✅ Tenant store initialized')
}
```

#### 1.8 Update Store Return Value

```javascript
return {
  // Core State
  currentTenant,
  userTenants,
  isLoading,
  error,
  initialized,

  // Tenant Data State
  tenantData,
  dataLoading,
  dataErrors,

  // Core Getters
  tenantSlug,
  hasTenant,
  tenantId,
  tenantName,

  // Data Getters
  currentTenantKnowledgeSources,
  currentTenantKnowledgeStats,
  isLoadingKnowledgeSources,
  isLoadingKnowledgeStats,
  isCriticalDataReady,

  // Core Actions
  fetchUserTenants,
  switchTenant,
  clearTenant,
  resetError,
  initialize,

  // Data Loading Actions
  loadTenantData,
  loadKnowledgeSources,
  loadKnowledgeStats,
  clearTenantData,
}
```

### Step 2: Update Components to Use Store Data

#### 2.1 Update IndexedDocumentsView

File: `/admin/frontend/src/views/IndexedDocumentsView.vue`

**BEFORE** (lines 389-514):
```javascript
const tenantStore = useTenantStore()
const { currentTenant, initialized } = storeToRefs(tenantStore)

const loadingDocuments = ref(false)
const knowledgeStats = ref({ ... })
const documents = ref([])

const loadKnowledgeStats = async () => { ... }
const loadDocuments = async () => { ... }

// Complex watcher watching both tenant and initialized
watch([() => currentTenant.value?.id, () => initialized.value], ...)
```

**AFTER**:
```javascript
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

export default {
  setup() {
    const tenantStore = useTenantStore()

    // Get cached data from store
    const {
      currentTenantKnowledgeStats,
      isLoadingKnowledgeStats,
      isCriticalDataReady
    } = storeToRefs(tenantStore)

    // Component-specific state (not cached in store because it's large)
    const loadingDocuments = ref(false)
    const documents = ref([])
    const embeddingModel = ref('text-embedding-3-small')

    // Use store's cached stats directly
    const knowledgeStats = currentTenantKnowledgeStats

    // Load heavy data (documents) locally - not cached
    const loadDocuments = async () => {
      if (!tenantStore.currentTenant?.slug) return

      loadingDocuments.value = true
      try {
        const data = await adminAPI.getKnowledgeDocuments(100, 0)
        documents.value = data.documents || []
        if (data.embedding_model) {
          embeddingModel.value = data.embedding_model
        }
      } catch (error) {
        console.error('Failed to load documents:', error)
      } finally {
        loadingDocuments.value = false
      }
    }

    // Simple watcher - only watch when critical data is ready
    watch(
      () => isCriticalDataReady.value,
      (isReady) => {
        if (isReady) {
          console.log('✅ Critical data ready, loading documents')
          loadDocuments()
        }
      },
      { immediate: true }
    )

    return {
      loadingDocuments,
      knowledgeStats, // From store
      embeddingModel,
      documents,
      loadDocuments,
      // ... rest of methods
    }
  }
}
```

#### 2.2 Update SourcesView

File: `/admin/frontend/src/views/knowledge/SourcesView.vue`

**BEFORE** (lines 753-759):
```javascript
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

const sources = ref([])
const loading = ref(false)

const loadSources = async () => { ... }

watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await loadSources()
  }
}, { deep: true })
```

**AFTER**:
```javascript
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'

setup() {
  const tenantStore = useTenantStore()

  // Use store's cached knowledge sources
  const {
    currentTenantKnowledgeSources,
    isLoadingKnowledgeSources
  } = storeToRefs(tenantStore)

  // Use cached sources directly - NO local fetching, NO watchers
  const sources = currentTenantKnowledgeSources
  const loading = isLoadingKnowledgeSources

  // If you need to refresh (e.g., after upload/delete):
  const refreshSources = async () => {
    await tenantStore.loadKnowledgeSources(true) // force=true
  }

  return {
    sources,      // From store
    loading,      // From store
    refreshSources,
    // ... rest of methods
  }
}
```

### Step 3: Update Other Stores (Queries, Performance)

File: `/admin/frontend/src/stores/queries.js`

**CHANGE** (lines 258-266):
```javascript
// ❌ OLD: Only clears data on change
watch(
  () => tenantStore.currentTenant?.id,
  (newTenantId, oldTenantId) => {
    if (oldTenantId && newTenantId && oldTenantId !== newTenantId) {
      clearTenantData()
    }
  }
)
```

**TO**:
```javascript
// ✅ NEW: Clears data AND auto-reloads if view is active
watch(
  () => tenantStore.currentTenant?.id,
  (newTenantId, oldTenantId) => {
    if (oldTenantId && newTenantId && oldTenantId !== newTenantId) {
      console.debug(`Queries store: tenant changed from ${oldTenantId} to ${newTenantId}`)
      clearTenantData()

      // If this view is currently active, reload data
      // Note: This is optional - you could also let the view handle it
      // fetchQueries().catch(console.error)
    }
  }
)
```

## Phase 2: Add Caching (After POC Validation)

Once the POC proves the architecture works, add caching:

### 2.1 Add Timestamp Tracking

```javascript
// Add to tenant store
const dataTimestamps = ref({
  knowledgeSources: null,
  knowledgeStats: null,
})

const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

const isCacheValid = (dataType) => {
  const timestamp = dataTimestamps.value[dataType]
  if (!timestamp) return false
  return (Date.now() - timestamp) < CACHE_TTL
}

const updateTimestamp = (dataType) => {
  dataTimestamps.value[dataType] = Date.now()
}
```

### 2.2 Update Loading Functions to Check Cache

```javascript
const loadKnowledgeSources = async (force = false) => {
  if (!currentTenant.value?.slug) return
  if (dataLoading.value.knowledgeSources && !force) return

  // NEW: Check cache validity
  if (!force && isCacheValid('knowledgeSources')) {
    console.debug('Using cached knowledge sources')
    return
  }

  // ... existing load logic ...

  updateTimestamp('knowledgeSources') // NEW: Update after load
}
```

### 2.3 Add More Data Types (Optional)

Only add if they meet the criteria (small, frequently accessed):

```javascript
const tenantData = ref({
  knowledgeSources: [],
  knowledgeStats: null,

  // Phase 2 additions:
  performanceMetrics: null,  // If used in multiple views
  recentSessions: [],        // If displayed in dashboard
})
```

### 2.4 Add Optimistic Updates (Optional)

```javascript
// In component after creating/deleting a source
const deleteSource = async (sourcePath) => {
  // Optimistic update
  const originalSources = [...tenantStore.currentTenantKnowledgeSources]
  tenantStore.tenantData.knowledgeSources = originalSources.filter(
    s => s.path !== sourcePath
  )

  try {
    await adminAPI.deleteKnowledgeSource(sourcePath)
  } catch (err) {
    // Revert on error
    tenantStore.tenantData.knowledgeSources = originalSources
    throw err
  }
}
```

## Phase 3: Route Guards (Optional)

Only needed if you want to block navigation until critical data loads:

```javascript
// In /admin/frontend/src/router/index.js

router.beforeEach(async (to, from, next) => {
  const tenantStore = useTenantStore()

  // Initialize tenant store if needed
  if (!tenantStore.initialized) {
    await tenantStore.initialize()
  }

  // Optional: Wait for critical data if navigating to data-heavy view
  if (to.meta.requiresTenantData && tenantStore.hasTenant) {
    // Show loading indicator while critical data loads
    if (!tenantStore.isCriticalDataReady) {
      // You could show a loading page here
      await tenantStore.loadCachedTenantData()
    }
  }

  next()
})
```

## Testing Plan

### Test Case 1: Page Refresh with Tenant in URL
1. Navigate to `http://localhost:3000/test-org/knowledge/sources`
2. Hard refresh (Cmd+R / Ctrl+R)
3. ✅ Verify: Knowledge sources display immediately from cache
4. ✅ Verify: No duplicate API calls in Network tab
5. ✅ Verify: Console shows "Cached tenant data loaded"

### Test Case 2: Tenant Switching
1. Start on `/test-org/dashboard`
2. Switch to `personal` tenant via OrgSwitcher
3. ✅ Verify: URL changes to `/personal/dashboard`
4. ✅ Verify: Old data cleared immediately
5. ✅ Verify: New tenant data loads
6. ✅ Verify: No duplicate API calls

### Test Case 3: Data Refresh (No Cache in POC)
1. Load `/test-org/knowledge/sources`
2. Navigate away and back to `/test-org/knowledge/sources`
3. ✅ Verify: Data reloaded from store (not new API call)
4. ✅ Verify: Components use store data, not independent fetches

### Test Case 4: Error Handling
1. Kill backend server
2. Switch tenants
3. ✅ Verify: Error state displayed
4. ✅ Verify: Previous data not lost
5. Restart server
6. ✅ Verify: Retry works

### Test Case 5: Component Data Refresh
1. Navigate to `/test-org/knowledge/sources`
2. Upload a new file
3. Click component's refresh button
4. ✅ Verify: Store data reloaded with `force=true`
5. ✅ Verify: New file appears in table

## Migration Checklist

### Phase 1 - POC (No Caching)
- [ ] Update tenant store with tenant data state (knowledgeSources, knowledgeStats)
- [ ] Add loading functions WITHOUT caching logic
- [ ] Update switchTenant to load tenant data
- [ ] Remove duplicate tenantSlug watcher
- [ ] Update initialize to load tenant data
- [ ] Update IndexedDocumentsView to use store
- [ ] Update SourcesView to use store
- [ ] Test page refresh scenario
- [ ] Test tenant switching scenario
- [ ] Validate POC works correctly

### Phase 2 - Add Caching (After POC Validation)
- [ ] Add timestamp tracking and TTL validation
- [ ] Update loading functions to check cache validity
- [ ] Test cache expiration and refresh
- [ ] Measure performance improvement

### Phase 3 - Expand & Polish
- [ ] Update queries store watcher
- [ ] Update performance store watcher (if exists)
- [ ] Add more data types to store (if needed)
- [ ] Add optimistic updates for mutations
- [ ] Add loading states to UI
- [ ] Update route guards (optional)

## Key Differences from Original Plan

### ✅ What Changed:
1. **API Signatures**: NO tenant parameters - context via `setCurrentTenant()`
2. **Data Types**: Removed non-existent endpoints (conversations, webhooks, analytics)
3. **Loading Strategy**: Lazy per-view instead of eager all-at-once
4. **Watchers**: Single watcher in store, removed component watchers
5. **Cache Strategy**: Added TTL and validation
6. **Performance**: Only cache small, frequently-used data

### ✅ What Stayed:
1. Centralized data in store (for common data)
2. Computed getters for reactive access
3. Clear data on tenant switch
4. Loading/error states per data type
5. Components use store instead of direct API calls

### ❌ What Was Removed:
1. Eager loading all data upfront
2. Non-existent API endpoints
3. Duplicate watchers causing double-loads
4. Tenant parameters on API methods
5. Route-level data loading

## Performance Expectations

### Before Refactor:
- Page refresh: 3-5 API calls (redundant, race conditions)
- Tenant switch: Race conditions, stale data
- Memory: ~200KB per view (duplicated)
- Data consistency: ❌ Unreliable on refresh

### After Refactor (Phase 1 - POC, No Caching):
- Page refresh: 2 API calls (sources + stats)
- Tenant switch: Instant clear, 2 API calls
- Memory: ~100KB stored (shared across views)
- Data consistency: ✅ Reliable on refresh
- Cache hits: 0% (no caching yet)

### After Refactor (Phase 2 - With Caching):
- Page refresh: 0-2 API calls (cache may be valid)
- Tenant switch: Instant with cached data
- Memory: ~100KB stored
- Data consistency: ✅ Reliable
- Cache hits: ~80-90% for knowledge sources/stats

## Success Criteria

✅ **Phase 1 (POC) Must Have**:
- Page refresh with tenant in URL loads correct data
- No duplicate API calls during tenant switch
- No race conditions between components
- Tenant data shared across views
- Loading states properly displayed
- Components use store data, not individual fetches

✅ **Phase 2 (Caching) Should Have**:
- Cache validation with TTL (5 min)
- Timestamp tracking per data type
- Performance improvement from cache hits

✅ **Phase 3 (Polish) Nice to Have**:
- Optimistic updates for mutations
- Error recovery without data loss
- Route guards for smooth navigation
- Additional data types in store
