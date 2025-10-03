<template>
  <div class="content-gaps-table">
    <!-- Header with filters -->
    <div class="d-flex justify-space-between align-center mb-4">
      <div class="d-flex align-center gap-4">
        <h2 class="text-h6 font-weight-bold">
          Content Gaps
        </h2>
        <v-chip
          :color="showResolved ? 'success' : 'warning'"
          variant="tonal"
          size="small"
        >
          {{ gaps.length }} {{ showResolved ? 'Total' : 'Unresolved' }} Gaps
        </v-chip>
      </div>

      <div class="d-flex align-center gap-2">
        <v-switch
          v-model="showResolved"
          :label="showResolved ? 'Show All' : 'Unresolved Only'"
          color="primary"
          hide-details
          inset
          class="mr-4"
          @update:model-value="fetchGaps"
        />

        <v-btn
          color="primary"
          variant="outlined"
          prepend-icon="$refresh"
          :loading="loading"
          @click="fetchGaps"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="loading && gaps.length === 0"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
      <p class="text-body-2 mt-2 text-medium-emphasis">
        Loading content gaps...
      </p>
    </div>

    <!-- Empty State -->
    <v-card v-else-if="!loading && gaps.length === 0">
      <v-card-text class="text-center py-8">
        <v-icon
          size="64"
          color="success"
          class="mb-4"
        >
          $check-circle
        </v-icon>
        <h3 class="text-h6 mb-2">
          No Content Gaps Found
        </h3>
        <p class="text-body-2 text-medium-emphasis">
          {{ showResolved ? 'No content gaps have been detected.' : 'All content gaps have been resolved!' }}
        </p>
      </v-card-text>
    </v-card>

    <!-- Gaps Table -->
    <v-card v-else>
      <v-table hover>
        <thead>
          <tr>
            <th class="text-left font-weight-bold">
              Pattern
            </th>
            <th class="text-center font-weight-bold">
              Count
            </th>
            <th class="text-center font-weight-bold">
              Avg Score
            </th>
            <th class="text-center font-weight-bold">
              First Seen
            </th>
            <th class="text-center font-weight-bold">
              Last Seen
            </th>
            <th class="text-center font-weight-bold">
              Status
            </th>
            <th class="text-center font-weight-bold">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="gap in gaps"
            :key="gap.id"
          >
            <!-- Pattern -->
            <td class="py-4">
              <div class="d-flex flex-column">
                <span class="font-weight-medium">{{ gap.pattern }}</span>
                <span
                  v-if="gap.sample_query"
                  class="text-caption text-medium-emphasis mt-1"
                  style="max-width: 300px;"
                >
                  Sample: "{{ truncateText(gap.sample_query, 60) }}"
                </span>
              </div>
            </td>

            <!-- Count -->
            <td class="text-center">
              <v-chip
                :color="getCountColor(gap.count)"
                variant="tonal"
                size="small"
              >
                {{ gap.count }}
              </v-chip>
            </td>

            <!-- Average Score -->
            <td class="text-center">
              <div class="d-flex flex-column align-center">
                <span class="font-weight-medium">{{ gap.avg_score.toFixed(2) }}</span>
                <v-progress-linear
                  :model-value="gap.avg_score * 100"
                  :color="getScoreColor(gap.avg_score)"
                  height="4"
                  class="mt-1"
                  style="width: 60px;"
                />
              </div>
            </td>

            <!-- First Seen -->
            <td class="text-center text-caption">
              {{ formatDate(gap.first_seen) }}
            </td>

            <!-- Last Seen -->
            <td class="text-center text-caption">
              {{ formatDate(gap.last_seen) }}
            </td>

            <!-- Status -->
            <td class="text-center">
              <v-chip
                :color="gap.resolved ? 'success' : 'warning'"
                :variant="gap.resolved ? 'flat' : 'tonal'"
                size="small"
              >
                {{ gap.resolved ? 'Resolved' : 'Open' }}
              </v-chip>
            </td>

            <!-- Actions -->
            <td class="text-center">
              <div class="d-flex justify-center gap-1">
                <v-btn
                  v-if="!gap.resolved"
                  color="success"
                  variant="text"
                  size="small"
                  icon="$check"
                  :loading="resolvingIds.has(gap.id)"
                  @click="markResolved(gap)"
                >
                  <v-icon>$check</v-icon>
                  <v-tooltip activator="parent">
                    Mark as Resolved
                  </v-tooltip>
                </v-btn>

                <v-btn
                  v-else
                  color="warning"
                  variant="text"
                  size="small"
                  icon="$undo"
                  :loading="resolvingIds.has(gap.id)"
                  @click="markUnresolved(gap)"
                >
                  <v-icon>$undo</v-icon>
                  <v-tooltip activator="parent">
                    Mark as Unresolved
                  </v-tooltip>
                </v-btn>

                <v-btn
                  color="primary"
                  variant="text"
                  size="small"
                  icon="$note-edit"
                  @click="openNotesDialog(gap)"
                >
                  <v-icon>$note-edit</v-icon>
                  <v-tooltip activator="parent">
                    Edit Notes
                  </v-tooltip>
                </v-btn>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Notes Dialog -->
    <v-dialog
      v-model="notesDialog.show"
      max-width="700px"
    >
      <v-card
        class="dialog-card"
        elevation="8"
      >
        <v-card-title class="dialog-header pa-6">
          <div class="d-flex align-center">
            <v-icon
              class="me-3"
              color="primary"
            >
              $note-edit
            </v-icon>
            <div>
              <h2 class="text-h6 font-weight-bold">
                Edit Notes
              </h2>
              <p class="text-body-2 text-medium-emphasis ma-0">
                Add notes for this content gap
              </p>
            </div>
          </div>
        </v-card-title>

        <v-divider class="border-opacity-25" />

        <v-card-text class="pa-6">
          <div class="mb-6">
            <h3 class="text-h7 font-weight-bold mb-3 text-primary">
              Content Gap Pattern
            </h3>
            <v-card
              variant="tonal"
              color="warning"
              class="pa-4 rounded-lg"
            >
              <div class="text-body-2 font-mono">
                {{ notesDialog.gap?.pattern }}
              </div>
            </v-card>
          </div>

          <div>
            <h3 class="text-h7 font-weight-bold mb-3 text-primary">
              Notes
            </h3>
            <v-textarea
              v-model="notesDialog.notes"
              placeholder="Add notes about this content gap, potential solutions, or action items..."
              rows="5"
              variant="outlined"
              counter
              :rules="[v => !v || v.length <= 500 || 'Notes must be less than 500 characters']"
              class="rounded-lg"
              auto-grow
            />
          </div>
        </v-card-text>

        <v-divider class="border-opacity-25" />

        <v-card-actions class="pa-6">
          <v-spacer />
          <v-btn 
            variant="outlined" 
            prepend-icon="$close"
            class="rounded-lg"
            @click="closeNotesDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            prepend-icon="$save"
            :loading="notesDialog.saving"
            class="rounded-lg"
            @click="saveNotes"
          >
            Save Notes
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Loading overlay for actions -->
    <v-overlay
      :model-value="loading && gaps.length > 0"
      contained
    >
      <v-progress-circular indeterminate />
    </v-overlay>

    <!-- Toasts are handled globally via NotificationMessage -->
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, reactive } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import api from '@/services/api'

