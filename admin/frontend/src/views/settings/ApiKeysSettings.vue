<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h5 font-weight-bold">
          API Keys Management
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Securely manage API keys for external services
        </p>
      </div>
      <div>
        <v-btn
          v-if="hasEnvironmentKeys"
          color="info"
          prepend-icon="$import"
          :loading="migrating"
          variant="outlined"
          class="mr-2"
          @click="migrateFromEnvironment"
        >
          Migrate from Environment
        </v-btn>
        <v-btn
          color="primary"
          prepend-icon="$plus"
          @click="showCreateDialog = true"
        >
          Add API Key
        </v-btn>
      </div>
    </div>

    <!-- Security Notice -->
    <v-alert
      type="info"
      variant="tonal"
      class="mb-6"
      icon="$shield-check"
    >
      <v-alert-title>Security Information</v-alert-title>
      <div>
        API keys are encrypted using AES-256-GCM before storage. 
        Only the last 4 characters are visible after creation. 
        All operations are logged for security auditing.
      </div>
    </v-alert>

    <!-- Migration Results -->
    <v-alert
      v-if="migrationResults"
      :type="migrationResults.success ? 'success' : 'error'"
      variant="tonal"
      class="mb-6"
      dismissible
      @click:close="migrationResults = null"
    >
      <v-alert-title>Migration Results</v-alert-title>
      <div>{{ migrationResults.message }}</div>
    </v-alert>

    <!-- API Keys List -->
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span>API Keys</span>
        <div class="d-flex align-center">
          <v-switch
            v-model="showInactive"
            label="Show Inactive"
            color="primary"
            hide-details
            inset
            @update:model-value="fetchKeys"
          />
          <v-btn
            icon="$refresh"
            size="small"
            :loading="loading"
            class="ml-2"
            @click="fetchKeys"
          />
        </div>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="keys"
        :loading="loading"
        item-key="id"
        no-data-text="No API keys found"
        class="elevation-0"
      >
        <!-- Key Name -->
        <template #[`item.key_name`]="{ item }">
          <div class="d-flex align-center">
            <v-chip
              :color="getKeyTypeColor(item.key_type)"
              size="small"
              class="mr-2"
            >
              {{ item.key_type }}
            </v-chip>
            <span class="font-weight-medium">{{ item.key_name }}</span>
          </div>
        </template>

        <!-- Last Four -->
        <template #[`item.last_four`]="{ item }">
          <span class="font-mono">****{{ item.last_four }}</span>
        </template>

        <!-- Status -->
        <template #[`item.is_active`]="{ item }">
          <v-chip
            :color="item.is_active ? 'success' : 'error'"
            :text="item.is_active ? 'Active' : 'Inactive'"
            size="small"
          />
        </template>

        <!-- Last Used -->
        <template #[`item.last_used_at`]="{ item }">
          <span
            v-if="item.last_used_at"
            class="text-body-2"
          >
            {{ formatDateTime(item.last_used_at) }}
          </span>
          <span
            v-else
            class="text-medium-emphasis"
          >Never</span>
        </template>

        <!-- Actions -->
        <template #[`item.actions`]="{ item }">
          <div class="action-buttons">
            <v-tooltip text="Test Connection">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="$check-circle"
                  size="small"
                  color="info"
                  variant="text"
                  :loading="validating === item.key_name"
                  @click="validateKey(item)"
                />
              </template>
            </v-tooltip>

            <v-tooltip text="Edit Key">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="$pencil"
                  size="small"
                  color="primary"
                  variant="text"
                  @click="editKey(item)"
                />
              </template>
            </v-tooltip>

            <v-tooltip :text="item.is_active ? 'Disable' : 'Enable'">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="item.is_active ? '$eye-off' : '$eye'"
                  size="small"
                  :color="item.is_active ? 'warning' : 'success'"
                  variant="text"
                  :loading="toggling === item.key_name"
                  @click="toggleKey(item)"
                />
              </template>
            </v-tooltip>

            <v-tooltip text="Delete Key">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="$delete"
                  size="small"
                  color="error"
                  variant="text"
                  @click="confirmDelete(item)"
                />
              </template>
            </v-tooltip>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
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
            :disabled="saving"
            @click="closeDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            :disabled="!formValid"
            @click="saveKey"
          >
            {{ editingKey ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title>
          <span class="text-h6">Confirm Deletion</span>
        </v-card-title>

        <v-card-text>
          <v-alert
            type="error"
            variant="tonal"
            class="mb-4"
          >
            <v-alert-title>Permanent Action</v-alert-title>
            This action cannot be undone.
          </v-alert>

          Are you sure you want to delete the API key 
          <strong>{{ keyToDelete?.key_name }}</strong>?
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            :disabled="deleting"
            @click="showDeleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deleting"
            @click="deleteKey"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Toasts are handled globally via NotificationMessage -->
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { adminAPI as apiService } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'
import { useTenantStore } from '@/stores/tenant'

const { showSuccess, showError, showInfo } = useNotifications()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Reactive state
const keys = ref([])
const loading = ref(false)
const showInactive = ref(false)
const migrating = ref(false)
const migrationResults = ref(null)

// Dialog state
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const editingKey = ref(null)
const keyToDelete = ref(null)

// Form state
const formValid = ref(false)
const keyForm = reactive({
  key_name: '',
  key_type: '',
  api_key: ''
})
const showKey = ref(false)
const saving = ref(false)
const deleting = ref(false)

// Validation state
const validating = ref(null)
const toggling = ref(null)
const showValidationResult = ref(false)
const validationResult = ref(null)

// Key form reference
const keyFormRef = ref(null)

// Computed
const hasEnvironmentKeys = computed(() => {
  // Check if any common environment-based keys are missing
  const commonKeys = ['anthropic_primary', 'google_primary', 'openai_primary']
  const existingNames = keys.value.map(k => k.key_name)
  return commonKeys.some(name => !existingNames.includes(name))
})

// Table headers
const headers = [
  { title: 'Name', key: 'key_name', sortable: true },
  { title: 'Key', key: 'last_four', sortable: false },
  { title: 'Status', key: 'is_active', sortable: true },
  { title: 'Last Used', key: 'last_used_at', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '240px', align: 'center' }
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
    // Allow masked format for editing (***...***last4) with variable asterisk count
    const isMasked = /^\*{10,}\w{4}$/.test(v) // At least 10 asterisks + 4 chars
    return isMasked || v.length >= 10 || 'API key must be at least 10 characters'
  },
  v => (v && v.trim() === v) || 'API key cannot have leading or trailing whitespace'
]

// Methods
const fetchKeys = async () => {
  loading.value = true
  try {
    const response = await apiService.getApiKeys(showInactive.value)
    keys.value = response.keys
  } catch (error) {
    console.error('Error fetching API keys:', error)
    showError('Failed to fetch API keys')
  } finally {
    loading.value = false
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
  
  // Create masked key with appropriate length based on key type
  const getTypicalKeyLength = (keyType) => {
    const lengths = {
      'anthropic': 104, // sk-ant-... format
      'google': 40,     // AIza... format  
      'openai': 56      // sk-... format
    }
    return lengths[keyType] || 50 // Default fallback
  }
  
  const keyLength = getTypicalKeyLength(key.key_type)
  const asteriskCount = keyLength - 4 // Total length minus last 4 chars
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

  saving.value = true
  const isEditing = Boolean(editingKey.value)
  
  try {
    if (isEditing) {
      // Check if the user is sending back the masked value (no actual change)
      const isMasked = /^\*{10,}\w{4}$/.test(keyForm.api_key)
      if (isMasked) {
        // User didn't change the key, just close the dialog
        closeDialog()
        return
      }
      
      // Update existing key with new value
      await apiService.updateApiKey(editingKey.value.key_name, {
        api_key: keyForm.api_key
      })
    } else {
      // Create new key
      await apiService.createApiKey({
        key_name: keyForm.key_name,
        key_type: keyForm.key_type,
        api_key: keyForm.api_key
      })
    }

    closeDialog()
    await fetchKeys()
    showSuccess(isEditing ? 'API key updated successfully' : 'API key created successfully')
  } catch (error) {
    console.error('Error saving API key:', error)
    showError('Error saving API key')
  } finally {
    saving.value = false
  }
}

const toggleKey = async (key) => {
  toggling.value = key.key_name
  try {
    await apiService.toggleApiKey(key.key_name, !key.is_active)
    await fetchKeys()
  } catch (error) {
    console.error('Error toggling API key:', error)
    showError('Error toggling API key')
  } finally {
    toggling.value = null
  }
}

const confirmDelete = (key) => {
  keyToDelete.value = key
  showDeleteDialog.value = true
}

const deleteKey = async () => {
  if (!keyToDelete.value) return

  deleting.value = true
  try {
    await apiService.deleteApiKey(keyToDelete.value.key_name)
    showDeleteDialog.value = false
    keyToDelete.value = null
    await fetchKeys()
  } catch (error) {
    console.error('Error deleting API key:', error)
    showError('Error deleting API key')
  } finally {
    deleting.value = false
  }
}

const validateKey = async (key) => {
  validating.value = key.key_name
  try {
    const response = await apiService.validateApiKey(key.key_name)
    validationResult.value = response
    if (response?.valid) {
      showSuccess(`${response?.key_name || 'API key'} validated successfully`)
    } else {
      showError(`${response?.key_name || 'API key'} validation failed${response?.message ? `: ${response.message}` : ''}`)
    }
  } catch (error) {
    console.error('Error validating API key:', error)
    validationResult.value = {
      key_name: key.key_name,
      valid: false,
      message: 'Validation failed'
    }
    showError(`${key.key_name} validation failed`)
  } finally {
    validating.value = null
  }
}

const migrateFromEnvironment = async () => {
  migrating.value = true
  migrationResults.value = null
  
  try {
    const response = await apiService.migrateApiKeysFromEnv()
    migrationResults.value = {
      success: true,
      message: response.message
    }
    await fetchKeys()
  } catch (error) {
    console.error('Error migrating API keys:', error)
    migrationResults.value = {
      success: false,
      message: `Migration failed: ${  error.response?.data?.detail || error.message}`
    }
  } finally {
    migrating.value = false
  }
}

// Initialize
onMounted(() => {
  console.log('✅ [ApiKeysSettings] Component mounted, currentTenant:', currentTenant.value)
  fetchKeys()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [ApiKeysSettings] Tenant slug watcher fired:', { oldSlug, newSlug, currentTenant: currentTenant.value })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [ApiKeysSettings] Tenant slug changed, refreshing API keys')
    fetchKeys()
  }
})
</script>

<style scoped>
.font-mono {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 200px;
}

.action-buttons .v-btn {
  min-width: 40px;
  margin: 0 2px;
}

/* Ensure proper spacing on mobile */
@media (max-width: 768px) {
  .action-buttons {
    gap: 2px;
    min-width: 160px;
  }
  
  .action-buttons .v-btn {
    min-width: 36px;
    margin: 0 1px;
  }
}
</style>
