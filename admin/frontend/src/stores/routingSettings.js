import { defineStore } from 'pinia'
import { ref } from 'vue'
import { routingSettingsService } from '@/services/settings/routingSettingsService'

export const useRoutingSettingsStore = defineStore('routingSettings', () => {
  const settings = ref({
    enable_smart_routing: true,
    similarity_threshold: 0.3,
    max_search_results: 15,
    enable_fuzzy_matching: true,
    fuzzy_threshold: 0.7
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await routingSettingsService.getSettings()
      if (data) {
        Object.assign(settings.value, data)
      }
    } catch (err) {
      console.error('Failed to load routing settings:', err)
      error.value = err.message || 'Failed to load settings'
    } finally {
      loading.value = false
    }
  }

  const updateSettings = async (newSettings = null) => {
    try {
      loading.value = true
      error.value = null
      const dataToSave = newSettings || settings.value
      await routingSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update routing settings:', err)
      error.value = err.message || 'Failed to update settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateSetting = (key, value) => {
    settings.value[key] = value
  }

  const clearError = () => {
    error.value = null
  }

  return {
    settings,
    loading,
    error,
    loadData,
    updateSettings,
    updateSetting,
    clearError
  }
})