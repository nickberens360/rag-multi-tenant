import { ref } from 'vue'

export function useSettings(service, store) {
  const loading = ref(false)
  const error = ref(null)
  const success = ref(false)

  const save = async (data) => {
    try {
      loading.value = true
      error.value = null
      success.value = false
      
      await service.updateSettings(data)
      success.value = true
      
      // Optionally refresh store
      if (store?.loadData) {
        await store.loadData()
      }
    } catch (err) {
      console.error('Failed to save settings:', err)
      error.value = err.message || 'Failed to save settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const load = async () => {
    try {
      loading.value = true
      error.value = null
      
      if (store?.loadData) {
        await store.loadData()
      }
    } catch (err) {
      console.error('Failed to load settings:', err)
      error.value = err.message || 'Failed to load settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    error.value = null
    success.value = false
  }

  return {
    loading,
    error,
    success,
    save,
    load,
    reset
  }
}