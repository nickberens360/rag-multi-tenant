<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Security & Privacy Settings</span>
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
          Security settings here govern rate limiting, analytics, and logging privacy. <strong>Excluded IPs</strong> and
          <strong>IP anonymization</strong> now apply to query logging. Feature flags like caching and routing are managed in
          their respective settings pages.
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
        
        <!-- IP Anonymization Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon
                color="primary"
                class="setting-icon"
              >
                $shield-check
              </v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">
                  IP Anonymization
                </div>
                <div class="setting-description text-medium-emphasis">
                  Anonymize IP addresses in logs for privacy compliance
                </div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.anonymize_ips"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.anonymize_ips ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Advanced Security Settings (hidden by feature flag) -->
        <section v-if="!flags.ADMIN_HIDE_INFRA_SETTINGS">
          <v-divider />

          <!-- Analytics & Monitoring Section Header -->
          <div class="section-header">
            <v-icon
              color="primary"
              class="section-icon"
            >
              $chart-line
            </v-icon>
            <div class="section-title">
              Analytics & Monitoring
            </div>
          </div>

          <!-- Enable Analytics Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $chart-line
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable Analytics
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Collect and analyze system usage statistics and performance metrics
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_analytics"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_analytics ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Query Logging Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $clipboard-list
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable Query Logging
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Log all user queries for analysis and improvement
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_query_logging"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_query_logging ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Query Log Retention Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $clock-outline
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Query Log Retention (Days)
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Number of days to keep query logs before automatic deletion
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-text-field
                  v-model.number="settings.query_log_retention_days"
                  type="number"
                  variant="outlined"
                  density="compact"
                  :min="1"
                  :max="365"
                  :disabled="!settings.enable_query_logging"
                  hide-details
                  style="width: 120px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Session Timeout Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $timer
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Session Timeout
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Admin session timeout in minutes (30-1440)
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-text-field
                  v-model.number="settings.session_timeout_minutes"
                  type="number"
                  variant="outlined"
                  density="compact"
                  :min="30"
                  :max="1440"
                  suffix="min"
                  hide-details
                  style="width: 140px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Session Fingerprinting Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $fingerprint
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Session Fingerprinting
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Enable session fingerprinting for enhanced security
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_session_fingerprinting"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_session_fingerprinting ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Audit Logging Row -->
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
                    Audit Logging
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Log all admin actions for security auditing
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_audit_logging"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_audit_logging ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Rate Limiting & Protection Section Header -->
          <div class="section-header">
            <v-icon
              color="primary"
              class="section-icon"
            >
              $shield
            </v-icon>
            <div class="section-title">
              Rate Limiting & Protection
            </div>
          </div>

          <!-- Enable Rate Limiting Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $speedometer
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Enable Rate Limiting
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Limit the number of requests to prevent abuse and ensure fair usage
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_rate_limiting"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_rate_limiting ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Rate Limit Requests Row -->
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
                    Rate Limit Requests
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Maximum number of requests allowed per time window (1-10000)
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-text-field
                  v-model.number="settings.rate_limit_requests"
                  type="number"
                  variant="outlined"
                  density="compact"
                  :min="1"
                  :max="10000"
                  :disabled="!settings.enable_rate_limiting"
                  hide-details
                  style="width: 120px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Rate Limit Window Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $clock-outline
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Rate Limit Window (seconds)
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Time window for rate limit counting (1-3600 seconds)
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-text-field
                  v-model.number="settings.rate_limit_window"
                  type="number"
                  variant="outlined"
                  density="compact"
                  :min="1"
                  :max="3600"
                  :disabled="!settings.enable_rate_limiting"
                  hide-details
                  style="width: 120px;"
                />
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Input Validation Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $check-circle
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Input Validation
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Enable strict input validation and sanitization
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-switch
                  v-model="settings.enable_input_validation"
                  color="primary"
                  inset
                  hide-details
                />
                <div class="setting-status text-medium-emphasis">
                  {{ settings.enable_input_validation ? 'Enabled' : 'Disabled' }}
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Low Query Quality Threshold Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $alert-circle
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Quality Alert Threshold
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    Flag queries with similarity scores below this threshold for quality monitoring and analysis
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <div class="setting-slider">
                  <v-slider
                    v-model="similarityThresholdPercent"
                    :min="0"
                    :max="100"
                    :step="1"
                    thumb-label="always"
                    show-ticks="always"
                    color="primary"
                    track-color="grey-lighten-3"
                    thumb-color="primary"
                    hide-details
                    style="width: 200px;"
                  />
                  <div class="setting-value text-medium-emphasis">
                    {{ similarityThresholdPercent }}%
                  </div>
                </div>
              </div>
            </div>
          </div>

          <v-divider />

          <!-- Excluded IPs Row -->
          <div class="setting-row">
            <div class="setting-content">
              <div class="setting-left">
                <v-icon
                  color="primary"
                  class="setting-icon"
                >
                  $ip-network
                </v-icon>
                <div class="setting-info">
                  <div class="setting-title text-high-emphasis">
                    Excluded IP Addresses
                  </div>
                  <div class="setting-description text-medium-emphasis">
                    IP addresses to exclude from logging (one per line)
                  </div>
                </div>
              </div>
              <div class="setting-right">
                <v-textarea
                  v-model="excludedIpsText"
                  variant="outlined"
                  density="compact"
                  placeholder="192.168.1.1&#10;10.0.0.1"
                  rows="3"
                  hide-details
                  style="width: 200px;"
                />
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
import { useTenantStore } from '@/stores/tenant'
import adminAPI from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'
import flags from '@/config/featureFlags'

