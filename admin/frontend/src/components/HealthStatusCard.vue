<template>
  <v-card
    class="mb-6"
    variant="tonal"
  >
    <v-card-title class="d-flex align-center">
      <v-icon
        :color="apiStatusColor"
        class="mr-2"
      >
        $dashboard
      </v-icon>
      System Health
      <v-spacer />
      <v-chip
        :color="apiStatusColor"
        size="small"
        class="mr-2"
        variant="flat"
      >
        API: {{ apiStatusLabel }}
      </v-chip>
      <v-chip
        :color="dbStatusColor"
        size="small"
        variant="flat"
      >
        DB: {{ dbStatusLabel }}
      </v-chip>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div class="d-flex flex-wrap align-center ga-4">
        <div class="d-flex align-center ga-2">
          <v-icon
            size="small"
            :color="apiStatusColor"
          >
            $web
          </v-icon>
          <span class="text-caption">API Base: {{ apiBase }}</span>
        </div>
        <div class="d-flex align-center ga-2">
          <v-icon
            size="small"
            :color="dbStatusColor"
          >
            $database
          </v-icon>
          <span class="text-caption">Status: {{ systemHealth.status || 'unknown' }}</span>
        </div>
        <div class="d-flex align-center ga-2">
          <v-icon size="small">
            $clock
          </v-icon>
          <span class="text-caption">Updated: {{ lastUpdated }}</span>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

const systemHealth = computed(() => adminStore.systemHealth || {})

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/admin'

const apiStatusColor = computed(() => (adminStore.isConnected ? 'success' : 'warning'))
const apiStatusLabel = computed(() => (adminStore.isConnected ? 'online' : 'connecting'))

const dbStatusColor = computed(() => {
  const status = (systemHealth.value.status || '').toLowerCase()
  if (status === 'healthy') return 'success'
  if (status === 'initializing' || status === 'degraded') return 'warning'
  if (status === 'error') return 'error'
  return 'info'
})
const dbStatusLabel = computed(() => (systemHealth.value.status || 'unknown'))

const lastUpdated = computed(() => {
  const ts = systemHealth.value.lastUpdated || systemHealth.value.timestamp
  if (!ts) return 'just now'
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch {
    return String(ts)
  }
})
</script>

<style scoped>
.mb-6 { margin-bottom: 24px; }
</style>
