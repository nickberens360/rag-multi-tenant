<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h5 font-weight-bold">
          Search & Retrieval Settings
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Configure query routing algorithms and RAG (Retrieval-Augmented Generation) parameters
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
      <!-- Query Routing Configuration Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $route
          </v-icon>
          Query Routing Configuration
        </v-card-title>
        
        <v-card-text class="pa-0">
          <v-alert
            type="info"
            variant="tonal"
            class="ma-6 mb-4"
          >
            These knobs control query-time behavior (routing choices, fuzzy keyword fallback) and do not change vector
            distances. For vector distance and MMR diversity, use the RAG section below.
          </v-alert>

          <v-alert
            v-if="routingError"
            type="error"
            variant="tonal"
            class="ma-6 mb-4"
          >
            {{ routingError }}
          </v-alert>
          
          <!-- Success notifications are shown via global toasts -->
          
          <!-- Enable Smart Routing Row -->
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
                    Enable Smart Routing
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Use intelligent routing algorithms for query processing and intent analysis
                    <a
                      :href="getBlogUrl('smart-query-routing-in-rag')"
                      target="_blank"
                      style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                    >Learn more →</a>
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="routingSettings.enable_smart_routing"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ routingSettings.enable_smart_routing ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Enable Fuzzy Matching Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $target
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable Fuzzy Matching
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Allow approximate string matching for better query results and typo tolerance
                    <a
                      :href="getBlogUrl('fuzzy-matching-thresholds-rag')"
                      target="_blank"
                      style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                    >Learn more →</a>
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="routingSettings.enable_fuzzy_matching"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ routingSettings.enable_fuzzy_matching ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Search Result Threshold Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $tune
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Search Result Threshold
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Minimum similarity score required to include results in responses (0.0 = very strict, 1.0 = very inclusive)
                    <a
                      :href="getBlogUrl('calibrating-fuzzy-thresholds')"
                      target="_blank"
                      style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                    >Learn more →</a>
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <div class="setting-slider">
                  <v-slider
                    v-model="routingSettings.similarity_threshold"
                    :min="0.0"
                    :max="1.0"
                    :step="0.1"
                    thumb-label="always"
                    show-ticks="always"
                    color="primary"
                    track-color="grey-lighten-3"
                    thumb-color="primary"
                    hide-details
                    style="width: 200px;"
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ routingSettings.similarity_threshold?.toFixed(1) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Max Search Results Row -->
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
                    Max Search Results
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Maximum number of search results to return per query
                    <a
                      :href="getBlogUrl('tuning-max-search-results-in-rag')"
                      target="_blank"
                      style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                    >Learn more →</a>
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-text-field
                  v-model.number="routingSettings.max_search_results"
                  type="number"
                  variant="outlined"
                  density="compact"
                  :min="1"
                  :max="100"
                  hide-details
                  style="width: 120px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Fuzzy Threshold Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $tune
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Fuzzy Threshold
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Threshold for fuzzy string matching accuracy (lower = more tolerant of typos)
                    <a
                      :href="getBlogUrl('calibrating-fuzzy-thresholds')"
                      target="_blank"
                      style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                    >Learn more →</a>
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <div class="setting-slider">
                  <v-slider
                    v-model="routingSettings.fuzzy_threshold"
                    :min="0.0"
                    :max="1.0"
                    :step="0.1"
                    thumb-label="always"
                    show-ticks="always"
                    color="primary"
                    track-color="grey-lighten-3"
                    thumb-color="primary"
                    :disabled="!routingSettings.enable_fuzzy_matching"
                    hide-details
                    style="width: 200px;"
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ routingSettings.fuzzy_threshold?.toFixed(1) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- RAG Configuration Card (hidden by feature flag) -->
      <v-card
        v-if="!flags.ADMIN_HIDE_INFRA_SETTINGS"
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $search
          </v-icon>
          RAG (Retrieval-Augmented Generation) Configuration
        </v-card-title>

        <v-card-text class="pa-0">
          <v-alert
            type="info"
            variant="tonal"
            class="ma-6 mb-4"
          >
            These settings affect how the vector index retrieves documents (distance threshold, MMR diversity,
            heading-based chunking, and which folders to index). They are independent from query-time routing knobs above.
          </v-alert>

          <v-alert
            v-if="ragError"
            type="error"
            variant="tonal"
            class="ma-6 mb-4"
          >
            {{ ragError }}
          </v-alert>

          <!-- Success notifications are shown via global toasts -->

          <div v-if="ragSettings && Object.keys(ragSettings).length > 0">
            <!-- Retrieval Settings Section -->
            <div class="section-header">
              <v-icon
                color="primary"
                class="section-icon"
              >
                $tune
              </v-icon>
              <div class="section-title">
                Vector Search Settings
              </div>
            </div>
            
            <!-- Vector Search Threshold -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $filter
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Vector Search Threshold
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Distance threshold for filtering vector similarity results (0.0 = most strict, 1.0 = least strict)
                      <a
                        :href="getBlogUrl()"
                        target="_blank"
                        style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                      >Learn more →</a>
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <div class="setting-slider">
                    <v-slider
                      v-model="ragSettings.rag_score_threshold"
                      :min="0.0"
                      :max="1.0"
                      :step="0.1"
                      thumb-label="always"
                      show-ticks="always"
                      color="primary"
                      track-color="grey-lighten-3"
                      thumb-color="primary"
                      hide-details
                      style="width: 200px;"
                    />
                    <div class="setting-status text-medium-emphasis">
                      {{ ragSettings.rag_score_threshold?.toFixed(1) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <v-divider />

            <!-- MMR Settings Section -->
            <div class="section-header">
              <v-icon
                color="primary"
                class="section-icon"
              >
                $diversity
              </v-icon>
              <div class="section-title">
                Maximum Marginal Relevance (MMR)
              </div>
            </div>

            <!-- Enable MMR -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $diversity
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Enable MMR
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Enable Maximum Marginal Relevance for diversity in search results
                      <a
                        :href="getBlogUrl('maximum-marginal-relevance-in-rag')"
                        target="_blank"
                        style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                      >Learn more →</a>
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="ragSettings.rag_use_mmr"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ ragSettings.rag_use_mmr ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider />

            <!-- MMR K Results -->
            <div
              v-show="ragSettings.rag_use_mmr"
              class="setting-row"
            >
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
                      MMR Results Count
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Number of results to return when using MMR
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-text-field
                    v-model.number="ragSettings.rag_mmr_k"
                    type="number"
                    variant="outlined"
                    density="compact"
                    :min="1"
                    :max="20"
                    :step="1"
                    hide-details
                    style="width: 120px;"
                  />
                </div>
              </div>
            </div>

            <v-divider v-show="ragSettings.rag_use_mmr" />

            <!-- MMR Fetch K -->
            <div
              v-show="ragSettings.rag_use_mmr"
              class="setting-row"
            >
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $database-search
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      MMR Fetch Count
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Number of candidates to fetch for MMR selection (higher = more diverse options)
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-text-field
                    v-model.number="ragSettings.rag_mmr_fetch_k"
                    type="number"
                    variant="outlined"
                    density="compact"
                    :min="10"
                    :max="100"
                    :step="5"
                    hide-details
                    style="width: 120px;"
                  />
                </div>
              </div>
            </div>

            <v-divider v-show="ragSettings.rag_use_mmr" />

            <!-- MMR Lambda -->
            <div
              v-show="ragSettings.rag_use_mmr"
              class="setting-row"
            >
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $tune
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      MMR Lambda Multiplier
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Balance between relevance and diversity (0.0 = max diversity, 1.0 = max relevance)
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <div class="setting-slider">
                    <v-slider
                      v-model="ragSettings.rag_mmr_lambda_mult"
                      :min="0.0"
                      :max="1.0"
                      :step="0.1"
                      thumb-label="always"
                      show-ticks="always"
                      color="primary"
                      track-color="grey-lighten-3"
                      thumb-color="primary"
                      hide-details
                      style="width: 200px;"
                    />
                    <div class="setting-status text-medium-emphasis">
                      {{ ragSettings.rag_mmr_lambda_mult?.toFixed(1) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <v-divider v-show="ragSettings.rag_use_mmr" />

            <!-- Content Processing Section -->
            <div class="section-header">
              <v-icon
                color="primary"
                class="section-icon"
              >
                $document
              </v-icon>
              <div class="section-title">
                Content Processing
              </div>
            </div>

            <!-- Heading Splitter -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $format-header
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Use Heading Splitter
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Use heading-aware splitters for better Markdown/HTML content chunking
                      <a
                        :href="getBlogUrl('smart-document-chunking-heading-splitters')"
                        target="_blank"
                        style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500; margin-left: 8px;"
                      >Learn more →</a>
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="ragSettings.rag_use_heading_splitter"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ ragSettings.rag_use_heading_splitter ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider />

            <!-- Index Directories -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $folder-search
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Index Directories
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Comma-separated list of directories to index for content search
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-text-field
                    v-model="ragSettings.rag_index_dirs"
                    variant="outlined"
                    density="compact"
                    hide-details
                    placeholder="e.g., backend/knowledge,public,docs"
                    style="width: 280px;"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <v-alert
            v-else
            type="info"
            variant="tonal"
            class="ma-6"
          >
            No RAG configuration available
          </v-alert>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAdminStore } from '@/stores/admin'
import { useSearchRetrievalSettingsStore } from '@/stores/searchRetrievalSettings'
import { adminAPI as apiService } from '@/services/api'
import ragConfigService from '@/services/settings/ragConfigSettingsService'
import { useNotifications } from '@/composables/useNotifications'
import { useTenantStore } from '@/stores/tenant'
import flags from '@/config/featureFlags'

const adminStore = useAdminStore()
const searchRetrievalStore = useSearchRetrievalSettingsStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Reactive state for different settings
const routingSettings = ref({
  enable_smart_routing: true,
  enable_fuzzy_matching: true,
  similarity_threshold: 0.7,
  max_search_results: 8,
  fuzzy_threshold: 0.8
})

const ragSettings = ref({
  rag_score_threshold: 0.7,
  rag_use_mmr: false,
  rag_mmr_k: 4,
  rag_mmr_fetch_k: 20,
  rag_mmr_lambda_mult: 0.5,
  rag_use_heading_splitter: true,
  rag_index_dirs: 'backend/knowledge,public'
})

// Loading and error states
const saving = ref(false)
const routingError = ref('')
const ragError = ref('')

// Notifications
const { showSuccess, showError } = useNotifications()

// Get blog URL based on environment
const getBlogUrl = (article = 'understanding-rag-score-thresholds') => {
  if (import.meta.env.PROD) {
    return `https://nickberens.com/blog/${article}`
  }
  return `http://localhost:4321/blog/${article}`
}

// Methods
const loadAllSettings = async () => {
  try {
    // Load search retrieval settings through store
    await searchRetrievalStore.loadData()
    
    // Load routing settings
    const routingData = await apiService.getRoutingSettings()
    if (routingData) {
      routingSettings.value = { ...routingSettings.value, ...routingData }
    }
    // Load RAG configuration using dedicated service so controls on this page work
    try {
      const ragResp = await ragConfigService.getRagConfig()
      if (ragResp && ragResp.settings) {
        ragSettings.value = { ...ragSettings.value, ...ragResp.settings }
      }
    } catch (e) {
      // Soft-fail: leave defaults and surface a gentle message
      ragError.value = `Unable to load RAG configuration: ${  e.message || 'unknown error'}`
    }
  } catch (err) {
    console.error('Failed to load settings:', err)
    routingError.value = `Failed to load settings: ${  err.response?.data?.detail || err.message}`
    if (!ragError.value) ragError.value = 'RAG settings could not be loaded'
  }
}

const saveAllSettings = async () => {
  try {
    saving.value = true
    routingError.value = ''
    ragError.value = ''
    
    // Save routing settings
    await apiService.updateRoutingSettings(routingSettings.value)
    
    // Save RAG settings via dedicated service
    await ragConfigService.updateRagConfig(ragSettings.value)
    
    // Toast success
    showSuccess('Search & Retrieval: routing settings saved')
    showSuccess('Search & Retrieval: RAG configuration saved')
    
  } catch (err) {
    console.error('Failed to save settings:', err)
    const errorMsg = `Failed to save settings: ${  err.response?.data?.detail || err.message}`
    routingError.value = errorMsg
    ragError.value = errorMsg
    showError(errorMsg)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  console.log('✅ [SearchRetrievalSettings] Component mounted, currentTenant:', currentTenant.value)
  loadAllSettings()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [SearchRetrievalSettings] Tenant slug watcher fired:', { oldSlug, newSlug, currentTenant: currentTenant.value })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [SearchRetrievalSettings] Tenant slug changed, refreshing search/retrieval settings')
    loadAllSettings()
  }
})
</script>

<style scoped>
/* Grid layout for responsive cards */
.grid-container {
  display: grid;
  gap: 24px;
}

/* Section Headers */
.section-header {
  display: flex;
  align-items: center;
  padding: 24px 24px 16px 24px;
  background: rgba(var(--v-theme-primary), 0.04);
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.12);
}

.section-icon {
  margin-right: 12px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
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
  min-width: 70px;
  text-align: right;
}

.setting-slider {
  display: flex;
  align-items: center;
}

.setting-slider .setting-status {
  margin-left: 16px;
  min-width: 50px;
  text-align: right;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .section-header {
    padding: 16px;
  }
  
  .section-title {
    font-size: 16px;
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
  
  .setting-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>
