<template>
  <div class="page-header mb-6">
    <div class="d-flex align-center justify-space-between">
      <div>
        <h1 class="page-title text-h4 font-weight-bold mb-2">
          Knowledge Base
        </h1>
        <p class="page-subtitle text-body-1 text-medium-emphasis">
          Manage sources, documents, and consistency of the knowledge base
        </p>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          color="primary"
          prepend-icon="$refresh"
          :loading="refreshLoading"
          variant="elevated"
          @click="$emit('refresh')"
        >
          Refresh
        </v-btn>
        <v-btn
          color="warning"
          prepend-icon="$refresh"
          :loading="reindexLoading"
          variant="elevated"
          @click="$emit('reindex')"
        >
          Re-Index
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  refreshLoading: { type: Boolean, default: false },
  reindexLoading: { type: Boolean, default: false },
})
defineEmits(['refresh', 'reindex'])
</script>

<style scoped>
.page-header {
  background: transparent;
}
.page-title { color: rgb(var(--v-theme-on-surface)); }
.gap-2 { gap: 8px; }
</style>

