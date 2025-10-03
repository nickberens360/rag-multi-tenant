<template>
  <div class="dashboard">
    <!-- Health Status -->
    <HealthStatusCard />
    <!-- Diagnostics Status -->
    <DiagnosticsCard />
    <!-- Metric Cards Grid -->
    <v-row class="ds-mb-6">
      <v-col
        v-for="metric in metrics"
        :key="metric.key"
        cols="12"
        sm="6"
        lg="3"
      >
        <MetricCard
          :title="metric.title"
          :value="metric.value"
          :unit="metric.unit"
          :icon="metric.icon"
          :color="metric.color"
          :loading="cardsLoading"
          clickable
          @click="handleMetricClick(metric)"
        />
      </v-col>
    </v-row>
    
    <!-- Charts Row -->
    <v-row class="ds-mb-6">
      <!-- Left Side: Response Time Chart -->
      <v-col
        cols="12"
        lg="8"
      >
        <PerformanceChart
          title="Response Time Timeline"
          :data="responseTimeChartData"
          :loading="isLoading || performanceLoading"
          type="line"
        />
      </v-col>
      
      <!-- Right Side: Donut Chart -->
      <v-col
        cols="12"
        lg="4"
      >
        <PerformanceChart
          title="Query Status Distribution"
          :data="statusChartData"
          :loading="isLoading"
          type="doughnut"
          :height="400"
        />
      </v-col>
    </v-row>
    
    <!-- Full Width Queries Table -->
    <v-row>
      <v-col cols="12">
        <QueryTable
          title="All Queries"
          @query-selected="handleQuerySelected"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { useQueriesStore } from '@/stores/queries'
import { usePerformanceStore } from '@/stores/performance'
import { useTenantStore } from '@/stores/tenant'
import MetricCard from '@/components/MetricCard.vue'
import HealthStatusCard from '@/components/HealthStatusCard.vue'
import DiagnosticsCard from '@/components/DiagnosticsCard.vue'
import PerformanceChart from '@/components/PerformanceChart.vue'
import QueryTable from '@/components/QueryTable.vue'

const router = useRouter()
const adminStore = useAdminStore()
const queriesStore = useQueriesStore()
const performanceStore = usePerformanceStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Computed properties - use storeToRefs for reactivity
const { stats, isLoading } = storeToRefs(adminStore)
const { chartData: performanceChartData, isLoading: performanceLoading } = storeToRefs(performanceStore)

// Computed property for loading state to ensure reactivity
const cardsLoading = computed(() => {
  // Force loading to false if we have stats data
  if (stats.value && stats.value.totalQueries !== undefined) {
    return false
  }
  return isLoading.value
})

const metrics = computed(() => {
  // Debug logging to see what data we're getting
  // Debug stats data (development only)
  // Stats validation and processing...
  
  return [
    {
      key: 'totalQueries',
      title: 'Total Queries',
      value: stats.value?.totalQueries || 0,
      icon: '$search',
      color: 'primary',
      change: stats.value?.totalQueriesChange ?? 0
    },
    {
      key: 'avgResponseTime',
      title: 'Avg Response Time',
      value: stats.value?.averageResponseTime || 0,
      unit: 'ms',
      icon: '$clock',
      color: 'info',
      change: stats.value?.averageResponseTimeChange ?? 0,
      inverse: true
    },
    {
      key: 'successRate',
      title: 'Success Rate',
      value: stats.value?.successRate || 0,
      unit: '%',
      icon: '$check',
      color: 'success',
      change: stats.value?.errorRateChange != null ? -stats.value.errorRateChange : 0,
      inverse: true
    },
    {
      key: 'activeSessions',
      title: 'Active Sessions',
      value: stats.value?.activeSessions || 0,
      icon: '$users',
      color: 'warning',
      change: stats.value?.uniqueSessionsChange ?? 0
    }
  ]
})

// Real-time response time chart data from performance store
const responseTimeChartData = computed(() => {
  return performanceChartData.value?.responseTime || {
    labels: [],
    datasets: [{
      label: 'Response Time (ms)',
      data: [],
      borderColor: '#1976D2',
      backgroundColor: 'rgba(25, 118, 210, 0.1)',
      tension: 0.4
    }]
  }
})

const statusChartData = computed(() => {
  // Use real data from stats if available
  const errorRate = stats.value?.errorRate || 0
  const successRate = 100 - errorRate
  
  return {
    labels: ['Success', 'Error'],
    datasets: [{
      data: [successRate, errorRate],
      backgroundColor: ['#4CAF50', '#FF5252'],
      borderWidth: 0,
      hoverBorderWidth: 3,
      hoverBorderColor: '#fff'
    }]
  }
})

// Methods
const handleMetricClick = (metric) => {
  const slug = currentTenant.value?.slug
  const p = (path) => (slug ? `/${slug}${path}` : path)
  // Navigate to relevant page based on metric
  switch (metric.key) {
    case 'totalQueries':
      router.push(p('/queries'))
      break
    case 'avgResponseTime':
    case 'successRate':
      router.push(p('/performance'))
      break
    case 'activeSessions':
      router.push(p('/sessions'))
      break
  }
}

const handleQuerySelected = (query) => {
  // Handle query selection
  // Could navigate to query details or show modal
}

// Refresh all dashboard data
const refreshDashboard = async () => {
  console.log('🔄 [DashboardView] Refreshing dashboard data, currentTenant:', currentTenant.value)
  await Promise.all([
    adminStore.fetchStats(),
    queriesStore.fetchQueries({ limit: 10 }),
    performanceStore.refreshData()
  ])
}

// Lifecycle
onMounted(async () => {
  console.log('✅ [DashboardView] Component mounted, currentTenant:', currentTenant.value)
  await refreshDashboard()
})

// Watch for tenant changes and refresh dashboard
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [DashboardView] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [DashboardView] Tenant slug changed, refreshing dashboard')
    refreshDashboard()
  }
})

onUnmounted(() => {
  // Cleanup if needed
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
