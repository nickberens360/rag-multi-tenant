<template>
  <div>
    <!-- RAG Configuration (hidden by feature flag) -->
    <div v-if="!flags.ADMIN_HIDE_INFRA_SETTINGS">
      <v-card elevation="2">
        <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
          <span>RAG Configuration</span>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="store.loading"
            prepend-icon="$check"
            @click="saveRagConfig"
          >
            Save Changes
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-0">
          <v-alert
            v-if="store.error"
            type="error"
            variant="tonal"
            class="ma-6 mb-4"
          >
            {{ store.error }}
          </v-alert>

          <div v-if="store.ragConfig && Object.keys(store.ragConfig).length > 0">
            <!-- Retrieval Settings Section -->
            <div class="section-header">
              <v-icon
                color="primary"
                class="section-icon"
              >
                $tune
              </v-icon>
              <div class="section-title">
                Retrieval Settings
              </div>
            </div>
          
            <div
              v-for="key in retrievalSettings"
              :key="key"
            >
              <div class="feature-row">
                <div class="feature-content">
                  <div class="feature-left">
                    <v-icon
                      v-if="getFeatureIcon(key)"
                      color="primary"
                      class="feature-icon"
                    >
                      {{ getFeatureIcon(key) }}
                    </v-icon>
                    <div class="feature-info">
                      <div class="feature-title text-high-emphasis">
                        {{ formatFeatureName(key) }}
                      </div>
                      <div
                        v-if="hasLearnMoreLink(key)"
                        class="feature-description text-medium-emphasis"
                        v-html="getFeatureDescription(key)"
                      />
                      <div
                        v-else
                        class="feature-description text-medium-emphasis"
                      >
                        {{ getFeatureDescription(key) }}
                      </div>
                    </div>
                  </div>
                  <div class="feature-right">
                    <!-- Boolean settings - switch -->
                    <template v-if="getSettingType(key) === 'boolean'">
                      <v-switch
                        v-model="store.ragConfig[key]"
                        color="primary"
                        inset
                        hide-details
                      />
                      <div class="feature-status text-medium-emphasis">
                        {{ store.ragConfig[key] ? 'Enabled' : 'Disabled' }}
                      </div>
                    </template>
                  
                    <!-- Float settings - slider -->
                    <template v-else-if="getSettingType(key) === 'float'">
                      <div class="feature-slider">
                        <v-slider
                          v-model="store.ragConfig[key]"
                          :min="getFieldBounds(key).min"
                          :max="getFieldBounds(key).max"
                          :step="getFieldBounds(key).step"
                          thumb-label="always"
                          show-ticks="always"
                          color="primary"
                          track-color="grey-lighten-3"
                          thumb-color="primary"
                          hide-details
                          style="width: 200px;"
                        />
                        <div class="feature-status text-medium-emphasis">
                          {{ store.ragConfig[key]?.toFixed(getFieldBounds(key).decimals || 1) }}
                        </div>
                      </div>
                    </template>
                  
                    <!-- Numeric settings - number input -->
                    <template v-else-if="getSettingType(key) === 'number'">
                      <v-text-field
                        v-model.number="store.ragConfig[key]"
                        type="number"
                        variant="outlined"
                        density="compact"
                        :min="getFieldBounds(key).min"
                        :max="getFieldBounds(key).max"
                        :step="getFieldBounds(key).step"
                        hide-details
                        :style="{ width: getFieldBounds(key).width + 'px' }"
                      />
                    </template>
                  
                    <!-- String settings - text input -->
                    <template v-else-if="getSettingType(key) === 'string'">
                      <v-text-field
                        v-model="store.ragConfig[key]"
                        variant="outlined"
                        density="compact"
                        hide-details
                        :placeholder="getFieldPlaceholder(key)"
                        style="width: 280px;"
                      />
                    </template>
                  </div>
                </div>
              </div>
              <v-divider />
            </div>

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
          
            <div
              v-for="key in processingSettings"
              :key="key"
            >
              <div class="feature-row">
                <div class="feature-content">
                  <div class="feature-left">
                    <v-icon
                      v-if="getFeatureIcon(key)"
                      color="primary"
                      class="feature-icon"
                    >
                      {{ getFeatureIcon(key) }}
                    </v-icon>
                    <div class="feature-info">
                      <div class="feature-title text-high-emphasis">
                        {{ formatFeatureName(key) }}
                      </div>
                      <div
                        v-if="hasLearnMoreLink(key)"
                        class="feature-description text-medium-emphasis"
                        v-html="getFeatureDescription(key)"
                      />
                      <div
                        v-else
                        class="feature-description text-medium-emphasis"
                      >
                        {{ getFeatureDescription(key) }}
                      </div>
                    </div>
                  </div>
                  <div class="feature-right">
                    <!-- String settings - text input -->
                    <template v-if="getSettingType(key) === 'string'">
                      <v-text-field
                        v-model="store.ragConfig[key]"
                        variant="outlined"
                        density="compact"
                        hide-details
                        :placeholder="getFieldPlaceholder(key)"
                        style="width: 280px;"
                      />
                    </template>
                  
                    <!-- Boolean settings - switch -->
                    <template v-else-if="getSettingType(key) === 'boolean'">
                      <v-switch
                        v-model="store.ragConfig[key]"
                        color="primary"
                        inset
                        hide-details
                      />
                      <div class="feature-status text-medium-emphasis">
                        {{ store.ragConfig[key] ? 'Enabled' : 'Disabled' }}
                      </div>
                    </template>
                  </div>
                </div>
              </div>
              <v-divider />
            </div>

            <!-- Data Management Section -->
            <div class="section-header">
              <v-icon
                color="primary"
                class="section-icon"
              >
                $database
              </v-icon>
              <div class="section-title">
                Data Management
              </div>
            </div>
          
            <div
              v-for="(key, index) in dataManagementSettings"
              :key="key"
            >
              <div class="feature-row">
                <div class="feature-content">
                  <div class="feature-left">
                    <v-icon
                      v-if="getFeatureIcon(key)"
                      color="primary"
                      class="feature-icon"
                    >
                      {{ getFeatureIcon(key) }}
                    </v-icon>
                    <div class="feature-info">
                      <div class="feature-title text-high-emphasis">
                        {{ formatFeatureName(key) }}
                      </div>
                      <div
                        v-if="hasLearnMoreLink(key)"
                        class="feature-description text-medium-emphasis"
                        v-html="getFeatureDescription(key)"
                      />
                      <div
                        v-else
                        class="feature-description text-medium-emphasis"
                      >
                        {{ getFeatureDescription(key) }}
                      </div>
                    </div>
                  </div>
                  <div class="feature-right">
                    <!-- Boolean settings - switch -->
                    <template v-if="getSettingType(key) === 'boolean'">
                      <v-switch
                        v-model="store.ragConfig[key]"
                        color="primary"
                        inset
                        hide-details
                      />
                      <div class="feature-status text-medium-emphasis">
                        {{ store.ragConfig[key] ? 'Enabled' : 'Disabled' }}
                      </div>
                    </template>
                  </div>
                </div>
              </div>
              <v-divider v-if="index < dataManagementSettings.length - 1" />
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

    <!-- Simplified message when RAG configuration is hidden -->
    <div v-else>
      <v-card elevation="2">
        <v-card-text class="pa-6">
          <v-alert
            type="info"
            variant="tonal"
          >
            RAG configuration settings are managed at the infrastructure level and are not available in this simplified view.
          </v-alert>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRagConfigStore } from '@/stores/ragConfigSettings'
