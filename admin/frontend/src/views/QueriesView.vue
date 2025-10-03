<template>
  <div class="queries-view">
    <QueryTable
      title="All Queries"
      @query-selected="handleQuerySelected"
    />
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useQueriesStore } from '@/stores/queries'
import { useTenantStore } from '@/stores/tenant'
import QueryTable from '@/components/QueryTable.vue'

console.log('🔵 QueriesView.vue script is executing!')

const queriesStore = useQueriesStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

const handleQuerySelected = (query) => {
  // Handle query selection
}

// Refresh queries when tenant changes
const refreshQueries = async () => {
  console.log('🔄 [QueriesView] Refreshing queries, currentTenant:', tenantStore.currentTenant)
  await queriesStore.fetchQueries()
}

onMounted(async () => {
  console.log('✅ [QueriesView] Component mounted, currentTenant:', tenantStore.currentTenant)
  await refreshQueries()
})

// Watch for tenant slug changes and refresh queries
// Use a computed getter to watch the slug specifically
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [QueriesView] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [QueriesView] Tenant slug changed, refreshing queries')
    refreshQueries()
  }
})
</script>

<style scoped>
.queries-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>