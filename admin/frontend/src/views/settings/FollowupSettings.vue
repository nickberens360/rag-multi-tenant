<template>
  <div>
    <!-- Overview Cards -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="success"
                size="large"
                class="me-3"
              >
                $folder
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ store.stats.active_categories }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Active Categories
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="primary"
                size="large"
                class="me-3"
              >
                $help-circle
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ store.stats.total_questions }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Total Questions
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="warning"
                size="large"
                class="me-3"
              >
                $alert
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ store.stats.inactive_categories }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Inactive Categories
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="info"
                size="large"
                class="me-3"
              >
                $brain
              </v-icon>
              <div>
                <div class="text-h6 text-capitalize">
                  {{ store.settings.service_type || 'Static' }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Service Mode
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- System Settings Section -->
    <div class="ds-section-spacing">
      <div class="ds-content-spacing">
        <h2 class="text-h6 ds-font-bold ds-mb-2">
          System Configuration
        </h2>
        <p class="ds-text-sm text-medium-emphasis">
          Configure follow-up question generation behavior and limits
        </p>
      </div>

      <v-card class="ds-card settings-card">
        <v-card-text
          class="pa-0"
          style="padding: 0 !important;"
        >
          <!-- Service Status Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $toggle-switch
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Service Status
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Toggle the follow-up question system on or off
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="store.settings.enabled"
                  color="primary"
                  inset
                  hide-details
                  @update:model-value="updateSetting('enabled', $event)"
                />
                <div class="setting-status text-medium-emphasis">
                  {{ store.settings.enabled ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Generation Method Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $brain
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Generation Method
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Choose how questions are generated and selected
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="store.settings.service_type"
                  :items="store.serviceTypeOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="min-width: 200px;"
                  @update:model-value="updateSetting('service_type', $event)"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Question Limit Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $numeric
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Question Limit
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Maximum number of follow-up questions to display
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <div class="setting-slider">
                  <v-slider
                    v-model="store.settings.max_questions"
                    :min="1"
                    :max="5"
                    :step="1"
                    thumb-label="always"
                    show-ticks="always"
                    color="primary"
                    track-color="grey-lighten-3"
                    thumb-color="primary"
                    hide-details
                    style="width: 200px;"
                    @update:model-value="updateSetting('max_questions', $event)"
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ store.settings.max_questions }} {{ store.settings.max_questions === 1 ? 'question' : 'questions' }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Categories Management Section -->
    <div class="ds-section-spacing">
      <div class="ds-content-spacing">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h2 class="text-h6 ds-font-bold ds-mb-2">
              Category Management
            </h2>
            <p class="ds-text-sm text-medium-emphasis">
              Manage question categories and their associated follow-up questions
            </p>
          </div>
        </div>
      </div>

      <!-- Bulk Actions Banner -->
      <v-card
        v-if="store.selectedCategories.length > 0"
        class="ds-card bulk-actions-card ds-mb-6"
        color="primary"
        variant="tonal"
      >
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2">
                $checkbox-marked
              </v-icon>
              <span class="font-weight-medium">
                {{ store.selectedCategories.length }} {{ store.selectedCategories.length === 1 ? 'category' : 'categories' }} selected
              </span>
            </div>
            <v-btn-group
              variant="outlined"
              density="compact"
            >
              <v-btn
                prepend-icon="$eye"
                :loading="store.loading"
                class="mr-3"
                @click="bulkActivate"
              >
                Activate
              </v-btn>
              <v-btn
                prepend-icon="$eye-off"
                :loading="store.loading"
                class="mr-3"
                @click="bulkDeactivate"
              >
                Deactivate
              </v-btn>
              <v-btn
                color="error"
                prepend-icon="$delete"
                :loading="store.loading"
                @click="bulkDelete"
              >
                Delete
              </v-btn>
            </v-btn-group>
          </div>
        </v-card-text>
      </v-card>

      <!-- Categories List -->
      <v-card class="ds-card categories-card">
        <v-card-title class="pa-3 pb-3">
          <div class="d-flex align-center justify-space-between categories-header">
            <div class="d-flex align-center">
              <span class="text-h6 ds-font-semibold">Question Categories</span>
              <v-chip
                :text="`${store.categories.length}`"
                variant="tonal"
                size="small"
                class="ml-3"
              />
            </div>
            <v-btn
              color="primary"
              prepend-icon="$plus"
              variant="elevated"
              @click="showCategoryDialog = true"
            >
              Add Category
            </v-btn>
          </div>
        </v-card-title>

        <v-divider class="mx-6 mb-4" />

        <v-card-text class="ds-p-6 pt-0">
          <FollowupAccordion
            v-if="store.categories.length > 0"
            :categories="store.categories"
            :category-stats="store.categoryStats"
            :expanded-panels="store.expandedPanels"
            :selected-categories="store.selectedCategories"
            :loading="store.loading"
            @update-selected-categories="store.updateSelectedCategories"
            @update-expanded-panels="store.updateExpandedPanels"
            @update-question-selection="store.updateQuestionSelection"
            @edit-category="editCategory"
            @delete-category="deleteCategory"
          />

          <!-- Empty State -->
          <div
            v-else
            class="empty-state text-center py-12"
          >
            <v-avatar
              size="80"
              color="grey-lighten-3"
              class="ds-mb-4"
            >
              <v-icon
                size="40"
                color="grey-lighten-1"
              >
                $format-list-group
              </v-icon>
            </v-avatar>

            <h3 class="text-h6 ds-font-semibold ds-mb-2">
              No Categories Yet
            </h3>
            <p
              class="text-body-2 text-medium-emphasis ds-mb-6 mx-auto"
              style="max-width: 320px;"
            >
              Create your first category to organize follow-up questions
            </p>

            <v-btn
              color="primary"
              prepend-icon="$plus"
              variant="elevated"
              @click="showCategoryDialog = true"
            >
              Create First Category
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Category Dialog -->
    <CategoryDialog
      v-model="showCategoryDialog"
      :category="editingCategory"
      :loading="store.loading"
      @save="saveCategory"
      @cancel="cancelCategory"
    />

    <!-- Delete Dialog -->
    <CategoryDeleteDialog
      v-model="showDeleteDialog"
      :category="deletingCategory"
      :category-stats="deletingCategory ? store.categoryStats[deletingCategory.id] : null"
      :available-categories="store.availableCategoriesForMove"
      :loading="store.loading"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { useFollowupSettingsStore } from '@/stores/followupSettings'
import { useNotifications } from '@/composables/useNotifications'
import FollowupAccordion from '@/components/FollowupAccordion.vue'
import CategoryDialog from '@/components/CategoryDialog.vue'
import CategoryDeleteDialog from '@/components/CategoryDeleteDialog.vue'

// Store and composables
const store = useFollowupSettingsStore()
const { showSuccess, showError } = useNotifications()

// Local state
const showCategoryDialog = ref(false)
const showDeleteDialog = ref(false)
const editingCategory = ref(null)
const deletingCategory = ref(null)

// Lifecycle
onMounted(() => {
  store.loadData()
})

// Reload follow-up data when tenant changes
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await store.loadData()
  }
}, { deep: true })

