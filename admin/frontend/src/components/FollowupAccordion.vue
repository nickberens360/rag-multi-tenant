<template>
  <div class="followup-container ds-card">
    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="ds-mb-4"
    >
      {{ error }}
    </v-alert>

    <!-- Subtle control bar -->
    <div
      v-if="categories.length > 0"
      class="ds-mb-4 d-flex align-center justify-space-between"
    >
      <div
        class="d-flex align-center"
        style="gap: 8px;"
      >
        <v-btn
          variant="tonal"
          size="small"
          prepend-icon="$chevron-down"
          :disabled="!categories.length || loading"
          @click="openAll"
        >
          Expand
        </v-btn>
        <v-btn
          variant="tonal"
          size="small"
          prepend-icon="$chevron-up"
          :disabled="!categories.length || loading"
          @click="closeAll"
        >
          Collapse
        </v-btn>
      </div>

      <v-progress-circular
        v-if="loading"
        indeterminate
        color="primary"
        size="16"
      />
    </div>

    <v-expansion-panels
      v-model="model"
      multiple
      variant="accordion"
      class="followup-panels"
    >
      <v-expansion-panel
        v-for="cat in categories"
        :key="cat.id"
        :value="cat.id"
      >
        <v-expansion-panel-title class="category-title-clean category-title-row">
          <div class="d-flex align-center w-100">
            <div class="d-flex align-center flex-grow-1">
              <v-avatar
                size="28"
                color="primary"
                variant="tonal"
                class="mr-3"
              >
                <v-icon size="16">
                  $tag
                </v-icon>
              </v-avatar>
              <!-- TODO: enable  once integrated
             <v-checkbox
                v-model="selectedCategories"
                :value="cat.id"
                hide-details
                density="compact"
                class="mr-3 category-checkbox"
                @click.stop
                @update:model-value="emitSelectedCategories"
              />-->
              <div class="category-info">
                <div class="category-name font-weight-medium">
                  {{ cat.display_name }}
                </div>
                <div class="category-meta text-caption text-medium-emphasis mt-1">
                  <v-chip
                    size="x-small"
                    label
                    variant="tonal"
                    class="mr-2"
                  >
                    {{ (questionsByCat[cat.id] || []).length }} questions
                  </v-chip>
                  <v-chip
                    size="x-small"
                    :color="cat.is_active ? 'success' : 'grey'"
                    variant="tonal"
                    label
                  >
                    {{ cat.is_active ? 'Active' : 'Inactive' }}
                  </v-chip>
                </div>
              </div>
            </div>

            <!-- Hover-revealed actions -->
            <div class="category-actions">
              <v-btn
                icon="$edit"
                size="small"
                variant="text"
                color="primary"
                :disabled="saving || loading"
                class="category-action-btn"
                @click.stop="openEditCategoryDialog(cat)"
              />
              <v-btn
                :icon="cat.is_active ? '$eye-off' : '$eye'"
                size="small"
                variant="text"
                :color="cat.is_active ? 'warning' : 'success'"
                :title="cat.is_active ? 'Deactivate' : 'Activate'"
                :disabled="saving || loading"
                class="category-action-btn"
                @click.stop="toggleCategoryActive(cat)"
              />
              <v-btn
                icon="$delete"
                size="small"
                variant="text"
                color="error"
                :disabled="saving || loading"
                class="category-action-btn"
                @click.stop="openDeleteCategoryDialog(cat)"
              />
            </div>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text class="question-panel-content">
          <div
            v-if="(questionsByCat[cat.id] || []).length === 0"
            class="empty-questions text-center py-8"
          >
            <v-icon
              size="36"
              class="mb-2"
              color="primary"
            >
              $help-circle
            </v-icon>
            <div class="text-body-2 text-medium-emphasis mb-3">
              No questions in this category
            </div>
            <v-btn
              variant="tonal"
              color="primary"
              size="small"
              prepend-icon="$plus"
              @click.stop="openAddDialog(cat)"
            >
              Add Question
            </v-btn>
          </div>
          <div
            v-else
            class="questions-list"
          >
            <div
              v-for="(q, idx) in questionsByCat[cat.id]"
              :key="q.id"
              class="question-item"
            >
              <div class="d-flex align-center">
                <div class="question-content flex-grow-1">
                  <div class="question-text text-body-2">
                    {{ q.question_text }}
                  </div>
                  <div class="question-meta text-caption text-medium-emphasis mt-1">
                    Order {{ q.sort_order }}
                    <span
                      v-if="!q.is_active"
                      class="inactive-question"
                    > • Inactive</span>
                  </div>
                </div>
                <div class="question-actions">
                  <v-btn
                    icon="$arrow-up"
                    size="x-small"
                    variant="text"
                    :disabled="saving || idx === 0"
                    class="question-action-btn"
                    @click.stop="moveUp(cat, idx)"
                  />
                  <v-btn
                    icon="$arrow-down"
                    size="x-small"
                    variant="text"
                    :disabled="saving || idx === (questionsByCat[cat.id].length - 1)"
                    class="question-action-btn"
                    @click.stop="moveDown(cat, idx)"
                  />
                  <v-btn
                    :icon="q.is_active ? '$eye-off' : '$eye'"
                    size="x-small"
                    variant="text"
                    :color="q.is_active ? 'warning' : 'success'"
                    :title="q.is_active ? 'Deactivate' : 'Activate'"
                    :disabled="saving"
                    class="question-action-btn"
                    @click.stop="toggleActive(cat, q)"
                  />
                  <v-btn
                    icon="$edit"
                    size="x-small"
                    variant="text"
                    color="primary"
                    :title="'Edit'"
                    :disabled="saving"
                    class="question-action-btn"
                    @click.stop="openEditDialog(cat, q)"
                  />
                  <v-btn
                    icon="$delete"
                    size="x-small"
                    variant="text"
                    color="error"
                    :disabled="saving"
                    class="question-action-btn"
                    @click.stop="openDeleteDialog(cat, q)"
                  />
                </div>
              </div>
            </div>

            <!-- Add Question Button -->
            <div class="add-question-section mt-4 pt-3 border-t-thin">
              <v-btn
                variant="tonal"
                prepend-icon="$plus"
                size="small"
                :disabled="saving || !cat.is_active"
                class="text-primary"
                @click="openAddDialog(cat)"
              >
                Add Question
              </v-btn>
            </div>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Add/Edit Dialog -->
    <v-dialog
      v-model="showDialog"
      max-width="580px"
    >
      <v-card class="ds-card">
        <v-card-title class="d-flex align-center ds-text-xl ds-font-semibold">
          <v-icon class="mr-2">
            $help-circle
          </v-icon>
          {{ editingQuestion ? 'Edit Question' : 'Add Question' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-textarea
              v-model="form.questionText"
              label="Question Text"
              rows="3"
              auto-grow
              :rules="[v => !!v || 'Required', v => (v?.length||0) <= 500 || 'Max 500 chars']"
            />
            <v-text-field
              v-model.number="form.sortOrder"
              type="number"
              label="Sort Order"
              :disabled="!!editingQuestion"
              :hint="editingQuestion ? 'Reordering is handled separately (drag & drop / move buttons)' : 'Lower numbers appear first'"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            class="ds-btn"
            variant="text"
            :disabled="saving"
            @click="closeDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            class="ds-btn"
            color="primary"
            :loading="saving"
            @click="save"
          >
            {{ editingQuestion ? 'Update' : 'Add' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="520px"
    >
      <v-card class="ds-card">
        <v-card-title class="d-flex align-center ds-text-xl ds-font-semibold">
          <v-icon
            class="mr-2"
            color="error"
          >
            $delete
          </v-icon>
          Delete Question
        </v-card-title>
        <v-card-text>
          <div class="ds-mb-3">
            Are you sure you want to delete this question?
          </div>
          <v-alert
            type="warning"
            variant="tonal"
            class="ds-mb-3"
            :icon="false"
          >
            This action cannot be undone.
          </v-alert>
          <v-card
            variant="outlined"
            class="ds-p-3"
          >
            <div class="ds-text-xs text-medium-emphasis ds-mb-1">
              Question
            </div>
            <div class="ds-text-sm">
              {{ deleteTargetQuestion?.question_text }}
            </div>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            class="ds-btn"
            variant="text"
            :disabled="saving"
            @click="cancelDelete"
          >
            Cancel
          </v-btn>
          <v-btn
            class="ds-btn"
            color="error"
            :loading="saving"
            @click="confirmDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Category Delete Confirmation Dialog -->
    <v-dialog
      v-model="showCategoryDeleteDialog"
      max-width="560px"
    >
      <v-card class="ds-card">
        <v-card-title class="d-flex align-center ds-text-xl ds-font-semibold">
          <v-icon
            class="mr-2"
            color="error"
          >
            $delete
          </v-icon>
          Delete Category
        </v-card-title>
        <v-card-text>
          <div class="ds-mb-3">
            Are you sure you want to delete
            <strong>{{ deleteCategoryTarget?.display_name }}</strong>
            and all of its questions?
          </div>
          <v-alert
            type="warning"
            variant="tonal"
            class="ds-mb-3"
            :icon="false"
          >
            This action cannot be undone. All questions in this category will be permanently deleted.
          </v-alert>
          <v-card
            variant="outlined"
            class="ds-p-3"
          >
            <div class="ds-text-xs text-medium-emphasis ds-mb-1">
              Summary
            </div>
            <div class="ds-text-sm">
              {{ (questionsByCat[deleteCategoryTarget?.id] || []).length }} questions will be deleted
            </div>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            class="ds-btn"
            variant="text"
            :disabled="saving"
            @click="cancelDeleteCategory"
          >
            Cancel
          </v-btn>
          <v-btn
            class="ds-btn"
            color="error"
            :loading="saving"
            @click="confirmDeleteCategory"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import api from '@/services/api'

const emit = defineEmits(['update-selected-categories', 'update-question-selection', 'changed', 'edit-category'])

const loading = ref(false)
const error = ref('')
const categories = ref([])
const questionsByCat = reactive({})
const selectedCategories = ref([]) // array of category ids
const selectedQuestionsIdsByCat = reactive({}) // catId -> array of question ids

// dialog state
const showDialog = ref(false)
const formRef = ref(null)
const editingQuestion = ref(null) // question object or null
const dialogCategory = ref(null) // category object
const form = reactive({ questionText: '', sortOrder: 0 })
const saving = ref(false)
const showDeleteDialog = ref(false)
const deleteTargetQuestion = ref(null)
const deleteTargetCategory = ref(null)
// category delete state
const showCategoryDeleteDialog = ref(false)
const deleteCategoryTarget = ref(null)

const model = ref([])
const allIds = computed(() => categories.value.map(c => c.id))

const openAll = () => { model.value = [...allIds.value] }
const closeAll = () => { model.value = [] }


// Debounced load function to prevent infinite loops
let loadTimeout = null
const load = async (force = false) => {
  // Prevent multiple simultaneous loads unless forced
  if (loading.value && !force) return

  // Debounce non-forced loads
  if (!force) {
    if (loadTimeout) clearTimeout(loadTimeout)
    loadTimeout = setTimeout(() => load(true), 300)
    return
  }

  try {
    loading.value = true
    error.value = ''
    const cats = await api.getFollowupCategories()
    categories.value = cats || []

    // Load questions in smaller batches to prevent overwhelming the API
    const batchSize = 3
    for (let i = 0; i < categories.value.length; i += batchSize) {
      const batch = categories.value.slice(i, i + batchSize)
      await Promise.all(batch.map(async (c) => {
        try {
          const qs = await api.getFollowupQuestions({ category_id: c.id, active_only: false })
          questionsByCat[c.id] = qs || []
          // ensure selection buckets exist and are valid
          const existing = selectedQuestionsIdsByCat[c.id] || []
          const validIdsSet = new Set((qs || []).map(q => q.id))
          selectedQuestionsIdsByCat[c.id] = existing.filter(id => validIdsSet.has(id))
        } catch (e) {
          console.warn('Failed loading questions for category', c.id, e)
          questionsByCat[c.id] = []
          selectedQuestionsIdsByCat[c.id] = []
        }
      }))
      // Small delay between batches to prevent API overload
      if (i + batchSize < categories.value.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }

    // prune selected categories to still-existing ones
    const existingCatIds = new Set(categories.value.map(c => c.id))
    selectedCategories.value = selectedCategories.value.filter(id => existingCatIds.has(id))
    // Keep accordions closed by default
    // model.value = [...allIds.value]
  } catch (e) {
    console.error(e)
    error.value = 'Failed to load categories/questions'
  } finally {
    loading.value = false
  }
}

onMounted(load)

// Reload data on tenant change to keep categories/questions in sync per org
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await load(true)
  }
}, { deep: true })

// event emitters
const emitSelectedCategories = () => {
  const selected = categories.value.filter(c => selectedCategories.value.includes(c.id))
  emit('update-selected-categories', selected)
}

const emitSelectedQuestions = (catId) => {
  const ids = selectedQuestionsIdsByCat[catId] || []
  const qs = (questionsByCat[catId] || []).filter(q => ids.includes(q.id))
  emit('update-question-selection', catId, qs)
}

// toggle active/inactive
const toggleActive = async (cat, q) => {
  try {
    saving.value = true
    await api.updateFollowupQuestion(q.id, { is_active: !q.is_active })
    await refreshCategoryQuestions(cat.id)
    emit('changed')
  } catch (e) {
    console.error('Failed to toggle active state', e)
  } finally {
    saving.value = false
  }
}

// delete helpers
const openDeleteDialog = (cat, q) => {
  deleteTargetCategory.value = cat
  deleteTargetQuestion.value = q
  showDeleteDialog.value = true
}

const cancelDelete = () => {
  showDeleteDialog.value = false
  deleteTargetCategory.value = null
  deleteTargetQuestion.value = null
}

const confirmDelete = async () => {
  if (!deleteTargetQuestion.value || !deleteTargetCategory.value) return
  try {
    saving.value = true
    await api.deleteFollowupQuestion(deleteTargetQuestion.value.id)
    const catId = deleteTargetCategory.value.id
    // prune selection for this category
    const ids = selectedQuestionsIdsByCat[catId] || []
    selectedQuestionsIdsByCat[catId] = ids.filter(id => id !== deleteTargetQuestion.value.id)
    await refreshCategoryQuestions(catId)
    emit('changed')
  } catch (e) {
    console.error('Failed to delete question', e)
  } finally {
    saving.value = false
    cancelDelete()
  }
}

// category editing
const openEditCategoryDialog = (cat) => {
  emit('edit-category', cat)
}

// category deletion
const openDeleteCategoryDialog = (cat) => {
  deleteCategoryTarget.value = cat
  showCategoryDeleteDialog.value = true
}

const cancelDeleteCategory = () => {
  showCategoryDeleteDialog.value = false
  deleteCategoryTarget.value = null
}

const confirmDeleteCategory = async () => {
  if (!deleteCategoryTarget.value) return
  try {
    saving.value = true
    await api.deleteFollowupCategoryWithStrategyNormalized({
      categoryId: deleteCategoryTarget.value.id,
      strategy: 'delete'
    })
    await load()
    emit('changed')
  } catch (e) {
    console.error('Failed to delete category', e)
  } finally {
    saving.value = false
    cancelDeleteCategory()
  }
}

// toggle category active/inactive
const toggleCategoryActive = async (cat) => {
  try {
    saving.value = true
    await api.updateFollowupCategory(cat.id, { is_active: !cat.is_active })
    cat.is_active = !cat.is_active
    emit('changed')
  } catch (e) {
    console.error('Failed to toggle category active state', e)
  } finally {
    saving.value = false
  }
}

// reordering helpers (swap adjacent sort_order values)
const moveUp = async (cat, idx) => {
  if (idx <= 0) return
  await swapQuestions(cat.id, idx, idx - 1)
}

const moveDown = async (cat, idx) => {
  const list = questionsByCat[cat.id] || []
  if (idx >= list.length - 1) return
  await swapQuestions(cat.id, idx, idx + 1)
}

const swapQuestions = async (catId, i, j) => {
  const list = questionsByCat[catId] || []
  const q1 = list[i]
  const q2 = list[j]
  if (!q1 || !q2) return
  try {
    saving.value = true
    await Promise.all([
      api.updateFollowupQuestion(q1.id, { sort_order: q2.sort_order }),
      api.updateFollowupQuestion(q2.id, { sort_order: q1.sort_order })
    ])
    await refreshCategoryQuestions(catId)
    emit('changed')
  } catch (e) {
    console.error('Failed to reorder questions', e)
  } finally {
    saving.value = false
  }
}

// dialog helpers
const openAddDialog = (cat) => {
  dialogCategory.value = cat
  editingQuestion.value = null
  form.questionText = ''
  // choose next sort order based on existing max to avoid collisions
  const list = questionsByCat[cat.id] || []
  const maxOrder = list.length ? Math.max(...list.map(q => Number(q.sort_order) || 0)) : -1
  form.sortOrder = maxOrder + 1
  showDialog.value = true
}

const openEditDialog = (cat, q) => {
  dialogCategory.value = cat
  editingQuestion.value = q
  form.questionText = q.question_text
  form.sortOrder = q.sort_order
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const refreshCategoryQuestions = async (catId) => {
  try {
    const qs = await api.getFollowupQuestions({ category_id: catId, active_only: false })
    questionsByCat[catId] = qs || []
  } catch (e) {
    console.warn('Failed to refresh questions for category', catId, e)
  }
}

const save = async () => {
  if (!dialogCategory.value) return
  const valid = await (formRef.value?.validate?.() || { valid: true })
  if (valid.valid === false) return
  try {
    saving.value = true
    if (!editingQuestion.value) {
      await api.createFollowupQuestion({
        category_id: dialogCategory.value.id,
        question_text: form.questionText.trim(),
        sort_order: form.sortOrder ?? 0
      })
    } else {
      // Only update text during edit – use the single-item endpoint
      const trimmed = form.questionText.trim()
      if (trimmed === editingQuestion.value.question_text) {
        showDialog.value = false
        return
      }
      await api.updateFollowupQuestion(editingQuestion.value.id, { question_text: trimmed })
    }
    await refreshCategoryQuestions(dialogCategory.value.id)
    showDialog.value = false
    emit('changed')
  } catch (e) {
    console.error('Failed to save question', e)
  } finally {
    saving.value = false
  }
}

// Expose methods for parent component
defineExpose({
  load
})
</script>

<style scoped>
.followup-container {
  padding: 16px;
}

.followup-panels :deep(.v-expansion-panel-title) {
  padding: 10px 12px;
}

.category-title-row {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.category-title-row:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

/* Category actions are always visible */
.category-actions {
  opacity: 1;
  transition: opacity 0.15s ease;
}

.inactive-indicator {
  color: rgb(var(--v-theme-warning));
}

.question-panel-content {
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-left: 2px solid rgba(var(--v-theme-primary), 0.18);
}

/* Increase inner X-padding of panel content to match Welcome styling */
.question-panel-content :deep(.v-expansion-panel-text__wrapper) {
  padding-left: 22px !important;
  padding-right: 22px !important;
}

.questions-list {
  margin-top: 8px;
}

.question-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* Increase horizontal padding for better readability */
  padding: 14px 22px;
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
  flex-direction: column; /* stack text and meta on separate lines */
  justify-content: flex-start;
  align-items: flex-start;
  width: 100%;
}

.question-text {
  white-space: normal;
}

/* Emphasize inactive state on the question meta line */
.inactive-question {
  color: rgb(var(--v-theme-warning));
  font-weight: 600;
}

.question-action-btn {
  opacity: 0.8;
}

/* Ensure action cluster is aligned to the far right */
.question-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

/* Ensure the row wrapper distributes content to the ends */
.question-item > .d-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.empty-questions {
  border: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.add-question-section {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Clean category title */
.category-title-clean {
  padding: 16px 20px;
}

.category-info {
  min-width: 0;
  flex: 1;
}

.category-name {
  line-height: 1.3;
}

.category-meta {
  line-height: 1.2;
  font-size: 0.85rem;
  color: rgba(var(--v-theme-on-surface), 0.70);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Category actions are always visible */
.category-actions {
  opacity: 1;
  transition: opacity 0.2s ease;
  display: flex;
  gap: 4px;
}

.category-action-btn {
  min-width: 32px !important;
  width: 32px;
  height: 32px;
}

.category-checkbox {
  margin-right: 12px !important;
}

/* Enhanced inactive indicator styling */
.inactive-indicator {
  color: rgb(var(--v-theme-warning));
  font-weight: 600;
  background: rgba(var(--v-theme-warning), 0.12);
  padding: 1px 8px;
  border-radius: 6px;
}

/* Question panel content - consolidated styling */
.question-panel-content {
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-left: 2px solid rgba(var(--v-theme-primary), 0.18);
  padding: 20px !important;
}

/* Enhanced empty questions styling */
.empty-questions {
  padding: 24px 0;
  border: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

/* Visual hierarchy improvements */
.v-expansion-panels {
  gap: 8px;
}

.v-expansion-panel {
  border: 1px solid rgba(var(--v-theme-outline), 0.08) !important;
  border-radius: 12px !important;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
}

.v-expansion-panel:not(:last-child) {
  margin-bottom: 8px;
}

/* Active/expanded panel header styling */
.v-expansion-panel--active .v-expansion-panel-title {
  background: rgba(var(--v-theme-primary), 0.08) !important;
}

.v-expansion-panel--active .v-expansion-panel-title:hover {
  background: rgba(var(--v-theme-primary), 0.12) !important;
}

/* Reduce visual noise from checkboxes */
.v-selection-control {
  margin: 0;
}

.v-selection-control__wrapper {
  margin-right: 0 !important;
}
</style>
