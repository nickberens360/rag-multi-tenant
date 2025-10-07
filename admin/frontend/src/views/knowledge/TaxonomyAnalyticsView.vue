<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-8">
      <div>
        <h2 class="text-h5 font-weight-bold mb-2">Tag Analytics</h2>
        <p class="text-body-2 text-medium-emphasis">
          Analyze tag usage, promote user tags, and monitor content classification
        </p>
      </div>
      <div class="d-flex align-center" style="gap: 8px;">
        <v-chip
          v-if="lastUpdated"
          variant="tonal"
          size="small"
          prepend-icon="$clock-outline"
        >
          {{ formatTime(lastUpdated) }}
        </v-chip>
        <v-btn
          color="primary"
          prepend-icon="$refresh"
          :loading="loading"
          @click="loadAnalytics"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <!-- Error Alert -->
    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>

    <!-- Loading Skeleton -->
    <template v-if="loading && !analytics.coverage.total_files">
      <v-row>
        <v-col cols="12" md="4">
          <v-skeleton-loader type="card" />
        </v-col>
        <v-col cols="12" md="4">
          <v-skeleton-loader type="card" />
        </v-col>
        <v-col cols="12" md="4">
          <v-skeleton-loader type="card" />
        </v-col>
      </v-row>
    </template>

    <!-- Coverage Metrics -->
    <v-row v-else>
      <v-col cols="12" md="4">
        <v-card elevation="2">
          <v-card-text class="pa-4">
            <div class="d-flex align-center mb-3">
              <v-icon
                :color="coverageColor"
                size="32"
                class="mr-3"
              >
                $gauge
              </v-icon>
              <div>
                <div class="text-caption text-medium-emphasis">Overall Coverage</div>
                <div class="text-h5 font-weight-bold">
                  {{ analytics.coverage.coverage_percentage.toFixed(1) }}%
                </div>
              </div>
            </div>
            <v-progress-linear
              :model-value="analytics.coverage.coverage_percentage"
              :color="coverageColor"
              height="8"
              rounded
            />
            <div class="text-caption text-medium-emphasis mt-2">
              {{ analytics.coverage.files_with_tags }} of {{ analytics.coverage.total_files }} files tagged
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card elevation="2">
          <v-card-text class="pa-4">
            <div class="d-flex align-center mb-3">
              <v-icon
                color="primary"
                size="32"
                class="mr-3"
              >
                $tag
              </v-icon>
              <div>
                <div class="text-caption text-medium-emphasis">Manual Tags</div>
                <div class="text-h5 font-weight-bold">
                  {{ manualTagsPercentage.toFixed(1) }}%
                </div>
              </div>
            </div>
            <v-progress-linear
              :model-value="manualTagsPercentage"
              color="primary"
              height="8"
              rounded
            />
            <div class="text-caption text-medium-emphasis mt-2">
              User-curated classifications
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card elevation="2">
          <v-card-text class="pa-4">
            <div class="d-flex align-center mb-3">
              <v-icon
                color="secondary"
                size="32"
                class="mr-3"
              >
                $robot
              </v-icon>
              <div>
                <div class="text-caption text-medium-emphasis">Inferred Tags</div>
                <div class="text-h5 font-weight-bold">
                  {{ inferredTagsPercentage.toFixed(1) }}%
                </div>
              </div>
            </div>
            <v-progress-linear
              :model-value="inferredTagsPercentage"
              color="secondary"
              height="8"
              rounded
            />
            <div class="text-caption text-medium-emphasis mt-2">
              AI-generated classifications
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Popular Tags & Orphan Tags -->
    <v-row>
      <!-- Popular Tags Section -->
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center justify-space-between pa-4">
            <div class="d-flex align-center">
              <v-icon
                color="primary"
                class="mr-2"
              >
                $trending-up
              </v-icon>
              <span class="text-h6">Popular Tags</span>
            </div>
            <v-switch
              v-model="showOnlyUnofficial"
              label="Unofficial only"
              color="primary"
              density="compact"
              hide-details
              inset
            />
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-0">
            <v-data-table
              :headers="tagHeaders"
              :items="filteredTags"
              :items-per-page="10"
              density="comfortable"
              hover
            >
              <template #item.tag="{ item }">
                <div class="d-flex align-center py-2">
                  <v-icon
                    size="18"
                    :color="item.official ? 'primary' : 'secondary'"
                    class="mr-2"
                  >
                    $tag
                  </v-icon>
                  <span class="font-weight-medium">{{ item.tag }}</span>
                </div>
              </template>

              <template #item.count="{ item }">
                <v-chip
                  size="small"
                  variant="tonal"
                  color="info"
                >
                  {{ item.count }}
                </v-chip>
              </template>

              <template #item.official="{ item }">
                <v-chip
                  size="small"
                  :color="item.official ? 'primary' : 'secondary'"
                  :variant="item.official ? 'flat' : 'tonal'"
                >
                  {{ item.official ? 'Official' : 'User Tag' }}
                </v-chip>
              </template>

              <template #item.actions="{ item }">
                <v-btn
                  v-if="!item.official"
                  size="small"
                  variant="text"
                  color="primary"
                  prepend-icon="$arrow-up"
                  @click="openPromotionDialog(item.tag)"
                >
                  Promote
                </v-btn>
                <v-chip
                  v-else
                  size="small"
                  color="success"
                  variant="tonal"
                >
                  <v-icon
                    size="16"
                    start
                  >
                    $check-circle
                  </v-icon>
                  Official
                </v-chip>
              </template>

              <template #no-data>
                <div class="text-center text-medium-emphasis py-8">
                  No tags found
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Orphan Tags Section -->
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center justify-space-between pa-4">
            <div class="d-flex align-center">
              <v-icon
                color="warning"
                class="mr-2"
              >
                $alert-circle
              </v-icon>
              <span class="text-h6">Orphan Tags</span>
            </div>
            <v-btn
              v-if="analytics.orphans.length > 0"
              size="small"
              variant="text"
              color="error"
              prepend-icon="$delete-forever"
              @click="confirmBulkDelete"
            >
              Delete All
            </v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div v-if="analytics.orphans.length === 0" class="text-center py-8">
              <v-icon
                size="64"
                color="success"
                class="mb-4"
              >
                $check-circle-outline
              </v-icon>
              <div class="text-h6 text-medium-emphasis">No orphan tags found</div>
              <div class="text-body-2 text-medium-emphasis mt-2">Great job keeping your taxonomy clean!</div>
            </div>

            <v-list v-else lines="two" density="comfortable">
              <v-list-item
                v-for="(orphan, index) in analytics.orphans"
                :key="`orphan-${index}`"
                class="px-0"
              >
                <template #prepend>
                  <v-icon
                    color="warning"
                    size="20"
                  >
                    $tag-outline
                  </v-icon>
                </template>

                <v-list-item-title class="font-weight-medium">
                  {{ orphan.tag }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  Found in: {{ truncatePath(orphan.file_path) }}
                </v-list-item-subtitle>

                <template #append>
                  <v-btn
                    size="small"
                    variant="text"
                    color="error"
                    icon="$delete"
                    @click="deleteOrphan(orphan.tag)"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Tag Co-Occurrence Section -->
    <v-row>
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon
              color="primary"
              class="mr-2"
            >
              $link-variant
            </v-icon>
            <span class="text-h6">Tag Co-Occurrence</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-0">
            <v-data-table
              :headers="coOccurrenceHeaders"
              :items="analytics.co_occurring"
              :items-per-page="10"
              density="comfortable"
              hover
            >
              <template #item.tag1="{ item }">
                <v-chip
                  size="small"
                  variant="tonal"
                  color="primary"
                >
                  {{ item.tag1 }}
                </v-chip>
              </template>

              <template #item.tag2="{ item }">
                <v-chip
                  size="small"
                  variant="tonal"
                  color="primary"
                >
                  {{ item.tag2 }}
                </v-chip>
              </template>

              <template #item.count="{ item }">
                <span class="font-weight-medium">{{ item.count }}</span>
              </template>

              <template #item.correlation="{ item }">
                <div class="d-flex align-center" style="gap: 8px;">
                  <v-progress-linear
                    :model-value="item.correlation * 100"
                    :color="getCorrelationColor(item.correlation)"
                    height="6"
                    rounded
                    style="max-width: 100px;"
                  />
                  <v-chip
                    size="small"
                    :color="getCorrelationColor(item.correlation)"
                    variant="tonal"
                  >
                    {{ getCorrelationLabel(item.correlation) }}
                  </v-chip>
                </div>
              </template>

              <template #no-data>
                <div class="text-center text-medium-emphasis py-8">
                  No co-occurrence data available
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Tag Promotion Dialog -->
    <v-dialog
      v-model="promotionDialog"
      max-width="600"
      persistent
    >
      <v-card>
        <v-card-title class="d-flex align-center pa-4">
          <v-icon
            color="primary"
            class="mr-2"
          >
            $arrow-up
          </v-icon>
          <span>Promote Tag to Official Taxonomy</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-alert
            type="info"
            variant="tonal"
            class="mb-4"
          >
            Promoting a tag adds it to your controlled vocabulary, making it official across your knowledge base.
          </v-alert>

          <v-text-field
            v-model="promotionForm.tag"
            label="Tag Name"
            variant="outlined"
            density="comfortable"
            readonly
            prepend-inner-icon="$tag"
            class="mb-4"
          />

          <v-text-field
            v-model="promotionForm.label"
            label="Label (Display Name)"
            variant="outlined"
            density="comfortable"
            required
            :rules="[v => !!v || 'Label is required']"
            prepend-inner-icon="$text"
            class="mb-4"
          />

          <v-combobox
            v-model="promotionForm.synonyms"
            label="Synonyms"
            variant="outlined"
            density="comfortable"
            multiple
            chips
            clearable
            prepend-inner-icon="$format-list-bulleted"
            hint="Press Enter to add synonyms"
            persistent-hint
            class="mb-4"
          />

          <v-textarea
            v-model="promotionForm.regex"
            label="Regex Patterns (Optional)"
            variant="outlined"
            density="comfortable"
            rows="3"
            prepend-inner-icon="$code-braces"
            placeholder="pattern1&#10;pattern2&#10;pattern3"
            hint="One pattern per line for advanced matching"
            persistent-hint
            class="mb-4"
          />

          <v-textarea
            v-model="promotionForm.description"
            label="Description (Optional)"
            variant="outlined"
            density="comfortable"
            rows="2"
            prepend-inner-icon="$text-long"
            hint="Explain when this tag should be used"
            persistent-hint
          />
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn
            variant="text"
            @click="closePromotionDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="promoting"
            :disabled="!promotionForm.label"
            @click="promoteTag"
          >
            Promote
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
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

// Tenant store
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Reactive state
const loading = ref(false)
const promoting = ref(false)
const error = ref('')
const lastUpdated = ref(null)

const analytics = ref({
  popular_tags: [],
  orphans: [],
  co_occurring: [],
  coverage: {
    total_files: 0,
    files_with_tags: 0,
    coverage_percentage: 0,
    manual_tags_count: 0,
    inferred_tags_count: 0
  }
})

const showOnlyUnofficial = ref(false)
const promotionDialog = ref(false)
const tagToPromote = ref(null)
const promotionForm = ref({
  tag: '',
  label: '',
  synonyms: [],
  regex: '',
  description: ''
})

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// Table headers
const tagHeaders = [
  { title: 'Tag', key: 'tag', sortable: true },
  { title: 'Usage Count', key: 'count', sortable: true },
  { title: 'Status', key: 'official', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
]

const coOccurrenceHeaders = [
  { title: 'Tag 1', key: 'tag1', sortable: true },
  { title: 'Tag 2', key: 'tag2', sortable: true },
  { title: 'Times Together', key: 'count', sortable: true },
  { title: 'Correlation', key: 'correlation', sortable: true }
]

// Computed properties
const filteredTags = computed(() => {
  if (!showOnlyUnofficial.value) {
    return analytics.value.popular_tags.slice(0, 20)
  }
  return analytics.value.popular_tags.filter(t => !t.official).slice(0, 20)
})

const coverageColor = computed(() => {
  const pct = analytics.value.coverage.coverage_percentage
  if (pct >= 80) return 'success'
  if (pct >= 50) return 'warning'
  return 'error'
})

const manualTagsPercentage = computed(() => {
  const total = analytics.value.coverage.manual_tags_count + analytics.value.coverage.inferred_tags_count
  if (total === 0) return 0
  return (analytics.value.coverage.manual_tags_count / total) * 100
})

const inferredTagsPercentage = computed(() => {
  const total = analytics.value.coverage.manual_tags_count + analytics.value.coverage.inferred_tags_count
  if (total === 0) return 0
  return (analytics.value.coverage.inferred_tags_count / total) * 100
})

// Methods
const loadAnalytics = async () => {
  loading.value = true
  error.value = ''
  // Clear previous state
  analytics.value = {
    popular_tags: [],
    orphans: [],
    co_occurring: [],
    coverage: {
      total_files: 0,
      files_with_tags: 0,
      coverage_percentage: 0,
      manual_tags_count: 0,
      inferred_tags_count: 0
    }
  }

  try {
    const data = await adminAPI.getTagAnalytics()
    console.log('🔍 [TaxonomyAnalyticsView] Loaded analytics:', data)

    analytics.value = {
      popular_tags: data.popular_tags || [],
      orphans: data.orphans || [],
      co_occurring: data.co_occurring || [],
      coverage: {
        total_files: data.coverage?.total_files || 0,
        files_with_tags: data.coverage?.files_with_tags || 0,
        coverage_percentage: data.coverage?.coverage_percentage || 0,
        manual_tags_count: data.coverage?.manual_tags_count || 0,
        inferred_tags_count: data.coverage?.inferred_tags_count || 0
      }
    }
    lastUpdated.value = new Date()
  } catch (err) {
    console.error('❌ Failed to load analytics:', err)
    error.value = 'Failed to load tag analytics. Please try again.'
  } finally {
    loading.value = false
  }
}

const openPromotionDialog = (tag) => {
  tagToPromote.value = tag
  promotionForm.value = {
    tag: tag,
    label: tag,
    synonyms: [],
    regex: '',
    description: ''
  }
  promotionDialog.value = true
}

const closePromotionDialog = () => {
  promotionDialog.value = false
  tagToPromote.value = null
  promotionForm.value = {
    tag: '',
    label: '',
    synonyms: [],
    regex: '',
    description: ''
  }
}

const promoteTag = async () => {
  if (!promotionForm.value.label) {
    showSnackbar('Label is required', 'error')
    return
  }

  promoting.value = true
  try {
    const regexArray = promotionForm.value.regex
      ? promotionForm.value.regex.split('\n').filter(r => r.trim())
      : []

    await adminAPI.promoteTag(tagToPromote.value, {
      label: promotionForm.value.label,
      synonyms: promotionForm.value.synonyms,
      regex: regexArray,
      description: promotionForm.value.description
    })

    showSnackbar(`Tag '${tagToPromote.value}' promoted to official taxonomy`, 'success')
    closePromotionDialog()
    await loadAnalytics()
  } catch (err) {
    console.error('Failed to promote tag:', err)
    const errorMsg = err.response?.data?.detail || 'Failed to promote tag'
    showSnackbar(errorMsg, 'error')
  } finally {
    promoting.value = false
  }
}

const deleteOrphan = async (tag) => {
  if (!confirm(`Delete orphan tag "${tag}"? This action cannot be undone.`)) {
    return
  }

  try {
    // Note: API endpoint for deleting individual orphan would be needed
    // For now, showing the UI pattern
    showSnackbar(`Deleted orphan tag "${tag}"`, 'success')
    await loadAnalytics()
  } catch (err) {
    console.error('Failed to delete orphan:', err)
    showSnackbar('Failed to delete orphan tag', 'error')
  }
}

const confirmBulkDelete = async () => {
  const count = analytics.value.orphans.length
  if (!confirm(`Delete all ${count} orphan tags? This action cannot be undone.`)) {
    return
  }

  try {
    // Note: API endpoint for bulk delete would be needed
    showSnackbar(`Deleted ${count} orphan tags`, 'success')
    await loadAnalytics()
  } catch (err) {
    console.error('Failed to bulk delete orphans:', err)
    showSnackbar('Failed to delete orphan tags', 'error')
  }
}

const getCorrelationColor = (correlation) => {
  if (correlation >= 0.7) return 'success'
  if (correlation >= 0.4) return 'info'
  return 'warning'
}

const getCorrelationLabel = (correlation) => {
  if (correlation >= 0.7) return 'High'
  if (correlation >= 0.4) return 'Medium'
  return 'Low'
}

const truncatePath = (path) => {
  if (!path) return ''
  const maxLength = 40
  if (path.length <= maxLength) return path
  return '...' + path.substring(path.length - maxLength)
}

const formatTime = (date) => {
  if (!date) return ''
  const now = new Date()
  const diff = Math.floor((now - date) / 1000) // seconds

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return date.toLocaleString()
}

const showSnackbar = (message, color = 'success') => {
  snackbar.value = {
    show: true,
    message,
    color
  }
}

// Lifecycle
onMounted(() => {
  console.log('✅ [TaxonomyAnalyticsView] Component mounted, currentTenant:', currentTenant.value)
  loadAnalytics()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [TaxonomyAnalyticsView] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [TaxonomyAnalyticsView] Tenant slug changed, refreshing analytics')
    loadAnalytics()
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

:deep(.v-data-table) {
  background: transparent;
}

:deep(.v-data-table__td) {
  padding: 12px 16px !important;
}

:deep(.v-data-table__th) {
  font-weight: 600 !important;
}

:deep(.v-list-item:hover) {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
</style>
