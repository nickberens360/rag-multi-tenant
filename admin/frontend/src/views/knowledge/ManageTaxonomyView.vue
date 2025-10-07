<template>
  <div>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-8">
      <div>
        <h2 class="text-h5 font-weight-bold mb-2">Manage Taxonomy</h2>
        <p class="text-body-2 text-medium-emphasis">
          Create, edit, and organize your controlled vocabulary categories
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
          :loading="loadingTaxonomy"
          @click="loadTaxonomy"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <!-- Main Table Card -->
    <v-row>
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center justify-space-between pa-4">
            <div class="d-flex align-center">
              <v-icon color="primary" class="mr-2">$database</v-icon>
              <span class="text-h6">Taxonomy Categories</span>
            </div>
            <v-btn
              color="primary"
              prepend-icon="$plus"
              @click="openCategoryDialog()"
            >
              Add Category
            </v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-0">
            <v-data-table
              :headers="taxonomyHeaders"
              :items="taxonomyEntries"
              :loading="loadingTaxonomy"
              density="comfortable"
              hover
            >
              <template #item.key="{ item }">
                <span class="font-weight-medium text-primary">{{ item.key }}</span>
              </template>

              <template #item.label="{ item }">
                {{ item.label }}
              </template>

              <template #item.synonyms="{ item }">
                <div v-if="item.synonyms && item.synonyms.length > 0" class="d-flex flex-wrap" style="gap: 4px;">
                  <v-chip
                    v-for="(synonym, idx) in item.synonyms.slice(0, 3)"
                    :key="idx"
                    size="small"
                    variant="tonal"
                    color="info"
                  >
                    {{ synonym }}
                  </v-chip>
                  <v-chip
                    v-if="item.synonyms.length > 3"
                    size="small"
                    variant="text"
                  >
                    +{{ item.synonyms.length - 3 }} more
                  </v-chip>
                </div>
                <span v-else class="text-medium-emphasis">—</span>
              </template>

              <template #item.regex_patterns="{ item }">
                <div v-if="item.regex_patterns && item.regex_patterns.length > 0">
                  <v-chip size="small" variant="tonal" color="secondary">
                    {{ item.regex_patterns.length }} pattern{{ item.regex_patterns.length > 1 ? 's' : '' }}
                  </v-chip>
                </div>
                <span v-else class="text-medium-emphasis">—</span>
              </template>

              <template #item.active="{ item }">
                <v-chip
                  size="small"
                  :color="item.active ? 'success' : 'default'"
                  :variant="item.active ? 'flat' : 'tonal'"
                >
                  {{ item.active ? 'Active' : 'Inactive' }}
                </v-chip>
              </template>

              <template #item.actions="{ item }">
                <div class="d-flex" style="gap: 4px;">
                  <v-btn
                    size="small"
                    variant="text"
                    icon="$pencil"
                    color="primary"
                    @click="openCategoryDialog(item)"
                  />
                  <v-btn
                    size="small"
                    variant="text"
                    icon="$delete"
                    color="error"
                    @click="confirmDeleteCategory(item.key)"
                  />
                </div>
              </template>

              <template #no-data>
                <div class="text-center text-medium-emphasis py-8">
                  <v-icon size="64" color="grey-lighten-1" class="mb-4">$database-off</v-icon>
                  <div class="text-h6">No taxonomy categories found</div>
                  <div class="text-body-2 mt-2">Add categories to organize your content</div>
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Category Add/Edit Dialog -->
    <v-dialog
      v-model="categoryDialog"
      max-width="700"
      persistent
    >
      <v-card>
        <v-card-title class="d-flex align-center pa-4">
          <v-icon color="primary" class="mr-2">
            {{ editingCategory ? '$pencil' : '$plus' }}
          </v-icon>
          <span>{{ editingCategory ? 'Edit Category' : 'Add Category' }}</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field
            v-model="categoryForm.key"
            label="Key"
            variant="outlined"
            density="comfortable"
            required
            :disabled="!!editingCategory"
            :rules="[v => !!v || 'Key is required']"
            prepend-inner-icon="$key"
            hint="Unique identifier (lowercase, no spaces)"
            persistent-hint
            class="mb-4"
          />

          <v-text-field
            v-model="categoryForm.label"
            label="Label"
            variant="outlined"
            density="comfortable"
            required
            :rules="[v => !!v || 'Label is required']"
            prepend-inner-icon="$text"
            class="mb-4"
          />

          <v-combobox
            v-model="categoryForm.synonyms"
            label="Synonyms"
            variant="outlined"
            density="comfortable"
            multiple
            chips
            clearable
            closable-chips
            prepend-inner-icon="$format-list-bulleted"
            hint="Press Enter to add synonyms"
            persistent-hint
            class="mb-4"
          />

          <v-combobox
            v-model="categoryForm.regex_patterns"
            label="Regex Patterns"
            variant="outlined"
            density="comfortable"
            multiple
            chips
            clearable
            closable-chips
            prepend-inner-icon="$code-braces"
            hint="Press Enter to add patterns for advanced matching"
            persistent-hint
            class="mb-4"
          />

          <v-switch
            v-model="categoryForm.active"
            label="Active"
            color="primary"
            density="comfortable"
            hide-details
            inset
          />
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" @click="closeCategoryDialog">
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="savingCategory"
            :disabled="!categoryForm.key || !categoryForm.label"
            @click="saveCategory"
          >
            {{ editingCategory ? 'Update' : 'Create' }}
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
const loadingTaxonomy = ref(false)
const savingCategory = ref(false)
const taxonomyEntries = ref([])
const categoryDialog = ref(false)
const editingCategory = ref(null)
const lastUpdated = ref(null)

