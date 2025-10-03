<template>
  <v-dialog
    v-model="dialog"
    max-width="640px"
    persistent
  >
    <v-card
      class="dialog-card"
      elevation="12"
      rounded="xl"
    >
      <v-card-title class="dialog-header pa-6">
        <div class="d-flex align-center">
          <v-avatar 
            size="48" 
            color="warning" 
            variant="tonal" 
            class="mr-4"
          >
            <v-icon size="24">
              $alert-triangle
            </v-icon>
          </v-avatar>
          <div class="flex-grow-1">
            <h2 class="text-h5 font-weight-bold mb-1">
              Delete Category
            </h2>
            <p class="text-body-2 text-medium-emphasis ma-0">
              {{ category?.display_name }} • {{ categoryStats?.question_count || 0 }} questions
            </p>
          </div>
          <v-chip
            :color="categoryStats?.question_count > 0 ? 'warning' : 'success'"
            variant="tonal"
            size="small"
          >
            {{ categoryStats?.question_count > 0 ? 'Has Questions' : 'Empty' }}
          </v-chip>
        </div>
      </v-card-title>

      <v-divider class="border-opacity-12" />

      <v-card-text class="pa-6">
        <!-- Category has questions - show options -->
        <div
          v-if="categoryStats?.question_count > 0"
          class="question-handling-section"
        >
          <v-card
            color="warning"
            variant="tonal" 
            class="mb-6"
            elevation="0"
            rounded="lg"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-center">
                <v-icon
                  color="warning"
                  class="mr-2"
                >
                  $information
                </v-icon>
                <span class="font-weight-medium">
                  This category contains <strong>{{ categoryStats.question_count }} questions</strong>. 
                  Choose how to handle them before deletion.
                </span>
              </div>
            </v-card-text>
          </v-card>

          <div class="strategy-section mb-6">
            <div class="section-title text-subtitle-1 font-weight-bold mb-4 d-flex align-center">
              <v-icon
                size="18"
                class="mr-2"
              >
                $tune
              </v-icon>
              Deletion Strategy
            </div>
            
            <v-radio-group
              v-model="deleteStrategy"
              class="strategy-options"
            >
              <!-- Move to another category -->
              <v-card 
                class="strategy-option mb-3" 
                :class="{ 'strategy-option--selected': deleteStrategy === 'move' }"
                elevation="0" 
                variant="outlined"
                rounded="lg"
              >
                <v-card-text class="pa-4">
                  <v-radio
                    value="move"
                    class="strategy-radio"
                  >
                    <template #label>
                      <div class="d-flex align-center">
                        <v-avatar
                          size="32"
                          color="info"
                          variant="tonal"
                          class="mr-3"
                        >
                          <v-icon size="16">
                            $chevron-right
                          </v-icon>
                        </v-avatar>
                        <div>
                          <div class="font-weight-bold text-body-1">
                            Move questions to another category
                          </div>
                          <div class="text-caption text-medium-emphasis">
                            Transfer all questions to a different category
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-radio>
                </v-card-text>
              </v-card>

              <!-- Delete all questions -->
              <v-card 
                class="strategy-option mb-3" 
                :class="{ 'strategy-option--selected': deleteStrategy === 'delete_all' }"
                elevation="0" 
                variant="outlined"
                rounded="lg"
              >
                <v-card-text class="pa-4">
                  <v-radio
                    value="delete_all"
                    class="strategy-radio"
                  >
                    <template #label>
                      <div class="d-flex align-center">
                        <v-avatar
                          size="32"
                          color="error"
                          variant="tonal"
                          class="mr-3"
                        >
                          <v-icon size="16">
                            $delete
                          </v-icon>
                        </v-avatar>
                        <div>
                          <div class="font-weight-bold text-body-1 text-error">
                            Delete all questions permanently
                          </div>
                          <div class="text-caption text-medium-emphasis">
                            ⚠️ This action cannot be undone
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-radio>
                </v-card-text>
              </v-card>

              <!-- Deactivate category -->
              <v-card 
                class="strategy-option mb-3" 
                :class="{ 'strategy-option--selected': deleteStrategy === 'deactivate' }"
                elevation="0" 
                variant="outlined"
                rounded="lg"
              >
                <v-card-text class="pa-4">
                  <v-radio
                    value="deactivate"
                    class="strategy-radio"
                  >
                    <template #label>
                      <div class="d-flex align-center">
                        <v-avatar
                          size="32"
                          color="warning"
                          variant="tonal"
                          class="mr-3"
                        >
                          <v-icon size="16">
                            $eye-off
                          </v-icon>
                        </v-avatar>
                        <div>
                          <div class="font-weight-bold text-body-1">
                            Deactivate instead of delete
                          </div>
                          <div class="text-caption text-medium-emphasis">
                            Hide the category but keep questions intact
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-radio>
                </v-card-text>
              </v-card>
            </v-radio-group>
          </div>

          <!-- Target category selection for move strategy -->
          <v-expand-transition>
            <div
              v-if="deleteStrategy === 'move'"
              class="target-selection-section mb-6"
            >
              <div class="section-title text-subtitle-2 font-weight-medium mb-3 d-flex align-center">
                <v-icon
                  size="16"
                  class="mr-2"
                >
                  $folder
                </v-icon>
                Select Target Category
              </div>
              <v-select
                v-model="targetCategoryId"
                :items="availableCategories.filter(c => c.id !== category?.id)"
                item-title="display_name"
                item-value="id"
                label="Move questions to"
                variant="outlined"
                density="comfortable"
                :rules="[v => !!v || 'Please select a target category']"
                prepend-inner-icon="$folder"
                rounded="lg"
                class="target-select"
              >
                <template #item="{ props, item }">
                  <v-list-item 
                    v-bind="props" 
                    class="target-category-item"
                    rounded="lg"
                  >
                    <template #prepend>
                      <v-avatar
                        size="32"
                        color="primary"
                        variant="tonal"
                      >
                        <v-icon size="16">
                          $folder
                        </v-icon>
                      </v-avatar>
                    </template>
                    <v-list-item-title class="font-weight-medium">
                      {{ item.raw.display_name }}
                    </v-list-item-title>
                    <v-list-item-subtitle>{{ item.raw.name }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-select>
            </div>
          </v-expand-transition>

          <!-- Confirmation for destructive operations -->
          <v-expand-transition>
            <div
              v-if="deleteStrategy === 'delete_all'"
              class="confirmation-section mb-6"
            >
              <v-card
                color="error"
                variant="tonal"
                elevation="0"
                rounded="lg"
              >
                <v-card-text class="pa-4">
                  <v-checkbox
                    v-model="confirmDestructive"
                    color="error"
                    class="confirmation-checkbox"
                  >
                    <template #label>
                      <span class="text-error font-weight-medium">
                        I understand this will permanently delete {{ categoryStats.question_count }} questions
                      </span>
                    </template>
                  </v-checkbox>
                </v-card-text>
              </v-card>
            </div>
          </v-expand-transition>
        </div>

        <!-- Category has no questions - simple deletion -->
        <div
          v-else
          class="empty-category-section"
        >
          <v-card
            color="success" 
            variant="tonal" 
            elevation="0" 
            rounded="lg"
            class="mb-4"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-center">
                <v-avatar
                  size="32"
                  color="success"
                  variant="tonal"
                  class="mr-3"
                >
                  <v-icon size="16">
                    $check-circle
                  </v-icon>
                </v-avatar>
                <div>
                  <div class="font-weight-medium">
                    Safe to delete
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    This category has no questions and can be safely deleted
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
          
          <p class="text-body-1 text-center text-medium-emphasis">
            The category "{{ category?.display_name }}" will be permanently removed from your system.
          </p>
        </div>

        <!-- Summary of action -->
        <v-card
          v-if="categoryStats?.question_count > 0"
          class="summary-card mt-6"
          elevation="1"
          rounded="lg"
          variant="tonal"
        >
          <v-card-text class="pa-4">
            <div class="d-flex align-center mb-3">
              <v-icon
                class="mr-2"
                size="18"
              >
                $format-list-bulleted
              </v-icon>
              <span class="text-subtitle-2 font-weight-bold">Action Summary</span>
            </div>
            <div class="summary-content text-body-2">
              <template v-if="deleteStrategy === 'move'">
                <div class="summary-item d-flex align-center mb-2">
                  <v-icon
                    size="16"
                    color="info"
                    class="mr-2"
                  >
                    $chevron-right
                  </v-icon>
                  Move {{ categoryStats.question_count }} questions to "{{ targetCategoryName }}"
                </div>
                <div class="summary-item d-flex align-center">
                  <v-icon
                    size="16"
                    color="warning"
                    class="mr-2"
                  >
                    $delete
                  </v-icon>
                  Delete category "{{ category?.display_name }}"
                </div>
              </template>
              <template v-else-if="deleteStrategy === 'delete_all'">
                <div class="summary-item d-flex align-center mb-2">
                  <v-icon
                    size="16"
                    color="error"
                    class="mr-2"
                  >
                    $delete
                  </v-icon>
                  <span class="text-error">Permanently delete {{ categoryStats.question_count }} questions</span>
                </div>
                <div class="summary-item d-flex align-center">
                  <v-icon
                    size="16"
                    color="error"
                    class="mr-2"
                  >
                    $delete
                  </v-icon>
                  <span class="text-error">Delete category "{{ category?.display_name }}"</span>
                </div>
              </template>
              <template v-else-if="deleteStrategy === 'deactivate'">
                <div class="summary-item d-flex align-center mb-2">
                  <v-icon
                    size="16"
                    color="warning"
                    class="mr-2"
                  >
                    $eye-off
                  </v-icon>
                  Deactivate category "{{ category?.display_name }}"
                </div>
                <div class="summary-item d-flex align-center mb-2">
                  <v-icon
                    size="16"
                    color="success"
                    class="mr-2"
                  >
                    $check-circle
                  </v-icon>
                  Keep all {{ categoryStats.question_count }} questions intact
                </div>
                <div class="summary-item d-flex align-center">
                  <v-icon
                    size="16"
                    color="info"
                    class="mr-2"
                  >
                    $eye-off
                  </v-icon>
                  Category will be hidden from question selection
                </div>
              </template>
            </div>
          </v-card-text>
        </v-card>
      </v-card-text>

      <v-divider class="border-opacity-12" />
      
      <v-card-actions class="dialog-actions pa-6">
        <v-spacer />
        <v-btn
          variant="outlined"
          size="large"
          :disabled="loading"
          class="mr-3"
          @click="cancel"
        >
          Cancel
        </v-btn>
        <v-btn
          :color="deleteStrategy === 'deactivate' ? 'warning' : 'error'"
          variant="elevated"
          size="large"
          :loading="loading"
          :disabled="!canProceed"
          :prepend-icon="deleteStrategy === 'deactivate' ? '$eye-off' : '$delete'"
          @click="confirmDelete"
        >
          <template v-if="deleteStrategy === 'deactivate'">
            Deactivate Category
          </template>
          <template v-else-if="categoryStats?.question_count > 0">
            {{ deleteStrategy === 'move' ? 'Move & Delete' : 'Delete All' }}
          </template>
          <template v-else>
            Delete Category
          </template>
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'CategoryDeleteDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    category: {
      type: Object,
      default: null
    },
    categoryStats: {
      type: Object,
      default: null
    },
    availableCategories: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'confirm', 'cancel'],
  setup(props, { emit }) {
    const deleteStrategy = ref('move')
    const targetCategoryId = ref(null)
    const confirmDestructive = ref(false)

    const dialog = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })

    const targetCategoryName = computed(() => {
      if (!targetCategoryId.value) return ''
      const target = props.availableCategories.find(c => c.id === targetCategoryId.value)
      return target?.display_name || ''
    })

    const canProceed = computed(() => {
      // No questions - can always proceed
      if (!props.categoryStats?.question_count) return Boolean(props.category?.id)
      if (!props.category?.id) return false
      
      // Strategy-specific validation
      switch (deleteStrategy.value) {
        case 'move':
          return Boolean(targetCategoryId.value) && targetCategoryId.value !== props.category.id
        case 'delete_all':
          return confirmDestructive.value
        case 'deactivate':
          return true
        default:
          return false
      }
    })

    // Reset form when dialog opens/closes
    watch(() => props.modelValue, (isOpen) => {
      if (isOpen) {
        // Reset to defaults
        deleteStrategy.value = 'move'
        targetCategoryId.value = null
        confirmDestructive.value = false
        
        // Auto-select first available category that isn't the current one
        const firstOther = props.availableCategories.find(c => c.id !== props.category?.id)
        targetCategoryId.value = firstOther ? firstOther.id : null
      }
    })

    const confirmDelete = () => {
      if (!canProceed.value) return
      if (!props.category?.id) {
        console.warn('CategoryDeleteDialog: missing category id')
        return
      }

      const deleteRequest = {
        categoryId: props.category.id,
        strategy: deleteStrategy.value,
        ...(deleteStrategy.value === 'move' && { targetCategoryId: targetCategoryId.value })
      }

      emit('confirm', deleteRequest)
    }

    const cancel = () => {
      emit('cancel')
      emit('update:modelValue', false)
    }

    return {
      deleteStrategy,
      targetCategoryId,
      confirmDestructive,
      dialog,
      targetCategoryName,
      canProceed,
      confirmDelete,
      cancel
    }
  }
}
</script>

