<template>
  <div class="indexed-documents-view">
    <!-- Indexed Documents Section -->
    <v-card>
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2">
          $search
        </v-icon>
        Indexed Documents
        <v-spacer />
        <v-text-field
          v-model="documentSearch"
          density="compact"
          variant="outlined"
          placeholder="Search documents..."
          hide-details
          class="me-2"
          style="max-width: 300px"
        />
      </v-card-title>
      <v-card-text class="pa-0">
        <!-- Empty state hint when there are no indexed chunks -->
        <div
          v-if="!loadingDocuments && (!documents || documents.length === 0)"
          class="pa-6"
        >
          <v-card
            variant="outlined"
            class="pa-6 text-center"
          >
            <v-icon
              size="40"
              color="warning"
              class="mb-2"
            >
              $alert
            </v-icon>
            <div class="text-h6 mb-1">
              No Indexed Documents
            </div>
            <div class="text-body-2 text-medium-emphasis mb-4">
              No chunks found in the vector store. If you recently uploaded files, index them via the Consistency page.
            </div>
            <v-btn
              color="primary"
              @click="$router.push({ name: 'knowledge-consistency' })"
            >
              Go to Consistency
            </v-btn>
          </v-card>
        </div>
        <v-data-table
          :headers="documentHeaders"
          :items="documents"
          :loading="loadingDocuments"
          :search="documentSearch"
          item-key="id"
          :items-per-page="15"
          hover
          @click:row="openDocumentDialog"
        >
          <template #[`item.source`]="{ item }">
            <div
              class="text-truncate"
              style="max-width: 300px"
              :title="item.source"
            >
              {{ item.source }}
            </div>
          </template>
          <template #[`item.content_preview`]="{ item }">
            <div
              class="text-truncate text-body-2"
              style="max-width: 400px"
              :title="item.content_preview"
            >
              {{ item.content_preview }}
            </div>
          </template>
          <template #[`item.metadata`]="{ item }">
            <v-chip
              v-for="type in getContentTypes(item.metadata)"
              :key="type"
              size="x-small"
              class="me-1"
              :color="getContentTypeColor(type)"
            >
              {{ type }}
            </v-chip>
          </template>
          <template #[`item.word_count`]="{ item }">
            <span class="text-body-2">{{ item.word_count }} words</span>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Document Details Dialog -->
    <v-dialog
      v-model="showDocumentDialog"
      max-width="900px"
      scrollable
    >
      <v-card
        v-if="selectedDocument"
        class="dialog-card"
        elevation="8"
      >
        <v-card-title class="dialog-header pa-6">
          <div class="d-flex align-center">
            <v-icon
              class="me-3"
              color="primary"
            >
              $document
            </v-icon>
            <div>
              <h2 class="text-h6 font-weight-bold">
                Document Details
              </h2>
              <p class="text-body-2 text-medium-emphasis ma-0">
                View indexed document information
              </p>
            </div>
          </div>
          <v-spacer />
          <v-btn
            icon="$close"
            variant="text"
            size="small"
            @click="closeDocumentDialog"
          />
        </v-card-title>

        <v-divider class="border-opacity-25" />

        <v-card-text
          class="pa-6"
          style="max-height: 70vh;"
        >
          <!-- Basic Information -->
          <div class="mb-6">
            <h3 class="text-h7 font-weight-bold mb-4 text-primary">
              Basic Information
            </h3>
            <v-card
              variant="outlined"
              class="pa-4 rounded-lg"
            >
              <v-row no-gutters>
                <v-col
                  cols="12"
                  sm="6"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      Document ID
                    </v-label>
                    <div class="text-body-2 font-mono">
                      {{ selectedDocument.id }}
                    </div>
                  </div>
                </v-col>
                <v-col
                  cols="12"
                  sm="6"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      Word Count
                    </v-label>
                    <div class="text-body-2 font-weight-medium">
                      {{ selectedDocument.word_count }} words
                    </div>
                  </div>
                </v-col>
                <v-col
                  cols="12"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      Source
                    </v-label>
                    <div class="text-body-2 font-weight-medium">
                      {{ selectedDocument.source }}
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card>
          </div>

          <!-- Content Types -->
          <div
            v-if="selectedDocument.metadata && selectedDocument.metadata.content_types"
            class="mb-6"
          >
            <h3 class="text-h7 font-weight-bold mb-4 text-primary">
              Content Types
            </h3>
            <v-card
              variant="outlined"
              class="pa-4 rounded-lg"
            >
              <div class="d-flex flex-wrap gap-2">
                <v-chip
                  v-for="type in getContentTypes(selectedDocument.metadata)"
                  :key="type"
                  :color="getContentTypeColor(type)"
                  size="small"
                  variant="tonal"
                >
                  {{ type }}
                </v-chip>
              </div>
            </v-card>
          </div>

          <!-- Metadata -->
          <div
            v-if="selectedDocument.metadata"
            class="mb-6"
          >
            <h3 class="text-h7 font-weight-bold mb-4 text-primary">
              Metadata
            </h3>
            <v-card
              variant="outlined"
              class="pa-4 rounded-lg"
            >
              <v-row no-gutters>
                <v-col
                  v-if="selectedDocument.metadata.file_name"
                  cols="12"
                  sm="6"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      File Name
                    </v-label>
                    <div class="text-body-2">
                      {{ selectedDocument.metadata.file_name }}
                    </div>
                  </div>
                </v-col>
                <v-col
                  v-if="selectedDocument.metadata.file_type"
                  cols="12"
                  sm="6"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      File Type
                    </v-label>
                    <div class="text-body-2">
                      {{ selectedDocument.metadata.file_type }}
                    </div>
                  </div>
                </v-col>
                <v-col
                  v-if="selectedDocument.metadata.content_length"
                  cols="12"
                  sm="6"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      Content Length
                    </v-label>
                    <div class="text-body-2">
                      {{ selectedDocument.metadata.content_length }} characters
                    </div>
                  </div>
                </v-col>
                <v-col
                  v-if="selectedDocument.metadata.hasOwnProperty('has_code')"
                  cols="12"
                  sm="6"
                  class="pa-2"
                >
                  <div class="metric-item">
                    <v-label class="text-caption text-medium-emphasis mb-1">
                      Contains Code
                    </v-label>
                    <div class="text-body-2">
                      <v-chip
                        :color="selectedDocument.metadata.has_code ? 'success' : 'default'"
                        size="x-small"
                        variant="flat"
                      >
                        {{ selectedDocument.metadata.has_code ? 'Yes' : 'No' }}
                      </v-chip>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card>
          </div>

          <!-- Full Content -->
          <div class="mb-6">
            <h3 class="text-h7 font-weight-bold mb-4 text-primary d-flex align-center">
              <v-icon
                class="me-2"
                color="primary"
              >
                $text
              </v-icon>
              Full Content
              <v-progress-circular
                v-if="loadingFullContent"
                indeterminate
                size="20"
                width="2"
                class="ml-3"
                color="primary"
              />
            </h3>
            <v-card
              variant="outlined"
              class="rounded-lg overflow-hidden"
            >
              <v-textarea
                :model-value="loadingFullContent ? 'Loading full content...' : fullDocumentContent"
                readonly
                variant="plain"
                rows="15"
                auto-grow
                no-resize
                :loading="loadingFullContent"
                :class="{'monospace-content': selectedDocument?.metadata?.has_code}"
                class="pa-4"
              />
            </v-card>
          </div>
        </v-card-text>

        <v-divider class="border-opacity-25" />

        <v-card-actions class="pa-6">
          <v-spacer />
          <v-btn
            prepend-icon="$close"
            variant="outlined"
            class="rounded-lg"
            @click="closeDocumentDialog"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

