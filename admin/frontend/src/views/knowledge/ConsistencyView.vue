<template>
  <div class="consistency-view">
    <div class="mb-4">
      <v-row>
        <v-col
          cols="12"
          sm="6"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Filesystem Files
                </div>
                <v-avatar
                  size="40"
                  color="rgba(59, 130, 246, 0.1)"
                  variant="flat"
                >
                  <v-icon
                    color="info"
                    size="20"
                  >
                    $folder
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ summary.filesystem_files }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col
          cols="12"
          sm="6"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Vector Docs (chunks)
                </div>
                <v-avatar
                  size="40"
                  color="rgba(16, 185, 129, 0.1)"
                  variant="flat"
                >
                  <v-icon
                    color="success"
                    size="20"
                  >
                    $database
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ summary.vector_docs }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col
          cols="12"
          sm="6"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Tracked Files
                </div>
                <v-avatar
                  size="40"
                  color="rgba(139, 92, 246, 0.1)"
                  variant="flat"
                >
                  <v-icon
                    color="primary"
                    size="20"
                  >
                    $file
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ summary.tracked_files }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col
          cols="12"
          sm="6"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Mismatches
                </div>
                <v-avatar
                  size="40"
                  color="rgba(245, 158, 11, 0.1)"
                  variant="flat"
                >
                  <v-icon
                    color="warning"
                    size="20"
                  >
                    $alert
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ mismatchTotal }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Knowledge Health & Settings Snapshot -->
    <v-card class="mb-4 settings-card">
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon
          class="me-2"
          :color="healthOk ? 'success' : 'warning'"
        >
          $shield-check
        </v-icon>
        Knowledge Health
        <v-chip
          size="x-small"
          class="ms-2"
          :color="healthOk ? 'success' : 'warning'"
        >
          {{ healthOk ? 'OK' : 'Degraded' }}
        </v-chip>
        <v-spacer />
        <v-btn
          size="small"
          variant="text"
          :loading="loadingHealth"
          @click="loadHealth"
        >
          Refresh
        </v-btn>
        <v-btn
          size="small"
          variant="text"
          prepend-icon="$tune"
          @click="$router.push({ name: 'settings-knowledge' })"
        >
          Settings
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col
            cols="12"
            md="6"
          >
            <div class="text-subtitle-2 text-medium-emphasis mb-2">
              Settings
            </div>
            <v-list density="compact">
              <v-list-item
                title="Index on Startup"
                :subtitle="settings.index_on_startup ? 'Enabled' : 'Disabled'"
              />
              <v-list-item
                title="Background Sync Interval (s)"
                :subtitle="String(settings.background_sync_interval_seconds || 0)"
              />
              <v-list-item
                title="Auto-Reindex Deltas"
                :subtitle="settings.auto_reindex_deltas ? 'Enabled' : 'Disabled'"
              />
              <v-list-item
                title="Heterogeneity Fallback"
                :subtitle="settings.enable_heterogeneity_fallback ? 'Enabled' : 'Disabled'"
              />
              <v-list-item
                title="Index Directories"
                :subtitle="(settings.index_directories || []).join(', ')"
              />
            </v-list>
          </v-col>
          <v-col
            cols="12"
            md="6"
          >
            <div class="text-subtitle-2 text-medium-emphasis mb-2">
              Summary
            </div>
            <v-list density="compact">
              <v-list-item
                title="Filesystem Files"
                :subtitle="String(summary.filesystem_files || 0)"
              />
              <v-list-item
                title="Vector Docs (chunks)"
                :subtitle="String(summary.vector_docs || 0)"
              />
              <v-list-item
                title="Tracked Files"
                :subtitle="String(summary.tracked_files || 0)"
              />
              <v-list-item
                title="Mismatches"
                :subtitle="String(mismatchTotal)"
              />
              <v-list-item
                title="Last Reconcile"
                :subtitle="formatLastReconcile(lastReconcileAt)"
              />
            </v-list>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card class="mb-4 settings-card">
      <v-card-title class="text-h6">
        Reconcile
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col
            cols="12"
            sm="6"
            md="3"
          >
            <v-switch
              v-model="dryRun"
              label="Dry Run"
              color="primary"
              hide-details
            />
          </v-col>
          <v-col
            cols="12"
            sm="6"
            md="3"
          >
            <v-switch
              v-model="allowDeletes"
              label="Allow Deletes"
              color="warning"
              hide-details
            />
          </v-col>
          <v-col
            cols="12"
            sm="6"
            md="3"
          >
            <v-text-field
              v-model.number="limit"
              type="number"
              min="1"
              label="Limit"
              hide-details
            />
          </v-col>
          <v-col
            cols="12"
            md="6"
          >
            <v-text-field
              v-model="pathsText"
              label="Paths (comma-separated)"
              hide-details
            />
          </v-col>
          <v-col
            cols="12"
            md="6"
            class="d-flex align-end"
          >
            <v-btn
              color="primary"
              :loading="running"
              @click="runReconcile"
            >
              {{ dryRun ? 'Plan' : 'Run' }} Reconcile
            </v-btn>
          </v-col>
        </v-row>

        <div
          v-if="planned || executed"
          class="mt-4"
        >
          <v-alert
            v-if="planned"
            type="info"
          >
            Planned reindex: {{ planned.reindex.length }}, delete orphans: {{ planned.delete_orphans.length }}
          </v-alert>
          <v-alert
            v-if="executed"
            type="success"
          >
            Reindexed: {{ executed.reindexed.length }}, Deleted: {{ executed.deleted_orphans.length }}, Errors: {{ executed.errors.length }}
          </v-alert>
        </div>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title class="text-h6">
            Discovered but not indexed
          </v-card-title>
          <v-card-text>
            <v-data-table
              v-model:page="dni.page"
              :items="dni.items"
              :headers="pathActionHeaders"
              :items-per-page="dni.perPage"
              :items-length="dni.total"
              :loading="dni.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div
                  class="text-truncate"
                  style="max-width: 520px"
                  :title="item.path"
                >
                  {{ item.path }}
                </div>
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  size="x-small"
                  variant="text"
                  color="primary"
                  @click="reindexOne(item)"
                >
                  Reindex
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title class="text-h6">
            Changed files
          </v-card-title>
          <v-card-text>
            <v-data-table
              v-model:page="chg.page"
              :items="chg.items"
              :headers="pathActionHeaders"
              :items-per-page="chg.perPage"
              :items-length="chg.total"
              :loading="chg.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div
                  class="text-truncate"
                  style="max-width: 520px"
                  :title="item.path"
                >
                  {{ item.path }}
                </div>
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  size="x-small"
                  variant="text"
                  color="primary"
                  @click="reindexOne(item)"
                >
                  Reindex
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title class="text-h6">
            Vector orphans
          </v-card-title>
          <v-card-text>
            <v-data-table
              v-model:page="orph.page"
              :items="orph.items"
              :headers="pathDeleteHeaders"
              :items-per-page="orph.perPage"
              :items-length="orph.total"
              :loading="orph.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div
                  class="text-truncate"
                  style="max-width: 520px"
                  :title="item.path"
                >
                  {{ item.path }}
                </div>
              </template>
              <template #item.actions="{ item }">
                <v-tooltip text="Delete from index">
                  <template #activator="{ props }">
                    <span v-bind="props">
                      <v-btn
                        size="x-small"
                        variant="text"
                        color="error"
                        @click="deleteFromIndex(item)"
                      >
                        Delete
                      </v-btn>
                    </span>
                  </template>
                </v-tooltip>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title class="text-h6">
            Tracked but missing
          </v-card-title>
          <v-card-text>
            <v-data-table
              v-model:page="tbm.page"
              :items="tbm.items"
              :headers="pathOnlyHeaders"
              :items-per-page="tbm.perPage"
              :items-length="tbm.total"
              :loading="tbm.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div
                  class="text-truncate"
                  style="max-width: 520px"
                  :title="item.path"
                >
                  {{ item.path }}
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { adminAPI } from '@/services/api'
import { useTenantStore } from '@/stores/tenant'
import { useNotifications } from '@/composables/useNotifications'