<style scoped>
.dialog-card {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.dialog-header {
  background: linear-gradient(135deg, rgb(var(--v-theme-surface)) 0%, rgba(var(--v-theme-warning), 0.02) 100%);
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.question-handling-section {
  padding: 0;
}

.strategy-section {
  padding: 20px;
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-outline), 0.06);
}

.section-title {
  color: rgb(var(--v-theme-primary));
}

.strategy-options {
  margin-top: 0;
}

.strategy-option {
  transition: all 0.2s ease;
  cursor: pointer;
  border: 2px solid rgba(var(--v-theme-outline), 0.12);
}

.strategy-option:hover {
  border-color: rgba(var(--v-theme-primary), 0.3);
  box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.1);
}

.strategy-option--selected {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.02);
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.15);
}

.strategy-radio {
  width: 100%;
}

.target-selection-section {
  padding: 20px;
  background: rgba(var(--v-theme-info), 0.02);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-info), 0.1);
}

.target-select :deep(.v-field) {
  border-radius: 10px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.target-select :deep(.v-field:hover) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.target-select :deep(.v-field--focused) {
  box-shadow: 0 6px 16px rgba(var(--v-theme-primary), 0.15);
  outline: none !important;
}


.target-category-item {
  margin: 4px 8px;
  border-radius: 8px;
}

.confirmation-section {
  padding: 20px;
  background: rgba(var(--v-theme-error), 0.02);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-error), 0.1);
}

