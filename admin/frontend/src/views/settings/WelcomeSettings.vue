<template>
  <div>
    <!-- Overview Cards -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        sm="6"
        md="4"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="primary"
                size="large"
                class="me-3"
              >
                $message-text
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ questions.filter(q => q.is_active).length }}
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
        md="4"
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
                  {{ questions.filter(q => !q.is_active).length }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Inactive Questions
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col
        cols="12"
        sm="6"
        md="4"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="info"
                size="large"
                class="me-3"
              >
                $web
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ questions.filter(q => q.is_active).length }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Homepage Display
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Questions Management Section -->
    <div class="questions-section">
      <div class="section-header mb-6">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h2 class="section-title text-h5 font-weight-bold">
              Welcome Questions
            </h2>
            <p class="section-subtitle text-body-2 text-medium-emphasis">
              Manage the suggested questions shown to users on the homepage
            </p>
          </div>
        </div>
      </div>

      <!-- Questions List -->
      <v-card
        class="questions-card"
        elevation="2"
      >
        <v-card-title class="pa-6 pb-0">
          <div class="d-flex align-center">
            <v-icon class="mr-3">
              $message-text
            </v-icon>
            <span class="text-h6 font-weight-bold">Homepage Questions</span>
            <v-spacer />

            <v-btn
              color="primary"
              size="small"
              prepend-icon="$plus"
              class="mr-2"
              @click="showCreateDialog"
            >
              Add Question
            </v-btn>

            <v-chip
              :text="`${questions.length} total`"
              variant="tonal"
              size="small"
            />
          </div>
        </v-card-title>

        <v-card-text class="pa-6">
          <div v-if="questions.length > 0">
            <v-list
              lines="two"
              class="questions-list"
            >
              <v-list-item 
                v-for="(question, index) in sortedQuestions" 
                :key="question.id"
                class="question-item"
                :class="{ 'question-item--inactive': !question.is_active }"
              >
                <template #prepend>
                  <v-avatar
                    size="40"
                    color="primary"
                    variant="tonal"
                  >
                    <span class="text-body-1 font-weight-bold">{{ question.sort_order || (index + 1) }}</span>
                  </v-avatar>
                </template>

                <v-list-item-title class="text-body-1 font-weight-medium">
                  {{ question.question_text }}
                </v-list-item-title>

                <v-list-item-subtitle class="text-caption text-medium-emphasis">
                  <span>Created {{ formatDate(question.created_at) }}</span>
                  <span
                    v-if="!question.is_active"
                    class="text-warning ml-2"
                  >• Inactive</span>
                </v-list-item-subtitle>

                <template #append>
                  <div class="d-flex align-center gap-2">
                    <v-tooltip text="Edit question">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          variant="text"
                          icon="$pencil"
                          size="small"
                          @click="editQuestion(question)"
                        />
                      </template>
                    </v-tooltip>

                    <v-tooltip :text="question.is_active ? 'Deactivate' : 'Activate'">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          variant="text"
                          :icon="question.is_active ? '$eye-off' : '$eye'"
                          size="small"
                          @click="toggleQuestionStatus(question)"
                        />
                      </template>
                    </v-tooltip>

                    <v-tooltip text="Delete question">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          variant="text"
                          icon="$delete"
                          size="small"
                          color="error"
                          @click="deleteQuestion(question)"
                        />
                      </template>
                    </v-tooltip>
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </div>

          <!-- Empty State -->
          <div
            v-else
            class="empty-state text-center py-16"
          >
            <v-avatar
              size="120"
              color="grey-lighten-3"
              class="mb-6"
            >
              <v-icon
                size="60"
                color="grey-lighten-1"
              >
                $message-text
              </v-icon>
            </v-avatar>

            <h3 class="text-h5 font-weight-bold mb-3">
              No Questions Yet
            </h3>
            <p
              class="text-body-1 text-medium-emphasis mb-8 mx-auto"
              style="max-width: 400px;"
            >
              Add welcome questions to help guide users when they first visit your site.
            </p>

            <v-btn
              color="primary"
              size="large"
              prepend-icon="$plus"
              variant="elevated"
              @click="showCreateDialog"
            >
              Add First Question
            </v-btn>
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
      <v-card
        class="question-dialog"
        elevation="12"
        rounded="xl"
      >
        <v-card-title class="dialog-header pa-6">
          <div class="d-flex align-center">
            <v-avatar
              size="48"
              color="primary"
              variant="tonal"
              class="mr-4"
            >
              <v-icon size="24">
                {{ editingQuestion ? '$pencil' : '$plus' }}
              </v-icon>
            </v-avatar>
            <div class="flex-grow-1">
              <h2 class="text-h5 font-weight-bold mb-1">
                {{ editingQuestion ? 'Edit Question' : 'Add New Question' }}
              </h2>
              <p class="text-body-2 text-medium-emphasis ma-0">
                {{ editingQuestion ? 'Update the welcome question' : 'Add a new suggested question' }}
              </p>
            </div>
          </div>
        </v-card-title>

        <v-divider class="border-opacity-12" />

        <v-card-text class="pa-6">
          <v-form
            ref="questionForm"
            v-model="formValid"
            @submit.prevent="saveQuestion"
          >
            <v-row>
              <v-col cols="12">
                <v-textarea
                  v-model="questionFormData.question_text"
                  label="Question Text"
                  placeholder="What would you like to know?"
                  :rules="questionRules"
                  rows="3"
                  variant="outlined"
                  density="comfortable"
                  counter
                  maxlength="500"
                  required
                />
              </v-col>

              <v-col
                cols="12"
                md="6"
              >
                <v-text-field
                  v-model.number="questionFormData.sort_order"
                  label="Display Order"
                  type="number"
                  :rules="sortOrderRules"
                  variant="outlined"
                  density="comfortable"
                  hint="Questions are displayed in this order (1 = first)"
                  persistent-hint
                />
              </v-col>

              <v-col
                v-if="editingQuestion"
                cols="12"
                md="6"
              >
                <v-switch
                  v-model="questionFormData.is_active"
                  label="Active"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="text-caption text-medium-emphasis mt-1">
                  Only active questions are shown on the homepage
                </div>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>

        <v-divider class="border-opacity-12" />

        <v-card-actions class="dialog-actions pa-6">
          <v-spacer />
          <v-btn
            variant="outlined"
            size="large"
            :disabled="loading"
            class="mr-3"
            @click="cancelQuestionEdit"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            size="large"
            :loading="loading"
            :disabled="!formValid"
            @click="saveQuestion"
          >
            {{ editingQuestion ? 'Update' : 'Create' }} Question
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="480px"
      persistent
    >
      <v-card
        class="delete-dialog"
        elevation="12"
        rounded="xl"
      >
        <v-card-title class="dialog-header pa-6">
          <div class="d-flex align-center">
            <v-avatar
              size="48"
              color="error"
              variant="tonal"
              class="mr-4"
            >
              <v-icon size="24">
                $delete
              </v-icon>
            </v-avatar>
            <div class="flex-grow-1">
              <h2 class="text-h5 font-weight-bold mb-1">
                Delete Question
              </h2>
              <p class="text-body-2 text-medium-emphasis ma-0">
                This action cannot be undone
              </p>
            </div>
          </div>
        </v-card-title>

        <v-divider class="border-opacity-12" />

        <v-card-text class="pa-6">
          <p class="text-body-1 mb-4">
            Are you sure you want to delete this question?
          </p>
          <v-card
            color="error"
            variant="tonal"
            elevation="0"
            rounded="lg"
            class="pa-4"
          >
            <div class="text-body-1 font-weight-medium">
              "{{ deletingQuestion?.question_text }}"
            </div>
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
            @click="cancelDelete"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="elevated"
            size="large"
            :loading="loading"
            prepend-icon="$delete"
            @click="confirmDelete"
          >
            Delete Question
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { format, parseISO } from 'date-fns'
import api from '@/services/api'

