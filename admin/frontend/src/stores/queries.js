import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import adminAPI from '@/services/api'
import { QueryStatus } from '@/types/admin'
import { useTenantStore } from '@/stores/tenant'

export const useQueriesStore = defineStore('queries', () => {
  // State
  const queries = ref([])
  const totalQueries = ref(0)
  const selectedQueries = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Filters
  const filters = ref({
    page: 1,
    limit: 25,
    search: '',
    startDate: null,
    endDate: null,
    errorOnly: false,
    minRelevance: 0,
    sortBy: 'timestamp',
    sortOrder: 'desc'
  })

  // Query insights
  const insights = ref({
    popularTopics: [],
    errorPatterns: [],
    lowConfidenceQueries: [],
    unansweredQuestions: []
  })

  // Server returns the current page; expose as-is
  const paginatedQueries = computed(() => queries.value)

  const totalPages = computed(() => {
    return Math.ceil(totalQueries.value / filters.value.limit)
  })

  const hasSelectedQueries = computed(() => {
    return selectedQueries.value.length > 0
  })

  const successfulQueries = computed(() => {
    return queries.value.filter(q => q.status === QueryStatus.SUCCESS)
  })

  const errorQueries = computed(() => {
    return queries.value.filter(q => q.status === QueryStatus.ERROR)
  })

  const averageResponseTime = computed(() => {
    const successful = successfulQueries.value
    if (successful.length === 0) return 0
    
    const total = successful.reduce((sum, q) => sum + (q.response_time || 0), 0)
    return Math.round(total / successful.length)
  })

  const successRate = computed(() => {
    if (queries.value.length === 0) return 0
    return Math.round((successfulQueries.value.length / queries.value.length) * 100)
  })

  // Actions
  const fetchQueries = async (params = {}) => {
    isLoading.value = true
    error.value = null

    try {
      // For client-side table, fetch all queries without pagination
      const mergedParams = { 
        limit: 1000, // Get a large number of queries
        offset: 0,
        ...params 
      }
      const data = await adminAPI.getQueries(mergedParams)
      
      queries.value = data.queries || []
      totalQueries.value = data.total || 0
      
      // Queries fetched successfully
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to fetch queries:', err)
    } finally {
      isLoading.value = false
    }
  }

  const fetchQuery = async (id) => {
    try {
      const query = await adminAPI.getQuery(id)
      
      // Update the query in the list if it exists
      const index = queries.value.findIndex(q => q.id === id)
      if (index !== -1) {
        queries.value[index] = query
      }
      
      return query
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to fetch query:', err)
      throw err
    }
  }

  const updateQueryFeedback = async (id, feedback) => {
    try {
      await adminAPI.updateQueryFeedback(id, feedback)
      
      // Update the query in the local list
      const query = queries.value.find(q => q.id === id)
      if (query) {
        query.feedback = feedback
        query.feedback_updated_at = new Date().toISOString()
      }
      
      // Feedback updated successfully
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to update feedback:', err)
      throw err
    }
  }

  const fetchInsights = async () => {
    try {
      const data = await adminAPI.getQueryInsights()
      insights.value = {
        popularTopics: data.popular_topics || [],
        errorPatterns: data.error_patterns || [],
        lowConfidenceQueries: data.low_confidence_queries || [],
        unansweredQuestions: data.unanswered_questions || []
      }
      // Query insights updated successfully
    } catch (err) {
      console.error('Failed to fetch insights:', err)
    }
  }

  const setFilters = async (newFilters) => {
    // Merge new filters with existing ones
    const updatedFilters = { ...filters.value, ...newFilters }
    
    // Reset page to 1 if search/filter criteria changed
    if (newFilters.search !== undefined || 
        newFilters.startDate !== undefined || 
        newFilters.endDate !== undefined ||
        newFilters.errorOnly !== undefined ||
        newFilters.minRelevance !== undefined) {
      updatedFilters.page = 1
    }
    
    filters.value = updatedFilters
    await fetchQueries()
  }

  const setPage = async (page) => {
    if (page >= 1 && page <= totalPages.value) {
      filters.value.page = page
      await fetchQueries()
    }
  }

  const toggleQuerySelection = (queryId) => {
    const index = selectedQueries.value.indexOf(queryId)
    if (index === -1) {
      selectedQueries.value.push(queryId)
    } else {
      selectedQueries.value.splice(index, 1)
    }
  }

  const selectAllQueries = () => {
    selectedQueries.value = queries.value.map(q => q.id)
  }

  const clearSelection = () => {
    selectedQueries.value = []
  }

  const exportQueries = async (format = 'csv', includeResponses = false) => {
    try {
      const params = {
        format,
        includeResponses,
        startDate: filters.value.startDate,
        endDate: filters.value.endDate
      }
      
      const blob = await adminAPI.exportQueries(params)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `queries_export_${new Date().toISOString().split('T')[0]}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      // Queries exported successfully
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to export queries:', err)
      throw err
    }
  }

  const searchQueries = async (searchTerm) => {
    await setFilters({ search: searchTerm })
  }

  const resetFilters = async () => {
    filters.value = {
      page: 1,
      limit: 25,
      search: '',
      startDate: null,
      endDate: null,
      errorOnly: false,
      minRelevance: 0,
      sortBy: 'timestamp',
      sortOrder: 'desc'
    }
    await fetchQueries()
  }

  const resetError = () => {
    error.value = null
  }

  // Access tenant store
  const tenantStore = useTenantStore()

  // Clear cached data when tenant changes
  const clearTenantData = () => {
    queries.value = []
    totalQueries.value = 0
    selectedQueries.value = []
    insights.value = {
      popularTopics: [],
      errorPatterns: [],
      lowConfidenceQueries: [],
      unansweredQuestions: []
    }
    error.value = null
    console.debug('Queries store: cleared tenant-specific data')
  }

  // Watch for tenant changes and clear cached data reactively
  watch(
    () => tenantStore.currentTenant?.id,
    (newTenantId, oldTenantId) => {
      if (oldTenantId && newTenantId && oldTenantId !== newTenantId) {
        console.debug(`Queries store: tenant changed from ${oldTenantId} to ${newTenantId}`)
        clearTenantData()
      }
    }
  )

  return {
    // State
    queries,
    totalQueries,
    selectedQueries,
    isLoading,
    error,
    filters,
    insights,

    // Getters
    paginatedQueries,
    totalPages,
    hasSelectedQueries,
    successfulQueries,
    errorQueries,
    averageResponseTime,
    successRate,

    // Actions
    fetchQueries,
    fetchQuery,
    updateQueryFeedback,
    fetchInsights,
    setFilters,
    setPage,
    toggleQuerySelection,
    selectAllQueries,
    clearSelection,
    exportQueries,
    searchQueries,
    resetFilters,
    resetError,
    clearTenantData
  }
})