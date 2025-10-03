<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Response Generation Settings</span>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="store.loading"
          prepend-icon="$check"
          @click="saveSettings"
        >
          Save Changes
        </v-btn>
      </v-card-title>
      
      <v-card-text class="pa-0">
        <v-alert
          type="info"
          variant="tonal"
          class="ma-6 mb-4"
        >
          This page controls the <strong>chat response</strong> provider, models, and formatting. The <em>processing LLM</em>
          used for background tasks is configured in <strong>System Settings</strong>.
        </v-alert>
        <v-alert
          v-if="store.error"
          type="error"
          variant="tonal"
          class="ma-6 mb-4"
        >
          {{ store.error }}
        </v-alert>
        
        <!-- Max Context Length Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $text
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Max Context Length
                </div>
                <div class="response-description text-medium-emphasis">
                  Maximum character length for context documents
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.max_context_length"
                type="number"
                variant="outlined"
                density="compact"
                :min="100"
                :max="10000"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Max Context Documents Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $document
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Max Context Documents
                </div>
                <div class="response-description text-medium-emphasis">
                  Maximum number of documents to include in context
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.max_context_documents"
                type="number"
                variant="outlined"
                density="compact"
                :min="1"
                :max="10"
                hide-details
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Context Fill Ratio Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $tune
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Context Fill Ratio
                </div>
                <div class="response-description text-medium-emphasis">
                  Ratio of context to fill with relevant documents
                </div>
              </div>
            </div>
            <div class="response-right">
              <div class="response-slider">
                <v-slider
                  v-model="store.settings.context_fill_ratio"
                  :min="0.1"
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
                <div class="response-status text-medium-emphasis">
                  {{ store.settings.context_fill_ratio.toFixed(1) }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Caching Section Header -->
        <div class="section-header">
          <v-icon
            color="primary"
            class="section-icon"
          >
            $cached
          </v-icon>
          <div class="section-title">
            Response Caching Settings
          </div>
        </div>

        <!-- Enable General Caching Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $cached
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Enable Caching
                </div>
                <div class="response-description text-medium-emphasis">
                  Master toggle for all response caching functionality
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-switch
                v-model="store.settings.enable_caching"
                color="primary"
                inset
                hide-details
              />
              <div class="response-status text-medium-emphasis">
                {{ store.settings.enable_caching ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Enable Response Caching Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $message-text
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Enable Response Caching
                </div>
                <div class="response-description text-medium-emphasis">
                  Cache generated responses to improve performance for repeated queries
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-switch
                v-model="store.settings.enable_response_caching"
                color="primary"
                inset
                hide-details
                :disabled="!store.settings.enable_caching"
              />
              <div class="response-status text-medium-emphasis">
                {{ store.settings.enable_response_caching ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Unified Cache TTL Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $clock
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Cache TTL (seconds)
                </div>
                <div class="response-description text-medium-emphasis">
                  Unified cache duration for all response types (60s - 24h)
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.cache_ttl_seconds"
                type="number"
                variant="outlined"
                density="compact"
                :min="60"
                :max="86400"
                :disabled="!store.settings.enable_caching"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Response Formatting Section Header -->
        <div class="section-header">
          <v-icon
            color="primary"
            class="section-icon"
          >
            $format-text
          </v-icon>
          <div class="section-title">
            Response Formatting
          </div>
        </div>

        <!-- Preferred Response Length Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $text-long
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Preferred Response Length
                </div>
                <div class="response-description text-medium-emphasis">
                  Default length preference for generated responses
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-select
                v-model="store.settings.preferred_response_length"
                :items="responseLengthOptions"
                variant="outlined"
                density="compact"
                hide-details
                style="width: 160px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Response Style Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $format-text
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Response Style
                </div>
                <div class="response-description text-medium-emphasis">
                  Tone and style for generated responses
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-select
                v-model="store.settings.response_style"
                :items="responseStyleOptions"
                variant="outlined"
                density="compact"
                hide-details
                style="width: 160px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Include Sources Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $link-variant
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Include Sources
                </div>
                <div class="response-description text-medium-emphasis">
                  Include source references in generated responses
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-switch
                v-model="store.settings.include_sources"
                color="primary"
                inset
                hide-details
              />
              <div class="response-status text-medium-emphasis">
                {{ store.settings.include_sources ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Source Format Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $format-list
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Source Format
                </div>
                <div class="response-description text-medium-emphasis">
                  How to display source references
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-select
                v-model="store.settings.source_format"
                :items="sourceFormatOptions"
                variant="outlined"
                density="compact"
                hide-details
                :disabled="!store.settings.include_sources"
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Max Sources Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $numeric
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Max Sources
                </div>
                <div class="response-description text-medium-emphasis">
                  Maximum number of sources to include (0-20)
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.max_sources"
                type="number"
                variant="outlined"
                density="compact"
                :min="0"
                :max="20"
                :disabled="!store.settings.include_sources"
                hide-details
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Enable Markdown Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $markdown
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Enable Markdown
                </div>
                <div class="response-description text-medium-emphasis">
                  Allow markdown formatting in responses
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-switch
                v-model="store.settings.enable_markdown"
                color="primary"
                inset
                hide-details
              />
              <div class="response-status text-medium-emphasis">
                {{ store.settings.enable_markdown ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Enable Code Highlighting Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon
                color="primary"
                class="response-icon"
              >
                $code-braces
              </v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">
                  Enable Code Highlighting
                </div>
                <div class="response-description text-medium-emphasis">
                  Enable syntax highlighting for code blocks
                </div>
              </div>
            </div>
            <div class="response-right">
              <v-switch
                v-model="store.settings.enable_code_highlighting"
                color="primary"
                inset
                hide-details
              />
              <div class="response-status text-medium-emphasis">
                {{ store.settings.enable_code_highlighting ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useResponseSettingsStore } from '@/stores/responseSettings'
import { useTenantStore } from '@/stores/tenant'
import { useNotifications } from '@/composables/useNotifications'

const store = useResponseSettingsStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)
const { showSuccess, showError } = useNotifications()

// Response formatting options
const responseLengthOptions = [
  { title: 'Brief', value: 'brief' },
  { title: 'Medium', value: 'medium' },
  { title: 'Detailed', value: 'detailed' },
  { title: 'Comprehensive', value: 'comprehensive' }
]

const responseStyleOptions = [
  { title: 'Conversational', value: 'conversational' },
  { title: 'Professional', value: 'professional' },
  { title: 'Technical', value: 'technical' },
  { title: 'Casual', value: 'casual' }
]

const sourceFormatOptions = [
  { title: 'Numbered', value: 'numbered' },
  { title: 'Bulleted', value: 'bulleted' },
  { title: 'Inline', value: 'inline' }
]

onMounted(() => {
  store.loadData()
})

// Reload settings when tenant changes
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await store.loadData()
  }
}, { deep: true })

const saveSettings = async () => {
  try {
    await store.updateSettings()
    showSuccess('Response settings saved successfully!')
  } catch (err) {
    showError(`Failed to save settings: ${err.message}`)
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

/* Response Settings Row Layout */
.response-row {
  padding: 20px 24px;
}

.response-row:last-child {
  border-bottom: none;
}

.response-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.response-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.response-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

.response-info {
  flex: 1;
  min-width: 0;
}

.response-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.response-description {
  font-size: 14px;
  line-height: 1.4;
}

.response-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.response-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

.response-slider {
  display: flex;
  align-items: center;
}

.response-slider .response-status {
  margin-left: 16px;
  min-width: 50px;
  text-align: right;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .response-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .response-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .response-slider {
    width: 100%;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .response-slider .response-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>
