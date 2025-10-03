<template>
  <div class="content-view">
    <!-- Analytics Cards -->
    <div class="mb-6">
      <v-row>
        <v-col
          cols="12"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Total Gaps
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
                {{ stats.total || 0 }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Unresolved
                </div>
                <v-avatar
                  size="40"
                  color="rgba(239, 68, 68, 0.1)"
                  variant="flat"
                >
                  <v-icon
                    color="error"
                    size="20"
                  >
                    $close
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ stats.unresolved || 0 }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Resolved
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
                    $check-circle
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ stats.resolved || 0 }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col
          cols="12"
          md="3"
        >
          <v-card class="metric-style-card">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div class="text-subtitle-1 font-weight-medium text-medium-emphasis">
                  Avg Score
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
                    $chart
                  </v-icon>
                </v-avatar>
              </div>
              <div class="metric-value text-h4 font-weight-bold text-high-emphasis">
                {{ stats.avgScore || '0.00' }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Content Gaps Table -->
    <ContentGapsTable @stats-updated="updateStats" />

    <!-- Help Section -->
    <v-card class="mt-6">
      <v-card-text>
        <div class="d-flex align-start gap-3">
          <v-icon color="info">
            $info
          </v-icon>
          <div>
            <h3 class="text-body-1 font-weight-bold mb-2">
              About Content Gaps
            </h3>
            <p class="text-body-2 mb-2">
              Content gaps are automatically detected when queries have low similarity scores (&lt; 0.7) 
              or result in errors. These indicate areas where your knowledge base might need improvement.
            </p>
            <ul class="text-body-2">
              <li><strong>Pattern:</strong> Normalized query pattern to group similar issues</li>
              <li><strong>Count:</strong> Number of times this pattern has occurred</li>
              <li><strong>Avg Score:</strong> Average similarity score for queries matching this pattern</li>
              <li><strong>Sample Query:</strong> Example of an actual query that triggered this gap</li>
            </ul>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ContentGapsTable from '@/components/ContentGapsTable.vue'

// Reactive state
const stats = ref({
  total: 0,
  unresolved: 0,
  resolved: 0,
  avgScore: '0.00'
})

// Methods
const updateStats = (newStats) => {
  stats.value = newStats
}
</script>

<style scoped>
.content-view {
  max-width: 1400px;
  margin: 0 auto;
}

.metric-style-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-style-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(var(--v-shadow-key-umbra-opacity), 0.08);
}

.metric-value {
  line-height: 1.2;
  letter-spacing: -0.02em;
}
</style>