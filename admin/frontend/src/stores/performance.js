import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { parseISO, parse, isValid } from 'date-fns'
import adminAPI from '@/services/api'
import { TimeRanges } from '@/types/admin'
import { useTenantStore } from '@/stores/tenant'

/**
 * Parse timestamp string using date-fns for robust handling
 * @param {string} dateStr - Timestamp string in various formats
 * @returns {Date|null} - Parsed date or null if invalid
 */
const parseTimestamp = (dateStr) => {
  if (!dateStr) return null

  try {
    // Handle ISO format with T or Z
    if (dateStr.includes('T') || dateStr.includes('Z')) {
      const date = parseISO(dateStr)
      return isValid(date) ? date : null
    }

    // Handle space-separated format (YYYY-MM-DD HH:MM:SS) with optional microseconds
    if (dateStr.includes(' ')) {
      // Try with microseconds first
      let date = parse(dateStr, 'yyyy-MM-dd HH:mm:ss.SSSSSS', new Date())
      if (isValid(date)) return date

      // Try without microseconds
      date = parse(dateStr, 'yyyy-MM-dd HH:mm:ss', new Date())
      return isValid(date) ? date : null
    }

    // Handle date-only format (YYYY-MM-DD)
    const date = parse(dateStr, 'yyyy-MM-dd', new Date())
    return isValid(date) ? date : null

  } catch (error) {
    console.warn('Failed to parse timestamp:', dateStr, error)
    return null
  }
}

