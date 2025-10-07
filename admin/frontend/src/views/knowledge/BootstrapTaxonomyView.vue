<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-8">
      <div>
        <h2 class="text-h5 font-weight-bold mb-2">Bootstrap Taxonomy</h2>
        <p class="text-body-2 text-medium-emphasis">
          Quick-start your taxonomy with industry-specific templates
        </p>
      </div>
    </div>

    <!-- Main Bootstrap Card -->
    <v-row>
      <v-col cols="12" md="8">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon color="primary" class="mr-2">$rocket-launch</v-icon>
            <span class="text-h6">Bootstrap Taxonomy</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-alert type="info" variant="tonal" class="mb-4">
              Bootstrap your taxonomy with a pre-built template. This will replace your existing categories.
            </v-alert>

            <v-alert v-if="detectedTemplate" type="success" variant="tonal" density="compact" class="mb-4">
              <div class="d-flex align-center">
                <v-icon size="small" class="mr-2">$check-circle</v-icon>
                <span class="text-body-2">
                  Currently using: <strong>{{ getTemplateDescription(detectedTemplate).title }}</strong>
                </span>
              </div>
            </v-alert>

            <v-select
              v-model="selectedTemplate"
              :items="templateOptions"
              label="Select Template"
              variant="outlined"
              density="comfortable"
              prepend-inner-icon="$file-document"
              :loading="loading"
              class="mb-4"
            />

            <v-card v-if="selectedTemplate" variant="outlined" class="mb-4">
              <v-card-text>
                <div class="text-subtitle-1 font-weight-medium mb-2">
                  {{ getTemplateDescription(selectedTemplate).title }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  {{ getTemplateDescription(selectedTemplate).description }}
                </div>
                <div class="text-caption text-medium-emphasis mt-2">
                  Categories: {{ getTemplateDescription(selectedTemplate).categories }}
                </div>
              </v-card-text>
            </v-card>

            <v-alert type="warning" variant="tonal" class="mb-4">
              <div class="text-subtitle-2 font-weight-medium mb-1">Warning</div>
              This will replace your existing taxonomy. All current categories will be deleted and replaced with the selected template.
            </v-alert>

            <v-btn
              color="primary"
              block
              size="large"
              prepend-icon="$rocket-launch"
              :disabled="!selectedTemplate"
              :loading="bootstrapping"
              @click="confirmBootstrap"
            >
              Bootstrap Now
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Confirmation Dialog -->
    <v-dialog
      v-model="confirmDialog.show"
      max-width="600"
      persistent
    >
      <v-card>
        <v-card-title class="d-flex align-center pa-4">
          <v-icon :color="confirmDialog.isForce ? 'warning' : 'primary'" class="mr-2">
            {{ confirmDialog.isForce ? '$alert' : '$help-circle' }}
          </v-icon>
          <span>{{ confirmDialog.title }}</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-alert
            :type="confirmDialog.isForce ? 'warning' : 'info'"
            variant="tonal"
            class="mb-4"
          >
            {{ confirmDialog.message }}
          </v-alert>
          <div v-if="confirmDialog.isForce" class="text-body-2">
            <strong>This action will:</strong>
            <ul class="mt-2">
              <li>Permanently delete all existing taxonomy categories</li>
              <li>Replace them with the selected template</li>
              <li>Cannot be undone</li>
            </ul>
          </div>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn
            variant="text"
            @click="cancelBootstrap"
          >
            Cancel
          </v-btn>
          <v-btn
            :color="confirmDialog.isForce ? 'warning' : 'primary'"
            variant="elevated"
            :loading="bootstrapping"
            @click="executeBootstrap"
          >
            {{ confirmDialog.isForce ? 'Replace All Categories' : 'Bootstrap Now' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Success Snackbar -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="bottom right"
    >
      {{ snackbar.message }}
      <template #actions>
        <v-btn
          variant="text"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

// Tenant store
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Reactive state
const bootstrapping = ref(false)
const selectedTemplate = ref(null)
const loading = ref(false)
const detectedTemplate = ref(null)

const templateOptions = [
  { title: 'Software Engineering', value: 'software' },
  { title: 'Legal & Compliance', value: 'legal' },
  { title: 'Medical & Healthcare', value: 'medical' },
  { title: 'Marketing & Content', value: 'marketing' },
  { title: 'Empty Template', value: 'empty' }
]

const confirmDialog = ref({
  show: false,
  title: '',
  message: '',
  isForce: false,
  templateKey: null
})

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// Methods
const getTemplateDescription = (templateKey) => {
  const descriptions = {
    software: {
      title: 'Software Engineering',
      description: 'Includes categories like Architecture, Backend, Frontend, DevOps, Security, Testing, etc.',
      categories: '12 categories'
    },
    legal: {
      title: 'Legal & Compliance',
      description: 'Includes categories like Contracts, Compliance, Regulations, Litigation, Intellectual Property, etc.',
      categories: '10 categories'
    },
    medical: {
      title: 'Medical & Healthcare',
      description: 'Includes categories like Clinical, Research, Diagnostics, Treatment, Patient Care, etc.',
      categories: '11 categories'
    },
    marketing: {
      title: 'Marketing & Content',
      description: 'Includes categories like Content Strategy, SEO, Social Media, Analytics, Campaigns, etc.',
      categories: '9 categories'
    },
    empty: {
      title: 'Empty Template',
      description: 'Start fresh with no predefined categories. Build your taxonomy from scratch.',
      categories: '0 categories'
    }
  }
  return descriptions[templateKey] || { title: 'Unknown', description: '', categories: '0' }
}

const confirmBootstrap = () => {
  if (!selectedTemplate.value) return

  const templateDesc = getTemplateDescription(selectedTemplate.value)

  // Show initial confirmation dialog
  confirmDialog.value = {
    show: true,
    title: 'Bootstrap Taxonomy',
    message: `Bootstrap taxonomy with "${templateDesc.title}"? This will replace your existing categories.`,
    isForce: false,
    templateKey: selectedTemplate.value
  }
}

const executeBootstrap = async () => {
  const templateKey = confirmDialog.value.templateKey
  const isForce = confirmDialog.value.isForce

  if (!templateKey) return

  const templateDesc = getTemplateDescription(templateKey)
  bootstrapping.value = true

  try {
    await adminAPI.bootstrapTaxonomy(templateKey, isForce)

    // Success
    confirmDialog.value.show = false
    showSnackbar(
      `Taxonomy ${isForce ? 'replaced' : 'bootstrapped'} with "${templateDesc.title}" successfully`,
      'success'
    )

    // Update detected template
    detectedTemplate.value = templateKey
    selectedTemplate.value = null

  } catch (err) {
    const errorDetail = err.response?.data?.detail || ''

    // Check if error is about existing entries
    if (errorDetail.includes('already has') && errorDetail.includes('taxonomy entries')) {
      // Expected conflict - show force confirmation dialog (don't log as error)
      confirmDialog.value = {
        show: true,
        title: 'Replace Existing Taxonomy?',
        message: errorDetail,
        isForce: true,
        templateKey: templateKey
      }
    } else {
      // Unexpected error - log and show error message
      console.error('❌ Bootstrap error:', err)
      confirmDialog.value.show = false
      showSnackbar(errorDetail || 'Failed to bootstrap taxonomy', 'error')
    }
  } finally {
    if (!confirmDialog.value.show) {
      bootstrapping.value = false
    }
  }
}

const cancelBootstrap = () => {
  confirmDialog.value.show = false
  bootstrapping.value = false
}

const showSnackbar = (message, color = 'success') => {
  snackbar.value = {
    show: true,
    message,
    color
  }
}

// Load detected template on mount
const loadDetectedTemplate = async () => {
  loading.value = true
  // Clear previous state
  selectedTemplate.value = null
  detectedTemplate.value = null

  try {
    const response = await adminAPI.detectBootstrapTemplate()
    console.log('🔍 [BootstrapTaxonomyView] Detected template response:', response)

    if (response.template && response.confidence > 0.5) {
      // Auto-select the detected template
      selectedTemplate.value = response.template
      detectedTemplate.value = response.template
      console.log(`✅ Detected bootstrap template: ${response.template} (${(response.confidence * 100).toFixed(0)}% confidence)`)
    } else {
      console.log('ℹ️ No template detected or low confidence:', response)
    }
  } catch (err) {
    console.error('❌ Failed to detect bootstrap template:', err)
    // Don't show error to user - this is a nice-to-have feature
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  console.log('✅ [BootstrapTaxonomyView] Component mounted, currentTenant:', currentTenant.value)
  loadDetectedTemplate()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [BootstrapTaxonomyView] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [BootstrapTaxonomyView] Tenant slug changed, refreshing bootstrap data')
    loadDetectedTemplate()
  }
})
</script>

<style scoped>
.v-card-title {
  font-weight: 600;
}

.font-weight-medium {
  font-weight: 500;
}
</style>
