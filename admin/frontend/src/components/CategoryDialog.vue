<template>
  <v-dialog
    v-model="dialog"
    max-width="560px"
    persistent
  >
    <v-card class="ds-card dialog-card">
      <v-card-title class="dialog-header ds-p-6">
        <div class="d-flex align-center">
          <v-avatar
            size="40"
            :color="isEdit ? 'info' : 'primary'"
            variant="tonal"
            class="mr-4"
          >
            <v-icon size="20">
              {{ isEdit ? '$edit' : '$plus' }}
            </v-icon>
          </v-avatar>
          <div>
            <h2 class="ds-text-2xl ds-font-bold ds-mb-1">
              {{ isEdit ? 'Edit Category' : 'New Category' }}
            </h2>
            <p class="ds-text-sm text-medium-emphasis ma-0">
              {{ isEdit ? 'Update category settings and configuration' : 'Create a new question category' }}
            </p>
          </div>
        </div>
      </v-card-title>

      <v-divider class="border-opacity-12" />

      <v-card-text class="ds-p-6">
        <v-form
          ref="form"
          v-model="valid"
          class="form-container"
        >
          <div class="form-section ds-mb-6">
            <div class="form-section-title ds-text-base ds-font-semibold ds-mb-4 d-flex align-center">
              <v-icon
                size="18"
                class="mr-2"
              >
                $info
              </v-icon>
              Basic Information
            </div>
            <v-text-field
              v-model="categoryData.display_name"
              label="Display Name"
              :rules="[
                v => !!v || 'Display name is required',
                v => (v && v.length >= 2) || 'Display name must be at least 2 characters',
                v => (v && v.length <= 100) || 'Display name must be 100 characters or less'
              ]"
              variant="outlined"
              density="comfortable"
              maxlength="100"
              counter
              required
              hint="This will be shown in the user interface"
              persistent-hint
              class="ds-ds-mb-4"
            />

            <v-text-field
              v-model="categoryData.name"
              label="Category Name"
              :rules="[
                v => !!v || 'Name is required',
                v => (v && v.length >= 2) || 'Name must be at least 2 characters',
                v => (v && v.length <= 50) || 'Name must be 50 characters or less',
                v => /^[a-z_][a-z0-9_]*$/.test(v) || 'Name must start with lowercase letter or underscore, and contain only lowercase letters, numbers, and underscores'
              ]"
              variant="outlined"
              density="comfortable"
              maxlength="50"
              counter
              required
              hint="Auto-generated snake_case format (e.g., technical_questions)"
              persistent-hint
              class="ds-ds-mb-4"
              :readonly="!isEdit"
              :class="{ 'auto-generated-field': !isEdit }"
            />

            <v-textarea
              v-model="categoryData.description"
              label="Description"
              :rules="[
                v => !v || v.length <= 500 || 'Description must be 500 characters or less'
              ]"
              variant="outlined"
              density="comfortable"
              maxlength="500"
              counter
              rows="3"
              hint="Optional description for this category"
              persistent-hint
            />
          </div>

          <div class="form-section ds-mb-6">
            <div class="form-section-title ds-text-base ds-font-semibold ds-mb-4 d-flex align-center">
              <v-icon
                size="18"
                class="mr-2"
              >
                $settings
              </v-icon>
              Configuration
            </div>
            <v-row>
              <v-col
                cols="12"
                md="6"
              >
                <v-text-field
                  v-model.number="categoryData.sort_order"
                  label="Sort Order"
                  type="number"
                  :rules="[
                    v => v >= 0 || 'Sort order must be 0 or greater',
                    v => v <= 999 || 'Sort order must be 999 or less'
                  ]"
                  variant="outlined"
                  density="comfortable"
                  hint="Lower numbers appear first (0-999)"
                  persistent-hint
                />
              </v-col>
              <v-col
                cols="12"
                md="6"
              >
                <div class="setting-group">
                  <div class="setting-label ds-text-sm ds-font-medium ds-mb-3 d-flex align-center">
                    <v-icon
                      size="16"
                      class="mr-2"
                    >
                      $toggle-switch
                    </v-icon>
                    Category Status
                  </div>
                  <v-switch
                    v-model="categoryData.is_active"
                    :label="categoryData.is_active ? 'Active' : 'Inactive'"
                    color="primary"
                    inset
                    hide-details
                  >
                    <template #append>
                      <v-tooltip
                        activator="parent"
                        location="top"
                      >
                        Inactive categories won't appear in the question selection interface
                      </v-tooltip>
                    </template>
                  </v-switch>
                </div>
              </v-col>
            </v-row>
          </div>
        </v-form>
      </v-card-text>

      <v-divider class="border-opacity-12" />

      <v-card-actions class="dialog-actions ds-p-6">
        <v-spacer />
        <v-btn
          class="ds-btn mr-3"
          variant="outlined"
          size="large"
          :disabled="loading"
          @click="cancel"
        >
          Cancel
        </v-btn>
        <v-btn
          class="ds-btn"
          color="primary"
          variant="elevated"
          size="large"
          :loading="loading"
          :disabled="!valid"
          :prepend-icon="isEdit ? '$check-circle' : '$plus'"
          @click="save"
        >
          {{ isEdit ? 'Update Category' : 'Create Category' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'CategoryDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    category: {
      type: Object,
      default: null
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'save', 'cancel'],
  setup(props, { emit }) {
    const form = ref(null)
    const valid = ref(false)

    const categoryData = ref({
      name: '',
      display_name: '',
      description: '',
      icon: 'help-circle',
      sort_order: 0,
      is_active: true
    })

    const dialog = computed({
      get: () => {
        return props.modelValue
      },
      set: (value) => {
        emit('update:modelValue', value)
      }
    })

    // Watch for modelValue changes
    watch(() => props.modelValue, (newValue) => {
      // Dialog visibility changed
    }, { immediate: true })

    const isEdit = computed(() => props.category && props.category.id)

    // Watch for category prop changes to populate form
    watch(() => props.category, (newCategory) => {
      if (newCategory) {
        categoryData.value = {
          name: newCategory.name || '',
          display_name: newCategory.display_name || '',
          description: newCategory.description || '',
          icon: newCategory.icon || 'help-circle',
          sort_order: newCategory.sort_order || 0,
          is_active: newCategory.is_active !== undefined ? newCategory.is_active : true
        }
      } else {
        // Reset for new category
        categoryData.value = {
          name: '',
          display_name: '',
          description: '',
          icon: 'help-circle',
          sort_order: 0,
          is_active: true
        }
      }
    }, { immediate: true })

    // Auto-generate name from display_name in create mode
    watch(() => categoryData.value.display_name, (newDisplayName) => {
      if (!isEdit.value && newDisplayName) {
        const snakeCase = newDisplayName
          .toLowerCase()
          .replace(/[^\w\s]/g, '')
          .replace(/\s+/g, '_')
          .replace(/^(\d)/, '_$1')
          .replace(/_+/g, '_')
          .replace(/^_|_$/g, '')
        categoryData.value.name = snakeCase
      }
    })

    const save = async () => {
      if (!form.value) return

      const validation = await form.value.validate()
      if (!validation.valid) return

      let saveData = {
        ...categoryData.value,
        // Include ID for edit operations
        ...(isEdit.value && { id: props.category.id })
      }

      // Remove is_active for create requests (not in CreateFollowupCategoryRequest model)
      if (!isEdit.value) {
        const { is_active, ...createData } = saveData
        saveData = createData
      }

      emit('save', saveData)
    }

    const cancel = () => {
      // Only emit cancel event - let parent handle the model update
      emit('cancel')
    }

    return {
      form,
      valid,
      categoryData,
      dialog,
      isEdit,
      save,
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
  background: linear-gradient(135deg, rgb(var(--v-theme-surface)) 0%, rgba(var(--v-theme-primary), 0.02) 100%);
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.form-container {
  background: rgb(var(--v-theme-surface));
}

.form-section {
  padding: 20px;
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-outline), 0.06);
}

.form-section-title {
  color: rgb(var(--v-theme-primary));
  margin-bottom: 16px;
}

.setting-group {
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-radius: 8px;
  border: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.setting-label {
  color: rgb(var(--v-theme-on-surface));
}

.dialog-actions {
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-top: 1px solid rgba(var(--v-theme-outline), 0.08);
}

/* Form field enhancements */
:deep(.v-field) {
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

:deep(.v-field:hover) {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

:deep(.v-field--focused) {
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.15);
  outline: none !important;
}


/* Switch styling */
:deep(.v-switch .v-selection-control__wrapper) {
  height: 32px;
}

:deep(.v-switch .v-selection-control__input) {
  border-radius: 16px;
}

/* Textarea styling */
:deep(.v-textarea .v-field__field) {
  border-radius: 8px;
}

/* Auto-generated field styling */
.auto-generated-field :deep(.v-field) {
  background: rgba(var(--v-theme-primary), 0.02);
  border: 1px dashed rgba(var(--v-theme-primary), 0.2);
}

.auto-generated-field :deep(.v-field__input) {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-style: italic;
}

.auto-generated-field :deep(.v-field--focused) {
  background: rgba(var(--v-theme-primary), 0.04);
  border-color: rgba(var(--v-theme-primary), 0.3);
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
  .form-section {
    padding: 16px;
  }

  .dialog-header {
    padding: 20px !important;
  }

  .dialog-actions {
    padding: 20px !important;
  }

  :deep(.v-btn) {
    min-width: 100px;
  }
}
</style>