const loading = ref(false)
const running = ref(false)
const summary = ref({ filesystem_files: 0, vector_docs: 0, tracked_files: 0, discovered_not_indexed: 0, changed_files: 0, vector_orphans: 0, tracked_but_missing: 0 })
const diff = ref({})

const dryRun = ref(true)
const allowDeletes = ref(false)
const limit = ref()
const pathsText = ref('')

const planned = ref(null)
const executed = ref(null)

const { showError, showSuccess } = useNotifications()

const mismatchTotal = computed(() => (summary.value.discovered_not_indexed || 0) + (summary.value.changed_files || 0) + (summary.value.vector_orphans || 0))

// Health/settings state
const loadingHealth = ref(false)
const healthOk = ref(false)
const lastReconcileAt = ref(null)
const settings = ref({
  index_on_startup: true,
  background_sync_interval_seconds: 0,
  auto_reindex_deltas: false,
  enable_heterogeneity_fallback: false,
  index_directories: ['backend/knowledge', 'public']
})

// Paginated lists state
const makeListState = () => ({ items: [], total: 0, page: 1, perPage: 10, loading: false })
const dni = ref(makeListState())
const chg = ref(makeListState())
const orph = ref(makeListState())
const tbm = ref(makeListState())

const pathActionHeaders = [
  { title: 'Path', key: 'path' },
  { title: 'Actions', key: 'actions', width: '120px' }
]
const pathDeleteHeaders = [
  { title: 'Path', key: 'path' },
  { title: 'Actions', key: 'actions', width: '120px' }
]
const pathOnlyHeaders = [
  { title: 'Path', key: 'path' }
]

const tenantStore = useTenantStore()

const load = async () => {
  loading.value = true
  planned.value = null
  executed.value = null
  try {
    const res = await adminAPI.getKnowledgeConsistency(100)
    summary.value = res.summary || summary.value
    diff.value = res.diff || {}
    // Keep shared stats fresh so other knowledge tabs reflect latest
    tenantStore.loadKnowledgeStats().catch(() => {})
  } catch (e) {
    showError('Failed to load consistency')
  } finally {
    loading.value = false
  }
}

