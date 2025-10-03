<template>
  <div class="question-manager pa-2">
    <div class="d-flex justify-space-between align-center mb-3">
      <div class="text-subtitle-2 text-medium-emphasis">
        Questions in {{ category.display_name }}
      </div>
      <v-btn
        color="primary"
        size="small"
        prepend-icon="$plus"
        :disabled="saving || !category.is_active"
        @click="openAddDialog()"
      >
        Add Question
      </v-btn>
    </div>

    <v-card
      v-if="loading"
      variant="tonal"
      class="text-center pa-6"
    >
      <v-progress-circular
        indeterminate
        color="primary"
        class="mb-2"
      />
      <div class="text-body-2">
        Loading questions…
      </div>
    </v-card>

    <v-card
      v-else-if="!questions.length"
      variant="tonal"
      class="text-center pa-6"
    >
      <v-icon
        size="40"
        color="grey-lighten-1"
      >
        $help-circle-outline
      </v-icon>
      <div class="text-subtitle-2 mt-2 mb-3">
        No questions yet
      </div>
      <v-btn
        color="primary"
        prepend-icon="$plus"
        :disabled="!category.is_active"
        @click="openAddDialog()"
      >
        Add Question
      </v-btn>
    </v-card>

    <v-list
      v-else
      density="comfortable"
      class="pa-0"
    >
      <v-list-item
        v-for="(q, idx) in questions"
        :key="q.id"
        class="px-0"
        :class="{ 'question--inactive': !q.is_active }"
      >
        <template #prepend>
          <v-checkbox
            :model-value="selectedIds.includes(q.id)"
            :value="q.id"
            hide-details
            density="compact"
            class="mr-3"
            @click.stop
            @update:model-value="toggleSelection(q, $event)"
          />
        </template>

        <v-list-item-title class="mr-2">
          {{ q.question_text }}
        </v-list-item-title>
        <v-list-item-subtitle>Order: {{ q.sort_order }} • Active: {{ q.is_active ? 'Yes' : 'No' }}</v-list-item-subtitle>

        <template #append>
          <v-btn
            icon="$arrow-up"
            size="x-small"
            variant="text"
            class="mr-1"
            :disabled="saving || idx === 0"
            @click.stop="moveUp(idx)"
          />
          <v-btn
            icon="$arrow-down"
            size="x-small"
            variant="text"
            class="mr-1"
            :disabled="saving || idx === questions.length - 1"
            @click.stop="moveDown(idx)"
          />
          <v-btn
            :icon="q.is_active ? '$eye-off' : '$eye'"
            size="x-small"
            variant="text"
            class="mr-1"
            :disabled="saving"
            @click.stop="toggleActive(q)"
          />
          <v-btn
            icon="$edit"
            size="x-small"
            variant="text"
            class="mr-1"
            :disabled="saving"
            @click.stop="openEditDialog(q)"
          />
          <v-btn
            icon="$delete"
            size="x-small"
            variant="text"
            color="error"
            :disabled="saving"
            @click.stop="openDeleteDialog(q)"
          />
        </template>
      </v-list-item>
    </v-list>

    <!-- Add/Edit Dialog -->
    <v-dialog
      v-model="showDialog"
      max-width="560px"
    >
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">
            $help-circle
          </v-icon>
          {{ editing ? 'Edit Question' : 'Add Question' }}
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
              label="Sort Order"
              type="number"
              :disabled="editing"
              :hint="editing ? 'Reorder with arrows' : 'Lower appears first'"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="saving"
            @click="closeDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            @click="save"
          >
            {{ editing ? 'Update' : 'Add' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="520px"
    >
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon
            class="mr-2"
            color="error"
          >
            $delete
          </v-icon>
          Delete Question
        </v-card-title>
        <v-card-text>
          <div class="mb-3">
            Are you sure you want to delete this question?
          </div>
          <v-card
            variant="outlined"
            class="pa-3"
          >
            <div class="text-caption text-medium-emphasis mb-1">
              Question
            </div>
            <div class="text-body-2">
              {{ deleteTarget?.question_text }}
            </div>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="saving"
            @click="cancelDelete"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="saving"
            @click="confirmDelete"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import api from '@/services/api'

const props = defineProps({
  category: { type: Object, required: true },
  selectedQuestions: { type: Array, default: () => [] }
})

const emit = defineEmits(['questions-updated', 'selection-changed'])

const loading = ref(false)
const saving = ref(false)
const questions = ref([])

// selection
const selectedIds = ref([])
watch(() => props.selectedQuestions, (val) => {
  selectedIds.value = (val || []).map(q => q.id)
}, { immediate: true, deep: true })

const formRef = ref(null)
const showDialog = ref(false)
const editing = ref(false)
const editTarget = ref(null)
const form = reactive({ questionText: '', sortOrder: 0 })

const showDeleteDialog = ref(false)
const deleteTarget = ref(null)

const loadQuestions = async () => {
  try {
    loading.value = true
    const res = await api.getFollowupQuestions({ category_id: props.category.id, active_only: false })
    questions.value = res || []
  } catch (e) {
    questions.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadQuestions)
watch(() => props.category.id, () => loadQuestions())

const toggleSelection = (q, selected) => {
  const set = new Set(selectedIds.value)
  if (selected) set.add(q.id); else set.delete(q.id)
  selectedIds.value = Array.from(set)
  const selectedQs = questions.value.filter(x => selectedIds.value.includes(x.id))
  emit('selection-changed', selectedQs)
}

const openAddDialog = () => {
  editing.value = false
  editTarget.value = null
  form.questionText = ''
  const list = questions.value || []
  const maxOrder = list.length ? Math.max(...list.map(q => Number(q.sort_order) || 0)) : -1
  form.sortOrder = maxOrder + 1
  showDialog.value = true
}

const openEditDialog = (q) => {
  editing.value = true
  editTarget.value = q
  form.questionText = q.question_text
  form.sortOrder = q.sort_order
  showDialog.value = true
}

const closeDialog = () => { showDialog.value = false }

const save = async () => {
  const valid = await (formRef.value?.validate?.() || { valid: true })
  if (valid.valid === false) return
  try {
    saving.value = true
    if (!editing.value) {
      await api.createFollowupQuestion({
        category_id: props.category.id,
        question_text: form.questionText.trim(),
        sort_order: form.sortOrder ?? 0
      })
    } else {
      const trimmed = form.questionText.trim()
      if (trimmed !== editTarget.value.question_text) {
        await api.updateFollowupQuestion(editTarget.value.id, { question_text: trimmed })
      }
    }
    await loadQuestions()
    showDialog.value = false
    emit('questions-updated')
  } catch (e) {
    // no-op
  } finally {
    saving.value = false
  }
}

const toggleActive = async (q) => {
  try {
    saving.value = true
    await api.updateFollowupQuestion(q.id, { is_active: !q.is_active })
    await loadQuestions()
    emit('questions-updated')
  } finally {
    saving.value = false
  }
}

const moveUp = async (idx) => {
  if (idx === 0) return
  await swap(idx, idx - 1)
}
const moveDown = async (idx) => {
  if (idx >= questions.value.length - 1) return
  await swap(idx, idx + 1)
}
const swap = async (i, j) => {
  const a = questions.value[i]
  const b = questions.value[j]
  try {
    saving.value = true
    await Promise.all([
      api.updateFollowupQuestion(a.id, { sort_order: b.sort_order }),
      api.updateFollowupQuestion(b.id, { sort_order: a.sort_order })
    ])
    await loadQuestions()
    emit('questions-updated')
  } finally {
    saving.value = false
  }
}

const openDeleteDialog = (q) => {
  deleteTarget.value = q
  showDeleteDialog.value = true
}
const cancelDelete = () => { showDeleteDialog.value = false; deleteTarget.value = null }
const confirmDelete = async () => {
  if (!deleteTarget.value) return
  try {
    saving.value = true
    await api.deleteFollowupQuestion(deleteTarget.value.id)
    await loadQuestions()
    emit('questions-updated')
  } finally {
    saving.value = false
    cancelDelete()
  }
}
</script>

<style scoped>
.question--inactive { opacity: 0.75 }
</style>