export default {
  name: 'WelcomeSettings',
  setup() {
    // Reactive state
    const loading = ref(false)
    const questions = ref([])
    
    // Form state
    const showQuestionDialog = ref(false)
    const showDeleteDialog = ref(false)
    const formValid = ref(false)
    const editingQuestion = ref(null)
    const deletingQuestion = ref(null)

    // Form data
    const questionFormData = reactive({
      question_text: '',
      sort_order: 1,
      is_active: true
    })

    // Helper function to get trimmed value for validation
    const getTrimmedValue = (v) => v ? v.trim() : ''

    // Form validation rules
    const questionRules = [
      v => Boolean(getTrimmedValue(v)) || 'Question text is required',
      v => getTrimmedValue(v).length >= 3 || 'Question must be at least 3 characters',
      v => getTrimmedValue(v).length <= 500 || 'Question must be less than 500 characters'
    ]

    const sortOrderRules = [
      v => v >= 0 || 'Sort order must be 0 or greater',
      v => v <= 1000 || 'Sort order must be less than 1000'
    ]

    // Computed properties
    const sortedQuestions = computed(() => 
      [...questions.value].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    )

    // Methods
    const loadQuestions = async () => {
      try {
        loading.value = true
        const response = await api.getWelcomeQuestions()
        questions.value = response || []
      } catch (error) {
        console.error('Failed to load welcome questions:', error)
      } finally {
        loading.value = false
      }
    }

    const showCreateDialog = () => {
      editingQuestion.value = null
      questionFormData.question_text = ''
      questionFormData.sort_order = (Math.max(...questions.value.map(q => q.sort_order || 0), 0)) + 1
      questionFormData.is_active = true
      showQuestionDialog.value = true
    }

    const editQuestion = (question) => {
      editingQuestion.value = question
      questionFormData.question_text = question.question_text
      questionFormData.sort_order = question.sort_order || 1
      questionFormData.is_active = question.is_active
      showQuestionDialog.value = true
    }

    const saveQuestion = async () => {
      try {
        loading.value = true
        
        if (editingQuestion.value) {
          // Update existing question
          await api.updateWelcomeQuestion(editingQuestion.value.id, questionFormData)
        } else {
          // Create new question
          await api.createWelcomeQuestion(questionFormData)
        }

        showQuestionDialog.value = false
        await loadQuestions()
      } catch (error) {
        console.error('Failed to save question:', error)
      } finally {
        loading.value = false
      }
    }

    const cancelQuestionEdit = () => {
      showQuestionDialog.value = false
      editingQuestion.value = null
    }

    const toggleQuestionStatus = async (question) => {
      try {
        loading.value = true
        await api.updateWelcomeQuestion(question.id, { is_active: !question.is_active })
        await loadQuestions()
      } catch (error) {
        console.error('Failed to toggle question status:', error)
      } finally {
        loading.value = false
      }
    }

    const deleteQuestion = (question) => {
      deletingQuestion.value = question
      showDeleteDialog.value = true
    }

    const confirmDelete = async () => {
      try {
        loading.value = true
        await api.deleteWelcomeQuestion(deletingQuestion.value.id)
        showDeleteDialog.value = false
        deletingQuestion.value = null
        await loadQuestions()
      } catch (error) {
        console.error('Failed to delete question:', error)
      } finally {
        loading.value = false
      }
    }

    const cancelDelete = () => {
      showDeleteDialog.value = false
      deletingQuestion.value = null
    }

    const formatDate = (dateString) => {
      try {
        return format(parseISO(dateString), 'MMM d, yyyy')
      } catch {
        return 'Unknown'
      }
    }

    // Initialize
    onMounted(() => {
      loadQuestions()
    })

    // React to tenant changes
    const tenantStore = useTenantStore()
    const { currentTenant } = storeToRefs(tenantStore)
    watch(currentTenant, async (newTenant, oldTenant) => {
      if (oldTenant && newTenant && oldTenant.id !== newTenant.id) {
        await loadQuestions()
      }
    }, { deep: true })

    return {
      loading,
      questions,
      showQuestionDialog,
      showDeleteDialog,
      formValid,
      editingQuestion,
      deletingQuestion,
      questionFormData,
      questionRules,
      sortOrderRules,
      sortedQuestions,
      loadQuestions,
      showCreateDialog,
      editQuestion,
      saveQuestion,
      cancelQuestionEdit,
      toggleQuestionStatus,
      deleteQuestion,
      confirmDelete,
      cancelDelete,
      formatDate
    }
  }
}
</script>

<style scoped>
.metric-card {
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-outline), 0.12);
  transition: all 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.metric-label {
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.metric-value {
  color: rgb(var(--v-theme-on-surface));
  line-height: 1.2;
}

.questions-section {
  margin-bottom: 32px;
}

.section-header {
  margin-bottom: 24px;
}

.section-title {
  color: rgb(var(--v-theme-on-surface));
  margin-bottom: 8px;
}

.section-subtitle {
  color: rgb(var(--v-theme-on-surface-variant));
  max-width: 600px;
}

.questions-card {
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-outline), 0.12);
}

.questions-list .question-item {
  border-radius: 12px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.questions-list .question-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.question-item--inactive {
  opacity: 0.6;
}

.empty-state {
  padding: 48px 24px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  border: 2px dashed rgba(var(--v-theme-outline), 0.2);
}

.question-dialog, .delete-dialog {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.dialog-header {
  background: linear-gradient(135deg, rgb(var(--v-theme-surface)) 0%, rgba(var(--v-theme-primary), 0.02) 100%);
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.dialog-actions {
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-top: 1px solid rgba(var(--v-theme-outline), 0.08);
}
</style>
