import { storeToRefs } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'

// Backward-compatible composable that delegates to the global Pinia store
export function useNotifications() {
  const store = useNotificationsStore()
  const { notifications } = storeToRefs(store)

  const showSuccess = (message, duration = 4000) => store.success(message, { timeout: duration })
  const showError = (message, duration = 6000) => store.error(message, { timeout: duration })
  const showInfo = (message, duration = 4000) => store.info(message, { timeout: duration })
  const showWarning = (message, duration = 5000) => store.warning(message, { timeout: duration })

  const dismiss = (id) => store.dismiss(id)
  const clear = () => store.clear()

  return { notifications, showSuccess, showError, showInfo, showWarning, dismiss, clear }
}
