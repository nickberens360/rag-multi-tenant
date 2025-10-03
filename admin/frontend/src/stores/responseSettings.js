import { defineStore } from 'pinia'
import { ref } from 'vue'
import { responseSettingsService } from '@/services/settings/responseSettingsService'

export const useResponseSettingsStore = defineStore('responseSettings', () => {
  const settings = ref({
    max_context_length: 2000,
    max_context_documents: 3,
    context_fill_ratio: 0.7,
    enable_caching: true,
    cache_ttl_seconds: 3600
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await responseSettingsService.getSettings()
      if (data) {
        Object.assign(settings.value, data)
      }
    } catch (err) {
      console.error('Failed to load response settings:', err)
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
      await responseSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update response settings:', err)
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