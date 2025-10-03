import { defineStore } from 'pinia'
import { ref } from 'vue'
import { searchRetrievalSettingsService } from '@/services/settings/searchRetrievalSettingsService'

export const useSearchRetrievalSettingsStore = defineStore('searchRetrievalSettings', () => {
  const settings = ref({
    semantic_similarity_threshold: 0.7,
    max_search_results: 10,
    search_timeout_seconds: 30,
    enable_fuzzy_matching: true,
    enable_metadata_boosting: true
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await searchRetrievalSettingsService.getSettings()
      if (data && data.settings) {
        Object.assign(settings.value, data.settings)
      }
    } catch (err) {
      console.error('Failed to load search retrieval settings:', err)
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
      await searchRetrievalSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update search retrieval settings:', err)
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