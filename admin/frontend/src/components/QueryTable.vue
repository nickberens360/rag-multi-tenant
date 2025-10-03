<template>
  <v-card class="query-table-card pt-4">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>{{ title }}</span>
      <v-spacer />
      <v-row
        justify="end"
        class="align-center"
      >
        <v-spacer />
        <v-col>
          <v-text-field
            v-model="searchQuery"
            placeholder="Search queries..."
            variant="outlined"
            density="compact"
            hide-details
            prepend-inner-icon="$search"
            clearable
            style="max-width: 300px;"
            @update:model-value="searchQuery = $event"
          />
        </v-col>
        <v-col cols="auto">
          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon="$filter"
                size="small"
                variant="outlined"
                v-bind="props"
              >
                <v-icon>$filter</v-icon>
                <v-badge
                  v-if="activeFiltersCount > 0"
                  :content="activeFiltersCount"
                  color="primary"
                  offset-x="2"
                  offset-y="2"
                />
              </v-btn>
            </template>

            <v-card min-width="320">
              <v-card-title>Filters</v-card-title>

              <v-card-text>
                <div class="mb-4">
                  <v-label class="mb-2">
                    Date Range
                  </v-label>
                  <div class="d-flex gap-2">
                    <v-text-field
                      v-model="filters.startDate"
                      type="date"
                      variant="outlined"
                      density="compact"
                      hide-details
                      label="Start Date"
                    />
                    <v-text-field
                      v-model="filters.endDate"
                      type="date"
                      variant="outlined"
                      density="compact"
                      hide-details
                      label="End Date"
                    />
                  </div>
                </div>

                <v-switch
                  v-model="filters.errorOnly"
                  label="Show errors only"
                  color="primary"
                  hide-details
                  class="mb-4"
                />

                <div class="mb-4">
                  <v-label class="mb-2">
                    Min Relevance Score
                  </v-label>
                  <v-slider
                    v-model="filters.minRelevance"
                    :min="0"
                    :max="100"
                    :step="5"
                    show-ticks
                    thumb-label
                    color="primary"
                  />
                </div>
              </v-card-text>

              <v-card-actions>
                <v-btn
                  text="Reset"
                  variant="text"
                  @click="resetFilters"
                />
                <v-spacer />
                <v-btn
                  text="Apply"
                  color="primary"
                  @click="applyFilters"
                />
              </v-card-actions>
            </v-card>
          </v-menu>
        </v-col>
        <v-col cols="auto">
          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon="$export"
                size="small"
                variant="outlined"
                v-bind="props"
              />
            </template>

            <v-list>
              <v-list-item @click="exportData('csv')">
                <v-list-item-title>Export as CSV</v-list-item-title>
              </v-list-item>
              <v-list-item @click="exportData('json')">
                <v-list-item-title>Export as JSON</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
      </v-row>
    </v-card-title>

    <v-data-table
      v-model="selectedQueries"
      :headers="headers"
      :items="queries"
      :loading="loading"
      :items-per-page="itemsPerPage"
      :items-per-page-options="itemsPerPageOptions"
      show-select
      :search="searchQuery"
      item-value="id"
      fixed-header
      @click:row="handleRowClick"
    >
      <template #[`item.user_query`]="{ item }">
        <div class="query-text">
          {{ truncateText(item.user_query, 60) }}
        </div>
      </template>

      <template #[`item.response`]="{ item }">
        <div class="response-preview">
          {{ truncateText(item.response, 80) }}
        </div>
      </template>

      <template #[`item.error_occurred`]="{ item }">
        <v-chip
          :color="getStatusColor(item.error_occurred ? 'error' : 'success')"
          size="small"
          variant="flat"
        >
          {{ item.error_occurred ? 'Error' : 'Success' }}
        </v-chip>
      </template>

      <template #[`item.response_time_ms`]="{ item }">
        <span :class="getResponseTimeColor(item.response_time_ms)">
          {{ formatDuration(item.response_time_ms) }}
        </span>
      </template>

      <template #[`item.vector_search_score`]="{ item }">
        <div class="d-flex align-center">
          <v-progress-linear
            :model-value="item.vector_search_score ? item.vector_search_score * 100 : 0"
            :color="getRelevanceColor(item.vector_search_score ? item.vector_search_score * 100 : 0)"
            height="6"
            class="mr-2"
            style="width: 60px;"
          />
          <span class="text-caption">{{
            item.vector_search_score ? Math.round(item.vector_search_score * 100) + '%' : 'N/A'
          }}</span>
        </div>
      </template>

      <template #[`item.llm_model`]="{ item }">
        <v-chip
          :color="getModelColor(item.llm_model)"
          size="small"
          variant="outlined"
        >
          {{ getModelDisplayName(item.llm_model) }}
        </v-chip>
      </template>

      <template #[`item.location`]="{ item }">
        <div class="text-no-wrap">
          <div class="text-caption">
            {{ item.location_city || 'N/A' }}
          </div>
          <div class="text-caption text-medium-emphasis">
            {{ item.location_country || 'N/A' }}
          </div>
        </div>
      </template>

      <template #[`item.timestamp`]="{ item }">
        <span class="text-no-wrap">
          {{ formatDate(item.timestamp) }}
        </span>
      </template>

      <template #[`item.actions`]="{ item }">
        <div class="d-flex gap-1">
          <v-btn
            icon="$view"
            size="small"
            variant="text"
            @click.stop="viewDetails(item)"
          >
            <v-icon>$view</v-icon>
            <v-tooltip
              activator="parent"
              location="top"
            >
              View Details
            </v-tooltip>
          </v-btn>

          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon
                size="small"
                variant="text"
                v-bind="props"
                @click.stop
              >
                <v-icon>$thumb-up-outline</v-icon>
              </v-btn>
            </template>

            <v-list>
              <v-list-item @click="updateFeedback(item.id, 'helpful')">
                <v-list-item-title>
                  <v-icon
                    start
                    color="success"
                  >
                    $thumb-up
                  </v-icon>
                  Helpful
                </v-list-item-title>
              </v-list-item>
              <v-list-item @click="updateFeedback(item.id, 'not_helpful')">
                <v-list-item-title>
                  <v-icon
                    start
                    color="error"
                  >
                    $thumb-down
                  </v-icon>
                  Not Helpful
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </template>

      <template #expanded-row="{ item }">
        <v-card
          flat
          class="ma-2"
        >
          <v-card-text>
            <div class="mb-4">
              <v-label class="mb-2 font-weight-bold">
                Query:
              </v-label>
              <div class="text-body-2">
                {{ item.user_query }}
              </div>
            </div>

            <div class="mb-4">
              <v-label class="mb-2 font-weight-bold">
                Response:
              </v-label>
              <div class="text-body-2">
                {{ item.response }}
              </div>
            </div>

            <div
              v-if="item.sources_used && item.sources_used.length"
              class="mb-4"
            >
              <v-label class="mb-2 font-weight-bold">
                Sources:
              </v-label>
              <div class="d-flex flex-wrap gap-2">
                <v-chip
                  v-for="source in item.sources_used"
                  :key="source"
                  size="small"
                  variant="outlined"
                >
                  {{ source }}
                </v-chip>
              </div>
            </div>

            <div class="d-flex gap-4 text-caption text-medium-emphasis">
              <span>ID: {{ item.id }}</span>
              <span>Session: {{ item.session_id }}</span>
              <span v-if="item.user_agent">{{ item.user_agent }}</span>
            </div>
          </v-card-text>
        </v-card>
      </template>
    </v-data-table>

    <!-- Query Details Dialog -->
    <v-dialog
      v-model="showDetailsDialog"
      max-width="900px"
      scrollable
    >
      <v-card
        v-if="selectedQuery"
        class="dialog-card"
        elevation="8"
      >
        <v-card-title class="dialog-header pa-6 d-flex align-center">
          <div class="d-flex align-center">
            <v-icon
              class="me-3"
              color="primary"
            >
              $search
            </v-icon>
            <div>
              <h2 class="text-h6 font-weight-bold">
                Query Details
              </h2>
              <p class="text-body-2 text-medium-emphasis ma-0">
                View comprehensive query information
              </p>
            </div>
          </div>
          <v-spacer />
          <v-btn
            icon="$close"
            variant="text"
            size="small"
            @click="showDetailsDialog = false"
          />
        </v-card-title>

        <v-divider class="border-opacity-25" />

        <v-card-text class="pa-6">
          <!-- Query details content here -->
          <div class="mb-4">
            <v-label class="mb-2 font-weight-bold">
              Query:
            </v-label>
            <v-card
              variant="outlined"
              class="pa-3"
            >
              <div class="text-body-2">
                {{ selectedQuery.user_query }}
              </div>
            </v-card>
          </div>

          <div class="mb-4">
            <v-label class="mb-2 font-weight-bold">
              Response:
            </v-label>
            <v-card
              variant="outlined"
              class="pa-3"
            >
              <div class="text-body-2">
                {{ selectedQuery.response }}
              </div>
            </v-card>
          </div>

          <!-- Technical Details Grid -->
          <v-row>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Status:
                </v-label>
                <v-chip
                  :color="getStatusColor(selectedQuery.error_occurred ? 'error' : 'success')"
                  size="small"
                  variant="flat"
                  class="ml-2"
                >
                  {{ selectedQuery.error_occurred ? 'Error' : 'Success' }}
                </v-chip>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Response Time:
                </v-label>
                <span class="ml-2">{{ formatDuration(selectedQuery.response_time_ms) }}</span>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  LLM Model:
                </v-label>
                <v-chip
                  :color="getModelColor(selectedQuery.llm_model)"
                  size="small"
                  variant="outlined"
                  class="ml-2"
                >
                  {{ getModelDisplayName(selectedQuery.llm_model) }}
                </v-chip>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Cache Hit:
                </v-label>
                <v-chip
                  :color="selectedQuery.cache_hit ? 'success' : 'default'"
                  size="small"
                  variant="flat"
                  class="ml-2"
                >
                  {{ selectedQuery.cache_hit ? 'Yes' : 'No' }}
                </v-chip>
              </div>
            </v-col>
            <v-col
              v-if="selectedQuery.vector_search_score !== null"
              cols="6"
            >
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Relevance Score:
                </v-label>
                <span class="ml-2">{{ Math.round(selectedQuery.vector_search_score * 100) }}%</span>
              </div>
            </v-col>
          </v-row>

          <!-- Session & Identity -->
          <v-divider class="my-4" />
          <v-row>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Session ID:
                </v-label>
                <span class="ml-2 text-caption font-mono">{{ selectedQuery.session_id || 'N/A' }}</span>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Query ID:
                </v-label>
                <span class="ml-2 text-caption font-mono">{{ selectedQuery.id }}</span>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Client IP:
                </v-label>
                <span class="ml-2 text-caption font-mono">{{ selectedQuery.client_ip || 'N/A' }}</span>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">
                  Timestamp:
                </v-label>
                <span class="ml-2 text-caption">{{ formatDate(selectedQuery.timestamp) }}</span>
              </div>
            </v-col>
          </v-row>

          <!-- Location Data -->
          <div
            v-if="selectedQuery.location_city || selectedQuery.location_country"
            class="mb-4"
          >
            <v-label class="mb-2 font-weight-bold">
              Location:
            </v-label>
            <div class="ml-2">
              <span v-if="selectedQuery.location_city">{{ selectedQuery.location_city }}</span>
              <span v-if="selectedQuery.location_city && selectedQuery.location_region">, </span>
              <span v-if="selectedQuery.location_region">{{ selectedQuery.location_region }}</span>
              <span v-if="(selectedQuery.location_city || selectedQuery.location_region) && selectedQuery.location_country">, </span>
              <span v-if="selectedQuery.location_country">{{ selectedQuery.location_country }}</span>
              <span
                v-if="selectedQuery.location_country_code"
                class="text-caption"
              > ({{ selectedQuery.location_country_code }})</span>
            </div>
          </div>

          <!-- Sources Used -->
          <div
            v-if="selectedQuery.sources_used"
            class="mb-4"
          >
            <v-label class="mb-2 font-weight-bold">
              Sources Used:
            </v-label>
            <div class="d-flex flex-wrap gap-2">
              <v-chip
                v-for="source in parseSourcesUsed(selectedQuery.sources_used)"
                :key="source"
                size="small"
                variant="outlined"
              >
                {{ source }}
              </v-chip>
            </div>
          </div>

          <!-- Follow-up Questions -->
          <div
            v-if="selectedQuery.follow_up_questions"
            class="mb-4"
          >
            <v-label class="mb-2 font-weight-bold">
              Follow-up Questions:
            </v-label>
            <v-list
              density="compact"
              class="ml-2"
            >
              <v-list-item
                v-for="(question, index) in parseFollowUpQuestions(selectedQuery.follow_up_questions)"
                :key="index"
                class="text-body-2"
              >
                <template #prepend>
                  <v-icon size="small">
                    $help
                  </v-icon>
                </template>
                {{ question }}
              </v-list-item>
            </v-list>
          </div>

          <!-- User Feedback -->
          <div
            v-if="selectedQuery.user_feedback"
            class="mb-4"
          >
            <v-label class="mb-2 font-weight-bold">
              User Feedback:
            </v-label>
            <v-chip
              :color="selectedQuery.user_feedback === 'helpful' ? 'success' : 'error'"
              size="small"
              variant="flat"
              class="ml-2"
            >
              {{ selectedQuery.user_feedback === 'helpful' ? 'Helpful' : 'Not Helpful' }}
            </v-chip>
          </div>

          <!-- Error Details -->
          <div
            v-if="selectedQuery.error_occurred && selectedQuery.error_message"
            class="mb-4"
          >
            <v-label class="mb-2 font-weight-bold">
              Error Details:
            </v-label>
            <v-card
              variant="outlined"
              color="error"
              class="pa-3"
            >
              <div class="text-body-2">
                {{ selectedQuery.error_message }}
              </div>
            </v-card>
          </div>
        </v-card-text>

        <v-divider class="border-opacity-25" />

        <v-card-actions class="pa-6">
          <v-spacer />
          <v-btn
            variant="outlined"
            prepend-icon="$close"
            class="rounded-lg"
            @click="showDetailsDialog = false"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useQueriesStore } from '@/stores/queries';
