<template>
  <v-card
    class="mb-6"
    variant="tonal"
  >
    <v-card-title class="d-flex align-center">
      <v-icon
        class="mr-2"
        :color="overallColor"
      >
        $tune
      </v-icon>
      Diagnostics
      <v-spacer />
      <v-btn
        size="small"
        variant="text"
        @click="$router.push((() => { const slug = $pinia.state.value.tenant?.currentTenant?.slug; return slug ? `/${slug}/settings/features` : '/settings/features' })())"
      >
        Open Feature Flags
      </v-btn>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div class="d-flex flex-wrap ga-4 align-center">
        <v-chip
          :color="configColor"
          variant="flat"
          size="small"
        >
          Config: {{ envConfigured }}/{{ envTotal }} env-only
        </v-chip>
        <v-chip
          :color="validationColor"
          variant="flat"
          size="small"
        >
          Validation: {{ validationStatus || 'unknown' }}
        </v-chip>
        <v-chip
          :color="criticalColor"
          variant="flat"
          size="small"
        >
          Critical: {{ criticalStatus || 'unknown' }}
        </v-chip>
        <span
          v-if="lastUpdated"
          class="text-caption"
        >
          Updated {{ lastUpdated }}
        </span>
      </div>
      <!-- Missing env-only keys preview -->
      <div
        v-if="missingEnvKeys?.length"
        class="mt-3"
      >
        <div class="text-caption text-medium-emphasis mb-1">
          Missing env-only keys:
        </div>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="(key, idx) in limitedMissing"
            :key="key"
            size="x-small"
            color="error"
            variant="outlined"
          >
            {{ key }}
          </v-chip>
          <v-chip
            v-if="missingOverflowCount > 0"
            size="x-small"
            variant="text"
          >
            +{{ missingOverflowCount }} more
          </v-chip>
        </div>
      </div>
      <div
        v-if="error"
        class="mt-3 text-error text-caption"
      >
        {{ error }}
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import adminAPI from '@/services/api'
import { useFeatureSettingsStore } from '@/stores/featureSettings'

const envConfigured = ref(0)
const envTotal = ref(0)
const missingEnvKeys = ref([])
const validationStatus = ref(null)
const criticalStatus = ref(null)
const error = ref(null)
const lastUpdated = ref('')

const featureStore = useFeatureSettingsStore()
const diagnosticsEnabled = computed(() => Boolean(featureStore?.featureFlags?.enable_admin_diagnostics))

const fetchDiagnostics = async () => {
  error.value = null
  try {
    // Ensure feature flags are loaded so we can respect the diagnostics toggle
    try {
      await featureStore.loadData()
    } catch (e) {
      // Non-fatal for this card; continue with safe default behavior
      console.warn('Feature flags load failed:', e?.message || e)
    }

    if (!diagnosticsEnabled.value) {
      error.value = 'Diagnostics are disabled. Enable in Feature Flags to view.'
      return
    }

    const [configStatus, validation, critical] = await Promise.all([
      // Be defensive: swallow 404s so the card degrades gracefully when routes are absent
      adminAPI.getDiagnosticsConfigStatus().catch(err => {
        console.warn('Config status endpoint unavailable:', err.message)
        return {}
      }),
      adminAPI.getDiagnosticsValidation().catch(err => {
        console.warn('Validation endpoint unavailable:', err.message)
        return {}
      }),
      adminAPI.getDiagnosticsCriticalCheck().catch(err => {
        console.warn('Critical check endpoint unavailable:', err.message)
        return {}
      })
    ])

    // Config status
    if (configStatus?.env_only) {
      const statusObj = configStatus.env_only
      const entries = Object.entries(statusObj)
      envTotal.value = entries.length
      envConfigured.value = entries.filter(([, setting]) => setting && setting.present).length
      missingEnvKeys.value = entries.filter(([, setting]) => !(setting && setting.present)).map(([key]) => key).sort()
    } else if (configStatus?.summary) {
      // Fallback if backend returns summary only
      envTotal.value = configStatus.summary.total || 0
      envConfigured.value = configStatus.summary.configured || 0
      if (Array.isArray(configStatus.summary.missing_keys)) {
        missingEnvKeys.value = configStatus.summary.missing_keys
      }
    }

    // Validation
    if (validation?.validation_results) {
      validationStatus.value = validation.validation_results.overall_status || 'ok'
    }

    // Critical
    if (critical?.status) {
      criticalStatus.value = critical.status
    }

    lastUpdated.value = new Date().toLocaleString()
  } catch (e) {
    console.error('Diagnostics fetch failed:', e)
    error.value = 'Failed to load diagnostics'
  }
}

onMounted(fetchDiagnostics)

const configColor = computed(() => {
  if (!envTotal.value) return 'info'
  const pct = (envConfigured.value / envTotal.value) * 100
  if (pct >= 90) return 'success'
  if (pct >= 60) return 'warning'
  return 'error'
})

const validationColor = computed(() => {
  const s = (validationStatus.value || '').toLowerCase()
  if (s.includes('ok') || s.includes('pass')) return 'success'
  if (s.includes('warning')) return 'warning'
  if (s) return 'error'
  return 'info'
})

const criticalColor = computed(() => {
  const s = (criticalStatus.value || '').toLowerCase()
  if (s === 'healthy') return 'success'
  if (s === 'warning') return 'warning'
  if (s === 'critical' || s === 'error') return 'error'
  return 'info'
})

const overallColor = computed(() => {
  // Favor the worst of the three to highlight issues
  const colors = new Set([configColor.value, validationColor.value, criticalColor.value])
  if (colors.has('error')) return 'error'
  if (colors.has('warning')) return 'warning'
  if (colors.has('success')) return 'success'
  return 'info'
})

// Limit missing env-only keys preview in the card to keep UI compact
// Shows first 8 keys with overflow indicator for better UX
const MISSING_PREVIEW_LIMIT = 8
const limitedMissing = computed(() => missingEnvKeys.value.slice(0, MISSING_PREVIEW_LIMIT))
const missingOverflowCount = computed(() => Math.max(0, (missingEnvKeys.value.length || 0) - MISSING_PREVIEW_LIMIT))
</script>

<style scoped>
.mb-6 { margin-bottom: 24px; }
</style>
