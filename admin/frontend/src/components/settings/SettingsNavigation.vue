<template>
  <nav class="settings-nav">
    <v-list
      class="settings-nav-list"
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
        class="settings-nav-item"
        :class="{ 'settings-nav-item--active': currentTab === tab.value }"
        rounded="lg"
        @click="navigateToTab(tab.value)"
      >
        <template #prepend>
          <v-icon
            :icon="tab.icon"
            size="20"
          />
        </template>
        <v-list-item-title class="settings-nav-title">
          {{ tab.title }}
        </v-list-item-title>
        <v-list-item-subtitle class="settings-nav-description">
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

// Phase 2: New 5-Section Organization
const navigationTabs = [
  {
    value: 'core',
    title: 'Core Settings',
    icon: '$cog-box',
    description: 'LLM models, API keys, and system mode'
  },
  {
    value: 'search-retrieval',
    title: 'Search & Retrieval',
    icon: '$magnify-scan',
    description: 'Query routing and RAG configuration'
  },
  {
    value: 'knowledge',
    title: 'Knowledge',
    icon: '$book-open',
    description: 'Indexing & synchronization settings'
  },
  {
    value: 'search-taxonomy',
    title: 'Search & Taxonomy',
    icon: '$tag',
    description: 'Categories, synonyms, and regex patterns'
  },
  {
    value: 'response',
    title: 'Response Settings',
    icon: '$message-reply',
    description: 'Response formatting and caching'
  },
  {
    value: 'security',
    title: 'Security & Monitoring',
    icon: '$shield-check',
    description: 'Security settings and analytics'
  },
  {
    value: 'features',
    title: 'Feature Flags',
    icon: '$tune',
    description: 'System and UX feature toggles'
  },
  {
    value: 'ux',
    title: 'User Experience',
    icon: '$account-heart',
    description: 'Welcome messages and user-facing features'
  }
]

const currentTab = computed(() => {
  const routeName = route.name
  if (routeName === 'settings-core') return 'core'
  if (routeName === 'settings-search-retrieval') return 'search-retrieval'
  if (routeName === 'settings-knowledge') return 'knowledge'
  if (routeName === 'settings-taxonomy') return 'search-taxonomy'
  if (routeName === 'settings-response') return 'response'
  if (routeName === 'settings-security') return 'security'
  if (routeName === 'settings-ux') return 'ux'
  return 'core' // default to core settings
})

const navigateToTab = (tabValue) => {
  const routeMap = {
    'core': 'settings-core',
    'search-retrieval': 'settings-search-retrieval',
    'knowledge': 'settings-knowledge',
    'search-taxonomy': 'settings-taxonomy',
    'response': 'settings-response',
    'security': 'settings-security',
    'features': 'settings-features',
    'ux': 'settings-ux'
  }

  const routeName = routeMap[tabValue]
  if (routeName && route.name !== routeName) {
    const slug = route.params?.tenant
    if (slug) {
      router.push({ name: routeName, params: { tenant: slug } })
    } else {
      router.push({ name: routeName })
    }
  }
}
</script>

<style scoped>
.settings-nav {
  flex-shrink: 0;
  width: 280px;
  position: sticky;
  top: 115px;
}

.settings-nav-list {
  background: transparent;
  padding: 0;
}

.settings-nav-item {
  margin: 8px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.settings-nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.settings-nav-item--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

.settings-nav-title {
  font-weight: 500;
  font-size: 0.95rem;
}

.settings-nav-description {
  font-size: 0.8rem;
  opacity: 0.7;
  margin-top: 2px;
}

/* Mobile responsiveness */
@media (max-width: 1024px) {
  .settings-nav {
    width: 100%;
    position: relative;
    top: auto;
  }

  .settings-nav .v-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px;
  }

  .settings-nav-item {
    flex: 1;
    min-width: 140px;
    margin: 0;
  }

  .settings-nav-title {
    font-size: 0.85rem;
  }

  .settings-nav-description {
    display: none; /* Hide descriptions on tablets for space */
  }
}

@media (max-width: 768px) {
  .settings-nav .v-list {
    flex-direction: column;
    gap: 0;
  }

  .settings-nav-item {
    min-width: auto;
    margin: 4px 8px;
  }
}
</style>