import { formatDate, formatDuration, getStatusColor } from '@/types/admin';

const props = defineProps({
  title: {
    type: String,
    default: 'Query Explorer'
  }
});

const emit = defineEmits(['querySelected']);

const queriesStore = useQueriesStore();

// Local state
const searchQuery = ref('');
const selectedQueries = ref([]);
const selectedQuery = ref(null);
const showDetailsDialog = ref(false);
const itemsPerPage = ref(25);
const itemsPerPageOptions = ref([
  { value: 10, title: '10' },
  { value: 25, title: '25' },
  { value: 50, title: '50' },
  { value: 100, title: '100' },
  { value: -1, title: 'All' }
]);

// Filters
const filters = ref({
  startDate: null,
  endDate: null,
  errorOnly: false,
  minRelevance: 0
});

// Computed properties - use storeToRefs to maintain reactivity
const {
  queries,
  totalQueries,
  isLoading: loading,
  error
} = storeToRefs(queriesStore);

// Remove totalPages - not needed for client-side table

const headers = computed(() => [
  {
    title: 'Query',
    key: 'user_query',
    sortable: true
  },
  {
    title: 'Response',
    key: 'response',
    sortable: false
  },
  {
    title: 'Status',
    key: 'error_occurred',
    sortable: true
  },
  {
    title: 'Response Time',
    key: 'response_time_ms',
    sortable: true
  },
  {
    title: 'Relevance',
    key: 'vector_search_score',
    sortable: true
  },
  {
    title: 'LLM',
    key: 'llm_model',
    sortable: true
  },
  {
    title: 'Location',
    key: 'location',
    sortable: false
  },
  {
    title: 'Timestamp',
    key: 'timestamp',
    sortable: true
  },
  {
    title: 'Actions',
    key: 'actions',
    sortable: false
  }
]);

