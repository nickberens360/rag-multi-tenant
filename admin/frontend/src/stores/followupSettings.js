import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useTenantStore } from '@/stores/tenant'
import { followupSettingsService } from '@/services/settings/followupSettingsService'

export const useFollowupSettingsStore = defineStore('followupSettings', () => {
  // State
  const settings = ref({
    enabled: true,
    service_type: 'static',
    max_questions: 3,
    include_technical: true,
    include_personal: true,
    include_creative: true
  })
  
  const categories = ref([])
  const categoryStats = ref({})
  const expandedPanels = ref([])
  const selectedCategories = ref([])
  const selectedQuestions = ref({})
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const stats = computed(() => ({
    active_categories: categories.value.filter(c => c.is_active).length,
    inactive_categories: categories.value.filter(c => !c.is_active).length,
    total_questions: Object.values(categoryStats.value)
      .reduce((sum, stat) => sum + (stat.question_count || 0), 0)
  }))

  const availableCategoriesForMove = computed(() => 
    categories.value.filter(c => c.is_active)
  )

  const serviceTypeOptions = ref([
    { title: 'Static (Sequential)', value: 'static' },
    { title: 'Dynamic (Context-aware)', value: 'dynamic' },
    { title: 'Contextual (AI-powered)', value: 'contextual' }
  ])

  // Actions
  const loadData = async () => {
    try {
      loading.value = true
      error.value = null

      const [settingsData, categoriesData] = await Promise.all([
        followupSettingsService.getSettings(),
        followupSettingsService.getCategories()
      ])

      if (settingsData && typeof settingsData === 'object') {
        Object.assign(settings.value, settingsData)
      }
      categories.value = categoriesData || []

      // Load stats for each category
      const statsPromises = categories.value.map(async (category) => {
        try {
          const stats = await followupSettingsService.getCategoryStats(category.id)
          categoryStats.value[category.id] = stats
        } catch (err) {
          console.warn(`Failed to load stats for category ${category.id}:`, err)
          categoryStats.value[category.id] = { question_count: 0 }
        }
      })

      await Promise.all(statsPromises)

      // Clean up expanded panels for non-existent categories
      const categoryIds = categories.value.map(c => c.id)
      expandedPanels.value = expandedPanels.value.filter(id => categoryIds.includes(id))

    } catch (err) {
      console.error('Failed to load followup settings data:', err)
      error.value = err.message || 'Failed to load data'
    } finally {
      loading.value = false
    }
  }

  const updateSetting = async (key, value) => {
    try {
      settings.value[key] = value
      await followupSettingsService.updateSettings(settings.value)
    } catch (err) {
      console.error('Failed to update setting:', err)
      error.value = err.message || 'Failed to update setting'
      throw err
    }
  }

  const saveSettings = async () => {
    try {
      loading.value = true
      await followupSettingsService.updateSettings(settings.value)
    } catch (err) {
      console.error('Failed to save settings:', err)
      error.value = err.message || 'Failed to save settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const createCategory = async (categoryData) => {
    try {
      loading.value = true
      await followupSettingsService.createCategory(categoryData)
      await loadData() // Refresh data
    } catch (err) {
      console.error('Failed to create category:', err)
      error.value = err.message || 'Failed to create category'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateCategory = async (categoryId, categoryData) => {
    try {
      loading.value = true
      await followupSettingsService.updateCategory(categoryId, categoryData)
      await loadData() // Refresh data
    } catch (err) {
      console.error('Failed to update category:', err)
      error.value = err.message || 'Failed to update category'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteCategory = async (deleteRequest) => {
    try {
      loading.value = true
      await followupSettingsService.deleteCategory(deleteRequest)
      await loadData() // Refresh data
    } catch (err) {
      console.error('Failed to delete category:', err)
      error.value = err.message || 'Failed to delete category'
      throw err
    } finally {
      loading.value = false
    }
  }

  const bulkActivateCategories = async (categories) => {
    try {
      loading.value = true
      const operations = categories.map(cat => ({
        id: cat.id,
        data: { is_active: true }
      }))
      await followupSettingsService.bulkUpdateCategories(operations)
      selectedCategories.value = []
      await loadData()
    } catch (err) {
      console.error('Failed to bulk activate categories:', err)
      error.value = err.message || 'Failed to activate categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  const bulkDeactivateCategories = async (categories) => {
    try {
      loading.value = true
      const operations = categories.map(cat => ({
        id: cat.id,
        data: { is_active: false }
      }))
      await followupSettingsService.bulkUpdateCategories(operations)
      selectedCategories.value = []
      await loadData()
    } catch (err) {
      console.error('Failed to bulk deactivate categories:', err)
      error.value = err.message || 'Failed to deactivate categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  const bulkDeleteCategories = async (categories) => {
    try {
      loading.value = true
      const deletePromises = categories.map(cat =>
        followupSettingsService.deleteCategory({
          categoryId: cat.id,
          strategy: 'delete'
        })
      )
      await Promise.all(deletePromises)
      selectedCategories.value = []
      await loadData()
    } catch (err) {
      console.error('Failed to bulk delete categories:', err)
      error.value = err.message || 'Failed to delete categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateSelectedCategories = (newSelection) => {
    selectedCategories.value = newSelection
  }

  const updateExpandedPanels = (newPanels) => {
    expandedPanels.value = newPanels
  }

  const updateQuestionSelection = (categoryId, questions) => {
    selectedQuestions.value[categoryId] = questions
  }

  const clearError = () => {
    error.value = null
  }

  // Clear store data when tenant changes to avoid cross-tenant bleed
  const clearTenantData = () => {
    categories.value = []
    categoryStats.value = {}
    expandedPanels.value = []
    selectedCategories.value = []
    selectedQuestions.value = {}
    error.value = null
  }

  const tenantStore = useTenantStore()
  watch(
    () => tenantStore.currentTenant?.id,
    (newId, oldId) => {
      if (oldId && newId && oldId !== newId) {
        clearTenantData()
      }
    }
  )

  return {
    // State
    settings,
    categories,
    categoryStats,
    expandedPanels,
    selectedCategories,
    selectedQuestions,
    loading,
    error,
    serviceTypeOptions,
    
    // Computed
    stats,
    availableCategoriesForMove,
    
    // Actions
    loadData,
    updateSetting,
    saveSettings,
    createCategory,
    updateCategory,
    deleteCategory,
    bulkActivateCategories,
    bulkDeactivateCategories,
    bulkDeleteCategories,
    updateSelectedCategories,
    updateExpandedPanels,
    updateQuestionSelection,
    clearError,
    clearTenantData
  }
})