const loadHealth = async () => {
  loadingHealth.value = true
  try {
    const [health, kset] = await Promise.all([
      adminAPI.getKnowledgeHealth(),
      adminAPI.getKnowledgeSettings()
    ])
    healthOk.value = Boolean(health && health.ok)
    lastReconcileAt.value = health?.last_reconcile_at || null
    if (kset?.settings) settings.value = { ...settings.value, ...kset.settings }
  } catch (e) {
    // Non-fatal
  } finally {
    loadingHealth.value = false
  }
}

const runReconcile = async () => {
  running.value = true
  planned.value = null
  executed.value = null
  try {
    const paths = (pathsText.value || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
    const res = await adminAPI.reconcileKnowledge({ dryRun: dryRun.value, allowDeletes: allowDeletes.value, limit: limit.value, paths })
    if (dryRun.value) {
      planned.value = res.planned || { reindex: [], delete_orphans: [] }
      showSuccess('Reconcile plan generated')
    } else {
      executed.value = res.actions || { reindexed: [], deleted_orphans: [], errors: [] }
      showSuccess('Reconcile completed')
      // Reload summary after execute
      await load()
    }
  } catch (e) {
    showError('Reconcile failed')
  } finally {
    running.value = false
  }
}

const formatLastReconcile = (timestamp) => {
  if (!timestamp) return 'Never'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString()
  } catch {
    return 'Invalid date'
  }
}

onMounted(async () => {
  // Ensure tenant context is ready before hitting tenant-scoped endpoints
  if (!tenantStore.initialized) {
    await tenantStore.initialize()
  }
  await Promise.all([load(), loadHealth()])
})

// Helpers: fetch paginated lists
const fetchList = async (stateRef, kind) => {
  stateRef.value.loading = true
  try {
    const offset = (stateRef.value.page - 1) * stateRef.value.perPage
    const res = await adminAPI.getKnowledgeConsistencyList(kind, { offset, limit: stateRef.value.perPage })
    stateRef.value.items = (res.items || []).map(p => ({ path: p }))
    stateRef.value.total = res.total || 0
  } catch (e) {
    // ignore per-section errors, keep prior
  } finally {
    stateRef.value.loading = false
  }
}

// Watchers for pagination
watch(() => dni.value.page, () => fetchList(dni, 'discovered_not_indexed'))
watch(() => chg.value.page, () => fetchList(chg, 'changed_files'))
watch(() => orph.value.page, () => fetchList(orph, 'vector_orphans'))
watch(() => tbm.value.page, () => fetchList(tbm, 'tracked_but_missing'))

// Initial load of lists
onMounted(async () => {
  await Promise.all([
    fetchList(dni, 'discovered_not_indexed'),
    fetchList(chg, 'changed_files'),
    fetchList(orph, 'vector_orphans'),
    fetchList(tbm, 'tracked_but_missing'),
  ])
})

// React to tenant switches: clear and reload all sections
const resetListState = (stateRef) => {
  stateRef.value = { items: [], total: 0, page: 1, perPage: stateRef.value.perPage || 10, loading: false }
}

watch(
  () => tenantStore.currentTenant?.id,
  async (newId, oldId) => {
    if (!oldId || !newId || newId === oldId) return
    // Reset summary/diff
    summary.value = { filesystem_files: 0, vector_docs: 0, tracked_files: 0, discovered_not_indexed: 0, changed_files: 0, vector_orphans: 0, tracked_but_missing: 0 }
    diff.value = {}
    // Reset lists to first page and clear items
    resetListState(dni)
    resetListState(chg)
    resetListState(orph)
    resetListState(tbm)
    // Reload for new tenant
    await Promise.all([load(), loadHealth()])
    await Promise.all([
      fetchList(dni, 'discovered_not_indexed'),
      fetchList(chg, 'changed_files'),
      fetchList(orph, 'vector_orphans'),
      fetchList(tbm, 'tracked_but_missing'),
    ])
  }
)

// Row actions
const reindexOne = async (itemOrPath) => {
  const path = typeof itemOrPath === 'string' ? itemOrPath : (itemOrPath?.path || '')
  if (!path) return
  try {
    await adminAPI.reindexKnowledgeFile(path)
    showSuccess('Reindex started')
    // Refresh lists and summary
    await Promise.all([
      fetchList(dni, 'discovered_not_indexed'),
      fetchList(chg, 'changed_files'),
    ])
    await load()
  } catch (e) {
    showError('Failed to reindex file')
  }
}

const deleteFromIndex = async (itemOrPath) => {
  const path = typeof itemOrPath === 'string' ? itemOrPath : (itemOrPath?.path || '')
  if (!path) return
  try {
    await adminAPI.deleteKnowledgeSource(path)
    showSuccess('Deleted from index')
    await fetchList(orph, 'vector_orphans')
    await load()
  } catch (e) {
    showError('Failed to delete from index')
  }
}
</script>

<style scoped>
.consistency-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
