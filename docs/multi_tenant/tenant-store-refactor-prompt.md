# Tenant Store Refactoring Implementation Guide

## Overview
Refactor the existing Pinia tenant store from a "thin" store (only storing tenant ID/name/role) to a "thick" store that acts as a central repository for ALL tenant-related data. This will solve the current issue where data doesn't refresh correctly when the page is refreshed with a tenant query parameter.

## Current Problem
- When `currentTenant` changes programmatically, data refreshes correctly
- When refreshing the page with a tenant query param, data is incorrect
- Components are managing their own watchers for tenant changes, leading to timing issues

## Solution Architecture
Transform the tenant store to:
1. Hold ALL tenant-specific data in a centralized `tenantData` object
2. Provide computed getters for each data type (knowledgeSources, indexedDocs, etc.)
3. Automatically load/clear data when tenant changes
4. Components simply use the getters - no watchers needed

## Implementation Steps

### Step 1: Update Tenant Store Structure

Update `/stores/tenant.js` with the following changes:

#### 1.1 Add Tenant Data State
After the existing state declarations, add:
```javascript
// Tenant Data State - ALL tenant-specific data goes here
const tenantData = ref({
  knowledgeSources: [],
  indexedDocuments: [],
  queryLogs: [],
  performanceStats: null,
  settings: null,
  users: [],
  conversations: [],
  apiKeys: [],
  webhooks: [],
  analytics: null,
  // Add any other tenant-specific data collections here
})

// Loading states for individual data types
const dataLoading = ref({
  knowledgeSources: false,
  indexedDocuments: false,
  queryLogs: false,
  performanceStats: false,
  settings: false,
  users: false,
  conversations: false,
  apiKeys: false,
  webhooks: false,
  analytics: false,
})

// Error states for individual data types (optional but recommended)
const dataErrors = ref({
  knowledgeSources: null,
  indexedDocuments: null,
  queryLogs: null,
  performanceStats: null,
  settings: null,
  users: null,
  conversations: null,
  apiKeys: null,
  webhooks: null,
  analytics: null,
})
```

#### 1.2 Add Data Getters
Add these computed getters after the existing getters:
```javascript
// Data Getters - these automatically update when currentTenant changes
const currentTenantKnowledgeSources = computed(() => 
  hasTenant.value ? tenantData.value.knowledgeSources : []
)

const currentTenantIndexedDocs = computed(() => 
  hasTenant.value ? tenantData.value.indexedDocuments : []
)

const currentTenantQueryLogs = computed(() => 
  hasTenant.value ? tenantData.value.queryLogs : []
)

const currentTenantPerformanceStats = computed(() => 
  hasTenant.value ? tenantData.value.performanceStats : null
)

const currentTenantSettings = computed(() => 
  hasTenant.value ? tenantData.value.settings : null
)

const currentTenantUsers = computed(() => 
  hasTenant.value ? tenantData.value.users : []
)

const currentTenantConversations = computed(() => 
  hasTenant.value ? tenantData.value.conversations : []
)

const currentTenantApiKeys = computed(() => 
  hasTenant.value ? tenantData.value.apiKeys : []
)

const currentTenantWebhooks = computed(() => 
  hasTenant.value ? tenantData.value.webhooks : []
)

const currentTenantAnalytics = computed(() => 
  hasTenant.value ? tenantData.value.analytics : null
)
```

