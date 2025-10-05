import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminAPI } from '@/services/api'

// Tenant interface definition for JSDoc
/**
 * @typedef {Object} Tenant
 * @property {string} id - The tenant ID
 * @property {string} slug - The tenant slug
 * @property {string} name - The tenant display name
 * @property {string} role - The user's role in this tenant
 */

export const useTenantStore = defineStore('tenant', () => {
  const route = useRoute()
  const router = useRouter()

  // State
  const currentTenant = ref(null)
  const userTenants = ref([])
  const isLoading = ref(false)
  const error = ref(null)
  const initialized = ref(false)

  // Tenant Data State - ONLY commonly-used, small datasets
  const tenantData = ref({
    knowledgeSources: [],    // Used in: SourcesView, IndexedDocsView, Dashboard
    knowledgeStats: null,    // Used in: IndexedDocsView, Dashboard
    indexedDocuments: [],    // Used in: DocumentsView
  })

  // Loading states per data type
  const dataLoading = ref({
    knowledgeSources: false,
    knowledgeStats: false,
    indexedDocuments: false,
  })

  // Error states per data type
  const dataErrors = ref({
    knowledgeSources: null,
    knowledgeStats: null,
    indexedDocuments: null,
  })

  // Getters
  const tenantSlug = computed(() => {
    // Check subdomain
    const subdomain = window.location.hostname.split('.')[0]
    if (subdomain && !['www', 'localhost', 'api', 'admin'].includes(subdomain)) {
      return subdomain
    }

    // Check path prefix
    const pathMatch = route.path.match(/^\/([^/]+)/)
    if (pathMatch) {
      return pathMatch[1]
    }

    return null
  })

  const hasTenant = computed(() => currentTenant.value !== null)

  const tenantId = computed(() => currentTenant.value?.id || null)

  const tenantName = computed(() => currentTenant.value?.name || null)

  // Data Getters - automatically reactive when currentTenant changes
  const currentTenantKnowledgeSources = computed(() =>
    hasTenant.value ? tenantData.value.knowledgeSources : []
  )

  const currentTenantKnowledgeStats = computed(() =>
    hasTenant.value ? tenantData.value.knowledgeStats : null
  )

  const currentTenantIndexedDocuments = computed(() =>
    hasTenant.value ? tenantData.value.indexedDocuments : []
  )

  // Loading state getters
  const isLoadingKnowledgeSources = computed(() =>
    dataLoading.value.knowledgeSources
  )

  const isLoadingKnowledgeStats = computed(() =>
    dataLoading.value.knowledgeStats
  )

  const isLoadingIndexedDocuments = computed(() =>
    dataLoading.value.indexedDocuments
  )

  // Check if critical data is ready
  const isCriticalDataReady = computed(() => {
    if (!hasTenant.value) return false
    return !dataLoading.value.knowledgeSources &&
           !dataLoading.value.knowledgeStats
  })

  // Actions
  const fetchUserTenants = async () => {
    if (isLoading.value) return

    isLoading.value = true
    error.value = null

    try {
      console.log('Fetching user tenants from API...')
      const response = await adminAPI.getMyTenants()
      console.log('Tenants API response:', response)
      userTenants.value = response || []

      // Set current tenant if slug matches
      const currentSlug = tenantSlug.value
      console.log('Current tenant slug from URL:', currentSlug)
      console.log('Current route path:', route.path)

      if (currentSlug) {
        const matchedTenant = userTenants.value.find(
          t => t.slug === currentSlug
        )
        console.log('Matched tenant:', matchedTenant)
        if (matchedTenant) {
          currentTenant.value = matchedTenant
          adminAPI.setCurrentTenant(matchedTenant.slug)
          console.log('✅ Current tenant set to:', matchedTenant.name, matchedTenant.slug)
        } else {
          console.warn('⚠️ No tenant matched slug:', currentSlug)
        }
      } else {
        console.log('No tenant slug in URL')
      }

      console.log('User tenants loaded:', userTenants.value)
    } catch (err) {
      console.error('Failed to fetch user tenants:', err)
      console.error('Error details:', err.response || err)
      error.value = adminAPI.formatError(err)
      userTenants.value = []
    } finally {
      isLoading.value = false
      initialized.value = true
    }
  }

  // Data Loading Functions
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

      // Use tenant-scoped files status so newly uploaded (discovered) files appear
      // This returns { files: [...], total }
      const data = await adminAPI.getKnowledgeFilesStatus({ limit: 1000 })

      // Normalize to the shape expected by the UI (path, status, content_type, chunk_count, display_path)
      const files = Array.isArray(data?.files) ? data.files : []
      tenantData.value.knowledgeSources = files.map(f => {
        const path = f.path || ''
        // Derive a friendlier display path when possible
        let displayPath = path
        if (displayPath.startsWith('backend/knowledge/')) {
          displayPath = displayPath.replace('backend/knowledge/', '')
        } else if (displayPath.startsWith('public/')) {
          displayPath = displayPath.replace('public/', '')
        }
        return {
          path,
          status: f.status || 'unknown',
          // content_type not tracked in metadata DB; default to 'unknown'
          content_type: f.content_type || 'unknown',
          chunk_count: f.chunk_count ?? 0,
          display_path: displayPath,
        }
      })

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

  const loadIndexedDocuments = async (force = false) => {
    if (!currentTenant.value?.slug) return
    if (dataLoading.value.indexedDocuments && !force) return

    dataLoading.value.indexedDocuments = true
    dataErrors.value.indexedDocuments = null

    try {
      console.debug(`Loading indexed documents for tenant: ${currentTenant.value.slug}`)

      // Context already set via setCurrentTenant
      const data = await adminAPI.getKnowledgeDocuments(100, 0)

      tenantData.value.indexedDocuments = data?.documents || []

      console.debug(`✅ Loaded ${tenantData.value.indexedDocuments.length} indexed documents`)
    } catch (err) {
      console.error('Failed to load indexed documents:', err)
      dataErrors.value.indexedDocuments = adminAPI.formatError(err)
      tenantData.value.indexedDocuments = []
    } finally {
      dataLoading.value.indexedDocuments = false
    }
  }

  // Composite Loading Functions
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
      loadIndexedDocuments(force),
    ])

    console.log('✅ Tenant data loaded')
  }

  // Load data for a specific view or route name
  const loadDataForView = async (viewName) => {
    if (!currentTenant.value?.slug) return

    const name = String(viewName || '').toLowerCase()
    try {
      if (name === 'knowledge-sources') {
        await loadKnowledgeSources()
        return
      }
      if (name === 'knowledge-documents') {
        await Promise.all([
          loadKnowledgeStats(),
          loadIndexedDocuments(),
        ])
        return
      }
      if (name === 'knowledge-overview') {
        await Promise.all([
          loadKnowledgeSources(),
          loadKnowledgeStats(),
        ])
        return
      }
      if (name === 'knowledge-stats') {
        await loadKnowledgeStats()
        return
      }
      if (name === 'knowledge-consistency') {
        // Summary charts rely on stats; lists are loaded in-view
        await loadKnowledgeStats()
        return
      }
      // Default: no-op
    } catch (e) {
      console.debug('loadDataForView error:', e)
    }
  }

  // Clear all tenant data
  const clearTenantData = () => {
    tenantData.value = {
      knowledgeSources: [],
      knowledgeStats: null,
      indexedDocuments: [],
    }

    // Reset error states
    Object.keys(dataErrors.value).forEach(key => {
      dataErrors.value[key] = null
    })

    console.debug('Cleared all tenant data')
  }

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
      // Await to ensure data is loaded before navigation completes
      await loadTenantData()

      // Step 5: Handle routing (navigate to tenant-prefixed URL)
      const slugs = (userTenants.value || []).map(t => t.slug)
      const cur = route.fullPath || '/'
      const parts = cur.split('/')
      let rest = cur

      // Strip existing tenant prefix if present
      if (parts.length > 1 && slugs.includes(parts[1])) {
        rest = cur.slice(parts[1].length + 1)
        if (!rest.startsWith('/')) rest = `/${  rest}`
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

  const clearTenant = () => {
    currentTenant.value = null
    adminAPI.setCurrentTenant(null)
    console.debug('Cleared tenant context')

    // Remove tenant prefix from URL if present
    try {
      const slugs = (userTenants.value || []).map(t => t.slug)
      const cur = route.fullPath || '/'
      const parts = cur.split('/')
      if (parts.length > 1 && slugs.includes(parts[1])) {
        const rest = cur.slice(parts[1].length + 1) || '/'
        router.replace(rest)
      }
    } catch (e) {
      // no-op
    }
  }

  const resetError = () => {
    error.value = null
  }

  // Initialize tenant from URL on store creation
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

  // Keep currentTenant in sync with URL - but delegate to switchTenant
  watch(tenantSlug, async (newSlug, oldSlug) => {
    if (newSlug && newSlug !== oldSlug && initialized.value) {
      console.log('🔍 Tenant slug watcher fired:', {
        oldSlug,
        newSlug,
        currentTenantSlug: currentTenant.value?.slug,
        routePath: route.path,
        initialized: initialized.value
      })

      // Guard: Don't switch if already on the correct tenant
      if (currentTenant.value?.slug === newSlug) {
        console.debug('Already on correct tenant, skipping switch')
        return
      }

      const matched = userTenants.value.find(t => t.slug === newSlug)
      if (matched) {
        await switchTenant(matched)
      } else {
        console.warn('No tenant matched new slug:', newSlug)
      }
    }
  })

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
    currentTenantIndexedDocuments,
    isLoadingKnowledgeSources,
    isLoadingKnowledgeStats,
    isLoadingIndexedDocuments,
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
    loadIndexedDocuments,
    loadDataForView,
    clearTenantData,
  }
})
