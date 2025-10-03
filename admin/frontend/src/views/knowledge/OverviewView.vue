<template>
  <div class="overview-view">
    <!-- Upload Section -->
    <v-card class="mb-6">
      <v-card-title class="text-h6">
        <v-icon class="me-2">
          $upload
        </v-icon>
        Upload Documents
      </v-card-title>
      <v-card-text class="pa-6">
        <v-file-input
          v-model="selectedFiles"
          label="Select files to upload"
          multiple
          accept=".md,.pdf,.json,.txt,.html,.docx"
          prepend-icon="$attach_file"
          variant="outlined"
          chips
          counter
          show-size
          :rules="fileRules"
        >
          <template #selection="{ fileNames }">
            <template
              v-for="(fileName, index) in fileNames"
              :key="fileName"
            >
              <v-chip
                v-if="index < 3"
                color="primary"
                size="small"
                class="me-2"
              >
                {{ fileName }}
              </v-chip>
              <span
                v-else-if="index === 3"
                class="text-overline grey--text"
              >
                +{{ fileNames.length - 3 }} File(s)
              </span>
            </template>
          </template>
        </v-file-input>

        <!-- Action notifications are shown via global toasts -->

        <div class="mt-4 d-flex gap-2">
          <v-btn
            color="primary"
            :disabled="!selectedFiles?.length || uploading"
            :loading="uploading"
            prepend-icon="$cloud_upload"
            class="mr-4"
            @click="uploadFiles"
          >
            Upload Files
          </v-btn>
          <v-btn
            variant="outlined"
            :disabled="!selectedFiles?.length || uploading"
            @click="clearSelection"
          >
            Clear
          </v-btn>
        </div>

        <!-- Inline refresh status (non-intrusive) -->
        <div
          v-if="refreshing"
          class="mt-2 text-caption text-medium-emphasis d-flex align-center"
        >
          <v-icon
            size="16"
            class="mr-1"
          >
            $refresh
          </v-icon>
          <span>
            Refreshing
            <template v-if="refreshInfo.current_file">: {{ refreshInfo.current_file }}</template>
            <template v-if="refreshInfo.files_processed"> — {{ refreshInfo.files_processed }} processed</template>
          </span>
        </div>

        <v-divider class="my-4" />

        <div class="text-body-2 text-medium-emphasis">
          <v-icon
            size="small"
            class="me-1"
          >
            $info
          </v-icon>
          <strong>Supported formats:</strong> .md, .pdf, .json, .txt, .html, .docx
          <br>
          <v-icon
            size="small"
            class="me-1"
          >
            $info
          </v-icon>
          <strong>Note:</strong> Files will be automatically indexed after upload. Use the "Re-Index" button above to force re-indexing if needed.
        </div>
      </v-card-text>
    </v-card>

    <!-- File List -->
    <v-card>
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2">
          $format-list-bulleted
        </v-icon>
        Knowledge Base Files
        <v-spacer />
      </v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="fileHeaders"
          :items="files"
          :loading="loadingFiles"
          item-key="name"
        >
          <template #[`item.name`]="{ item }">
            <div class="d-flex align-center">
              <v-icon
                :color="getFileIcon(item.name).color"
                class="me-2"
              >
                {{ getFileIcon(item.name).icon }}
              </v-icon>
              {{ item.name }}
            </div>
          </template>
          <template #[`item.size`]="{ item }">
            {{ formatFileSize(item.size) }}
          </template>
          <template #[`item.modified`]="{ item }">
            {{ formatDate(item.modified) }}
          </template>
          <template #[`item.actions`]="{ item }">
            <v-btn
              v-if="canEdit(item.name)"
              icon="$edit"
              variant="text"
              size="small"
              color="primary"
              class="me-1"
              @click="openFileEditor(item)"
            />
            <v-btn
              icon="$delete"
              variant="text"
              size="small"
              color="error"
              @click="confirmDelete(item)"
            />
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="deleteDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Confirm Delete</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ fileToDelete?.name }}"?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            text
            @click="deleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deleting"
            @click="deleteFile"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- File Editor Modal -->
    <FileEditorModal
      v-model="editorDialog"
      :filename="selectedFilename"
      @file-saved="onFileSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'