// Methods
const updateSetting = async (key, value) => {
  try {
    await store.updateSetting(key, value)
    showSuccess(`Setting "${key}" updated successfully!`)
  } catch (err) {
    showError(`Failed to update setting: ${err.message}`)
  }
}

const editCategory = (category) => {
  editingCategory.value = category
  showCategoryDialog.value = true
}

const saveCategory = async (categoryData) => {
  try {
    if (editingCategory.value) {
      await store.updateCategory(editingCategory.value.id, categoryData)
      showSuccess('Category updated successfully!')
    } else {
      await store.createCategory(categoryData)
      showSuccess('Category created successfully!')
    }
    showCategoryDialog.value = false
    editingCategory.value = null
  } catch (err) {
    showError(`Failed to save category: ${err.message}`)
  }
}

const cancelCategory = () => {
  showCategoryDialog.value = false
  editingCategory.value = null
}

const deleteCategory = (category) => {
  deletingCategory.value = category
  showDeleteDialog.value = true
}

const confirmDelete = async (deleteRequest) => {
  try {
    await store.deleteCategory(deleteRequest)
    showSuccess('Category deleted successfully!')
    showDeleteDialog.value = false
    deletingCategory.value = null
  } catch (err) {
    showError(`Failed to delete category: ${err.message}`)
  }
}

const bulkActivate = async () => {
  try {
    await store.bulkActivateCategories(store.selectedCategories)
    showSuccess(`${store.selectedCategories.length} categories activated!`)
  } catch (err) {
    showError(`Failed to activate categories: ${err.message}`)
  }
}

const bulkDeactivate = async () => {
  try {
    await store.bulkDeactivateCategories(store.selectedCategories)
    showSuccess(`${store.selectedCategories.length} categories deactivated!`)
  } catch (err) {
    showError(`Failed to deactivate categories: ${err.message}`)
  }
}

const bulkDelete = async () => {
  try {
    await store.bulkDeleteCategories(store.selectedCategories)
    showSuccess(`${store.selectedCategories.length} categories deleted!`)
  } catch (err) {
    showError(`Failed to delete categories: ${err.message}`)
  }
}
</script>

<style scoped>
.categories-header {
  padding-bottom: 16px;
}

/* Settings Row Layout */
.setting-row {
  padding: 20px 24px;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.setting-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.setting-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

.setting-info {
  flex: 1;
  min-width: 0;
}

.setting-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.setting-description {
  font-size: 14px;
  line-height: 1.4;
}

.setting-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.setting-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

.setting-slider {
  display: flex;
  align-items: center;
}

.setting-slider .setting-status {
  margin-left: 16px;
  min-width: 80px;
  text-align: right;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .setting-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .setting-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .setting-slider {
    width: 100%;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .setting-slider .setting-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>
