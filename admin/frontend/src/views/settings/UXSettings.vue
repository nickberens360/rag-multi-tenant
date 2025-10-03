<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h5 font-weight-bold">
          User Experience Settings
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Configure welcome messages and user-facing features for enhanced user experience
        </p>
      </div>
      <v-btn
        color="primary"
        variant="elevated"
        :loading="saving"
        prepend-icon="$check"
        @click="saveAllSettings"
      >
        Save All Changes
      </v-btn>
    </div>

    <div class="grid-container">
      <!-- Welcome Questions Management Card -->
      <v-card
        v-if="featureStore && featureStore.featureFlags"
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6 d-flex justify-space-between align-center">
          <div class="d-flex align-center">
            <v-icon
              color="primary"
              class="mr-2"
            >
              $message-question
            </v-icon>
            Welcome Questions
          </div>
          <div class="d-flex align-center">
            <v-chip
              :text="`${activeQuestions.length} active`"
              color="success"
              size="small"
              variant="tonal"
              class="mr-2"
            />
            <v-btn
              color="primary"
              prepend-icon="$plus"
              size="small"
              @click="showCreateQuestionDialog"
            >
              Add Question
            </v-btn>
          </div>
        </v-card-title>

        <v-card-text>
          <!-- Active Questions List -->
          <div v-if="questions.length > 0">
            <div
              v-for="(question, index) in sortedQuestions"
              :key="question.id"
              class="question-item"
            >
              <div class="question-content">
                <div class="question-info">
                  <div class="d-flex align-center">
                    <v-avatar
                      size="24"
                      color="primary"
                      variant="tonal"
                      class="mr-2"
                    >
                      <span class="text-caption font-weight-bold">{{ question.sort_order || (index + 1) }}</span>
                    </v-avatar>
                    <span class="font-weight-medium">{{ question.question_text }}</span>
                    <v-chip
                      v-if="!question.is_active"
                      color="warning"
                      size="x-small"
                      variant="tonal"
                      class="ml-2"
                    >
                      Inactive
                    </v-chip>
                  </div>
                  <div class="text-caption text-medium-emphasis mt-1">
                    Created {{ formatDate(question.created_at) }}
                  </div>
                </div>
                <div class="question-actions">
                  <v-btn
                    icon="$pencil"
                    size="small"
                    color="primary"
                    variant="text"
                    @click="editQuestion(question)"
                  />
                  <v-btn
                    :icon="question.is_active ? '$eye-off' : '$eye'"
                    size="small"
                    :color="question.is_active ? 'warning' : 'success'"
                    variant="text"
                    @click="toggleQuestionStatus(question)"
                  />
                  <v-btn
                    icon="$delete"
                    size="small"
                    color="error"
                    variant="text"
                    @click="deleteQuestion(question)"
                  />
                </div>
              </div>
            </div>
          </div>

          <div
            v-else
            class="text-center py-8 text-medium-emphasis"
          >
            <v-icon
              size="48"
              class="mb-4"
            >
              $message-question
            </v-icon>
            <div class="text-h6 mb-2">
              No Welcome Questions
            </div>
            <p class="text-body-2 mb-4">
              Add questions to help guide users when they visit your site.
            </p>
            <v-btn
              color="primary"
              prepend-icon="$plus"
              @click="showCreateQuestionDialog"
            >
              Add First Question
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Follow-up Questions Management Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6 d-flex justify-space-between align-center">
          <div class="d-flex align-center">
            <v-icon
              color="primary"
              class="mr-2"
            >
              $message-reply
            </v-icon>
            Follow-up Questions
          </div>
          <div class="d-flex align-center">
            <v-chip
              :text="`${followupStats.active_categories} active`"
              color="success"
              size="small"
              variant="tonal"
              class="mr-2"
            />
            <v-chip
              :text="`${followupStats.total_questions} questions`"
              color="primary"
              size="small"
              variant="tonal"
              class="mr-2"
            />
            <v-btn
              color="primary"
              prepend-icon="$plus"
              size="small"
              @click="showCreateFollowupCategoryDialog"
            >
              Add Category
            </v-btn>
          </div>
        </v-card-title>

        <v-card-text class="pa-0">
          <!-- Followup System Settings -->
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
                    Follow-up Questions
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Generate suggested follow-up questions after responses
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="followupSettings.enabled"
                  color="primary"
                  inset
                  hide-details
                  @update:model-value="saveFollowupSettings"
                />
                <div class="setting-status text-medium-emphasis">
                  {{ followupSettings.enabled ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Service Type Row -->
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
                    How follow-up questions are generated
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="followupSettings.service_type"
                  :items="serviceTypeOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="min-width: 160px"
                  @update:model-value="saveFollowupSettings"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Max Questions Row -->
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
                    Max Questions
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Maximum number of follow-up questions to show
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-text-field
                  v-model.number="followupSettings.max_questions"
                  type="number"
                  variant="outlined"
                  density="compact"
                  hide-details
                  min="1"
                  max="5"
                  style="width: 80px"
                  @update:model-value="saveFollowupSettings"
                />
              </div>
            </div>
          </div>

          <!-- Categories List -->
          <v-divider class="mb-4" />

          <div class="pa-6">
            <div class="d-flex justify-space-between align-center mb-4">
              <h3 class="text-h6">
                Question Categories
              </h3>
              <div class="d-flex align-center">
                <v-btn
                  variant="outlined"
                  size="small"
                  prepend-icon="$plus"
                  @click="openCreateFollowupCategoryDialog"
                >
                  Create Category
                </v-btn>
              </div>
            </div>

            <!-- Use the full-featured FollowupAccordion for in-place management -->
            <FollowupAccordion
              :key="followupKey"
              @changed="onFollowupChanged"
              @edit-category="onEditFollowupCategory"
            />
          </div>
        </v-card-text>
      </v-card>

      <!-- User-Facing Features Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $feature-search
          </v-icon>
          User-Facing Features
        </v-card-title>

        <v-card-text class="pa-0">
          <v-alert
            v-if="featureError"
            type="error"
            variant="tonal"
            class="ma-6 mb-4"
          >
            {{ featureError }}
          </v-alert>

          <!-- Success notifications are shown via global toasts -->

          <!-- Enable Illustrations Row hidden for now -->

          <!-- Enable Geolocation Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $map-marker
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable Geolocation
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Allow location-based features and personalized responses
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="featureStore.featureFlags.enable_geolocation"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ featureStore.featureFlags.enable_geolocation ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Enable Query Preprocessing Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $wrench
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable Query Preprocessing
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Enhance user queries with preprocessing and optimization
                    <a
                      :href="getBlogUrl('query-preprocessing-security-rag')"
                      target="_blank"
                      style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                    >Learn more →</a>
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="featureStore.featureFlags.enable_query_preprocessing"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ featureStore.featureFlags.enable_query_preprocessing ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Enable API Versioning Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $source-branch
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable API Versioning
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Support multiple API versions for backward compatibility
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="featureStore.featureFlags.enable_api_versioning"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ featureStore.featureFlags.enable_api_versioning ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Create/Edit Question Dialog -->
    <v-dialog
      v-model="showQuestionDialog"
      max-width="600px"
      persistent
    >
      <v-card>
        <v-card-title>
          <span class="text-h6">{{ editingQuestion ? 'Edit' : 'Add' }} Welcome Question</span>
        </v-card-title>

        <v-card-text>
          <v-form
            ref="questionFormRef"
            v-model="formValid"
          >
            <v-textarea
              v-model="questionForm.question_text"
              label="Question Text"
              :rules="questionRules"
              rows="3"
              counter
              maxlength="500"
              variant="outlined"
              required
            />

            <v-row class="mt-4">
              <v-col cols="6">
                <v-text-field
                  v-model.number="questionForm.sort_order"
                  label="Display Order"
                  type="number"
                  :rules="sortOrderRules"
                  variant="outlined"
                  hint="1 = first"
                />
              </v-col>
              <v-col
                v-if="editingQuestion"
                cols="6"
              >
                <v-switch
                  v-model="questionForm.is_active"
                  label="Active"
                  color="primary"
                  inset
                />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            :disabled="savingQuestion"
            @click="closeQuestionDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="savingQuestion"
            :disabled="!formValid"
            @click="saveQuestion"
          >
            {{ editingQuestion ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title>
          <span class="text-h6">Confirm Deletion</span>
        </v-card-title>

        <v-card-text>
          <v-alert
            type="error"
            variant="tonal"
            class="mb-4"
          >
            This action cannot be undone.
          </v-alert>

          Are you sure you want to delete this welcome question?
          <div class="mt-2 pa-3 bg-grey-lighten-4 rounded">
            <strong>"{{ questionToDelete?.question_text }}"</strong>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            :disabled="deletingQuestion"
            @click="showDeleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deletingQuestion"
            @click="confirmDeleteQuestion"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create/Edit Follow-up Category Dialog -->
    <CategoryDialog
      v-model="showCategoryDialog"
      :category="editingCategory"
      :loading="saving"
      @save="saveFollowupCategory"
      @cancel="onCancelCategoryDialog"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { useAdminStore } from '@/stores/admin'
import { useUXSettingsStore } from '@/stores/uxSettings'
import { useFeatureSettingsStore } from '@/stores/featureSettings'
import { adminAPI as apiService } from '@/services/api'
import { format, parseISO } from 'date-fns'
import FollowupAccordion from '@/components/FollowupAccordion.vue'
import CategoryDialog from '@/components/CategoryDialog.vue'
import { useNotifications } from '@/composables/useNotifications'

const adminStore = useAdminStore()
const uxStore = useUXSettingsStore()
const featureStore = useFeatureSettingsStore()

// Feature flags come from centralized store

// Welcome questions state
const questions = ref([])
const activeQuestions = computed(() => questions.value.filter(q => q.is_active))
const sortedQuestions = computed(() =>
  [...questions.value].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
)

// Followup questions state
const followupSettings = ref({
  enabled: true,
  service_type: 'static',
  max_questions: 1
})

const followupCategories = ref([])
const followupStats = computed(() => ({
  active_categories: followupCategories.value.filter(c => c.is_active).length,
  inactive_categories: followupCategories.value.filter(c => !c.is_active).length,
  total_questions: followupCategories.value.reduce((sum, c) => sum + (c.question_count || 0), 0)
}))

const serviceTypeOptions = [
  { title: 'Static', value: 'static', subtitle: 'Pre-defined questions' },
  { title: 'Dynamic', value: 'dynamic', subtitle: 'Context-based generation' },
  { title: 'Contextual', value: 'contextual', subtitle: 'AI-generated based on conversation' }
]

// Loading and error states
const saving = ref(false)
const featureError = ref('')
const { showSuccess, showError } = useNotifications()
const followupKey = ref(0)
const showCategoryDialog = ref(false)
const editingCategory = ref(null)

// Question dialog state
const showQuestionDialog = ref(false)
const showDeleteDialog = ref(false)
const editingQuestion = ref(null)
const questionToDelete = ref(null)
const formValid = ref(false)
const savingQuestion = ref(false)
const deletingQuestion = ref(false)
const questionFormRef = ref(null)

const questionForm = reactive({
  question_text: '',
  sort_order: 1,
  is_active: true
})

// Form validation rules
const questionRules = [
  v => Boolean(v) || 'Question text is required',
  v => (v && v.length >= 3) || 'Question must be at least 3 characters',
  v => (v && v.length <= 500) || 'Question must be less than 500 characters'
]

const sortOrderRules = [
  v => v >= 0 || 'Sort order must be 0 or greater',
  v => v <= 1000 || 'Sort order must be less than 1000'
]

// Methods
const loadAllSettings = async () => {
  try {
    // Load UX settings through store
    await uxStore.loadData()

    // Load feature flags via store
    await featureStore.loadData()

    // Load welcome questions
    await loadQuestions()

    // Load followup settings and categories
    await loadFollowupSettings()
    await loadFollowupCategories()

  } catch (err) {
    console.error('Failed to load settings:', err)
    featureError.value = `Failed to load settings: ${  err.response?.data?.detail || err.message}`
  }
}

const saveAllSettings = async () => {
  try {
    saving.value = true
    featureError.value = ''

    // Save feature flags via store
    await featureStore.updateFeatureFlags()
    showSuccess('User experience settings saved successfully!')

  } catch (err) {
    console.error('Failed to save settings:', err)
    featureError.value = `Failed to save settings: ${  err.response?.data?.detail || err.message}`
    showError('Failed to save settings')
  } finally {
    saving.value = false
  }
}

// Welcome Questions methods
const loadQuestions = async () => {
  try {
    const response = await apiService.getWelcomeQuestions()
    questions.value = response || []
  } catch (error) {
    console.error('Failed to load welcome questions:', error)
  }
}

const showCreateQuestionDialog = () => {
  editingQuestion.value = null
  questionForm.question_text = ''
  questionForm.sort_order = (Math.max(...questions.value.map(q => q.sort_order || 0), 0)) + 1
  questionForm.is_active = true
  showQuestionDialog.value = true
}

const editQuestion = (question) => {
  editingQuestion.value = question
  questionForm.question_text = question.question_text
  questionForm.sort_order = question.sort_order || 1
  questionForm.is_active = question.is_active
  showQuestionDialog.value = true
}

const closeQuestionDialog = () => {
  showQuestionDialog.value = false
  editingQuestion.value = null
  nextTick(() => {
    if (questionFormRef.value) {
      questionFormRef.value.resetValidation()
    }
  })
}

const saveQuestion = async () => {
  if (!formValid.value) return

  savingQuestion.value = true
  try {
    if (editingQuestion.value) {
      await apiService.updateWelcomeQuestion(editingQuestion.value.id, questionForm)
    } else {
      await apiService.createWelcomeQuestion(questionForm)
    }

    closeQuestionDialog()
    await loadQuestions()
  } catch (error) {
    console.error('Failed to save question:', error)
  } finally {
    savingQuestion.value = false
  }
}

const toggleQuestionStatus = async (question) => {
  try {
    await apiService.updateWelcomeQuestion(question.id, { is_active: !question.is_active })
    await loadQuestions()
  } catch (error) {
    console.error('Failed to toggle question status:', error)
  }
}

const deleteQuestion = (question) => {
  questionToDelete.value = question
  showDeleteDialog.value = true
}

const confirmDeleteQuestion = async () => {
  if (!questionToDelete.value) return

  deletingQuestion.value = true
  try {
    await apiService.deleteWelcomeQuestion(questionToDelete.value.id)
    showDeleteDialog.value = false
    questionToDelete.value = null
    await loadQuestions()
  } catch (error) {
    console.error('Failed to delete question:', error)
  } finally {
    deletingQuestion.value = false
  }
}

const formatDate = (dateString) => {
  try {
    return format(parseISO(dateString), 'MMM d, yyyy')
  } catch {
    return 'Unknown'
  }
}

// Followup questions methods
const loadFollowupSettings = async () => {
  try {
    const response = await apiService.getFollowupSettings()
    if (response) {
      followupSettings.value = { ...followupSettings.value, ...response }
    }
  } catch (error) {
    console.error('Failed to load followup settings:', error)
  }
}

const loadFollowupCategories = async () => {
  try {
    // Use the working getFollowupCategories endpoint directly
    const response = await apiService.getFollowupCategories()
    followupCategories.value = response || []

    // Load question counts separately for each category
    for (const category of followupCategories.value) {
      try {
        const statsResponse = await apiService.getFollowupCategoryStats(category.id)
        category.question_count = statsResponse?.question_count || 0
      } catch (error) {
        console.error(`Failed to load stats for category ${category.id}:`, error)
        category.question_count = 0
      }
    }
  } catch (error) {
    console.error('Failed to load followup categories:', error)
    followupCategories.value = []
  }
}

const saveFollowupSettings = async () => {
  try {
    await apiService.updateFollowupSettings(followupSettings.value)
    showSuccess('Follow-up settings saved successfully!')
  } catch (error) {
    console.error('Failed to save followup settings:', error)
    featureError.value = `Failed to save follow-up settings: ${  error.response?.data?.detail || error.message}`
    showError('Failed to save follow-up settings')
  }
}

const showCreateFollowupCategoryDialog = () => {
  // For now, redirect to the full followup manager
  openFullFollowupManager()
}

const openFullFollowupManager = () => {
  // Open the full followup settings in a new tab/modal or navigate to it
  // For now, we could navigate to a dedicated followup route or show info
  showSuccess('Full followup manager will open the complete FollowupSettings component')

  // TODO: Implement either:
  // 1. Navigate to a dedicated followup route
  // 2. Open the FollowupSettings component in a modal
  // 3. Add route for the standalone FollowupSettings component
}

onMounted(() => {
  loadAllSettings()
})

// Refresh UX settings when tenant changes
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)
watch(currentTenant, async (newTenant, oldTenant) => {
  if (oldTenant && newTenant && oldTenant.id !== newTenant.id) {
    try {
      await loadAllSettings()
    } catch (e) {
      // non-blocking
    }
  }
}, { deep: true })

// Handle FollowupAccordion change events to refresh counts
const onFollowupChanged = async () => {
  showSuccess('Follow-up questions updated')
  try {
    await loadFollowupCategories()
  } catch (e) {
    // ignore refresh errors
  } finally {
    // no-op
  }
}

// Open create/edit dialogs
const openCreateFollowupCategoryDialog = () => {
  editingCategory.value = null
  showCategoryDialog.value = true
}

const onEditFollowupCategory = (cat) => {
  editingCategory.value = cat
  showCategoryDialog.value = true
}

// Save handler from CategoryDialog
const saveFollowupCategory = async (data) => {
  try {
    if (data && data.id) {
      await apiService.updateFollowupCategory(data.id, data)
    } else {
      await apiService.createFollowupCategory(data)
    }
    showCategoryDialog.value = false
    editingCategory.value = null
    // Force reload of FollowupAccordion
    followupKey.value++
    await loadFollowupCategories()
    showSuccess(data && data.id ? 'Category updated' : 'Category created')
  } catch (e) {
    console.error('Failed to save follow-up category', e)
    featureError.value = `Failed to save category: ${  e.response?.data?.detail || e.message}`
  }
}

const onCancelCategoryDialog = () => {
  showCategoryDialog.value = false
  editingCategory.value = null
}

// Get blog URL based on environment
const getBlogUrl = (article = 'understanding-rag-score-thresholds') => {
  if (import.meta.env.PROD) {
    return `https://nickberens.com/blog/${article}`
  }
  return `http://localhost:4321/blog/${article}`
}
</script>

<style scoped>
/* Grid layout for responsive cards */
.grid-container {
  display: grid;
  gap: 24px;
}

/* Question items styling */
.question-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  margin-bottom: 8px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgba(var(--v-theme-surface));
  transition: background-color 0.2s ease;
}

.question-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.question-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.question-info {
  flex: 1;
  min-width: 0;
}

.question-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
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

/* Responsive adjustments */
@media (max-width: 768px) {
  .question-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .question-actions {
    width: 100%;
    justify-content: flex-end;
  }

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

  .setting-status {
    margin-left: 0;
  }
}
</style>
