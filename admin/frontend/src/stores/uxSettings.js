import { defineStore } from 'pinia'
import { ref } from 'vue'
import { uxSettingsService } from '@/services/settings/uxSettingsService'

export const useUXSettingsStore = defineStore('uxSettings', () => {
  const settings = ref({
    enable_animations: true,
    theme_preference: 'auto',
    compact_mode: false,
    response_streaming: true,
    show_typing_indicators: true
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await uxSettingsService.getSettings()
      if (data && data.settings) {
        Object.assign(settings.value, data.settings)
      }
    } catch (err) {
      console.error('Failed to load UX settings:', err)
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
      await uxSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update UX settings:', err)
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