import { useNotifications } from '@/composables/useNotifications'
import { useTenantStore } from '@/stores/tenant'
import flags from '@/config/featureFlags'

const store = useRagConfigStore()
const { showSuccess, showError } = useNotifications()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Get blog URL based on environment with validation
const getBlogUrl = (article = 'understanding-rag-score-thresholds') => {
  // Validate article parameter
  if (!article || typeof article !== 'string') {
    console.warn('Invalid article parameter for getBlogUrl:', article)
    article = 'understanding-rag-score-thresholds'
  }
  
  // Sanitize article to prevent invalid URLs
  const sanitizedArticle = article.replace(/[^a-z0-9-]/gi, '-').toLowerCase()
  
  try {
    // In production, use the main site domain
    if (import.meta.env.PROD) {
      const url = `https://nickberens.com/blog/${sanitizedArticle}`
      new URL(url) // Validate URL format
      return url
    }
    // In development, use localhost:4321 (Astro dev server)
    const url = `http://localhost:4321/blog/${sanitizedArticle}`
    new URL(url) // Validate URL format
    return url
  } catch (error) {
    console.error('Failed to generate valid blog URL:', error)
    // Return a safe fallback URL
    return import.meta.env.PROD 
      ? 'https://nickberens.com/blog' 
      : 'http://localhost:4321/blog'
  }
}

onMounted(() => {
  console.log('✅ [RagConfigSettings] Component mounted, currentTenant:', currentTenant.value)
  store.loadData()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [RagConfigSettings] Tenant slug watcher fired:', { oldSlug, newSlug, currentTenant: currentTenant.value })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [RagConfigSettings] Tenant slug changed, refreshing RAG config')
    store.loadData()
  }
})

// Organized setting groups
const retrievalSettings = computed(() => [
  'rag_score_threshold',
  'rag_use_mmr', 
  'rag_mmr_k',
  'rag_mmr_fetch_k',
  'rag_mmr_lambda_mult'
])

const processingSettings = computed(() => [
  'rag_use_heading_splitter',
  'rag_index_dirs'
])

const dataManagementSettings = computed(() => [
  'rag_enable_delete',
  'rag_safe_delete'
])

