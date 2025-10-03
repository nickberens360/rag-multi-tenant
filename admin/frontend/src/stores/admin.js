import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import adminAPI from '@/services/api'
import { TimeRanges } from '@/types/admin'

export const useAdminStore = defineStore('admin', () => {
  // State
  const stats = ref({
    totalQueries: 0,
    averageResponseTime: 0,
    successRate: 0,
    cacheHitRate: 0,
    activeSessions: 0,
    errorRate: 0,
    totalSources: 0,
    totalTopics: 0
  })

  const systemHealth = ref({
    status: 'unknown',
    uptime: 0,
    version: '1.0.0',
    lastUpdated: null
  })

  const timeRange = ref(TimeRanges.DAY)
  const isLoading = ref(false)
  const lastUpdate = ref(null)
  const error = ref(null)
  const isConnected = ref(false)
  
  // Authentication state
  const user = ref(null)
  const isAuthenticated = ref(false)

  // Getters
  const formattedStats = computed(() => ({
    ...stats.value,
    averageResponseTime: `${stats.value.averageResponseTime}ms`,
    successRate: `${stats.value.successRate}%`,
    cacheHitRate: `${stats.value.cacheHitRate}%`,
    errorRate: `${stats.value.errorRate}%`
  }))

  const needsRefresh = computed(() => {
    if (!lastUpdate.value) return true
    const now = new Date()
    const lastUpdateTime = new Date(lastUpdate.value)
    const refreshInterval = parseInt(import.meta.env.VITE_REFRESH_INTERVAL) || 30000
    return now - lastUpdateTime > refreshInterval
  })

  const isHealthy = computed(() => {
    return systemHealth.value.status === 'healthy' && stats.value.errorRate < 10
  })
  
  const userRole = computed(() => user.value?.role || 'viewer')

  // Actions
  const initialize = async () => {
    if (import.meta.env.DEV) {
      // Development initialization code can be added here
    }
    
    // First check if user is authenticated
    const authenticated = await checkAuth()
    
    if (!authenticated) {
      if (import.meta.env.DEV) {
        // Development-specific unauthenticated handling
      }
      return false
    }
    
    await testConnection()
    if (isConnected.value) {
      await Promise.all([
        fetchStats(),
        fetchSystemHealth()
      ])
      startAutoRefresh()
    }
    
    return true
  }

  const testConnection = async () => {
    try {
      isConnected.value = await adminAPI.testConnection()
      if (isConnected.value) {
        error.value = null
        if (import.meta.env.DEV) {
          // Development-specific connection success handling
        }
      } else {
        error.value = 'Unable to connect to admin API'
        if (import.meta.env.DEV) {
          console.error('Failed to connect to admin API')
        }
      }
    } catch (err) {
      isConnected.value = false
      error.value = adminAPI.formatError(err)
      if (import.meta.env.DEV) {
        console.error('Connection test failed:', err)
      }
    }
    return isConnected.value
  }

  const fetchStatsInternal = async (days = 7) => {
    error.value = null

    try {
      if (import.meta.env.DEV) {
        // Debug stats loading
      }
      const data = await adminAPI.getStats(days)
      // API response received successfully
      
      // Update stats with received data - fix field mappings
      stats.value = {
        totalQueries: data.total_queries || 0,
        averageResponseTime: Math.round(data.avg_response_time_ms || 0),
        successRate: Math.round((100 - (data.error_rate || 0))), // Calculate from error rate
        cacheHitRate: Math.round((data.cache_hit_rate || 0)),
        activeSessions: data.unique_sessions || 0, // Use unique_sessions as active sessions
        errorRate: Math.round((data.error_rate || 0)),
        totalSources: data.total_sources || 0,
        totalTopics: data.total_topics || 0,
        queriesToday: data.queries_today || 0,
        queriesThisWeek: data.queries_this_week || 0,
        helpfulRate: Math.round((data.helpful_rate || 0)),
        // Add comparison data for percentage calculations
        totalQueriesChange: data.total_queries_change || 0,
        averageResponseTimeChange: data.avg_response_time_change || 0,
        uniqueSessionsChange: data.unique_sessions_change || 0,
        errorRateChange: data.error_rate_change || 0,
        cacheHitRateChange: data.cache_hit_rate_change || 0,
        helpfulRateChange: data.helpful_rate_change || 0
      }
      
      lastUpdate.value = new Date().toISOString()
      // Stats updated successfully
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to fetch stats:', err)
      throw err // Re-throw so refreshData can handle it
    }
  }

  const fetchStats = async (days = 7) => {
    // Don't return early if already loading - this could cause stuck state
    // Instead, let the operation proceed and manage loading state properly
    
    try {
      isLoading.value = true
      await fetchStatsInternal(days)
    } catch (err) {
      // Make sure we catch and handle errors properly
      console.error('Failed to fetch stats:', err)
      error.value = adminAPI.formatError(err)
    } finally {
      // Always reset loading state
      isLoading.value = false
    }
  }

  const fetchSystemHealth = async () => {
    try {
      const data = await adminAPI.getSystemHealth()
      systemHealth.value = {
        status: data.status || 'unknown',
        uptime: data.uptime || 0,
        version: data.version || '1.0.0',
        lastUpdated: new Date().toISOString(),
        ...data
      }
      if (import.meta.env.DEV && import.meta.env.VITE_DEBUG_STORES) {
        // Debug store state updates
      }
    } catch (err) {
      console.error('Failed to fetch system health:', err)
      systemHealth.value.status = 'error'
    }
  }

  const setTimeRange = async (newTimeRange) => {
    if (timeRange.value !== newTimeRange) {
      timeRange.value = newTimeRange
      
      // Convert time range to days for API
      const daysMap = {
        [TimeRanges.HOUR]: 0.04,
        [TimeRanges.SIX_HOURS]: 0.25,
        [TimeRanges.DAY]: 1,
        [TimeRanges.WEEK]: 7,
        [TimeRanges.MONTH]: 30
      }
      
      const days = daysMap[newTimeRange] || 7
      await fetchStats(days)
    }
  }

  const refreshData = async () => {
    // Remove the early return to prevent getting stuck
    // Instead, we'll use a timeout to force reset if needed
    
    if (import.meta.env.DEV) {
      // Development data refresh debugging
    }
    
    // Force reset loading state if it's been stuck for too long
    let loadingTimeout = null
    
    try {
      // Set loading state
      isLoading.value = true
      
      // Set a timeout to force reset loading state after 10 seconds
      loadingTimeout = setTimeout(() => {
        if (isLoading.value) {
          console.warn('Force resetting loading state after timeout')
          isLoading.value = false
        }
      }, 10000)
      
      await Promise.all([
        fetchStatsInternal().catch(err => {
          console.error('Stats fetch failed:', err)
          // Don't re-throw, just log the error
        }),
        fetchSystemHealth().catch(err => {
          console.error('System health fetch failed:', err)
          // Don't re-throw, just log the error  
        })
      ])
    } catch (err) {
      console.error('Refresh data failed:', err)
      error.value = adminAPI.formatError(err)
    } finally {
      // Clear the timeout and reset loading state
      if (loadingTimeout) {
        clearTimeout(loadingTimeout)
      }
      isLoading.value = false
    }
  }

  let refreshInterval = null

  const startAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }

    const interval = parseInt(import.meta.env.VITE_REFRESH_INTERVAL) || 30000
    refreshInterval = setInterval(() => {
      if (needsRefresh.value) {
        refreshData()
      }
    }, interval)

    if (import.meta.env.DEV) {
      // Debug auto-refresh interval setup
    }
  }

  const stopAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
      if (import.meta.env.DEV) {
        // Debug auto-refresh stop
      }
    }
  }

  const resetError = () => {
    error.value = null
  }

  // Authentication actions
  const login = async (username, password) => {
    try {
      const response = await adminAPI.login(username, password)
      if (response.success && response.user) {
        user.value = response.user
        isAuthenticated.value = true
        
        // Initialize data in background - don't block login response
        Promise.resolve().then(async () => {
          try {
            await testConnection()
            if (isConnected.value) {
              await Promise.all([fetchStats(), fetchSystemHealth()])
              startAutoRefresh()
            }
          } catch (err) {
            console.warn('Post-login data initialization failed:', err)
          }
        })
        
        return response
      } else {
        throw new Error(response.message || 'Login failed')
      }
    } catch (err) {
      console.error('Login failed:', err)
      throw err
    }
  }

  const logout = async () => {
    try {
      await adminAPI.logout()
    } catch (err) {
      console.error('Logout failed:', err)
    } finally {
      stopAutoRefresh()
      user.value = null
      isAuthenticated.value = false
    }
  }

  // Track ongoing auth checks to prevent race conditions
  let authCheckPromise = null

  const checkAuth = async () => {
    // If an auth check is already in progress, wait for it
    if (authCheckPromise) {
      return await authCheckPromise
    }

    authCheckPromise = (async () => {
      try {
        const response = await adminAPI.getCurrentUser()
        if (response.user) {
          user.value = response.user
          isAuthenticated.value = true
          return true
        } else {
          user.value = null
          isAuthenticated.value = false
          return false
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.debug('Not authenticated or session expired')
        }
        user.value = null
        isAuthenticated.value = false
        return false
      } finally {
        authCheckPromise = null
      }
    })()

    return await authCheckPromise
  }

  // Cleanup function for when store is no longer used
  const cleanup = () => {
    stopAutoRefresh()
  }

  return {
    // State
    stats,
    systemHealth,
    timeRange,
    isLoading,
    lastUpdate,
    error,
    isConnected,
    user,
    isAuthenticated,

    // Getters
    formattedStats,
    needsRefresh,
    isHealthy,
    userRole,

    // Actions
    initialize,
    testConnection,
    fetchStats,
    fetchSystemHealth,
    setTimeRange,
    refreshData,
    startAutoRefresh,
    stopAutoRefresh,
    resetError,
    login,
    logout,
    checkAuth,
    cleanup
  }
})