export default {
  name: 'IndexedDocumentsView',
  setup() {
    const tenantStore = useTenantStore()
    const {
      currentTenantKnowledgeStats: knowledgeStats,
      currentTenantIndexedDocuments: documents,
      isLoadingKnowledgeStats,
      isLoadingIndexedDocuments,
    } = storeToRefs(tenantStore)

    const documentSearch = ref('')
    const showDocumentDialog = ref(false)
    const selectedDocument = ref(null)
    const loadingFullContent = ref(false)
    const fullDocumentContent = ref('')

    // Computed loading state
    const loadingDocuments = computed(() => isLoadingIndexedDocuments.value)

    const embeddingModel = ref('text-embedding-3-small')

    const documentHeaders = [
      { title: 'Source', key: 'source', sortable: true },
      { title: 'Content Preview', key: 'content_preview', sortable: false },
      { title: 'Content Types', key: 'metadata', sortable: false },
      { title: 'Size', key: 'word_count', sortable: true }
    ]

    const loadKnowledgeStats = async () => tenantStore.loadKnowledgeStats()
    const loadDocuments = async () => tenantStore.loadIndexedDocuments()

    const getContentTypes = (metadata) => {
      if (!metadata) return []
      // Check both content_type (singular) and content_types (plural) for backward compatibility
      const contentTypeStr = metadata.content_type || metadata.content_types
      if (!contentTypeStr || contentTypeStr === 'unknown') return ['unknown']

      // Canonicalize to our allowed set to avoid noisy labels (e.g., 'code' -> 'technical')
      const allowed = new Set(['technical', 'experience', 'skills', 'about', 'creative', 'project', 'documentation', 'general'])
      const canonMap = { code: 'technical', personal: 'about', doc: 'documentation', docs: 'documentation', document: 'documentation' }

      const types = contentTypeStr
        .split(',')
        .map(t => (t || '').trim().toLowerCase())
        .map(t => canonMap[t] || t)
        .filter(t => t && t !== 'unknown' && allowed.has(t) && !t.includes('based on'))
        .slice(0, 4)
      return [...new Set(types)]
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
        'documentation': 'cyan'
      }
      return colorMap[type.toLowerCase()] || 'grey'
    }

    const openDocumentDialog = async (event, { item }) => {
      selectedDocument.value = item
      showDocumentDialog.value = true
      fullDocumentContent.value = ''

      // Fetch the full document content
      try {
        loadingFullContent.value = true
        const fullDoc = await adminAPI.getDocumentContent(item.id)
        fullDocumentContent.value = fullDoc.content || 'No content available'
      } catch (error) {
        console.error('Failed to load full document content:', error)
        fullDocumentContent.value = 'Failed to load full content'
      } finally {
        loadingFullContent.value = false
      }
    }

    const closeDocumentDialog = () => {
      showDocumentDialog.value = false
      selectedDocument.value = null
      fullDocumentContent.value = ''
      loadingFullContent.value = false
    }

    onMounted(() => {
      // Ensure data is loaded when landing directly on this view
      loadKnowledgeStats()
      loadDocuments()
    })

    return {
      loadingDocuments,
      documentSearch,
      showDocumentDialog,
      selectedDocument,
      loadingFullContent,
      fullDocumentContent,
      knowledgeStats,
      embeddingModel,
      documents,
      documentHeaders,
      loadKnowledgeStats,
      loadDocuments,
      getContentTypes,
      getContentTypeColor,
      openDocumentDialog,
      closeDocumentDialog
    }
  }
}
</script>

<style scoped>
.indexed-documents-view {
  max-width: 1400px;
  margin: 0 auto;
}

.v-card {
  margin-bottom: 16px;
}

.monospace-content :deep(textarea) {
  font-family: 'JetBrains Mono', 'SF Mono', Monaco, Inconsolata, 'Source Code Pro', Consolas, 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.4;
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

.metric-item {
  min-height: 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

:deep(.v-textarea .v-field) {
  border-radius: 12px;
}
</style>
