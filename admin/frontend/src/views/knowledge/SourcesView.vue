<template>
  <div class="sources-view">
    <div class="mb-4">
      <v-alert
        type="info"
        variant="tonal"
        class="mb-4"
      >
        <div class="d-flex align-center gap-2">
          <div>
            <strong>Status Legend</strong> — <v-chip
              size="x-small"
              color="success"
            >
              indexed
            </v-chip>: file has chunks in the vector store; <v-chip
              size="x-small"
              color="grey"
            >
              discovered
            </v-chip>: file found on disk but not yet indexed; <v-chip
              size="x-small"
              color="warning"
            >
              orphaned/missing
            </v-chip>: vector or file mismatch; <v-chip
              size="x-small"
              color="error"
            >
              error
            </v-chip>: indexing failed.
          </div>
        </div>
      </v-alert>
      <div class="d-flex justify-end align-center">
        <v-btn
          color="success"
          prepend-icon="$upload"
          variant="text"
          @click="showUploadDialog = true"
        >
          Upload Files
        </v-btn>
      </div>
    </div>

    <!-- Global Indexing Progress (visible even after dialog closes) -->
    <div v-if="indexingProgress.active" class="mb-4">
      <v-card variant="outlined">
        <v-card-text>
          <div class="d-flex align-center justify-space-between mb-2">
            <span class="text-body-2">Re-indexing uploaded files...</span>
            <span class="text-body-2">{{ indexingProgress.completed }}/{{ indexingProgress.total }}</span>
          </div>
          <v-progress-linear
            :model-value="indexingProgress.total ? (indexingProgress.completed / indexingProgress.total) * 100 : 0"
            color="primary"
            height="8"
            rounded
          />
        </v-card-text>
      </v-card>
    </div>

    <v-card>
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2">
          $folder
        </v-icon>
        Source Files and Usage
        <v-spacer />
        <v-text-field
          v-model="search"
          density="compact"
          variant="outlined"
          placeholder="Search sources..."
          hide-details
          style="max-width: 300px"
        />
      </v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="sourceHeaders"
          :items="sources"
          :loading="loading"
          :search="search"
          item-key="path"
        >
          <template #[`item.status`]="{ item }">
            <v-chip
              size="x-small"
              :color="getStatusColor(item.status)"
            >
              {{ (item.status || 'unknown').replace('_', ' ') }}
            </v-chip>
          </template>
          <template #[`item.path`]="{ item }">
            <div class="d-flex align-center">
              <v-icon
                :color="getFileIcon(item.path).color"
                class="me-2"
              >
                {{ getFileIcon(item.path).icon }}
              </v-icon>
              <div
                class="text-truncate"
                style="max-width: 400px"
                :title="item.path"
              >
                {{ item.path }}
              </div>
              <!-- Non-editable indicator at end of path with tooltip -->
              <v-tooltip
                v-if="isNonEditableFile(item.path)"
                :text="getNonEditableTooltip(item.path)"
                location="top"
                :max-width="300"
                content-class="kb-tooltip"
              >
                <template #activator="{ props }">
                  <v-icon
                    v-bind="props"
                    size="18"
                    color="info"
                    class="ms-2"
                  >
                    $help-circle-outline
                  </v-icon>
                </template>
              </v-tooltip>
            </div>
          </template>
          <template #[`item.content_type`]="{ item }">
            <div class="d-flex flex-wrap gap-1 align-center">
              <v-chip
                v-if="item.effective_content_type || item.content_type"
                :color="getContentTypeColor(item.effective_content_type || item.content_type)"
                size="small"
              >
                {{ item.effective_content_type || item.content_type || 'unknown' }}
              </v-chip>
              <v-chip
                v-if="item.metadata_provenance"
                :color="item.metadata_provenance === 'manual' ? 'primary' : 'secondary'"
                size="x-small"
                variant="outlined"
              >
                {{ item.metadata_provenance === 'manual' ? 'Manual' : 'Inferred' }}
              </v-chip>
            </div>
          </template>
          <template #[`item.tags`]="{ item }">
            <div class="d-flex flex-wrap gap-1">
              <v-chip
                v-for="tag in getEffectiveTags(item)"
                :key="tag"
                size="x-small"
                variant="tonal"
              >
                {{ tag }}
              </v-chip>
              <span
                v-if="!getEffectiveTags(item).length"
                class="text-caption text-disabled"
              >No tags</span>
            </div>
          </template>
          <template #[`item.chunk_count`]="{ item }">
            <span class="text-body-2">{{ item.chunk_count }} chunks</span>
          </template>
          <template #[`item.actions`]="{ item }">
            <div class="d-flex align-center gap-1">
              <!-- Edit button with conditional tooltip/disable for non-editable types -->
              <v-tooltip
                v-if="isNonEditableFile(item.path)"
                :text="getNonEditableTooltip(item.path)"
                location="top"
                :max-width="300"
                content-class="kb-tooltip"
              >
                <template #activator="{ props }">
                  <!-- Wrap disabled button in span so tooltip still works -->
                  <span v-bind="props">
                    <v-btn
                      icon="$edit"
                      size="small"
                      variant="text"
                      color="grey"
                      :disabled="true"
                      title="View/Edit File Content"
                    />
                  </span>
                </template>
              </v-tooltip>
              <template v-else>
                <v-btn
                  icon="$edit"
                  size="small"
                  variant="text"
                  color="green"
                  :disabled="loading"
                  title="View/Edit File Content"
                  @click="viewFileContent(item)"
                />
              </template>

              <!-- Edit Metadata button -->
              <v-btn
                icon="$tag"
                size="small"
                variant="text"
                color="orange"
                :disabled="loading"
                title="Edit Metadata (Content Type & Tags)"
                @click="editSource(item)"
              />

              <!-- Reindex button -->
              <v-btn
                icon="$refresh"
                size="small"
                variant="text"
                color="primary"
                :disabled="loading"
                title="Reindex this file"
                @click="reindexSource(item)"
              />

              <!-- Delete button -->
              <v-btn
                icon="$delete"
                size="small"
                variant="text"
                color="red"
                :disabled="loading"
                title="Delete Source"
                @click="confirmDelete(item)"
              />
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Edit Source Dialog -->
    <v-dialog
      v-model="showEditDialog"
      max-width="600px"
    >
      <v-card>
        <v-card-title class="text-h5">
          Edit Source Metadata
        </v-card-title>
        <v-card-text>
          <!-- Taxonomy Bootstrap Notice -->
          <v-alert
            v-if="!taxonomy || taxonomy.length === 0"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <div class="text-caption">
              <strong>Note:</strong> Using default taxonomy.
              <router-link to="/knowledge/manage-taxonomy" class="text-decoration-none">
                Bootstrap your taxonomy
              </router-link>
              to customize content types and tags.
            </div>
          </v-alert>

          <v-text-field
            label="Source Path"
            :model-value="selectedSource?.path"
            readonly
            variant="outlined"
            density="compact"
            class="mb-3"
          />

          <!-- Current Metadata Display -->
          <v-alert
            v-if="selectedSource"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <div class="text-caption">
              <strong>Current:</strong>
              {{ selectedSource.effective_content_type || 'No content type' }}
              <v-chip
                v-if="selectedSource.metadata_provenance"
                :color="selectedSource.metadata_provenance === 'manual' ? 'primary' : 'secondary'"
                size="x-small"
                variant="outlined"
                class="ms-2"
              >
                {{ selectedSource.metadata_provenance === 'manual' ? 'Manual' : 'Inferred' }}
              </v-chip>
            </div>
            <div
              v-if="getEffectiveTags(selectedSource).length"
              class="text-caption mt-1"
            >
              <strong>Tags:</strong> {{ getEffectiveTags(selectedSource).join(', ') }}
            </div>
          </v-alert>

          <h3 class="text-subtitle-2 mb-3">
            Update Metadata (Manual Override)
          </h3>

          <v-select
            v-model="editedContentType"
            label="Content Type"
            :items="contentTypeOptions"
            item-title="label"
            item-value="key"
            variant="outlined"
            clearable
            hint="Select a content type to override current classification"
            persistent-hint
            class="mb-3"
          />

          <v-combobox
            v-model="editedTags"
            label="Tags"
            :items="tagSuggestions"
            :loading="loadingTagSuggestions"
            variant="outlined"
            multiple
            chips
            closable-chips
            clearable
            hint="Add or remove tags (will override inferred tags)"
            persistent-hint
            @update:search="fetchTagSuggestions"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon v-if="item.raw?.official">
                    $checkCircle
                  </v-icon>
                </template>
                <template #append>
                  <v-chip
                    v-if="item.raw?.usage_count"
                    size="x-small"
                    variant="outlined"
                  >
                    {{ item.raw.usage_count }}
                  </v-chip>
                </template>
              </v-list-item>
            </template>
          </v-combobox>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            text="Cancel"
            variant="text"
            @click="cancelEdit"
          />
          <v-btn
            text="Save"
            color="primary"
            variant="elevated"
            :loading="loading"
            @click="saveEdit"
          />
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title class="text-h5">
          Delete Source
        </v-card-title>
        <v-card-text>
          <p>Are you sure you want to delete this source?</p>
          <p class="text-subtitle-2 text-medium-emphasis mt-2">
            <strong>Path:</strong> {{ selectedSource?.path }}
          </p>
          <p class="text-body-2 text-medium-emphasis">
            This will permanently remove the source file and all associated chunks from the knowledge base.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            text="Cancel"
            variant="text"
            @click="cancelDelete"
          />
          <v-btn
            text="Delete"
            color="red"
            variant="elevated"
            :loading="loading"
            @click="deleteSource"
          />
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Upload Dialog -->
    <v-dialog
      v-model="showUploadDialog"
      max-width="600px"
    >
      <v-card>
        <v-card-title class="text-h5 d-flex align-center">
          <v-icon class="me-2">
            $upload
          </v-icon>
          Upload Knowledge Files
        </v-card-title>

        <v-card-text>
          <div class="mb-4">
            <p class="text-body-2 text-medium-emphasis mb-3">
              Upload documents to add them to your knowledge base. Supported formats:
              <strong>MD, PDF, TXT, JSON, HTML, DOCX</strong>
            </p>

            <v-file-input
              v-model="selectedFiles"
              label="Select files to upload"
              prepend-icon="$attach_file"
              variant="outlined"
              multiple
              accept=".md,.pdf,.txt,.json,.html,.docx,.doc"
              show-size
              counter
              :rules="fileRules"
            />
          </div>

          <!-- Metadata Fields -->
          <div class="mb-4">
            <h3 class="text-subtitle-1 mb-3">
              Optional Metadata
            </h3>

            <v-select
              v-model="uploadMetadata.contentType"
              label="Content Type"
              :items="contentTypeOptions"
              item-title="label"
              item-value="key"
              variant="outlined"
              clearable
              hint="Categorize the content type of uploaded files"
              persistent-hint
              class="mb-3"
            />

            <v-combobox
              v-model="uploadMetadata.tags"
              label="Tags"
              :items="tagSuggestions"
              :loading="loadingTagSuggestions"
              variant="outlined"
              multiple
              chips
              closable-chips
              clearable
              hint="Add relevant tags (select from suggestions or create new)"
              persistent-hint
              @update:search="fetchTagSuggestions"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <v-icon v-if="item.raw?.official">
                      $checkCircle
                    </v-icon>
                  </template>
                  <template #append>
                    <v-chip
                      v-if="item.raw?.usage_count"
                      size="x-small"
                      variant="outlined"
                    >
                      {{ item.raw.usage_count }}
                    </v-chip>
                  </template>
                </v-list-item>
              </template>
            </v-combobox>
          </div>

          <!-- Upload Progress -->
          <div
            v-if="uploadProgress.active"
            class="mb-4"
          >
            <v-card variant="outlined">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2">
                  <span class="text-body-2">Uploading files...</span>
                  <span class="text-body-2">{{ uploadProgress.completed }}/{{ uploadProgress.total }}</span>
                </div>
                <v-progress-linear
                  :model-value="(uploadProgress.completed / uploadProgress.total) * 100"
                  color="success"
                  height="8"
                  rounded
                />
              </v-card-text>
            </v-card>
          </div>

          <!-- Upload Results -->
          <div
            v-if="uploadResults.length > 0"
            class="mb-4"
          >
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1">
                Upload Results
              </v-card-title>
              <v-card-text>
                <v-list density="compact">
                  <v-list-item
                    v-for="result in uploadResults"
                    :key="result.filename"
                  >
                    <template #prepend>
                      <v-icon
                        :color="result.success ? 'success' : 'error'"
                        :icon="result.success ? '$check' : '$alert'"
                      />
                    </template>
                    <v-list-item-title>{{ result.filename }}</v-list-item-title>
                    <v-list-item-subtitle v-if="result.success">
                      {{ formatFileSize(result.size) }}
                    </v-list-item-subtitle>
                    <v-list-item-subtitle
                      v-else
                      class="text-error"
                    >
                      {{ result.error }}
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </div>

          
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            :disabled="uploadProgress.active"
            variant="text"
            @click="cancelUpload"
          >
            Cancel
          </v-btn>
          <v-btn
            color="success"
            :loading="uploadProgress.active"
            :disabled="!selectedFiles || selectedFiles.length === 0"
            variant="elevated"
            @click="uploadFiles"
          >
            Upload {{ selectedFiles ? selectedFiles.length : 0 }} File{{ selectedFiles && selectedFiles.length !== 1 ? 's' : '' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- File Editor Modal -->
    <FileEditorModal
      v-model="showFileEditorModal"
      :filename="selectedFilename"
      @file-saved="handleFileSaved"
    />

    <!-- Toasts are handled globally via NotificationMessage -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
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

const tenantStore = useTenantStore()

// Use store's cached knowledge sources with proper reactivity
const {
  currentTenantKnowledgeSources: sources,
  isLoadingKnowledgeSources: storeLoading,
  currentTenantTaxonomy: taxonomy
} = storeToRefs(tenantStore)

// Local loading state for operations (separate from store's loading state)
const localLoading = ref(false)

// Computed loading that combines both store and local loading
const loading = computed(() => storeLoading.value || localLoading.value)

const search = ref('')
const statusRows = ref([])
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const showFileEditorModal = ref(false)
const selectedSource = ref(null)
const editedContentType = ref('')
const editedTags = ref([])
const selectedFilename = ref('')

// Upload dialog state
const showUploadDialog = ref(false)

// Upload metadata state
const uploadMetadata = ref({
  contentType: null,
  tags: []
})

// Notifications
const { showSuccess, showError, showInfo, showWarning } = useNotifications()
const selectedFiles = ref(null)
const uploadResults = ref([])
const uploadProgress = ref({
  active: false,
  completed: 0,
  total: 0
})

// Tag autocomplete state
const tagSuggestions = ref([])
const loadingTagSuggestions = ref(false)
let tagAutocompleteTimeout = null

// Indexing progress state (post-upload background tasks)
const indexingProgress = ref({
  active: false,
  completed: 0,
  total: 0
})
let indexingPollTimer = null
let indexingPaths = []

const sourceHeaders = [
  { title: 'Source Path', key: 'path', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Content Type', key: 'content_type', sortable: true },
  { title: 'Tags', key: 'tags', sortable: false },
  { title: 'Chunks', key: 'chunk_count', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '190px' }
]

// File validation rules
const fileRules = [
  files => !files || files.length <= 10 || 'Maximum 10 files at once',
  files => !files || files.every(file => file.size <= 50 * 1024 * 1024) || 'Files must be smaller than 50MB'
]

// Computed properties for taxonomy-based options
const contentTypeOptions = computed(() => {
  // Provide fallback content types when taxonomy is not yet bootstrapped
  const defaultContentTypes = [
    { key: 'technical', label: 'Technical Documentation' },
    { key: 'experience', label: 'Experience & Projects' },
    { key: 'creative', label: 'Creative Content' },
    { key: 'personal', label: 'Personal Information' },
    { key: 'brand', label: 'Brand Assets' },
  ]

  if (!taxonomy.value || taxonomy.value.length === 0) {
    return defaultContentTypes
  }

  // Filter active content types only
  return taxonomy.value
    .filter(item => item.active)
    .map(item => ({
      key: item.key,
      label: item.label || item.key
    }))
})

const availableTags = computed(() => {
  // Provide fallback tags when taxonomy is not yet bootstrapped
  const defaultTags = [
    'technical', 'documentation', 'guide', 'reference', 'tutorial',
    'experience', 'portfolio', 'project', 'case-study',
    'creative', 'blog', 'article', 'content',
    'personal', 'bio', 'about', 'resume'
  ]

  if (!taxonomy.value || taxonomy.value.length === 0) {
    return defaultTags
  }

  // Extract all tags from taxonomy (synonyms can be used as tags)
  const tags = new Set()

  taxonomy.value.forEach(item => {
    if (item.active) {
      // Add the main key as a tag option
      tags.add(item.key)
      // Add synonyms as tag options
      if (Array.isArray(item.synonyms)) {
        item.synonyms.forEach(syn => tags.add(syn))
      }
    }
  })

  return Array.from(tags).sort()
})

// Notification helper (now uses global toasts)
const showAlert = (message, type = 'info') => {
  const map = {
    success: showSuccess,
    error: showError,
    info: showInfo,
    warning: showWarning,
  }
  const fn = map[type] || showInfo
  fn(message)
}

// Upload methods
const uploadFiles = async () => {
  if (!selectedFiles.value || selectedFiles.value.length === 0) return

  uploadProgress.value = {
    active: true,
    completed: 0,
    total: selectedFiles.value.length
  }
  uploadResults.value = []

  // Close the dialog immediately after the user clicks Upload
  showUploadDialog.value = false

  try {
    const formData = new FormData()
    for (const file of selectedFiles.value) {
      formData.append('files', file)
    }

    // Add metadata fields if provided
    if (uploadMetadata.value.contentType) {
      formData.append('metadata_content_type', uploadMetadata.value.contentType)
    }

    if (uploadMetadata.value.tags && uploadMetadata.value.tags.length > 0) {
      // Convert array to comma-separated string
      formData.append('metadata_tags', uploadMetadata.value.tags.join(','))
    }

    // Request immediate indexing on upload
    const response = await adminAPI.uploadKnowledgeFiles(formData, { indexNow: true })

    // Normalize new response shape from tenant-aware endpoint
    const files = response.files || []
    uploadResults.value = files.map(f => ({
      filename: f.filename || f.path?.split('/').pop() || 'unknown',
      success: (f.status || 'uploaded') === 'uploaded',
      error: null,
    }))
    uploadProgress.value.completed = selectedFiles.value.length

    // Kick off indexing polling for uploaded file paths
    indexingPaths = files.map(f => f.path).filter(Boolean)
    if (indexingPaths.length) {
      startIndexingPoll(indexingPaths)
      showInfo(`Re-indexing ${indexingPaths.length} file${indexingPaths.length>1?'s':''}...`)
    }

  } catch (error) {
    console.error('Upload failed:', error)
    uploadResults.value = (selectedFiles.value || []).map(file => ({
      filename: file.name,
      success: false,
      error: error.response?.data?.detail || 'Upload failed'
    }))
    showError('Upload failed')
  } finally {
    uploadProgress.value.active = false
  }
}

const cancelUpload = () => {
  showUploadDialog.value = false
  selectedFiles.value = null
  uploadResults.value = []
  uploadProgress.value = {
    active: false,
    completed: 0,
    total: 0
  }
  // Reset metadata
  uploadMetadata.value = {
    contentType: null,
    tags: []
  }
  stopIndexingPoll()
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

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

const getContentTypes = (contentTypeStr) => {
  if (!contentTypeStr || contentTypeStr === 'unknown') {
    return ['unknown']
  }
  return contentTypeStr.split(',').map(type => type.trim()).filter(type => type.length > 0)
}

const getEffectiveTags = (item) => {
  // Use effective_tags if available, otherwise fall back to tags
  const tags = item.effective_tags || item.tags || []

  if (Array.isArray(tags)) {
    return tags
  }

  // Handle comma-separated string format
  if (typeof tags === 'string' && tags.length > 0) {
    return tags.split(',').map(t => t.trim()).filter(t => t.length > 0)
  }

  return []
}

const getContentTypeColor = (type) => {
  const colorMap = {
    'technical': 'blue',
    'experience': 'green',
    'skills': 'orange',
    'about': 'purple',
    'creative': 'pink',
    'project': 'teal',
    'code': 'indigo',
    'documentation': 'cyan',
    'general': 'grey',
    'unknown': 'grey'
  }
  return colorMap[type?.toLowerCase()] || 'grey'
}

// If you need to refresh (e.g., after upload/delete):
const refreshSources = async () => {
  // Load both knowledge sources and taxonomy to ensure metadata dropdowns work
  await Promise.all([
    tenantStore.loadKnowledgeSources(true), // force=true
    tenantStore.loadTaxonomy(true) // force=true to ensure fresh data
  ])
  emit('refresh-complete')
}

// Keep the old loadSources function for compatibility with existing code
const loadSources = refreshSources

// Watch for refresh trigger from parent
watch(() => props.refreshTrigger, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    loadSources()
  }
})

const editSource = (source) => {
  selectedSource.value = source
  // Use manual metadata if available, otherwise use effective metadata
  editedContentType.value = source.manual_content_type || source.effective_content_type || ''

  // Get effective tags as array
  const tags = getEffectiveTags(source)
  editedTags.value = source.manual_tags || tags || []

  showEditDialog.value = true
}

const confirmDelete = (source) => {
  selectedSource.value = source
  showDeleteDialog.value = true
}

const saveEdit = async () => {
  if (!selectedSource.value) return

  try {
    localLoading.value = true

    // Build update payload
    const updateData = {}

    // Only send content_type if it has a value
    if (editedContentType.value) {
      updateData.manual_content_type = editedContentType.value
    }

    // Only send tags if array has items
    if (editedTags.value && editedTags.value.length > 0) {
      updateData.manual_tags = editedTags.value
    }

    await adminAPI.updateKnowledgeSource(selectedSource.value.path, updateData)

    showSuccess('Metadata updated successfully')

    // Refresh from server to avoid mutating store-computed data directly
    await tenantStore.loadKnowledgeSources(true)
    showEditDialog.value = false
  } catch (error) {
    console.error('Failed to update source:', error)
    showError('Failed to update source')
  } finally {
    localLoading.value = false
  }
}

const deleteSource = async () => {
  if (!selectedSource.value) return

  try {
    localLoading.value = true
    await adminAPI.deleteKnowledgeSource(selectedSource.value.path)

    // Refresh from server to avoid mutating store-computed data directly
    await tenantStore.loadKnowledgeSources(true)
    showDeleteDialog.value = false
  } catch (error) {
    console.error('Failed to delete source:', error)
    showError('Failed to delete source')
  } finally {
    localLoading.value = false
  }
}

const reindexSource = async (source) => {
  try {
    localLoading.value = true
    await adminAPI.reindexKnowledgeFile(source.path)
    showSuccess(`Reindex started for ${  source.path}`)
    // Reload to refresh chunk counts
    loadSources()
  } catch (e) {
    console.error('Failed to reindex source:', e)
    showError('Failed to reindex source')
  } finally {
    localLoading.value = false
  }
}

const cancelEdit = () => {
  showEditDialog.value = false
  selectedSource.value = null
  editedContentType.value = ''
  editedTags.value = []
}

const cancelDelete = () => {
  showDeleteDialog.value = false
  selectedSource.value = null
}

const viewFileContent = (source) => {
  selectedSource.value = source

  // Check if this is a binary file type that can't be edited
  const ext = source.path.split('.').pop()?.toLowerCase()
  const binaryTypes = ['pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'woff', 'woff2', 'ttf', 'otf']

  if (binaryTypes.includes(ext)) {
    showAlert(`Cannot edit binary file: ${source.path}. File type: ${ext.toUpperCase()}. This file contains binary data that cannot be edited as text.`, 'warning')
    return
  }

  // Use the display path provided by the backend (no path manipulation needed)
  selectedFilename.value = source.display_path || source.path
  showFileEditorModal.value = true
}

const handleFileSaved = () => {
  // Reload sources when file is saved to reflect any changes
  loadSources()
}

// Helpers to control edit availability and tooltip messaging
const isNonEditableFile = (filePath) => {
  if (!filePath) return false
  const ext = filePath.split('.').pop()?.toLowerCase()
  return ['pdf', 'docx'].includes(ext)
}

const getNonEditableTooltip = (filePath) => {
  const ext = filePath.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') {
    return 'PDF files cannot be edited here. Download or replace the file instead.'
  }
  if (ext === 'docx') {
    return 'DOCX files are binary and not editable in-browser. Upload a new version or convert to Markdown/HTML to edit.'
  }
  return 'This file type is not editable.'
}

const isBinaryFile = (filePath) => {
  if (!filePath) return false
  const ext = filePath.split('.').pop()?.toLowerCase()
  const binaryTypes = ['pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'woff', 'woff2', 'ttf', 'otf']
  return binaryTypes.includes(ext)
}

onMounted(() => {
  // Initial load will happen automatically via store on tenant change
  // But if we need to ensure data is fresh on mount, we can call refresh
  if (tenantStore.currentTenant) {
    refreshSources()
  }
})

onUnmounted(() => {
  stopIndexingPoll()
})

// UI helpers
const getStatusColor = (status) => {
  const s = (status || '').toLowerCase()
  if (s === 'indexed') return 'success'
  if (s === 'discovered') return 'grey'
  if (s === 'pending_index') return 'info'
  if (s === 'error') return 'error'
  if (s === 'orphaned' || s === 'missing_file') return 'warning'
  return 'default'
}

// ---- Indexing poll helpers ----
const startIndexingPoll = (paths) => {
  stopIndexingPoll()
  indexingProgress.value = { active: true, completed: 0, total: paths.length }
  const start = Date.now()
  const timeoutMs = 120000 // 2 minutes max wait
  const tick = async () => {
    try {
      // Fetch current file statuses (tenant-scoped)
      const res = await adminAPI.getKnowledgeFilesStatus({ limit: 1000 })
      const rows = Array.isArray(res?.files) ? res.files : []
      // Count how many of our uploaded files are indexed
      let done = 0
      const byPath = new Map(rows.map(r => [r.path, r]))
      for (const p of paths) {
        const r = byPath.get(p)
        if (r && ((r.status && String(r.status).toLowerCase() === 'indexed') || (r.vector_count && r.vector_count > 0))) {
          done += 1
        }
      }
      indexingProgress.value.completed = done
      // Refresh sources to reflect chunk_count updates while polling
      tenantStore.loadKnowledgeSources(true).catch(() => {})
      if (done >= paths.length) {
        showSuccess('Re-indexing complete')
        stopIndexingPoll()
        // One more refresh for final state
        loadSources()
        return
      }
      if (Date.now() - start > timeoutMs) {
        // Timeout: stop polling but leave UI; user can manually refresh
        showWarning('Indexing taking longer than expected — still in progress')
        stopIndexingPoll()
        return
      }
    } catch (e) {
      // Non-fatal; keep polling a few times
    }
  }
  indexingPollTimer = setInterval(tick, 1500)
  // Run first tick shortly
  setTimeout(tick, 800)
}

const stopIndexingPoll = () => {
  if (indexingPollTimer) {
    clearInterval(indexingPollTimer)
    indexingPollTimer = null
  }
  indexingProgress.value.active = false
}

// ---- Tag autocomplete helpers ----
const fetchTagSuggestions = async (query) => {
  // Debounce the autocomplete requests
  if (tagAutocompleteTimeout) {
    clearTimeout(tagAutocompleteTimeout)
  }

  tagAutocompleteTimeout = setTimeout(async () => {
    if (!query || query.length < 1) {
      tagSuggestions.value = availableTags.value
      return
    }

    try {
      loadingTagSuggestions.value = true
      const response = await adminAPI.getTagAutocomplete(query, 20)

      // Transform suggestions to include raw data for templates
      if (response && response.suggestions) {
        tagSuggestions.value = response.suggestions.map(s => ({
          title: s.tag,
          value: s.tag,
          raw: {
            usage_count: s.usage_count,
            official: s.source === 'official'
          }
        }))
      } else {
        tagSuggestions.value = []
      }
    } catch (error) {
      console.error('Failed to fetch tag suggestions:', error)
      // Fallback to taxonomy tags
      tagSuggestions.value = availableTags.value
    } finally {
      loadingTagSuggestions.value = false
    }
  }, 300) // 300ms debounce
}
</script>

<style scoped>
.sources-view {
  max-width: 1400px;
  margin: 0 auto;
}

/* Ensure proper spacing for content type chips */
.gap-1 > .v-chip {
  margin: 2px;
}

/* Ensure tooltip text wraps nicely at ~300px */
:deep(.kb-tooltip) {
  white-space: normal;
}
</style>