const categoryForm = ref({
  key: '',
  label: '',
  synonyms: [],
  regex_patterns: [],
  active: true
})

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// Table headers
const taxonomyHeaders = [
  { title: 'Key', key: 'key', sortable: true },
  { title: 'Label', key: 'label', sortable: true },
  { title: 'Synonyms', key: 'synonyms', sortable: false },
  { title: 'Regex Patterns', key: 'regex_patterns', sortable: false },
  { title: 'Status', key: 'active', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
]

// Methods
const loadTaxonomy = async () => {
  loadingTaxonomy.value = true
  // Clear previous state
  taxonomyEntries.value = []

  try {
    const data = await adminAPI.getTaxonomy()
    console.log('🔍 [ManageTaxonomyView] Loaded taxonomy:', data)

    // Backend returns { entries: [], total: N, tenant_id: "..." }
    taxonomyEntries.value = (data.entries || []).map(entry => ({
      key: entry.key,
      label: entry.label || entry.key,
      synonyms: entry.synonyms || [],
      regex_patterns: entry.regex_patterns || [],
      active: entry.active !== false
    }))
    lastUpdated.value = new Date()
  } catch (err) {
    console.error('Failed to load taxonomy:', err)
    showSnackbar('Failed to load taxonomy entries', 'error')
  } finally {
    loadingTaxonomy.value = false
  }
}

const openCategoryDialog = (category = null) => {
  if (category) {
    editingCategory.value = category.key
    categoryForm.value = {
      key: category.key,
      label: category.label,
      synonyms: [...(category.synonyms || [])],
      regex_patterns: [...(category.regex_patterns || [])],
      active: category.active !== false
    }
  } else {
    editingCategory.value = null
    categoryForm.value = {
      key: '',
      label: '',
      synonyms: [],
      regex_patterns: [],
      active: true
    }
  }
  categoryDialog.value = true
}

const closeCategoryDialog = () => {
  categoryDialog.value = false
  editingCategory.value = null
  categoryForm.value = {
    key: '',
    label: '',
    synonyms: [],
    regex_patterns: [],
    active: true
  }
}

const saveCategory = async () => {
  if (!categoryForm.value.key || !categoryForm.value.label) {
    showSnackbar('Key and label are required', 'error')
    return
  }

  savingCategory.value = true
  try {
    const payload = {
      label: categoryForm.value.label,
      synonyms: categoryForm.value.synonyms || [],
      regex_patterns: categoryForm.value.regex_patterns || [],
      active: categoryForm.value.active
    }

    if (editingCategory.value) {
      await adminAPI.updateTaxonomyEntry(categoryForm.value.key, payload)
      showSnackbar(`Category '${categoryForm.value.key}' updated successfully`, 'success')
    } else {
      await adminAPI.createTaxonomyEntry({ key: categoryForm.value.key, ...payload })
      showSnackbar(`Category '${categoryForm.value.key}' created successfully`, 'success')
    }

    closeCategoryDialog()
    await loadTaxonomy()
  } catch (err) {
    console.error('Failed to save category:', err)
    const errorMsg = err.response?.data?.detail || 'Failed to save category'
    showSnackbar(errorMsg, 'error')
  } finally {
    savingCategory.value = false
  }
}

const confirmDeleteCategory = async (key) => {
  if (!confirm(`Delete category "${key}"? This action cannot be undone.`)) {
    return
  }

  try {
    await adminAPI.deleteTaxonomyEntry(key)
    showSnackbar(`Category '${key}' deleted successfully`, 'success')
    await loadTaxonomy()
  } catch (err) {
    console.error('Failed to delete category:', err)
    const errorMsg = err.response?.data?.detail || 'Failed to delete category'
    showSnackbar(errorMsg, 'error')
  }
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
  console.log('✅ [ManageTaxonomyView] Component mounted, currentTenant:', currentTenant.value)
  loadTaxonomy()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [ManageTaxonomyView] Tenant slug watcher fired:', {
    oldSlug,
    newSlug,
    currentTenant: currentTenant.value
  })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [ManageTaxonomyView] Tenant slug changed, refreshing taxonomy')
    loadTaxonomy()
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
</style>
