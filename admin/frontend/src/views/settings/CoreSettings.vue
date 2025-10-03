<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h5 font-weight-bold">
          Core Settings
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Essential system configuration, LLM models, and API key management
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
      <!-- LLM Configuration Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $brain
          </v-icon>
          Language Model Configuration
        </v-card-title>
        
        <v-card-text class="pa-0">
          <v-alert
            v-if="modelError"
            type="error"
            variant="tonal"
            class="ma-6 mb-4"
          >
            {{ modelError }}
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
                  $message-text
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Response LLM
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Language model used for all user-facing chat responses
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="responseSettings.response_llm"
                  :items="llmOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 160px;"
                />
              </div>
            </div>
          </div>

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
                    Language model for background operations like content indexing
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="systemSettings.processing_llm"
                  :items="processingLlmOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 200px;"
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
                    Automatically choose between fast and quality models based on query complexity
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="responseSettings.enable_smart_selection"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ responseSettings.enable_smart_selection ? 'Enabled' : 'Disabled' }}
                </div>
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
                    Specific Claude model for response generation
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="responseSettings.response_claude_model"
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
                    Specific Gemini model for response generation
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-select
                  v-model="responseSettings.response_gemini_model"
                  :items="geminiModelOptions"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="width: 180px;"
                />
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- API Keys Management Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6 d-flex justify-space-between align-center">
          <div class="d-flex align-center">
            <v-icon
              color="primary"
              class="mr-2"
            >
              $key
            </v-icon>
            API Keys
          </div>
          <v-btn
            color="primary"
            prepend-icon="$plus"
            size="small"
            @click="showCreateDialog = true"
          >
            Add Key
          </v-btn>
        </v-card-title>
        
        <v-card-text>
          <!-- Security Notice -->
          <v-alert
            type="info"
            variant="tonal"
            class="mb-4"
            icon="$shield-check"
          >
            API keys are encrypted using AES-256-GCM before storage. Only the last 4 characters are visible after creation.
          </v-alert>

          <!-- Active Keys List -->
          <div
            v-if="activeKeys.length > 0"
            class="keys-list"
          >
            <div
              v-for="key in activeKeys"
              :key="key.id"
              class="key-item"
            >
              <div class="key-info">
                <div class="d-flex align-center">
                  <v-chip
                    :color="getKeyTypeColor(key.key_type)"
                    size="small"
                    class="mr-2"
                  >
                    {{ key.key_type }}
                  </v-chip>
                  <span class="font-weight-medium">{{ key.key_name }}</span>
                </div>
                <div class="text-caption text-medium-emphasis mt-1">
                  Key: ****{{ key.last_four }} | 
                  Last used: {{ key.last_used_at ? formatDateTime(key.last_used_at) : 'Never' }}
                </div>
              </div>
              <div class="key-actions">
                <v-btn
                  icon="$check-circle"
                  size="small"
                  color="info"
                  variant="text"
                  :loading="validating === key.key_name"
                  @click="validateKey(key)"
                />
                <v-btn
                  icon="$pencil"
                  size="small"
                  color="primary"
                  variant="text"
                  @click="editKey(key)"
                />
              </div>
            </div>
          </div>
          
          <div
            v-else
            class="text-center py-4 text-medium-emphasis"
          >
            No API keys configured. Add your first API key to get started.
          </div>

          <div class="text-center mt-4">
            <v-btn
              variant="outlined"
              prepend-icon="$settings"
              @click="$router.push((() => { const slug = $pinia.state.value.tenant?.currentTenant?.slug; return slug ? `/${slug}/settings/api-keys` : '/settings/api-keys' })())"
            >
              Manage All Keys
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- System Mode Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $cog-box
          </v-icon>
          System Mode
        </v-card-title>
        
        <v-card-text class="pa-0">
          <v-alert
            v-if="systemError"
            type="error"
            variant="tonal"
            class="ma-6 mb-4"
          >
            {{ systemError }}
          </v-alert>
          
          <!-- Success notifications are shown via global toasts -->

          <!-- Debug Mode temporarily hidden -->

          <!-- Maintenance Mode Toggle -->
          <div
            v-if="featureStore && featureStore.featureFlags"
            class="setting-row"
          >
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="error"
                  class="setting-icon"
                >
                  $wrench
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Maintenance Mode
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Put the system into maintenance mode (blocks user queries)
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="featureStore.featureFlags.enable_maintenance_mode"
                  color="error"
                  inset
                  hide-details
                  @update:model-value="() => featureStore.updateFeatureFlags()"
                />
                <div class="setting-status text-medium-emphasis">
                  {{ featureStore.featureFlags.enable_maintenance_mode ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Create/Edit API Key Dialog -->
    <v-dialog
      v-model="showCreateDialog"
      max-width="600px"
      persistent
    >
      <v-card>
        <v-card-title>
          <span class="text-h6">{{ editingKey ? 'Edit' : 'Add' }} API Key</span>
        </v-card-title>

        <v-card-text>
          <v-form
            ref="keyFormRef"
            v-model="formValid"
          >
            <v-text-field
              v-model="keyForm.key_name"
              label="Key Name"
              :rules="nameRules"
              :readonly="!!editingKey"
              hint="Unique identifier for this API key (e.g., 'anthropic_primary')"
              persistent-hint
              required
            />

            <v-select
              v-model="keyForm.key_type"
              label="Key Type"
              :items="keyTypeOptions"
              item-title="text"
              item-value="value"
              :rules="typeRules"
              :readonly="!!editingKey"
              variant="outlined"
              density="comfortable"
              required
              class="mt-4"
            />

            <v-textarea
              v-model="keyForm.api_key"
              label="API Key"
              :rules="keyRules"
              :type="showKey ? 'text' : 'password'"
              :append-inner-icon="showKey ? '$eye-off' : '$eye'"
              rows="3"
              auto-grow
              :hint="editingKey ? 'Enter new API key to replace current key, or leave unchanged to keep existing key' : 'The actual API key from your provider'"
              persistent-hint
              required
              class="mt-4"
              @click:append-inner="showKey = !showKey"
            />

            <v-alert
              v-if="!editingKey"
              type="warning"
              variant="tonal"
              class="mt-4"
            >
              <v-alert-title>Security Notice</v-alert-title>
              The API key will be encrypted and stored securely. 
              After saving, only the last 4 characters will be visible.
            </v-alert>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            :disabled="savingKey"
            @click="closeDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="savingKey"
            :disabled="!formValid"
            @click="saveKey"
          >
            {{ editingKey ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAdminStore } from '@/stores/admin'
import { useCoreSettingsStore } from '@/stores/coreSettings'
import { useFeatureSettingsStore } from '@/stores/featureSettings'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI as apiService } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'

const adminStore = useAdminStore()
const coreStore = useCoreSettingsStore()
const featureStore = useFeatureSettingsStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Reactive state for different settings
const responseSettings = ref({
  response_llm: 'claude',
  enable_smart_selection: true,
  response_claude_model: 'claude-3-5-sonnet-20241022',
  response_gemini_model: 'gemini-1.5-flash'
})

const systemSettings = ref({
  processing_llm: 'claude_haiku'
})

// Feature flags come from centralized store

// Loading and error states
const loading = ref(false)
const saving = ref(false)
const modelError = ref('')
const systemError = ref('')
const { showSuccess, showError } = useNotifications()

// API Keys state
const keys = ref([])
const activeKeys = computed(() => keys.value.filter(key => key.is_active))

// Dialog state for API keys
const showCreateDialog = ref(false)
const editingKey = ref(null)
const formValid = ref(false)
const keyForm = reactive({
  key_name: '',
  key_type: '',
  api_key: ''
})
const showKey = ref(false)
const savingKey = ref(false)
const validating = ref(null)
const keyFormRef = ref(null)

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

// Key type options
const keyTypeOptions = [
  { text: 'Anthropic (Claude)', value: 'anthropic' },
  { text: 'Google (Gemini)', value: 'google' },
  { text: 'OpenAI (GPT)', value: 'openai' }
]

// Form validation rules
const nameRules = [
  v => Boolean(v) || 'Key name is required',
  v => (v && v.length >= 3) || 'Key name must be at least 3 characters',
  v => (v && /^[a-z0-9_]+$/.test(v)) || 'Key name must contain only lowercase letters, numbers, and underscores',
  v => !keys.value.some(k => k.key_name === v && k.id !== editingKey.value?.id) || 'Key name already exists'
]

const typeRules = [
  v => Boolean(v) || 'Key type is required'
]

const keyRules = [
  v => Boolean(v) || 'API key is required',
  v => {
    if (!v) return 'API key is required'
    const isMasked = /^\*{10,}\w{4}$/.test(v)
    return isMasked || v.length >= 10 || 'API key must be at least 10 characters'
  },
  v => (v && v.trim() === v) || 'API key cannot have leading or trailing whitespace'
]

// Methods
const loadAllSettings = async () => {
  try {
    loading.value = true
    
    // Load core settings through store
    await coreStore.loadData()
    
    // Load response settings
    const responseData = await apiService.getResponseSettings()
    if (responseData) {
      responseSettings.value = { ...responseSettings.value, ...responseData }
    }
    
    // Load system settings
    const systemData = await apiService.getSystemConfigSettings()
    if (systemData) {
      systemSettings.value = { ...systemSettings.value, ...systemData }
    }
    
    // Load feature flags via store
    await featureStore.loadData()
    
    // Load API keys
    await fetchKeys()
    
  } catch (err) {
    console.error('Failed to load settings:', err)
    modelError.value = `Failed to load settings: ${  err.response?.data?.detail || err.message}`
  } finally {
    loading.value = false
  }
}

const saveAllSettings = async () => {
  try {
    saving.value = true
    modelError.value = ''
    systemError.value = ''
    
    // Save response settings
    await apiService.updateResponseSettings(responseSettings.value)
    
    // Save system settings
    await apiService.updateSystemConfigSettings(systemSettings.value)
    
    // Save feature flags via store
    await featureStore.updateFeatureFlags()
    
    showSuccess('Core settings saved successfully!')
    showSuccess('System mode updated successfully!')
    
  } catch (err) {
    console.error('Failed to save settings:', err)
    const errorMsg = `Failed to save settings: ${  err.response?.data?.detail || err.message}`
    modelError.value = errorMsg
    systemError.value = errorMsg
    showError(errorMsg)
  } finally {
    saving.value = false
  }
}

// API Keys methods
const fetchKeys = async () => {
  try {
    const response = await apiService.getApiKeys(false) // Only active keys
    keys.value = response.keys
  } catch (error) {
    console.error('Error fetching API keys:', error)
  }
}

const getKeyTypeColor = (type) => {
  const colors = {
    anthropic: 'deep-orange',
    google: 'blue',
    openai: 'green'
  }
  return colors[type] || 'grey'
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

const editKey = (key) => {
  if (!key) return
  
  editingKey.value = key
  keyForm.key_name = key.key_name || ''
  keyForm.key_type = key.key_type || ''
  
  const getTypicalKeyLength = (keyType) => {
    const lengths = {
      'anthropic': 104,
      'google': 40,
      'openai': 56
    }
    return lengths[keyType] || 50
  }
  
  const keyLength = getTypicalKeyLength(key.key_type)
  const asteriskCount = keyLength - 4
  const maskedKey = '*'.repeat(asteriskCount) + (key.last_four || '')
  
  keyForm.api_key = maskedKey
  showCreateDialog.value = true
}

const closeDialog = () => {
  showCreateDialog.value = false
  editingKey.value = null
  keyForm.key_name = ''
  keyForm.key_type = ''
  keyForm.api_key = ''
  showKey.value = false
  nextTick(() => {
    if (keyFormRef.value) {
      keyFormRef.value.resetValidation()
    }
  })
}

const saveKey = async () => {
  if (!formValid.value) return

  savingKey.value = true
  const isEditing = Boolean(editingKey.value)
  
  try {
    if (isEditing) {
      const isMasked = /^\*{10,}\w{4}$/.test(keyForm.api_key)
      if (isMasked) {
        closeDialog()
        return
      }
      
      await apiService.updateApiKey(editingKey.value.key_name, {
        api_key: keyForm.api_key
      })
    } else {
      await apiService.createApiKey({
        key_name: keyForm.key_name,
        key_type: keyForm.key_type,
        api_key: keyForm.api_key
      })
    }

    closeDialog()
    await fetchKeys()
    
  } catch (error) {
    console.error('Error saving API key:', error)
  } finally {
    savingKey.value = false
  }
}

const validateKey = async (key) => {
  validating.value = key.key_name
  try {
    const response = await apiService.validateApiKey(key.key_name)
    // Show validation result (could add a snackbar here)
    console.log('Validation result:', response)
  } catch (error) {
    console.error('Error validating API key:', error)
  } finally {
    validating.value = null
  }
}

onMounted(() => {
  loadAllSettings()
})

// Reload settings when tenant changes
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await loadAllSettings()
  }
}, { deep: true })
</script>

<style scoped>
/* Grid layout for responsive cards */
.grid-container {
  display: grid;
  gap: 24px;
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
}

/* Keys list styling */
.keys-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.key-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgba(var(--v-theme-surface));
}

.key-info {
  flex: 1;
}

.key-actions {
  display: flex;
  gap: 8px;
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

  .key-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .key-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
