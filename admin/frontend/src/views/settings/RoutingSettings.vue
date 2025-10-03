<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Query Routing Settings</span>
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
          v-if="store.error"
          type="error"
          variant="tonal"
          class="ma-6 mb-4"
        >
          {{ store.error }}
        </v-alert>
        
        <!-- Enable Smart Routing Row -->
        <div class="routing-row">
          <div class="routing-content">
            <div class="routing-left">
              <v-icon
                color="primary"
                class="routing-icon"
              >
                $brain
              </v-icon>
              <div class="routing-info">
                <div class="routing-title text-high-emphasis">
                  Enable Smart Routing
                </div>
                <div class="routing-description text-medium-emphasis">
                  Use intelligent routing algorithms for query processing
                </div>
              </div>
            </div>
            <div class="routing-right">
              <v-switch
                v-model="store.settings.enable_smart_routing"
                color="primary"
                inset
                hide-details
              />
              <div class="routing-status text-medium-emphasis">
                {{ store.settings.enable_smart_routing ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Enable Fuzzy Matching Row -->
        <div class="routing-row">
          <div class="routing-content">
            <div class="routing-left">
              <v-icon
                color="primary"
                class="routing-icon"
              >
                $target
              </v-icon>
              <div class="routing-info">
                <div class="routing-title text-high-emphasis">
                  Enable Fuzzy Matching
                </div>
                <div class="routing-description text-medium-emphasis">
                  Allow approximate string matching for better results
                </div>
              </div>
            </div>
            <div class="routing-right">
              <v-switch
                v-model="store.settings.enable_fuzzy_matching"
                color="primary"
                inset
                hide-details
              />
              <div class="routing-status text-medium-emphasis">
                {{ store.settings.enable_fuzzy_matching ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Similarity Threshold Row -->
        <div class="routing-row">
          <div class="routing-content">
            <div class="routing-left">
              <v-icon
                color="primary"
                class="routing-icon"
              >
                $tune
              </v-icon>
              <div class="routing-info">
                <div class="routing-title text-high-emphasis">
                  Search Result Threshold
                </div>
                <div class="routing-description text-medium-emphasis">
                  Minimum similarity score required to include results in responses (0.0 = very strict, 1.0 = very inclusive)
                </div>
              </div>
            </div>
            <div class="routing-right">
              <div class="routing-slider">
                <v-slider
                  v-model="store.settings.similarity_threshold"
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
                <div class="routing-status text-medium-emphasis">
                  {{ store.settings.similarity_threshold.toFixed(1) }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <v-divider />

        <!-- Max Search Results Row -->
        <div class="routing-row">
          <div class="routing-content">
            <div class="routing-left">
              <v-icon
                color="primary"
                class="routing-icon"
              >
                $numeric
              </v-icon>
              <div class="routing-info">
                <div class="routing-title text-high-emphasis">
                  Max Search Results
                </div>
                <div class="routing-description text-medium-emphasis">
                  Maximum number of search results to return
                </div>
              </div>
            </div>
            <div class="routing-right">
              <v-text-field
                v-model.number="store.settings.max_search_results"
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
        <div class="routing-row">
          <div class="routing-content">
            <div class="routing-left">
              <v-icon
                color="primary"
                class="routing-icon"
              >
                $tune
              </v-icon>
              <div class="routing-info">
                <div class="routing-title text-high-emphasis">
                  Fuzzy Threshold
                </div>
                <div class="routing-description text-medium-emphasis">
                  Threshold for fuzzy string matching accuracy
                </div>
              </div>
            </div>
            <div class="routing-right">
              <div class="routing-slider">
                <v-slider
                  v-model="store.settings.fuzzy_threshold"
                  :min="0.0"
                  :max="1.0"
                  :step="0.1"
                  thumb-label="always"
                  show-ticks="always"
                  color="primary"
                  track-color="grey-lighten-3"
                  thumb-color="primary"
                  :disabled="!store.settings.enable_fuzzy_matching"
                  hide-details
                  style="width: 200px;"
                />
                <div class="routing-status text-medium-emphasis">
                  {{ store.settings.fuzzy_threshold.toFixed(1) }}
                </div>
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
import { useRoutingSettingsStore } from '@/stores/routingSettings'
import { useNotifications } from '@/composables/useNotifications'
import { useTenantStore } from '@/stores/tenant'

const store = useRoutingSettingsStore()
const { showSuccess, showError } = useNotifications()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

onMounted(() => {
  console.log('✅ [RoutingSettings] Component mounted, currentTenant:', currentTenant.value)
  store.loadData()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [RoutingSettings] Tenant slug watcher fired:', { oldSlug, newSlug, currentTenant: currentTenant.value })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [RoutingSettings] Tenant slug changed, refreshing routing settings')
    store.loadData()
  }
})

const saveSettings = async () => {
  try {
    await store.updateSettings()
    showSuccess('Routing settings saved successfully!')
  } catch (err) {
    showError(`Failed to save settings: ${err.message}`)
  }
}
</script>

<style scoped>
/* Routing Settings Row Layout */
.routing-row {
  padding: 20px 24px;
}

.routing-row:last-child {
  border-bottom: none;
}

.routing-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.routing-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.routing-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

.routing-info {
  flex: 1;
  min-width: 0;
}

.routing-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.routing-description {
  font-size: 14px;
  line-height: 1.4;
}

.routing-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.routing-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

.routing-slider {
  display: flex;
  align-items: center;
}

.routing-slider .routing-status {
  margin-left: 16px;
  min-width: 50px;
  text-align: right;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .routing-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .routing-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .routing-slider {
    width: 100%;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .routing-slider .routing-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>