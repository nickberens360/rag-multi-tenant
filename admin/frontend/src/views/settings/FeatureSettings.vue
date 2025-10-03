<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Feature Flags</span>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="store.loading"
          prepend-icon="$check"
          @click="saveFeatureFlags"
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
        
        <div v-if="store.featureFlags && filteredKeys.length > 0">
          <v-alert
            type="info"
            variant="tonal"
            class="ma-6 mb-4"
          >
            This page shows active system/UX feature flags only. Settings for caching, routing, and RAG have dedicated
            pages (Response Settings, Routing Settings, and RAG Configuration).
          </v-alert>
          <div 
            v-for="(key, index) in filteredKeys" 
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
                    <div class="feature-description text-medium-emphasis">
                      {{ getFeatureDescription(key) }}
                    </div>
                  </div>
                </div>
                <div class="feature-right">
                  <!-- Boolean settings - switch -->
                  <template v-if="getSettingType(key) === 'boolean'">
                    <v-switch
                      v-model="store.featureFlags[key]"
                      color="primary"
                      inset
                      hide-details
                    />
                    <div class="feature-status text-medium-emphasis">
                      {{ store.featureFlags[key] ? 'Enabled' : 'Disabled' }}
                    </div>
                  </template>
                  
                  <!-- Numeric settings - number input -->
                  <template v-else-if="getSettingType(key) === 'number'">
                    <v-text-field
                      v-model.number="store.featureFlags[key]"
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
                  
                  <!-- Float settings - number input with decimal step -->
                  <template v-else-if="getSettingType(key) === 'float'">
                    <div class="feature-slider">
                      <v-slider
                        v-model="store.featureFlags[key]"
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
                        {{ store.featureFlags[key].toFixed(getFieldBounds(key).decimals || 1) }}
                      </div>
                    </div>
                  </template>
                  
                  <!-- String settings - text input -->
                  <template v-else-if="getSettingType(key) === 'string'">
                    <v-text-field
                      v-model="store.featureFlags[key]"
                      variant="outlined"
                      density="compact"
                      hide-details
                      style="width: 280px;"
                      :placeholder="getFieldPlaceholder(key)"
                    />
                  </template>
                </div>
              </div>
            </div>
            <v-divider v-if="index < filteredKeys.length - 1" />
          </div>
        </div>
        
        <v-alert
          v-else
          type="info"
          variant="tonal"
          class="ma-6"
        >
          No feature flags available
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useFeatureSettingsStore } from '@/stores/featureSettings'
import { useTenantStore } from '@/stores/tenant'
import { useNotifications } from '@/composables/useNotifications'

const store = useFeatureSettingsStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)
const { showSuccess, showError } = useNotifications()

onMounted(() => {
  store.loadData()
})

// Reload settings when tenant changes
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await store.loadData()
  }
}, { deep: true })

const formatFeatureName = (key) => {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const getFeatureDescription = (key) => {
  const descriptions = {
    enable_debug_mode: 'Enable debug mode for troubleshooting',
    enable_maintenance_mode: 'Put system in maintenance mode',
    enable_api_versioning: 'Enable API versioning support',
    enable_illustrations: 'Show illustration images in responses',
    enable_geolocation: 'Use location-based query processing',
    enable_query_preprocessing: 'Preprocess queries for better accuracy'
  }
  return descriptions[key] || 'Feature setting'
}

const getSettingType = (key) => {
  const types = {
    enable_debug_mode: 'boolean',
    enable_maintenance_mode: 'boolean',
    enable_api_versioning: 'boolean',
    enable_illustrations: 'boolean',
    enable_geolocation: 'boolean',
    enable_query_preprocessing: 'boolean'
  }
  return types[key] || 'boolean'
}

const getFieldBounds = (key) => {
  const bounds = {}
  return bounds[key] || { min: 0, max: 100, step: 1, width: 120 }
}

const getFieldPlaceholder = (key) => {
  const placeholders = {}
  return placeholders[key] || ''
}

const getFeatureIcon = (key) => {
  const icons = {
    enable_debug_mode: '$developer-mode',
    enable_maintenance_mode: '$construction',
    enable_api_versioning: '$api',
    enable_illustrations: '$image',
    enable_geolocation: '$map',
    enable_query_preprocessing: '$tune'
  }
  return icons[key]
}

const saveFeatureFlags = async () => {
  try {
    await store.updateFeatureFlags()
    showSuccess('Feature flags updated successfully!')
  } catch (err) {
    showError(`Failed to save feature flags: ${err.message}`)
  }
}

// Only show active and meaningful feature flags managed in FeatureFlags schema
const filteredKeys = computed(() => {
  const allowed = new Set([
    'enable_maintenance_mode',
    'enable_api_versioning',
    'enable_geolocation',
    'enable_query_preprocessing',
    'enable_admin_diagnostics'
  ])
  return Object.keys(store.featureFlags).filter(k => allowed.has(k))
})
</script>

<style scoped>
/* Feature Flags Row Layout */
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

.feature-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

/* Responsive adjustments */
@media (max-width: 768px) {
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
  
  .feature-slider {
    width: 100%;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .feature-slider .feature-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>