import FileEditorModal from '@/components/FileEditorModal.vue'
import { useNotifications } from '@/composables/useNotifications'

const props = defineProps({
  refreshTrigger: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['refresh-complete'])

const selectedFiles = ref([])
const uploading = ref(false)
const refreshing = ref(false)
const loadingFiles = ref(false)
const deleting = ref(false)
const { showSuccess, showError, showInfo } = useNotifications()
const deleteDialog = ref(false)
const fileToDelete = ref(null)
const editorDialog = ref(false)
const selectedFilename = ref('')

const files = ref([])
const refreshInfo = ref({ current_file: null, files_processed: 0, total_files: null })

const fileHeaders = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Type', key: 'type', sortable: true },
  { title: 'Size', key: 'size', sortable: true },
  { title: 'Modified', key: 'modified', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

const fileRules = [
  value => {
    if (!value || !value.length) return true
    const maxSize = 10 * 1024 * 1024 // 10MB
    const oversized = value.some(file => file.size > maxSize)
    return !oversized || 'File size must be less than 10MB'
  }
]

const getFileIcon = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  const iconMap = {
    md: { icon: '$description', color: 'blue' },
    pdf: { icon: '$picture_as_pdf', color: 'red' },
    json: { icon: '$data_object', color: 'orange' },
    txt: { icon: '$text_snippet', color: 'grey' },
    html: { icon: '$language', color: 'orange' },
    docx: { icon: '$article', color: 'blue' }
  }
  return iconMap[ext] || { icon: '$insert_drive_file', color: 'grey' }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))  } ${  sizes[i]}`
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleDateString()
}

const tenantStore = useTenantStore()

const uploadFiles = async () => {
  if (!selectedFiles.value?.length) return

  uploading.value = true

  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })

    await adminAPI.uploadKnowledgeFiles(formData)

    showSuccess(`Successfully uploaded ${selectedFiles.value.length} file(s)`)
    selectedFiles.value = []

    // Refresh data in this view and store cache so other views update
    await Promise.all([
      loadFiles(),
      tenantStore.loadKnowledgeSources(true),
      tenantStore.loadKnowledgeStats(true)
    ])
  } catch (error) {
    console.error('Upload error:', error)
    showError(error.response?.data?.detail || 'Failed to upload files')
  } finally {
    uploading.value = false
  }
}

const refreshKnowledgeBase = async () => {
  refreshing.value = true

  try {
    // Start the refresh
    const startResult = await adminAPI.refreshKnowledgeBase(true)

    if (startResult.status === 'running') {
      showInfo('Knowledge base refresh started...')
      refreshInfo.value = { current_file: null, files_processed: 0, total_files: null }

      // Poll for status updates
      const pollInterval = setInterval(async () => {
        try {
          const status = await adminAPI.getRefreshStatus()

          // Update inline status
          if (status.progress) {
            refreshInfo.value.current_file = status.progress.current_file || refreshInfo.value.current_file
            refreshInfo.value.files_processed = status.progress.files_processed ?? refreshInfo.value.files_processed
            refreshInfo.value.total_files = status.progress.total_files ?? refreshInfo.value.total_files
          }

          if (status.status === 'completed') {
            clearInterval(pollInterval)
            showSuccess(`Knowledge base refreshed successfully! Processed ${status.progress?.files_processed || 0} files.`)
            refreshing.value = false
            refreshInfo.value = { current_file: null, files_processed: 0, total_files: null }
          } else if (status.status === 'failed') {
            clearInterval(pollInterval)
            showError(`Refresh failed: ${status.progress?.current_file || 'Unknown error'}`)
            refreshing.value = false
            refreshInfo.value = { current_file: null, files_processed: 0, total_files: null }
          }
        } catch (pollError) {
          console.error('Status polling error:', pollError)
          clearInterval(pollInterval)
          showError('Lost connection to refresh process')
          refreshing.value = false
          refreshInfo.value = { current_file: null, files_processed: 0, total_files: null }
        }
      }, 2000) // Poll every 2 seconds

      // Set a timeout for the entire process
      setTimeout(() => {
        if (refreshing.value) {
          clearInterval(pollInterval)
          showError('Refresh operation timed out')
          refreshing.value = false
          refreshInfo.value = { current_file: null, files_processed: 0, total_files: null }
        }
      }, 300000) // 5 minutes timeout
    } else {
      showSuccess(startResult.message || 'Knowledge base refresh completed')
    }
  } catch (error) {
    console.error('Refresh error:', error)
    showError(error.response?.data?.detail || 'Failed to refresh knowledge base')
  } finally {
    if (!refreshing.value) {
      refreshing.value = false
    }
  }
}

const loadFiles = async () => {
  loadingFiles.value = true
  try {
    // Use tenant-scoped DB-backed status endpoint
    const response = await adminAPI.getKnowledgeFilesStatus({ limit: 200 })
    const rows = response.files || response.uploads || []
    // Normalize for table display
    files.value = rows.map(r => ({
      id: r.id,
      name: r.filename || r.name || r.path?.split('/').pop() || 'unknown',
      type: r.ext || r.file_type || '',
      size: r.size || 0,
      modified: r.indexed_at || r.discovered_at || null,
      path: r.path,
      status: r.status || 'unknown',
    }))
    emit('refresh-complete')
  } catch (error) {
    console.error('Failed to load files from DB status, falling back to vector sources:', error)
    try {
      const vec = await adminAPI.getKnowledgeSources()
      const vecList = vec.sources || []
      files.value = vecList.map(v => ({
        id: undefined,
        name: v.path?.split('/').pop() || 'unknown',
        type: v.ext || '',
        size: 0,
        modified: null,
        path: v.path,
        status: 'indexed',
      }))
    } catch (e2) {
      console.error('Vector fallback also failed:', e2)
    }
  } finally {
    loadingFiles.value = false
  }
}

// Watch for refresh trigger from parent
watch(() => props.refreshTrigger, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    loadFiles()
  }
})

const confirmDelete = (file) => {
  fileToDelete.value = file
  deleteDialog.value = true
}

const deleteFile = async () => {
  if (!fileToDelete.value) return

  deleting.value = true
  try {
    // Prefer tenant-scoped delete by file id when available
    if (fileToDelete.value.id) {
      await adminAPI.deleteUpload(fileToDelete.value.id)
      showSuccess(`File deleted successfully`)
    } else {
      // Fallback to legacy delete by filename (non-tenant aware)
      await adminAPI.deleteKnowledgeFile(fileToDelete.value.name)
      showSuccess(`File "${fileToDelete.value.name}" deleted successfully`)
    }

    await loadFiles()
  } catch (error) {
    console.error('Delete error:', error)
    showError('Failed to delete file')
  } finally {
    deleting.value = false
    deleteDialog.value = false
    fileToDelete.value = null
  }
}

const clearSelection = () => {
  selectedFiles.value = []
}

const canEdit = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  return ['json', 'md', 'txt', 'html'].includes(ext)
}

const openFileEditor = (file) => {
  selectedFilename.value = file.name
  editorDialog.value = true
}

const onFileSaved = (filename) => {
  showSuccess(`File "${filename}" saved successfully`)
  // Optionally refresh the file list to update modified time
  loadFiles()
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.overview-view {
  max-width: 1400px;
  margin: 0 auto;
}

.v-file-input :deep(.v-field__input) {
  padding-top: 8px;
}
</style>