// Define emits
const emit = defineEmits(['stats-updated'])

// Reactive state
const gaps = ref([])
const loading = ref(false)
const showResolved = ref(false)
const resolvingIds = reactive(new Set())

const notesDialog = ref({
  show: false,
  gap: null,
  notes: '',
  saving: false
})

// Notifications
const { showSuccess, showError, showInfo, showWarning } = useNotifications()

// Methods
const showSnackbar = (message, color = 'success') => {
  const map = {
    success: showSuccess,
    error: showError,
    info: showInfo,
    warning: showWarning,
  }
  const fn = map[color] || showInfo
  fn(message)
}

const fetchGaps = async () => {
  try {
    loading.value = true
    const response = await api.getContentGaps({
      resolved: showResolved.value,
      limit: 100
    })
    gaps.value = response.gaps || []
  } catch (error) {
    console.error('Failed to fetch content gaps:', error)
    showSnackbar('Failed to fetch content gaps', 'error')
  } finally {
    loading.value = false
  }
}

const markResolved = async (gap) => {
  try {
    resolvingIds.add(gap.id)
    await api.updateContentGap(gap.id, { resolved: true })
    gap.resolved = true
    showSnackbar(`Content gap "${truncateText(gap.pattern, 30)}" marked as resolved`)
  } catch (error) {
    console.error('Failed to mark gap as resolved:', error)
    showSnackbar('Failed to mark gap as resolved', 'error')
  } finally {
    resolvingIds.delete(gap.id)
  }
}

const markUnresolved = async (gap) => {
  try {
    resolvingIds.add(gap.id)
    await api.updateContentGap(gap.id, { resolved: false })
    gap.resolved = false
    showSnackbar(`Content gap "${truncateText(gap.pattern, 30)}" marked as unresolved`)
  } catch (error) {
    console.error('Failed to mark gap as unresolved:', error)
    showSnackbar('Failed to mark gap as unresolved', 'error')
  } finally {
    resolvingIds.delete(gap.id)
  }
}

const openNotesDialog = (gap) => {
  notesDialog.value = {
    show: true,
    gap: gap,
    notes: gap.notes || '',
    saving: false
  }
}

const closeNotesDialog = () => {
  notesDialog.value.show = false
}

const saveNotes = async () => {
  try {
    notesDialog.value.saving = true
    const gap = notesDialog.value.gap
    await api.updateContentGap(gap.id, { notes: notesDialog.value.notes })
    gap.notes = notesDialog.value.notes
    closeNotesDialog()
    showSnackbar('Notes saved successfully')
  } catch (error) {
    console.error('Failed to save notes:', error)
    showSnackbar('Failed to save notes', 'error')
  } finally {
    notesDialog.value.saving = false
  }
}

// Utility functions
const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getCountColor = (count) => {
  if (count >= 10) return 'error'
  if (count >= 5) return 'warning'
  return 'info'
}

const getScoreColor = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'error'
}

// Computed stats
const stats = computed(() => {
  const total = gaps.value.length
  const resolved = gaps.value.filter(g => g.resolved).length
  const unresolved = total - resolved
  const avgScore = total > 0
    ? (gaps.value.reduce((sum, g) => sum + g.avg_score, 0) / total).toFixed(2)
    : '0.00'

  return {
    total,
    resolved,
    unresolved,
    avgScore
  }
})

// Watch for stats changes and emit
watch(stats, (newStats) => {
  emit('stats-updated', newStats)
}, { immediate: true })

// Lifecycle
onMounted(() => {
  fetchGaps()
})
</script>

<style scoped>
.content-gaps-table {
  width: 100%;
}

.v-table th {
  background-color: rgb(var(--v-theme-surface-variant));
  font-weight: 600;
}

.v-table tbody tr:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

/* Dialog Styles */
.dialog-card {
  border-radius: 16px !important;
  overflow: hidden;
}

.dialog-header {
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.04), rgba(var(--v-theme-primary), 0.02));
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

:deep(.v-textarea .v-field) {
  border-radius: 12px;
}
</style>
