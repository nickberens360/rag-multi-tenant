<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>System Configuration</span>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="loading"
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
          Response model selection for chat is managed in <strong>Core Settings → Response Settings</strong>.
          This page primarily configures the <em>processing LLM</em> used for background tasks (indexing, reformulation).
        </v-alert>
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          class="ma-6 mb-4"
        >
          {{ error }}
        </v-alert>
        
        <!-- Success notifications are shown via global toasts -->
        
        <!-- Response LLM Selection Row -->
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
                  Response LLM
                </div>
                <div class="setting-description text-medium-emphasis">
                  Language model used for all user-facing chat responses. Supports smart selection between model variants.
                </div>
              </div>
            </div>
            <div class="setting-right">
              <div>
                <v-select
                  v-model="settings.response_llm"
                  :items="llmOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 160px;"
                  :disabled="true"
                />
                <div
                  class="text-caption text-medium-emphasis mt-1"
                  style="max-width: 320px;"
                >
                  This setting is managed in Core Settings → Response Settings and shown here for reference.
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Infrastructure Settings (hidden by feature flag) -->
        <section v-if="!flags.ADMIN_HIDE_INFRA_SETTINGS">
          <v-divider />

          <!-- Processing LLM Selection Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $cog
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Processing LLM
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Language model for background operations like content indexing and query reformulation. Fast models recommended.
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="settings.processing_llm"
                  :items="processingLlmOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 160px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Claude Model Selection Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $robot
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Claude Model
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Specific Claude model to use for Anthropic queries
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="settings.claude_model"
                  :items="claudeModelOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 220px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Gemini Model Selection Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $google
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Gemini Model
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Specific Gemini model to use for Google queries
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="settings.gemini_model"
                  :items="geminiModelOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 180px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Smart Model Selection Row -->
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
                    Smart Model Selection
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Automatically choose between fast (Haiku) and quality (Sonnet) models within the selected Response LLM family based on query complexity
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_smart_model_selection"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_smart_model_selection ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>
        </section>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAdminStore } from '@/stores/admin'
import adminAPI from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'
import { useTenantStore } from '@/stores/tenant'
import flags from '@/config/featureFlags'

const adminStore = useAdminStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Reactive state
const settings = ref({
  primary_llm: 'claude',  // Legacy field for backward compatibility
  response_llm: 'claude',  // User-facing responses
  processing_llm: 'claude_haiku',  // Background operations
  claude_model: 'claude-3-5-sonnet-20241022',
  gemini_model: 'gemini-1.5-flash',
  response_claude_model: 'claude-3-5-sonnet-20241022',
  response_gemini_model: 'gemini-1.5-flash',
  processing_claude_model: 'claude-3-haiku-20240307',
  processing_gemini_model: 'gemini-1.5-flash',
  embedding_model: 'models/embedding-001',
  enable_smart_model_selection: true,
  enable_response_smart_selection: true,
  default_search_k: 8,
  expanded_search_k: 12
})

const loading = ref(false)
const error = ref('')
const { showSuccess, showError } = useNotifications()

// Model options
const llmOptions = [
  { title: 'Claude (Anthropic)', value: 'claude' },
  { title: 'Gemini (Google)', value: 'gemini' }
]

const processingLlmOptions = [
  { title: 'Claude Haiku (Fast)', value: 'claude_haiku' },
  { title: 'Claude (Balanced)', value: 'claude' },
  { title: 'Gemini (Google)', value: 'gemini' }
]

const claudeModelOptions = [
  { title: 'Claude 3.5 Sonnet', value: 'claude-3-5-sonnet-20241022' },
  { title: 'Claude 3.5 Haiku', value: 'claude-3-5-haiku-20241022' },
  { title: 'Claude 3 Opus', value: 'claude-3-opus-20240229' }
]

const geminiModelOptions = [
  { title: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' },
  { title: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
  { title: 'Gemini Pro', value: 'gemini-pro' }
]

// Load settings on mount
const loadSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const response = await adminAPI.getSystemConfigSettings()
    if (response) {
      // Merge response with defaults
      settings.value = { ...settings.value, ...response }
      
      // Ensure response_llm is initialized from primary_llm for backward compatibility
      if (!settings.value.response_llm && settings.value.primary_llm) {
        settings.value.response_llm = settings.value.primary_llm
      }
      
      // Ensure processing_llm has a sensible default
      if (!settings.value.processing_llm) {
        settings.value.processing_llm = 'claude_haiku'
      }
    }
  } catch (err) {
    console.error('Failed to load system config settings:', err)
    error.value = `Failed to load system configuration settings: ${  err.response?.data?.detail || err.message}`
  } finally {
    loading.value = false
  }
}

// Save settings
const saveSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    
    // Ensure legacy primary_llm field is synced with response_llm for backward compatibility
    const settingsToSave = { ...settings.value }
    settingsToSave.primary_llm = settingsToSave.response_llm
    
    const response = await adminAPI.updateSystemConfigSettings(settingsToSave)
    if (response && response.success) {
      showSuccess('System configuration settings saved successfully!')
      // Update local settings with the response to ensure UI is in sync
      if (response.settings) {
        settings.value = { ...settings.value, ...response.settings }
      }
    }
  } catch (err) {
    console.error('Failed to save system config settings:', err)
    error.value = `Failed to save system configuration settings: ${  err.response?.data?.detail || err.message}`
    showError('Failed to save system configuration settings')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  console.log('✅ [SystemSettings] Component mounted, currentTenant:', currentTenant.value)
  loadSettings()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [SystemSettings] Tenant slug watcher fired:', { oldSlug, newSlug, currentTenant: currentTenant.value })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [SystemSettings] Tenant slug changed, refreshing system settings')
    loadSettings()
  }
})
</script>

<style scoped>
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

.setting-slider {
  display: flex;
  align-items: center;
  gap: 16px;
}

.setting-value {
  font-size: 14px;
  font-weight: 500;
  min-width: 50px;
  text-align: center;
}

.setting-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 768px) {
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
  }
}
</style>