const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

const adminStore = useAdminStore()

// Reactive state
const settings = ref({
  excluded_ips: [],
  anonymize_ips: true,
  // Analytics & Monitoring (consolidated from FeatureFlags)
  enable_analytics: true,
  enable_query_logging: true,
  enable_audit_logging: true,
  query_log_retention_days: 30,
  // Quality Monitoring
  low_similarity_threshold: 0.7,
  // Session Security
  session_timeout_minutes: 480,
  enable_session_fingerprinting: true,
  // Rate Limiting (consolidated from FeatureFlags)
  enable_rate_limiting: true,
  rate_limit_requests: 100,
  rate_limit_window: 60,
  // Input Validation
  enable_input_validation: true
})

const loading = ref(false)
const error = ref('')
const { showSuccess, showError } = useNotifications()

// Convert arrays to text for display
const excludedIpsText = computed({
  get: () => settings.value.excluded_ips.join('\n'),
  set: (value) => {
    settings.value.excluded_ips = value ? value.split('\n').map(ip => ip.trim()).filter(ip => ip) : []
  }
})


// Convert similarity threshold to percentage for display
const similarityThresholdPercent = computed({
  get: () => Math.round(settings.value.low_similarity_threshold * 100),
  set: (value) => {
    settings.value.low_similarity_threshold = value / 100
  }
})

// Load settings on mount
const loadSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const response = await adminAPI.getSecuritySettings()
    if (response) {
      settings.value = { ...settings.value, ...response }
    }
  } catch (err) {
    console.error('Failed to load security settings:', err)
    error.value = `Failed to load security settings: ${  err.response?.data?.detail || err.message}`
  } finally {
    loading.value = false
  }
}

// Save settings
const saveSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const response = await adminAPI.updateSecuritySettings(settings.value)
    if (response && response.success) {
      showSuccess('Security settings saved successfully!')
    }
  } catch (err) {
    console.error('Failed to save security settings:', err)
    error.value = `Failed to save security settings: ${  err.response?.data?.detail || err.message}`
    showError('Failed to save security settings')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSettings()
})

// Reload settings when tenant changes
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await loadSettings()
  }
}, { deep: true })
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