#### 1.3 Add Data Loading Functions
Add individual loading functions for each data type:
```javascript
// Data Loading Actions
const loadKnowledgeSources = async (force = false) => {
  if (!tenantId.value || (dataLoading.value.knowledgeSources && !force)) return
  
  dataLoading.value.knowledgeSources = true
  dataErrors.value.knowledgeSources = null
  
  try {
    const data = await adminAPI.getKnowledgeSources(tenantId.value)
    tenantData.value.knowledgeSources = data || []
  } catch (err) {
    console.error('Failed to load knowledge sources:', err)
    dataErrors.value.knowledgeSources = adminAPI.formatError(err)
    tenantData.value.knowledgeSources = []
  } finally {
    dataLoading.value.knowledgeSources = false
  }
}

const loadIndexedDocuments = async (force = false) => {
  if (!tenantId.value || (dataLoading.value.indexedDocuments && !force)) return
  
  dataLoading.value.indexedDocuments = true
  dataErrors.value.indexedDocuments = null
  
  try {
    const data = await adminAPI.getIndexedDocuments(tenantId.value)
    tenantData.value.indexedDocuments = data || []
  } catch (err) {
    console.error('Failed to load indexed documents:', err)
    dataErrors.value.indexedDocuments = adminAPI.formatError(err)
    tenantData.value.indexedDocuments = []
  } finally {
    dataLoading.value.indexedDocuments = false
  }
}

const loadQueryLogs = async (force = false) => {
  if (!tenantId.value || (dataLoading.value.queryLogs && !force)) return
  
  dataLoading.value.queryLogs = true
  dataErrors.value.queryLogs = null
  
  try {
    const data = await adminAPI.getQueryLogs(tenantId.value)
    tenantData.value.queryLogs = data || []
  } catch (err) {
    console.error('Failed to load query logs:', err)
    dataErrors.value.queryLogs = adminAPI.formatError(err)
    tenantData.value.queryLogs = []
  } finally {
    dataLoading.value.queryLogs = false
  }
}

const loadPerformanceStats = async (force = false) => {
  if (!tenantId.value || (dataLoading.value.performanceStats && !force)) return
  
  dataLoading.value.performanceStats = true
  dataErrors.value.performanceStats = null
  
  try {
    const data = await adminAPI.getPerformanceStats(tenantId.value)
    tenantData.value.performanceStats = data || null
  } catch (err) {
    console.error('Failed to load performance stats:', err)
    dataErrors.value.performanceStats = adminAPI.formatError(err)
    tenantData.value.performanceStats = null
  } finally {
    dataLoading.value.performanceStats = false
  }
}

const loadSettings = async (force = false) => {
  if (!tenantId.value || (dataLoading.value.settings && !force)) return
  
  dataLoading.value.settings = true
  dataErrors.value.settings = null
  
  try {
    const data = await adminAPI.getTenantSettings(tenantId.value)
    tenantData.value.settings = data || null
  } catch (err) {
    console.error('Failed to load settings:', err)
    dataErrors.value.settings = adminAPI.formatError(err)
    tenantData.value.settings = null
  } finally {
    dataLoading.value.settings = false
  }
}

const loadUsers = async (force = false) => {
  if (!tenantId.value || (dataLoading.value.users && !force)) return
  
  dataLoading.value.users = true
  dataErrors.value.users = null
  
  try {
    const data = await adminAPI.getTenantUsers(tenantId.value)
    tenantData.value.users = data || []
  } catch (err) {
    console.error('Failed to load users:', err)
    dataErrors.value.users = adminAPI.formatError(err)
    tenantData.value.users = []
  } finally {
    dataLoading.value.users = false
  }
}

// Add similar functions for conversations, apiKeys, webhooks, analytics, etc.
```

#### 1.4 Add Composite Loading Functions
```javascript
// Load all tenant data
const loadAllTenantData = async () => {
  if (!tenantId.value) return

  console.log('Loading all data for tenant:', tenantName.value)
  
  // Load critical data first (settings, users)
  await Promise.all([
    loadSettings(),
    loadUsers(),
  ])
  
  // Then load the rest in parallel
  await Promise.all([
    loadKnowledgeSources(),
    loadIndexedDocuments(),
    loadQueryLogs(),
    loadPerformanceStats(),
    // Add other load functions...
  ])
  
  console.log('All tenant data loaded')
}

// Load data for a specific view/page
const loadDataForView = async (viewName) => {
  if (!tenantId.value) return
  
  switch (viewName) {
    case 'knowledge':
      await Promise.all([
        loadKnowledgeSources(),
        loadIndexedDocuments(),
      ])
      break
    case 'analytics':
      await Promise.all([
        loadQueryLogs(),
        loadPerformanceStats(),
        // loadAnalytics(),
      ])
      break
    case 'settings':
      await Promise.all([
        loadSettings(),
        loadUsers(),
        loadApiKeys(),
        loadWebhooks(),
      ])
      break
    // Add other view-specific loading patterns
  }
}

// Clear all tenant data
const clearTenantData = () => {
  tenantData.value = {
    knowledgeSources: [],
    indexedDocuments: [],
    queryLogs: [],
    performanceStats: null,
    settings: null,
    users: [],
    conversations: [],
    apiKeys: [],
    webhooks: [],
    analytics: null,
  }
  
  // Reset all error states
  Object.keys(dataErrors.value).forEach(key => {
    dataErrors.value[key] = null
  })
}
```

