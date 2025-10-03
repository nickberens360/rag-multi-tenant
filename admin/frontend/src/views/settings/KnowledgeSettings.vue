<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h5 font-weight-bold">
          Knowledge Settings
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Configure indexing behavior, synchronization, and content processing options
        </p>
      </div>
      <v-btn
        color="primary"
        variant="elevated"
        :loading="saving"
        prepend-icon="$check"
        @click="save"
      >
        Save Changes
      </v-btn>
    </div>

    <div class="grid-container">
      <!-- Knowledge Processing Card -->
      <v-card
        elevation="2"
        class="mb-6"
      >
        <v-card-title class="text-h6 font-weight-bold pa-6">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $book-open
          </v-icon>
          Knowledge Processing Configuration
        </v-card-title>
        
        <v-card-text class="pa-0">
          <!-- Infrastructure Settings (hidden by feature flag) -->
          <section v-if="!flags.ADMIN_HIDE_INFRA_SETTINGS">
            <v-alert
              type="info"
              variant="tonal"
              class="ma-6 mb-4"
            >
              These settings control how content is discovered, indexed, and synchronized across your knowledge base.
            </v-alert>

            <!-- Index on Startup Row -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $book-open
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Index on Startup
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Automatically index all configured directories when the application starts
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="form.index_on_startup"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ form.index_on_startup ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider />

            <!-- Auto-Reindex Deltas Row -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $cached
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Auto-Reindex Changes
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Automatically reindex files when changes are detected during background sync
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="form.auto_reindex_deltas"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ form.auto_reindex_deltas ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider />

            <!-- Background Sync Interval Row -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $clock
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Background Sync Interval
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      How often to check for file changes in seconds (0 disables background sync)
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-text-field
                    v-model.number="form.background_sync_interval_seconds"
                    type="number"
                    variant="outlined"
                    density="compact"
                    :min="0"
                    :max="3600"
                    hide-details
                    style="width: 120px;"
                  />
                </div>
              </div>
            </div>

            <v-divider />

            <!-- Enable Heterogeneity Fallback Row -->
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
                      Enable Heterogeneity Fallback
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Use advanced content classification for mixed content types
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="form.enable_heterogeneity_fallback"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ form.enable_heterogeneity_fallback ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider />

            <!-- Fallback Include Globs Row -->
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
                      Fallback Include Patterns
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Glob patterns to force per-chunk classification (only when heterogeneity fallback is enabled)
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-combobox
                    v-model="form.heterogeneity_fallback_include"
                    variant="outlined"
                    density="compact"
                    multiple
                    chips
                    clearable
                    :disabled="!form.enable_heterogeneity_fallback"
                    hide-details
                    placeholder="e.g., *.md, docs/**"
                    style="width: 280px;"
                  />
                </div>
              </div>
            </div>

            <v-divider />

            <!-- Index Directories Row -->
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
                      Directories to scan and index for content search
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-combobox
                    v-model="form.index_directories"
                    variant="outlined"
                    density="compact"
                    multiple
                    chips
                    clearable
                    hide-details
                    placeholder="e.g., backend/knowledge, public"
                    style="width: 280px;"
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- Simplified message when infrastructure settings are hidden -->
          <section v-else>
            <v-alert
              type="info"
              variant="tonal"
              class="ma-6"
            >
              Knowledge indexing and processing settings are managed at the infrastructure level and are not available in this simplified view.
            </v-alert>
          </section>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { adminAPI } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'
import { useTenantStore } from '@/stores/tenant'
import flags from '@/config/featureFlags'

const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

const form = ref({
  index_on_startup: true,
  background_sync_interval_seconds: 0,
  auto_reindex_deltas: false,
  enable_heterogeneity_fallback: false,
  heterogeneity_fallback_include: [],
  index_directories: ['backend/knowledge', 'public']
})
const saving = ref(false)
const { showSuccess, showError } = useNotifications()

const load = async () => {
  try {
    const resp = await adminAPI.getKnowledgeSettings()
    if (resp?.settings) form.value = { ...form.value, ...resp.settings }
  } catch (e) {
    showError('Failed to load knowledge settings')
  }
}

const save = async () => {
  try {
    saving.value = true
    const resp = await adminAPI.updateKnowledgeSettings(form.value)
    if (resp?.success) showSuccess('Knowledge settings updated')
  } catch (e) {
    showError('Failed to save knowledge settings')
  } finally {
    saving.value = false
  }
}

const reset = () => load()

onMounted(load)

// Reload settings when tenant changes
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await load()
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
  min-width: 70px;
  text-align: right;
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
  
  .setting-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>