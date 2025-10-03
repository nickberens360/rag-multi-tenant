import { defineStore } from 'pinia'
import { ref } from 'vue'
import { featureSettingsService } from '@/services/settings/featureSettingsService'

export const useFeatureSettingsStore = defineStore('featureSettings', () => {
  const featureFlags = ref({
    // Supported feature flags (FeatureFlags schema)
    enable_debug_mode: false,
    enable_maintenance_mode: false,
    enable_api_versioning: false,
    enable_illustrations: true,
    enable_geolocation: true,
    enable_query_preprocessing: true
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await featureSettingsService.getFeatureFlags()
      if (data) {
        Object.assign(featureFlags.value, data)
      }
    } catch (err) {
      console.error('Failed to load feature flags:', err)
      error.value = err.message || 'Failed to load feature flags'
    } finally {
      loading.value = false
    }
  }

  const updateFeatureFlags = async (updatedFlags = null) => {
    try {
      loading.value = true
      error.value = null
      const dataToSave = updatedFlags || featureFlags.value
      await featureSettingsService.updateFeatureFlags(dataToSave)
      if (updatedFlags) {
        Object.assign(featureFlags.value, updatedFlags)
      }
    } catch (err) {
      console.error('Failed to update feature flags:', err)
      error.value = err.message || 'Failed to update feature flags'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateFeatureFlag = (key, value) => {
    featureFlags.value[key] = value
  }

  const clearError = () => {
    error.value = null
  }

  return {
    featureFlags,
    loading,
    error,
    loadData,
    updateFeatureFlags,
    updateFeatureFlag,
    clearError
  }
})
