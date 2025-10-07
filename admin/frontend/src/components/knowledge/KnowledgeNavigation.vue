<template>
  <nav class="knowledge-nav">
    <v-list
      class="knowledge-nav-list"
      nav
      density="comfortable"
      lines="two"
      rounded="lg"
    >
      <v-list-item
        v-for="tab in navigationTabs"
        :key="tab.value"
        :value="tab.value"
        :active="currentTab === tab.value"
        class="knowledge-nav-item"
        :class="{ 'knowledge-nav-item--active': currentTab === tab.value }"
        rounded="lg"
        @click="navigateToTab(tab.value)"
      >
        <template #prepend>
          <v-icon
            :icon="tab.icon"
            size="20"
          />
        </template>
        <v-list-item-title class="knowledge-nav-title">
          {{ tab.title }}
        </v-list-item-title>
        <v-list-item-subtitle class="knowledge-nav-description">
          {{ tab.description }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const navigationTabs = [
  { value: 'sources', title: 'Sources', icon: '$folder', description: 'Source files and usage' },
  { value: 'documents', title: 'Documents', icon: '$description', description: 'Indexed chunks' },
  { value: 'analytics', title: 'Analytics', icon: '$chart-bar', description: 'Tag usage and analytics' },
  { value: 'manage-taxonomy', title: 'Manage Taxonomy', icon: '$tag', description: 'Categories and vocabulary' },
  { value: 'bootstrap', title: 'Bootstrap', icon: '$rocket-launch', description: 'Template-based setup' }
  // { value: 'consistency', title: 'Consistency', icon: '$shield-check', description: 'Validate & reconcile' },
  // { value: 'gaps', title: 'Content Gaps', icon: '$warning', description: 'Missing topics and patterns' },
  // { value: 'stats', title: 'Statistics', icon: '$chart', description: 'Knowledge analytics' }
]

const currentTab = computed(() => {
  const name = route.name
  if (name === 'knowledge-sources') return 'sources'
  if (name === 'knowledge-documents') return 'documents'
  if (name === 'knowledge-analytics') return 'analytics'
  if (name === 'knowledge-manage-taxonomy') return 'manage-taxonomy'
  if (name === 'knowledge-bootstrap') return 'bootstrap'
  if (name === 'knowledge-consistency') return 'consistency'
  if (name === 'knowledge-gaps') return 'gaps'
  if (name === 'knowledge-stats') return 'stats'
  return 'sources'
})

const navigateToTab = (tabValue) => {
  const map = {
    sources: 'knowledge-sources',
    documents: 'knowledge-documents',
    analytics: 'knowledge-analytics',
    'manage-taxonomy': 'knowledge-manage-taxonomy',
    bootstrap: 'knowledge-bootstrap',
    consistency: 'knowledge-consistency',
    gaps: 'knowledge-gaps',
    stats: 'knowledge-stats'
  }
  const target = map[tabValue]
  if (target && route.name !== target) {
    const slug = route.params?.tenant
    if (slug) {
      router.push({ name: target, params: { tenant: slug } })
    } else {
      router.push({ name: target })
    }
  }
}
</script>

<style scoped>
.knowledge-nav {
  flex-shrink: 0;
  width: 280px;
  position: sticky;
  top: 115px;
}

.knowledge-nav-list {
  background: transparent;
  padding: 0;
}

.knowledge-nav-item {
  margin: 8px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.knowledge-nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.knowledge-nav-item--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

.knowledge-nav-title {
  font-weight: 500;
  font-size: 0.95rem;
}

.knowledge-nav-description {
  font-size: 0.8rem;
  opacity: 0.7;
  margin-top: 2px;
}

@media (max-width: 1024px) {
  .knowledge-nav {
    width: 100%;
    position: relative;
    top: auto;
  }
  .knowledge-nav .v-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px;
  }
  .knowledge-nav-item { flex: 1; min-width: 140px; margin: 0; }
  .knowledge-nav-title { font-size: 0.85rem; }
  .knowledge-nav-description { display: none; }
}

@media (max-width: 768px) {
  .knowledge-nav .v-list { flex-direction: column; gap: 0; }
  .knowledge-nav-item { min-width: auto; margin: 4px 8px; }
}
</style>
