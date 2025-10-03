import { defineStore } from 'pinia'

// Simple ID generator
const genId = () => Math.random().toString(36).slice(2) + Date.now().toString(36)

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    notifications: [],
    maxStack: 5,
  }),
  actions: {
    notify(payload) {
      const id = genId()
      const item = {
        id,
        type: payload.type || 'info',
        message: payload.message || '',
        timeout: typeof payload.timeout === 'number' ? payload.timeout : (payload.type === 'error' ? 6000 : 4000),
        dismissible: payload.dismissible !== false,
        persistent: payload.persistent === true,
        actionLabel: payload.actionLabel,
        onAction: payload.onAction,
        meta: payload.meta || {},
      }

      // Push and trim stack
      this.notifications.push(item)
      if (this.notifications.length > this.maxStack) {
        this.notifications.shift()
      }
      return id
    },
    success(message, opts = {}) {
      return this.notify({ type: 'success', message, ...opts })
    },
    info(message, opts = {}) {
      return this.notify({ type: 'info', message, ...opts })
    },
    warning(message, opts = {}) {
      return this.notify({ type: 'warning', message, ...opts })
    },
    error(message, opts = {}) {
      return this.notify({ type: 'error', message, ...opts })
    },
    dismiss(id) {
      const idx = this.notifications.findIndex(n => n.id === id)
      if (idx !== -1) this.notifications.splice(idx, 1)
    },
    clear() {
      this.notifications = []
    },
    setMaxStack(n) {
      this.maxStack = Math.max(1, Number(n) || 5)
      if (this.notifications.length > this.maxStack) {
        this.notifications.splice(0, this.notifications.length - this.maxStack)
      }
    }
  }
})