.confirmation-checkbox :deep(.v-selection-control__wrapper) {
  margin-right: 12px;
}

.empty-category-section {
  text-align: center;
  padding: 24px;
}

.summary-card {
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border: 1px solid rgba(var(--v-theme-outline), 0.12);
}

.summary-item {
  padding: 4px 0;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.summary-item:hover {
  background: rgba(var(--v-theme-surface-variant), 0.1);
}

.dialog-actions {
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-top: 1px solid rgba(var(--v-theme-outline), 0.08);
}

/* Radio styling */
:deep(.v-radio .v-selection-control__wrapper) {
  margin-right: 0;
}

:deep(.v-radio .v-label) {
  opacity: 1;
  width: 100%;
}

/* Animation */
.dialog-card {
  animation: dialogSlideIn 0.3s ease-out;
}

@keyframes dialogSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Mobile responsiveness */
@media (max-width: 600px) {
  .strategy-section,
  .target-selection-section,
  .confirmation-section {
    padding: 16px;
    margin: 0 -6px 16px -6px;
  }
  
  .dialog-header {
    padding: 20px !important;
  }
  
  .dialog-actions {
    padding: 20px !important;
  }
  
  .strategy-option {
    margin-bottom: 12px;
  }
  
  :deep(.v-btn) {
    min-width: 120px;
  }
}
</style>