#### 1.5 Update the switchTenant Function
Replace the existing `switchTenant` function:
```javascript
const switchTenant = async (tenant) => {
  if (!tenant || currentTenant.value?.id === tenant.id) {
    return // No change needed
  }

  const previousTenant = currentTenant.value
  console.log(`Switching from tenant ${previousTenant?.name} to ${tenant.name}`)

  try {
    // Clear previous tenant data immediately
    clearTenantData()
    
    // Update API service tenant context
    adminAPI.setCurrentTenant(tenant.slug)
    
    // Update current tenant state
    currentTenant.value = tenant
    
    // Start loading new tenant data (don't await - let it load in background)
    loadAllTenantData().catch(err => {
      console.error('Error loading tenant data after switch:', err)
    })
    
    console.log(`Switched to tenant: ${tenant.name} (${tenant.slug})`)

    // Handle routing
    const slugs = (userTenants.value || []).map(t => t.slug)
    const cur = route.fullPath || '/'
    const parts = cur.split('/')
    let rest = cur
    if (parts.length > 1 && slugs.includes(parts[1])) {
      rest = cur.slice(parts[1].length + 1)
      if (!rest.startsWith('/')) rest = '/' + rest
    }
    const newPath = `/${tenant.slug}${rest === '' ? '/' : rest}`
    if (newPath !== cur) {
      await router.replace(newPath)
    }

    return { success: true, previousTenant, newTenant: tenant }
  } catch (err) {
    console.error('Failed to switch tenant:', err)
    error.value = adminAPI.formatError(err)
    
    // Revert on error
    if (previousTenant) {
      adminAPI.setCurrentTenant(previousTenant.slug)
      currentTenant.value = previousTenant
      // Reload previous tenant data
      loadAllTenantData().catch(console.error)
    }
    
    return { success: false, error: err }
  }
}
```

#### 1.6 Update Watchers
Replace the existing watchers with:
```javascript
// Watch for tenant ID changes and reload data
watch(tenantId, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    console.log('Tenant ID changed, reloading data:', oldId, '->', newId)
    clearTenantData()
    await loadAllTenantData()
  }
})

// Keep currentTenant in sync with URL
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
  if (initialized.value) return
  
  console.log('Initializing tenant store...')
  await fetchUserTenants()
  
  // If we have a current tenant after loading user tenants, load its data
  if (currentTenant.value) {
    console.log('Current tenant found on init, loading data:', currentTenant.value.name)
    await loadAllTenantData()
  }
  
  console.log('Tenant store initialized')
}
```

#### 1.8 Update Store Return Value
Update the return statement to include all new properties:
```javascript
return {
  // Core State
  currentTenant,
  userTenants,
  isLoading,
  error,
  initialized,
  
  // Data State
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
  currentTenantIndexedDocs,
  currentTenantQueryLogs,
  currentTenantPerformanceStats,
  currentTenantSettings,
  currentTenantUsers,
  currentTenantConversations,
  currentTenantApiKeys,
  currentTenantWebhooks,
  currentTenantAnalytics,

  // Core Actions
  fetchUserTenants,
  switchTenant,
  clearTenant,
  resetError,
  initialize,
  
  // Data Loading Actions
  loadAllTenantData,
  loadDataForView,
  loadKnowledgeSources,
  loadIndexedDocuments,
  loadQueryLogs,
  loadPerformanceStats,
  loadSettings,
  loadUsers,
  // Add other individual loaders...
  
  // Utility Actions
  clearTenantData,
}
```

### Step 2: Update Components to Use New Store