export const usePerformanceStore = defineStore('performance', () => {
  // State
  const metrics = ref({
    responseTime: {
      current: 0,
      previous: 0,
      change: 0
    },
    throughput: {
      current: 0,
      previous: 0,
      change: 0
    },
    errorRate: {
      current: 0,
      previous: 0,
      change: 0
    },
    cacheHitRate: {
      current: 0,
      previous: 0,
      change: 0
    }
  })

  const timeline = ref([])
  const percentiles = ref({
    p50: 0,
    p95: 0,
    p99: 0
  })

  const chartData = ref({
    responseTime: { labels: [], datasets: [] },
    throughput: { labels: [], datasets: [] },
    errorRate: { labels: [], datasets: [] },
    cacheHitRate: { labels: [], datasets: [] }
  })
  
  // Initialize with empty but valid chart structure
  const initializeChartData = () => {
    chartData.value = {
      responseTime: { labels: [], datasets: [] },
      throughput: { labels: [], datasets: [] },
      errorRate: { labels: [], datasets: [] },
      cacheHitRate: { labels: [], datasets: [] }
    }
  }

  const isLoading = ref(false)
  const error = ref(null)
  const timeRange = ref(TimeRanges.WEEK)

  // Getters
  const hasData = computed(() => {
    return timeline.value.length > 0
  })

  const averageResponseTime = computed(() => {
    if (timeline.value.length === 0) return 0
    const total = timeline.value.reduce((sum, point) => sum + (point.avg_response_time || 0), 0)
    return Math.round(total / timeline.value.length)
  })

  const totalQueries = computed(() => {
    return timeline.value.reduce((sum, point) => sum + (point.query_count || 0), 0)
  })

  const peakThroughput = computed(() => {
    if (timeline.value.length === 0) return 0
    return Math.max(...timeline.value.map(point => point.query_count || 0))
  })

  const performanceScore = computed(() => {
    // Calculate a performance score based on multiple factors
    const responseTimeScore = Math.max(0, 100 - (averageResponseTime.value / 10))
    const errorRateScore = Math.max(0, 100 - (metrics.value.errorRate.current * 10))
    const cacheScore = metrics.value.cacheHitRate.current
    
    return Math.round((responseTimeScore + errorRateScore + cacheScore) / 3)
  })

  const trendDirection = computed(() => {
    const responseTrend = metrics.value.responseTime.change
    const errorTrend = metrics.value.errorRate.change
    
    if (responseTrend < 0 && errorTrend <= 0) return 'improving'
    if (responseTrend > 0 || errorTrend > 0) return 'degrading'
    return 'stable'
  })

  // Actions
  const fetchMetrics = async (selectedTimeRange = null) => {
    if (selectedTimeRange) {
      timeRange.value = selectedTimeRange
    }

    isLoading.value = true
    error.value = null

    try {
      const data = await adminAPI.getPerformanceMetrics(timeRange.value)
      
      // Debug logging removed - issue identified and fixed
      
      metrics.value = {
        responseTime: {
          current: Math.round(data.response_time?.current || 0),
          previous: Math.round(data.response_time?.previous || 0),
          change: Math.round((data.response_time?.change || 0) * 100) / 100
        },
        throughput: {
          current: data.throughput?.current || 0,
          previous: data.throughput?.previous || 0,
          change: Math.round((data.throughput?.change || 0) * 100) / 100
        },
        errorRate: {
          current: Math.round((data.error_rate?.current || 0) * 100) / 100,
          previous: Math.round((data.error_rate?.previous || 0) * 100) / 100,
          change: Math.round((data.error_rate?.change || 0) * 100) / 100
        },
        cacheHitRate: {
          current: Math.round((data.cache_hit_rate?.current || 0) * 100) / 100,
          previous: Math.round((data.cache_hit_rate?.previous || 0) * 100) / 100,
          change: Math.round((data.cache_hit_rate?.change || 0) * 100) / 100
        }
      }
      
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to fetch metrics:', err)
    } finally {
      isLoading.value = false
    }
  }

  const fetchTimeline = async (days = 7, interval = 'hour') => {
    try {
      const data = await adminAPI.getPerformanceTimeline(days, interval)

      // Ensure we have valid timeline data
      if (data && data.timeline && Array.isArray(data.timeline)) {
        timeline.value = data.timeline

        // Only update chart data if we have valid timeline points
        if (timeline.value.length > 0) {
          updateChartData()
        } else {
          console.warn('Timeline array is empty')
          initializeChartData()
        }
      } else {
        console.warn('Invalid timeline data received:', data)
        timeline.value = []
        initializeChartData()
      }

    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to fetch timeline:', err)
      timeline.value = [] // Reset timeline on error
      initializeChartData()
    }
  }

  const fetchPercentiles = async () => {
    try {
      const data = await adminAPI.getResponseTimePercentiles(timeRange.value)
      // Backend may return { percentiles: { p50, p75, p90, p95, p99 }, sample_size } or just { p50, p95, p99 }
      const p = data?.percentiles ?? data ?? {}
      percentiles.value = {
        p50: Math.round(p.p50 ?? 0),
        p95: Math.round(p.p95 ?? 0),
        p99: Math.round(p.p99 ?? 0)
      }

    } catch (err) {
      console.error('Failed to fetch percentiles:', err)
    }
  }

  const updateChartData = () => {
    if (!timeline.value || timeline.value.length === 0) {
      initializeChartData() // Initialize with empty structure
      return
    }

    const labels = timeline.value.map(point => {
      // Check if point exists and has either timestamp or period field
      if (!point) {
        console.warn('Missing data point')
        return 'N/A'
      }

      // Backend returns 'period' field for some endpoints, 'timestamp' for others
      const dateStr = point.timestamp || point.period

      if (!dateStr) {
        console.warn('Missing timestamp/period in data point:', point)
        return 'N/A'
      }

      // Parse timestamp using robust date-fns helper
      const date = parseTimestamp(dateStr)

      // Check if date parsing was successful
      if (!date) {
        console.warn('Invalid date format:', dateStr)
        return dateStr // Return original string as fallback
      }

      // Format based on time range - build options conditionally
      const formatOptions = {
        month: 'short',
        day: 'numeric'
      }

      // Add hour for short time ranges only
      if (timeRange.value === '1h' || timeRange.value === '6h' || timeRange.value === '24h') {
        formatOptions.hour = '2-digit'
      }

      return date.toLocaleDateString('en-US', formatOptions)
    })

    const newChartData = {
      responseTime: {
        labels: [...labels],
        datasets: [{
          label: 'Response Time (ms)',
          data: timeline.value.map(point => Math.round(point.avg_response_time || 0)),
          borderColor: '#1976D2',
          backgroundColor: 'rgba(25, 118, 210, 0.1)',
          tension: 0.4,
          fill: false
        }]
      },
      throughput: {
        labels: [...labels],
        datasets: [{
          label: 'Queries/Day',
          data: timeline.value.map(point => point.query_count || 0),
          backgroundColor: '#4CAF50',
          borderColor: '#4CAF50',
          borderWidth: 1
        }]
      },
      errorRate: {
        labels: [...labels],
        datasets: [{
          label: 'Error Rate (%)',
          data: timeline.value.map(point => Math.round((point.error_rate || 0) * 100 * 100) / 100),
          borderColor: '#FF5252',
          backgroundColor: 'rgba(255, 82, 82, 0.1)',
          tension: 0.4,
          fill: false
        }]
      },
      cacheHitRate: {
        labels: [...labels],
        datasets: [{
          label: 'Cache Hit Rate (%)',
          data: timeline.value.map(point => Math.round((point.cache_hit_rate || 0) * 100 * 100) / 100),
          borderColor: '#FF9800',
          backgroundColor: 'rgba(255, 152, 0, 0.1)',
          tension: 0.4,
          fill: false
        }]
      }
    }
    
    // Force reactivity update
    chartData.value = newChartData
  }

  const calculatePercentiles = () => {
    if (timeline.value.length === 0) return

    const responseTimes = timeline.value
      .map(point => point.avg_response_time || 0)
      .filter(time => time > 0)
      .sort((a, b) => a - b)

    if (responseTimes.length === 0) return

    const getPercentile = (arr, percentile) => {
      const index = Math.ceil((percentile / 100) * arr.length) - 1
      return arr[Math.max(0, index)]
    }

    percentiles.value = {
      p50: Math.round(getPercentile(responseTimes, 50)),
      p95: Math.round(getPercentile(responseTimes, 95)),
      p99: Math.round(getPercentile(responseTimes, 99))
    }
  }

  const refreshData = async () => {
    // Set loading state
    isLoading.value = true
    error.value = null
    
    // Initialize chart data structure
    initializeChartData()
    
    const daysMap = {
      [TimeRanges.HOUR]: 0.04,
      [TimeRanges.SIX_HOURS]: 0.25,
      [TimeRanges.DAY]: 1,
      [TimeRanges.WEEK]: 7,
      [TimeRanges.MONTH]: 30
    }
    
    const days = daysMap[timeRange.value] || 7
    const interval = days <= 1 ? 'hour' : 'day'
    
    try {
      await Promise.all([
        fetchMetrics(),
        fetchTimeline(days, interval),
        fetchPercentiles()
      ])
    } catch (err) {
      console.error('Error refreshing performance data:', err)
      error.value = err
    } finally {
      isLoading.value = false
    }
  }

  const exportPerformanceReport = async () => {
    try {
      const blob = await adminAPI.exportPerformanceReport(timeRange.value)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `performance_report_${timeRange.value}_${new Date().toISOString().split('T')[0]}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to export report:', err)
      throw err
    }
  }

  const setTimeRange = async (newTimeRange) => {
    if (timeRange.value !== newTimeRange) {
      timeRange.value = newTimeRange
      await refreshData()
    }
  }

  const resetError = () => {
    error.value = null
  }

  // Access tenant store
  const tenantStore = useTenantStore()

  // Clear cached data when tenant changes
  const clearTenantData = () => {
    metrics.value = {
      responseTime: { current: 0, previous: 0, change: 0 },
      throughput: { current: 0, previous: 0, change: 0 },
      errorRate: { current: 0, previous: 0, change: 0 },
      cacheHitRate: { current: 0, previous: 0, change: 0 }
    }
    timeline.value = []
    percentiles.value = { p50: 0, p95: 0, p99: 0 }
    initializeChartData()
    error.value = null
    console.debug('Performance store: cleared tenant-specific data')
  }

  // Watch for tenant changes and clear cached data reactively
  watch(
    () => tenantStore.currentTenant?.id,
    (newTenantId, oldTenantId) => {
      if (oldTenantId && newTenantId && oldTenantId !== newTenantId) {
        console.debug(`Performance store: tenant changed from ${oldTenantId} to ${newTenantId}`)
        clearTenantData()
      }
    }
  )

  return {
    // State
    metrics,
    timeline,
    percentiles,
    chartData,
    isLoading,
    error,
    timeRange,

    // Getters
    hasData,
    averageResponseTime,
    totalQueries,
    peakThroughput,
    performanceScore,
    trendDirection,

    // Actions
    fetchMetrics,
    fetchTimeline,
    fetchPercentiles,
    updateChartData,
    calculatePercentiles,
    refreshData,
    exportPerformanceReport,
    setTimeRange,
    resetError,
    initializeChartData,
    clearTenantData
  }
})