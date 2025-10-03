import { defineStore } from 'pinia'
import { ref } from 'vue'
import { coreSettingsService } from '@/services/settings/coreSettingsService'

export const useCoreSettingsStore = defineStore('coreSettings', () => {
  const settings = ref({
    system_name: 'Nick Berens AI Assistant',
    version: '2.0',
    default_model: 'claude-3-sonnet',
    anthropic_api_key_configured: false,
    google_api_key_configured: false
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await coreSettingsService.getSettings()
      if (data && data.settings) {
        Object.assign(settings.value, data.settings)
      }
    } catch (err) {
      console.error('Failed to load core settings:', err)
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
      await coreSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update core settings:', err)
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