import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemSettingsService } from '@/services/settings/systemSettingsService'

export const useSystemSettingsStore = defineStore('systemSettings', () => {
  const settings = ref({
    app_name: 'Nick Berens AI Assistant',
    app_version: '2.0.0',
    api_base_url: import.meta.env.VITE_API_BASE_URL || '/api/admin',
    enable_debug_mode: false,
    enable_maintenance_mode: false,
    admin_contact_email: 'admin@nickberens.com',
    session_timeout: 3600,
    max_concurrent_sessions: 10
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await systemSettingsService.getSettings()
      if (data) {
        Object.assign(settings.value, data)
      }
    } catch (err) {
      console.error('Failed to load system settings:', err)
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
      await systemSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update system settings:', err)
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