#### 2.1 Example Component Refactor
For each component that currently watches tenant changes, refactor like this:

**BEFORE:**
```javascript
import { ref, watch, onMounted } from 'vue'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

export default {
  setup() {
    const tenantStore = useTenantStore()
    const knowledgeSources = ref([])
    const loading = ref(false)
    
    const loadData = async () => {
      if (!tenantStore.tenantId) return
      loading.value = true
      try {
        const data = await adminAPI.getKnowledgeSources(tenantStore.tenantId)
        knowledgeSources.value = data
      } finally {
        loading.value = false
      }
    }
    
    watch(() => tenantStore.tenantId, () => {
      loadData()
    })
    
    onMounted(() => {
      loadData()
    })
    
    return { knowledgeSources, loading }
  }
}
```

**AFTER:**
```javascript
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'

export default {
  setup() {
    const tenantStore = useTenantStore()
    const { 
      currentTenantKnowledgeSources,
      dataLoading 
    } = storeToRefs(tenantStore)
    
    // That's it! No watchers, no manual loading
    
    return {
      knowledgeSources: currentTenantKnowledgeSources,
      loading: computed(() => dataLoading.value.knowledgeSources)
    }
  }
}
```

#### 2.2 Components That Need Fresh Data
If a component needs to refresh data (e.g., after creating a new item):
```javascript
const handleCreate = async (newSource) => {
  // ... create logic ...
  
  // Refresh the knowledge sources
  await tenantStore.loadKnowledgeSources(true) // force=true to reload
}
```

### Step 3: Update Route Guards

Update any route guards to ensure tenant is initialized:
```javascript
router.beforeEach(async (to, from, next) => {
  const tenantStore = useTenantStore()
  
  // Initialize tenant store if not already done
  if (!tenantStore.initialized) {
    await tenantStore.initialize()
  }
  
  // Load view-specific data
  if (to.meta.viewName) {
    tenantStore.loadDataForView(to.meta.viewName)
  }
  
  next()
})
```

### Step 4: Testing Plan

1. Test page refresh with tenant in URL
2. Test switching between tenants
3. Test navigating between views within a tenant
4. Test creating/updating/deleting items and data refresh
5. Test error states and recovery
6. Test loading states during data fetch

### API Endpoints to Implement/Verify

Ensure these adminAPI methods exist:
- `adminAPI.getKnowledgeSources(tenantId)`
- `adminAPI.getIndexedDocuments(tenantId)`
- `adminAPI.getQueryLogs(tenantId)`
- `adminAPI.getPerformanceStats(tenantId)`
- `adminAPI.getTenantSettings(tenantId)`
- `adminAPI.getTenantUsers(tenantId)`
- `adminAPI.getTenantConversations(tenantId)`
- `adminAPI.getTenantApiKeys(tenantId)`
- `adminAPI.getTenantWebhooks(tenantId)`
- `adminAPI.getTenantAnalytics(tenantId)`

### Benefits of This Approach

1. **Solves the refresh issue**: Data is always loaded from the store, which handles initialization
2. **Simpler components**: No watchers or lifecycle hooks needed
3. **Better performance**: Data is cached in store, only loaded when needed
4. **Consistent loading states**: Centralized loading/error handling
5. **Easy to extend**: Just add new data types to tenantData and create getters
6. **Type safety**: With TypeScript, all data flows are properly typed

### Migration Strategy

1. Implement new store structure alongside existing code
2. Update one component at a time to use new getters
3. Once all components migrated, remove old watchers
4. Add any missing data types as needed

### Potential Optimizations

1. **Lazy Loading**: Only load data when first accessed
2. **Caching**: Add TTL to cached data, refresh if stale
3. **Partial Updates**: Update specific items without full reload
4. **Optimistic Updates**: Update UI before API confirms
5. **Background Refresh**: Periodically refresh data in background

### Key Points to Remember

- The store is now the single source of truth for ALL tenant data
- Components should never fetch tenant data directly - always use store getters
- When tenant changes, all data is automatically cleared and reloaded
- Loading states are granular - can show skeleton for specific sections
- Errors are captured per data type - one failure doesn't break everything