const formatFeatureName = (key) => {
  return key
    .replace('rag_', '')
    .split('_')
    .map(word => {
      if (word.toLowerCase() === 'mmr') return 'MMR'
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join(' ')
    .replace('Score Threshold', 'Vector Search Threshold')
}

// Check if setting has a learn more link
const hasLearnMoreLink = (key) => {
  const settingsWithLinks = [
    'rag_use_mmr',
    'rag_score_threshold', 
    'rag_mmr_k',
    'rag_mmr_fetch_k',
    'rag_mmr_lambda_mult',
    'rag_use_heading_splitter',
    'rag_enable_delete',
    'rag_safe_delete'
  ]
  return settingsWithLinks.includes(key)
}

const getFeatureDescription = (key) => {
  const descriptions = {
    // Retrieval Settings
    rag_use_mmr: `Enable Maximum Marginal Relevance for diversity in search results <a href="${getBlogUrl('maximum-marginal-relevance-in-rag')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    rag_score_threshold: `Vector Search Threshold - Distance threshold for filtering vector similarity results (0.0 = most strict, 1.0 = least strict) <a href="${getBlogUrl()}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    rag_mmr_k: `Number of results to return when using MMR <a href="${getBlogUrl('maximum-marginal-relevance-in-rag')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    rag_mmr_fetch_k: `Number of candidates to fetch for MMR selection (higher = more diverse options) <a href="${getBlogUrl('maximum-marginal-relevance-in-rag')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    rag_mmr_lambda_mult: `Balance between relevance and diversity (0.0 = max diversity, 1.0 = max relevance) <a href="${getBlogUrl('maximum-marginal-relevance-in-rag')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    
    // Content Processing
    rag_use_heading_splitter: `Use heading-aware splitters for better Markdown/HTML content chunking <a href="${getBlogUrl('smart-document-chunking-heading-splitters')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    rag_index_dirs: 'Comma-separated list of directories to index for content search',
    
    // Data Management
    rag_enable_delete: `Enable delete operations for vector store cleanup <a href="${getBlogUrl('safe-vector-store-management-rag')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`,
    rag_safe_delete: `Enable validation checks before deletion to prevent data loss <a href="${getBlogUrl('safe-vector-store-management-rag')}" target="_blank" style="color: rgb(var(--v-theme-primary)); text-decoration: none; font-weight: 500;">Learn more →</a>`
  }
  return descriptions[key] || 'RAG configuration setting'
}

const getSettingType = (key) => {
  const types = {
    // Boolean settings
    rag_use_mmr: 'boolean',
    rag_use_heading_splitter: 'boolean',
    rag_enable_delete: 'boolean',
    rag_safe_delete: 'boolean',
    
    // Numeric settings
    rag_mmr_k: 'number',
    rag_mmr_fetch_k: 'number',
    
    // Float settings  
    rag_score_threshold: 'float',
    rag_mmr_lambda_mult: 'float',
    
    // String settings
    rag_index_dirs: 'string'
  }
  return types[key] || 'boolean'
}

const getFieldBounds = (key) => {
  const bounds = {
    rag_score_threshold: { min: 0.0, max: 1.0, step: 0.1, width: 200, decimals: 1 },
    rag_mmr_lambda_mult: { min: 0.0, max: 1.0, step: 0.1, width: 200, decimals: 1 },
    rag_mmr_k: { min: 1, max: 20, step: 1, width: 120 },
    rag_mmr_fetch_k: { min: 10, max: 100, step: 5, width: 120 }
  }
  return bounds[key] || { min: 0, max: 100, step: 1, width: 120 }
}

const getFieldPlaceholder = (key) => {
  const placeholders = {
    rag_index_dirs: 'e.g., backend/knowledge,public,docs'
  }
  return placeholders[key] || ''
}

const getFeatureIcon = (key) => {
  const icons = {
    rag_use_mmr: '$diversity',
    rag_use_heading_splitter: '$format-header',
    rag_enable_delete: '$delete',
    rag_safe_delete: '$shield-check',
    rag_score_threshold: '$filter',
    rag_mmr_k: '$numeric',
    rag_mmr_fetch_k: '$database-search',
    rag_mmr_lambda_mult: '$tune',
    rag_index_dirs: '$folder-search'
  }
  return icons[key]
}


const saveRagConfig = async () => {
  try {
    await store.updateRagConfig()
    showSuccess('RAG configuration updated successfully!')
  } catch (err) {
    showError(`Failed to save RAG configuration: ${err.message}`)
  }
}
</script>

<style scoped>
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

/* Feature Rows */
.feature-row {
  padding: 20px 24px;
}

.feature-row:last-child {
  border-bottom: none;
}

.feature-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.feature-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.feature-info {
  flex: 1;
  min-width: 0;
}

.feature-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.feature-description {
  font-size: 14px;
  line-height: 1.4;
}

.feature-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.feature-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
  min-width: 70px;
  text-align: right;
}

.feature-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

.feature-slider {
  display: flex;
  align-items: center;
}

.feature-slider .feature-status {
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

  .feature-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .feature-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }
  
  .feature-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>