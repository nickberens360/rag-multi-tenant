<template>
  <div class="notifications-container">
    <v-snackbar
      v-for="n in notifications"
      :key="n.id"
      :model-value="true"
      :timeout="n.persistent ? -1 : n.timeout"
      :color="n.type"
      :scrim="false"
      :contained="true"
      :retain-focus="false"
      :close-on-back="false"
      location="top right"
      class="notification-item"
      @update:model-value="onUpdate(n.id, $event)"
    >
      <div class="d-flex align-center">
        <div class="mr-2">
          {{ n.message }}
        </div>
      </div>

      <template #actions>
        <v-btn
          v-if="n.actionLabel && typeof n.onAction === 'function'"
          variant="text"
          size="small"
          class="mr-1"
          @click="handleAction(n)"
        >
          {{ n.actionLabel }}
        </v-btn>
        <v-btn
          v-if="n.dismissible !== false"
          variant="text"
          size="small"
          @click="dismiss(n.id)"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'

const store = useNotificationsStore()
const { notifications } = storeToRefs(store)

const dismiss = (id) => store.dismiss(id)

const onUpdate = (id, show) => {
  // When v-snackbar auto-hides (show=false), remove from store
  if (!show) dismiss(id)
}

const handleAction = (n) => {
  try {
    if (typeof n.onAction === 'function') {
      n.onAction()
    }
  } finally {
    // Close after action by default
    dismiss(n.id)
  }
}
</script>

<style scoped>
.notifications-container {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 9999;
  pointer-events: none;
}

.notification-item {
  pointer-events: all;
  margin-top: 8px;
}
</style>
