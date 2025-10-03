<template>
  <div class="indexed-documents-view">
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">
        Indexed Documents
      </h1>
      <v-btn
        color="primary"
        prepend-icon="$refresh"
        :loading="loadingDocuments"
        variant="outlined"
        @click="loadDocuments"
      >
        Refresh
      </v-btn>
    </div>

    <!-- Knowledge Base Stats -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="blue"
                size="large"
                class="me-3"
              >
                $folder
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ knowledgeStats?.unique_sources || 0 }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Source Files
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="green"
                size="large"
                class="me-3"
              >
                $description
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ knowledgeStats?.total_documents || 0 }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Indexed Documents
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="purple"
                size="large"
                class="me-3"
              >
                $data_object
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ knowledgeStats?.total_chunks || 0 }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Vector Chunks
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="3"
      >
        <v-card elevation="1">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="orange"
                size="large"
                class="me-3"
              >
                $memory
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ embeddingModel }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Embedding Model
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Indexed Documents Section -->
    <v-card elevation="2">
      <v-card-title class="text-h6 bg-surface-variant d-flex align-center">
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
        <v-btn
          icon="$refresh"
          variant="text"
          size="small"
          :loading="loadingDocuments"
          @click="loadDocuments"
        />
      </v-card-title>
      <v-card-text class="pa-0">
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
      max-width="800px"
      scrollable
    >
      <v-card v-if="selectedDocument">
        <v-card-title class="text-h5 d-flex align-center">
          <v-icon class="me-2">
            $document
          </v-icon>
          Document Details
          <v-spacer />
          <v-btn
            icon="$close"
            variant="text"
            @click="closeDocumentDialog"
          />
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-0">
          <v-container>
            <!-- Basic Information -->
            <div class="mb-4">
              <h3 class="text-h6 mb-3">
                Basic Information
              </h3>
              <v-row>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Document ID"
                    :model-value="selectedDocument.id"
                    readonly
                    density="compact"
                    variant="outlined"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Word Count"
                    :model-value="selectedDocument.word_count + ' words'"
                    readonly
                    density="compact"
                    variant="outlined"
                  />
                </v-col>
              </v-row>
              <v-text-field
                label="Source"
                :model-value="selectedDocument.source"
                readonly
                density="compact"
                variant="outlined"
                class="mb-3"
              />
            </div>

            <!-- Content Types -->
            <div
              v-if="selectedDocument.metadata && selectedDocument.metadata.content_types"
              class="mb-4"
            >
              <h3 class="text-h6 mb-3">
                Content Types
              </h3>
              <div class="d-flex flex-wrap gap-2">
                <v-chip
                  v-for="type in getContentTypes(selectedDocument.metadata)"
                  :key="type"
                  :color="getContentTypeColor(type)"
                  size="small"
                >
                  {{ type }}
                </v-chip>
              </div>
            </div>

            <!-- Metadata -->
            <div
              v-if="selectedDocument.metadata"
              class="mb-4"
            >
              <h3 class="text-h6 mb-3">
                Metadata
              </h3>
              <v-row>
                <v-col
                  v-if="selectedDocument.metadata.file_name"
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="File Name"
                    :model-value="selectedDocument.metadata.file_name"
                    readonly
                    density="compact"
                    variant="outlined"
                  />
                </v-col>
                <v-col
                  v-if="selectedDocument.metadata.file_type"
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="File Type"
                    :model-value="selectedDocument.metadata.file_type"
                    readonly
                    density="compact"
                    variant="outlined"
                  />
                </v-col>
                <v-col
                  v-if="selectedDocument.metadata.content_length"
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Content Length"
                    :model-value="selectedDocument.metadata.content_length + ' characters'"
                    readonly
                    density="compact"
                    variant="outlined"
                  />
                </v-col>
                <v-col
                  v-if="selectedDocument.metadata.hasOwnProperty('has_code')"
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Contains Code"
                    :model-value="selectedDocument.metadata.has_code ? 'Yes' : 'No'"
                    readonly
                    density="compact"
                    variant="outlined"
                  />
                </v-col>
              </v-row>
            </div>

            <!-- Full Content -->
            <div class="mb-4">
              <h3 class="text-h6 mb-3 d-flex align-center">
                Full Content
                <v-progress-circular
                  v-if="loadingFullContent"
                  indeterminate
                  size="20"
                  width="2"
                  class="ml-2"
                />
              </h3>
              <v-textarea
                :model-value="loadingFullContent ? 'Loading full content...' : fullDocumentContent"
                readonly
                variant="outlined"
                rows="15"
                auto-grow
                no-resize
                :loading="loadingFullContent"
                :class="{'monospace-content': selectedDocument?.metadata?.has_code}"
              />
            </div>
          </v-container>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn
            text="Close"
            variant="text"
            @click="closeDocumentDialog"
          />
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

export default {
  name: 'IndexedDocumentsView',
  setup() {
    const tenantStore = useTenantStore()

    // Get cached data from store
    const {
      isLoadingKnowledgeStats,
      isCriticalDataReady
    } = storeToRefs(tenantStore)

    // Use computed to ensure reactivity is maintained
    const knowledgeStats = computed(() => tenantStore.currentTenantKnowledgeStats)

    // Component-specific state (not cached in store because it's large)
    const loadingDocuments = ref(false)
    const documentSearch = ref('')
    const showDocumentDialog = ref(false)
    const selectedDocument = ref(null)
    const loadingFullContent = ref(false)
    const fullDocumentContent = ref('')
    const embeddingModel = ref('text-embedding-3-small')
    const documents = ref([])

    const documentHeaders = [
      { title: 'Source', key: 'source', sortable: true },
      { title: 'Content Preview', key: 'content_preview', sortable: false },
      { title: 'Content Types', key: 'metadata', sortable: false },
      { title: 'Size', key: 'word_count', sortable: true }
    ]

    // Load heavy data (documents) locally - not cached
    const loadDocuments = async () => {
      if (!tenantStore.currentTenant?.slug) return

      loadingDocuments.value = true
      try {
        const data = await adminAPI.getKnowledgeDocuments(100, 0)
        documents.value = data.documents || []
        if (data.embedding_model) {
          embeddingModel.value = data.embedding_model
        }
      } catch (error) {
        console.error('Failed to load documents:', error)
      } finally {
        loadingDocuments.value = false
      }
    }

    const getContentTypes = (metadata) => {
      if (!metadata || !metadata.content_types) return []
      const types = metadata.content_types.split(',')
        .map(t => t.trim())
        .filter(t => t && t !== 'unknown' && !t.includes('based on'))
        .slice(0, 3)  // Show max 3 types
      return [...new Set(types)]  // Remove duplicates
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

    // Simple watcher - only watch when critical data is ready
    watch(
      () => isCriticalDataReady.value,
      (isReady) => {
        if (isReady) {
          console.log('✅ Critical data ready, loading documents')
          loadDocuments()
        }
      },
      { immediate: true }
    )

    return {
      loadingDocuments,
      documentSearch,
      showDocumentDialog,
      selectedDocument,
      loadingFullContent,
      fullDocumentContent,
      knowledgeStats, // From store
      embeddingModel,
      documents,
      documentHeaders,
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

.v-card {
  margin-bottom: 16px;
}

.monospace-content :deep(textarea) {
  font-family: 'JetBrains Mono', 'SF Mono', Monaco, Inconsolata, 'Source Code Pro', Consolas, 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.4;
}
</style>