<template>
  <div class="performance-view">
    <v-row class="mb-6">
      <v-col
        v-for="metric in performanceMetrics"
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
          :loading="isLoading"
        />
      </v-col>
    </v-row>
    
    <v-row>
      <v-col
        cols="12"
        lg="8"
      >
        <PerformanceChart
          title="Response Time Timeline"
          :data="responseTimeData"
          :loading="isLoading"
          type="line"
        />
      </v-col>
      
      <v-col
        cols="12"
        lg="4"
      >
        <PerformanceChart
          title="Throughput"
          :data="throughputData"
          :loading="isLoading"
          type="bar"
          :height="400"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onActivated, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { usePerformanceStore } from '@/stores/performance'
import { useTenantStore } from '@/stores/tenant'
import MetricCard from '@/components/MetricCard.vue'
import PerformanceChart from '@/components/PerformanceChart.vue'

const performanceStore = usePerformanceStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Use storeToRefs for proper reactivity like the dashboard does
const { metrics, chartData, isLoading } = storeToRefs(performanceStore)

const performanceMetrics = computed(() => {
  if (!metrics.value) {
    return []
  }
  
  return [
    {
      key: 'responseTime',
      title: 'Avg Response Time',
      value: metrics.value?.responseTime?.current || 0,
      unit: 'ms',
      icon: '$clock',
      color: 'primary',
      change: metrics.value?.responseTime?.change || 0,
      inverse: true
    },
    {
      key: 'throughput',
      title: 'Throughput',
      value: metrics.value?.throughput?.current || 0,
      unit: '/hr',
      icon: '$trendUp',
      color: 'success',
      change: metrics.value?.throughput?.change || 0
    },
    {
      key: 'errorRate',
      title: 'Error Rate',
      value: metrics.value?.errorRate?.current || 0,
      unit: '%',
      icon: '$alert',
      color: 'error',
      change: metrics.value?.errorRate?.change || 0,
      inverse: true
    },
    {
      key: 'cacheHitRate',
      title: 'Cache Hit Rate',
      value: metrics.value?.cacheHitRate?.current || 0,
      unit: '%',
      icon: '$check',
      color: 'info',
      change: metrics.value?.cacheHitRate?.change || 0
    }
  ]
})

// Chart data computed properties with fallbacks like dashboard
const responseTimeData = computed(() => {
  return chartData.value?.responseTime || { 
    labels: [], 
    datasets: [] 
  }
})

const throughputData = computed(() => {
  return chartData.value?.throughput || {
    labels: [],
    datasets: []
  }
})

// Refresh performance data
const refreshPerformance = async () => {
  console.log('🔄 [PerformanceView] Refreshing performance data, currentTenant:', currentTenant.value)
  await performanceStore.refreshData()
}

onMounted(async () => {
  console.log('✅ [PerformanceView] Component mounted, currentTenant:', currentTenant.value)
  await refreshPerformance()
})

// Watch for tenant changes and refresh performance data
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [PerformanceView] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [PerformanceView] Tenant slug changed, refreshing performance')
    refreshPerformance()
  }
})
</script>

<style scoped>
.performance-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>