const activeFiltersCount = computed(() => {
  let count = 0;
  if (filters.value.startDate) count++;
  if (filters.value.endDate) count++;
  if (filters.value.errorOnly) count++;
  if (filters.value.minRelevance > 0) count++;
  return count;
});

// Methods
const truncateText = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};

const getResponseTimeColor = (responseTime) => {
  if (responseTime < 1000) return 'text-success';
  if (responseTime < 3000) return 'text-warning';
  return 'text-error';
};

const getRelevanceColor = (score) => {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'error';
};

const getModelColor = (model) => {
  if (!model) return 'grey';
  const lowerModel = model.toLowerCase();
  if (lowerModel.includes('haiku') || lowerModel.includes('claude_haiku')) return 'info';
  if (lowerModel.includes('claude')) return 'primary';
  if (lowerModel.includes('gemini')) return 'purple';
  if (lowerModel.includes('cached')) return 'success';
  if (lowerModel.includes('image')) return 'orange';
  return 'grey';
};

const getModelDisplayName = (model) => {
  if (!model) return 'Unknown';
  const lowerModel = model.toLowerCase();
  if (lowerModel.includes('haiku') || lowerModel.includes('claude_haiku')) return 'Claude Haiku';
  if (lowerModel.includes('claude-3-5-sonnet')) return 'Claude Sonnet 3.5';
  if (lowerModel.includes('claude-3-sonnet')) return 'Claude Sonnet 3';
  if (lowerModel.includes('claude')) return 'Claude';
  if (lowerModel.includes('gemini')) return 'Gemini';
  if (lowerModel === 'cached') return 'Cached';
  if (lowerModel.includes('image')) return 'Image Search';

  // Fallback to prettified version of the raw model name
  return model.replace(/-/g, ' ').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Remove updateOptions and updatePage - not needed for client-side table

const handleRowClick = (event, { item }) => {
  viewDetails(item);
};

const viewDetails = (query) => {
  selectedQuery.value = query;
  showDetailsDialog.value = true;
  emit('querySelected', query);
};

const updateFeedback = async (queryId, feedback) => {
  try {
    await queriesStore.updateQueryFeedback(queryId, feedback);
  } catch (error) {
    console.error('Failed to update feedback:', error);
  }
};

const applyFilters = async () => {
  await queriesStore.setFilters({
    ...filters.value
  });
};

const resetFilters = async () => {
  filters.value = {
    startDate: null,
    endDate: null,
    errorOnly: false,
    minRelevance: 0
  };
  await queriesStore.resetFilters();
};

const exportData = async (format) => {
  try {
    await queriesStore.exportQueries(format, true);
  } catch (error) {
    console.error('Export failed:', error);
  }
};

// Helper functions for parsing JSON fields
const parseSourcesUsed = (sources) => {
  if (!sources) return [];
  if (typeof sources === 'string') {
    try {
      return JSON.parse(sources);
    } catch {
      return sources.split(',').map(s => s.trim());
    }
  }
  return Array.isArray(sources) ? sources : [];
};

const parseFollowUpQuestions = (questions) => {
  if (!questions) return [];
  if (typeof questions === 'string') {
    try {
      return JSON.parse(questions);
    } catch {
      return [questions];
    }
  }
  return Array.isArray(questions) ? questions : [];
};

// For client-side table, no need for debounced search - just update the reactive searchQuery

// Watch for changes
watch(selectedQueries, (newSelection) => {
  // Handle bulk actions if needed
});

// Lifecycle - ensure data is loaded on component mount
onMounted(async () => {
  // Only fetch if we don't have any queries loaded
  if (!queries.value || queries.value.length === 0) {
    await queriesStore.fetchQueries();
  }
});
</script>

<style scoped>
.query-table-card {
  overflow: hidden;
}

.query-text,
.response-preview {
  font-family: 'JetBrains Mono', 'SF Mono', Monaco, Inconsolata, 'Source Code Pro', Consolas, 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.4;
}

.query-text {
  color: rgb(var(--v-theme-primary));
}

.response-preview {
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.87;
}

:deep(.v-data-table__wrapper) {
  overflow-x: auto;
}

/* Allow table to auto-size columns */
:deep(.v-data-table__wrapper table) {
  width: 100% !important;
  table-layout: fixed;
}

:deep(.v-data-table-row--clickable:hover) {
  background-color: rgba(var(--v-theme-primary), 0.04);
  cursor: pointer;
}

/* Force column widths */
:deep(.v-data-table th:nth-child(2)),
:deep(.v-data-table td:nth-child(2)) {
  width: 30% !important;
  min-width: 250px;
}

:deep(.v-data-table th:nth-child(3)),
:deep(.v-data-table td:nth-child(3)) {
  width: 30% !important;
  min-width: 250px;
}

/* Dialog Styles */
.dialog-card {
  border-radius: 16px !important;
  overflow: hidden;
}

.dialog-header {
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.04), rgba(var(--v-theme-primary), 0.02));
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}
</style>