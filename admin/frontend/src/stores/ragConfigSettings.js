import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import ragConfigService from '@/services/settings/ragConfigSettingsService'

export const useRagConfigStore = defineStore('ragConfigSettings', () => {
  // State
  const ragConfig = ref({
    // Feature Toggles (Boolean)
    rag_use_mmr: false,
    rag_use_heading_splitter: false,
    rag_enable_delete: false,
    rag_safe_delete: true,
    
    // Numeric Settings
    rag_score_threshold: 0.2,
    rag_mmr_k: 4,
    rag_mmr_fetch_k: 20,
    rag_mmr_lambda_mult: 0.5,
    
    // String Settings
    rag_index_dirs: 'backend/knowledge,public'
  })
  
  const loading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)

  // Computed
  const hasChanges = computed(() => {
    // This could be enhanced to track actual changes from original values
    return true
  })

  const isValidConfig = computed(() => {
    // Validate numeric ranges
    if (ragConfig.value.rag_score_threshold < 0.0 || ragConfig.value.rag_score_threshold > 1.0) {
      return false
    }
    
    if (ragConfig.value.rag_mmr_k < 1 || ragConfig.value.rag_mmr_k > 20) {
      return false
    }
    
    if (ragConfig.value.rag_mmr_fetch_k < 10 || ragConfig.value.rag_mmr_fetch_k > 100) {
      return false
    }
    
    if (ragConfig.value.rag_mmr_lambda_mult < 0.0 || ragConfig.value.rag_mmr_lambda_mult > 1.0) {
      return false
    }
    
    // Validate string settings
    if (!ragConfig.value.rag_index_dirs || ragConfig.value.rag_index_dirs.trim() === '') {
      return false
    }
    
    return true
  })

  // Actions
  const loadData = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await ragConfigService.getRagConfig()
      if (response.settings) {
        // Merge with defaults, ensuring all expected fields exist
        ragConfig.value = {
          ...ragConfig.value, // Default values
          ...response.settings  // Server values override defaults
        }
        lastUpdated.value = response.lastUpdated || new Date().toISOString()
      }
    } catch (err) {
      error.value = err.message || 'Failed to load RAG configuration'
      console.error('Error loading RAG configuration:', err)
    } finally {
      loading.value = false
    }
  }

  const updateRagConfig = async (newConfig = null) => {
    loading.value = true
    error.value = null
    
    try {
      const configToSave = newConfig || ragConfig.value
      
      // Validate before saving
      if (!isValidConfig.value) {
        throw new Error('Invalid configuration values')
      }
      
      const response = await ragConfigService.updateRagConfig(configToSave)
      
      if (response.settings) {
        ragConfig.value = response.settings
        lastUpdated.value = response.lastUpdated || new Date().toISOString()
      }
      
      return response
    } catch (err) {
      error.value = err.message || 'Failed to update RAG configuration'
      console.error('Error updating RAG configuration:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateSetting = async (key, value) => {
    if (!(key in ragConfig.value)) {
      throw new Error(`Unknown RAG setting: ${key}`)
    }
    
    // Update local state optimistically
    const oldValue = ragConfig.value[key]
    ragConfig.value[key] = value
    
    try {
      await updateRagConfig()
    } catch (err) {
      // Rollback on error
      ragConfig.value[key] = oldValue
      throw err
    }
  }

  const resetToDefaults = () => {
    ragConfig.value = {
      rag_use_mmr: false,
      rag_use_heading_splitter: false,
      rag_enable_delete: false,
      rag_safe_delete: true,
      rag_score_threshold: 0.2,
      rag_mmr_k: 4,
      rag_mmr_fetch_k: 20,
      rag_mmr_lambda_mult: 0.5,
      rag_index_dirs: 'backend/knowledge,public'
    }
  }

  const validateSetting = (key, value) => {
    switch (key) {
      case 'rag_score_threshold':
      case 'rag_mmr_lambda_mult':
        return typeof value === 'number' && value >= 0.0 && value <= 1.0
      
      case 'rag_mmr_k':
        return Number.isInteger(value) && value >= 1 && value <= 20
      
      case 'rag_mmr_fetch_k':
        return Number.isInteger(value) && value >= 10 && value <= 100
      
      case 'rag_use_mmr':
      case 'rag_use_heading_splitter':
      case 'rag_enable_delete':
      case 'rag_safe_delete':
        return typeof value === 'boolean'
      
      case 'rag_index_dirs':
        return typeof value === 'string' && value.trim().length > 0
      
      default:
        return false
    }
  }

  // Return store interface
  return {
    // State
    ragConfig,
    loading,
    error,
    lastUpdated,
    
    // Computed
    hasChanges,
    isValidConfig,
    
    // Actions
    loadData,
    updateRagConfig,
    updateSetting,
    resetToDefaults,
    validateSetting
  }
})