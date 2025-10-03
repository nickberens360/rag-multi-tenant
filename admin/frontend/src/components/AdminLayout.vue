<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      :permanent="!mobile"
      :temporary="mobile"
      style="position: fixed;"
      color="surface"
      width="280"
      class="sidebar-drawer"
    >
      <!-- Brand Logo Section -->
      <div class="sidebar-header ds-p-6">
        <div class="d-flex align-center">
          <div class="brand-logo">
            <v-avatar
              color="primary"
              size="40"
            >
              <v-icon
                size="24"
                color="white"
              >
                $dashboard
              </v-icon>
            </v-avatar>
          </div>
          <div class="ml-3">
            <div class="brand-title text-h6 font-weight-bold">
              RAG MNGR
            </div>
          </div>
        </div>
      </div>

      <v-divider class="ds-mb-4" />

      <!-- Main Menu Section -->
      <div class="ds-px-4">
        <div class="menu-label ds-text-xs ds-font-medium text-medium-emphasis ds-mb-3">
          MAIN MENU
        </div>
        <v-list
          nav
          density="compact"
          class="ds-py-0"
        >
          <template
            v-for="item in navigationItems"
            :key="item.name"
          >
            <!-- Main navigation item -->
            <v-list-item
              v-if="!item.children"
              :to="item.to"
              :active="$route.name === item.name"
              rounded="lg"
              class="mb-1 nav-item"
              :prepend-icon="item.icon"
              color="primary"
            >
              <v-list-item-title class="font-weight-medium">
                {{ item.title }}
              </v-list-item-title>
            </v-list-item>

            <!-- Navigation item with children -->
            <v-list-group
              v-else
              :key="item.name"
              :value="item.name"
              class="mb-1"
            >
              <template #activator="{ props }">
                <v-list-item
                  v-bind="props"
                  :prepend-icon="item.icon"
                  rounded="lg"
                  class="nav-item"
                  color="primary"
                  :active="$route.name === item.name || item.children.some(child => $route.name === child.name)"
                  @click="navigateToParent(item)"
                >
                  <v-list-item-title class="font-weight-medium">
                    {{ item.title }}
                  </v-list-item-title>
                </v-list-item>
              </template>

              <v-list-item
                v-for="child in item.children"
                :key="child.name"
                :to="child.to"
                :active="$route.name === child.name"
                rounded="lg"
                class="ms-4 nav-item"
                color="primary"
              >
                <v-list-item-title class="font-weight-medium">
                  {{ child.title }}
                </v-list-item-title>
              </v-list-item>
            </v-list-group>
          </template>
        </v-list>
      </div>


      <template #append>
        <v-divider class="mb-2" />

        <v-list density="compact">
          <div class="px-4 d-flex justify-space-between align-center mb-2">
            <v-list-item-title class="text-caption text-medium-emphasis">
              System Status
            </v-list-item-title>
            <v-chip
              :color="getStatusColor(systemHealth.status)"
              size="x-small"
              variant="flat"
            >
              {{ systemHealth.status }}
            </v-chip>
          </div>

          <div
            class="px-4 d-flex justify-space-between align-center mb-2"
            @click="refreshData"
          >
            <v-list-item-title class="text-caption text-medium-emphasis">
              Last Updated
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ formatLastUpdate }}
            </v-list-item-subtitle>
          </div>
        </v-list>
      </template>
    </v-navigation-drawer>

    <v-app-bar
      style="position: fixed;"
      color="background"
      elevation="0"
      height="80"
      class="modern-header px-8"
    >
      <v-app-bar-nav-icon
        v-if="mobile"
        @click="drawer = !drawer"
      />

      <v-toolbar-title class="text-h5 font-weight-bold">
        {{ currentPageTitle }}
      </v-toolbar-title>

      <v-spacer />

      <!-- Time Range Selector -->
      <TimeRangeSelector
        v-if="showTimeRangeSelector"
        :model-value="timeRange"
        class="mr-4"
        @update:model-value="setTimeRange"
      />

      <!-- Organization Switcher + Active Tenant ID -->
      <div class="d-flex align-center mr-4">
        <OrgSwitcher class="mr-2" />
        <v-chip
          v-if="currentTenant?.id"
          size="small"
          variant="tonal"
          color="primary"
          class="text-no-wrap"
          title="Active Tenant ID"
        >
          {{ currentTenant.id }}
        </v-chip>
      </div>

      <!-- Notifications (hidden until notification system is implemented) -->
      <v-btn
        v-if="false"
        icon
        variant="text"
        size="large"
        class="mr-2"
      >
        <v-badge
          color="error"
          :content="notificationCount"
          :value="notificationCount > 0"
          dot
        >
          <v-icon>$bell</v-icon>
        </v-badge>
        <v-tooltip
          activator="parent"
          location="bottom"
        >
          Notifications
        </v-tooltip>
      </v-btn>

      <!-- User Profile -->
      <v-menu>
        <template #activator="{ props }">
          <div
            v-bind="props"
            class="user-profile-section d-flex align-center pa-2 rounded-lg cursor-pointer"
          >
            <v-avatar
              size="40"
              class="mr-3"
              color="primary"
            >
              <v-icon color="white">
                $account
              </v-icon>
            </v-avatar>
            <div class="user-info d-none d-sm-block">
              <div class="user-name text-subtitle-1 font-weight-medium">
                {{ userDisplayName }}
              </div>
              <div class="user-role text-caption text-medium-emphasis">
                {{ userRole }}
              </div>
            </div>
            <v-icon class="ml-2 d-none d-sm-block">
              $chevron-down
            </v-icon>
          </div>
        </template>

        <v-list width="200">
          <v-list-item @click="refreshData">
            <v-list-item-title>
              <v-icon start>
                $refresh
              </v-icon>
              Refresh Data
            </v-list-item-title>
          </v-list-item>

          <v-list-item @click="exportData">
            <v-list-item-title>
              <v-icon start>
                $export
              </v-icon>
              Export Data
            </v-list-item-title>
          </v-list-item>

          <v-divider />

          <v-list-item @click="toggleTheme">
            <v-list-item-title>
              <v-icon start>
                {{ isDark ? '$light-mode' : '$weather-night' }}
              </v-icon>
              {{ isDark ? 'Light' : 'Dark' }} Mode
            </v-list-item-title>
          </v-list-item>

          <v-divider />

          <v-list-item :to="currentTenant?.slug ? `/${currentTenant.slug}/user-settings` : '/user-settings'">
            <v-list-item-title>
              <v-icon start>
                $account
              </v-icon>
              User Settings
            </v-list-item-title>
          </v-list-item>

          <v-divider />

          <v-list-item @click="handleLogout">
            <v-list-item-title>
              <v-icon start>
                $logout
              </v-icon>
              Logout
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container
        fluid
        class="ds-p-8"
        style="background-color: rgb(var(--v-theme-background));"
      >
        <!-- Maintenance Mode Banner -->
        <v-alert
          v-if="featureStore && featureStore.featureFlags && featureStore.featureFlags.enable_maintenance_mode"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          <v-icon start>
            $construction
          </v-icon>
          Maintenance mode is enabled. Public endpoints are unavailable. Admins can still access settings here.
        </v-alert>
        <router-view v-slot="{ Component }">
          <Transition
            name="fade"
            mode="out-in"
          >
            <component :is="Component" />
          </Transition>
        </router-view>
      </v-container>
    </v-main>

    <!-- Toasts are handled globally via NotificationMessage -->
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay, useTheme } from 'vuetify'
import { storeToRefs } from 'pinia'
import { useAdminStore } from '@/stores/admin'
import { useFeatureSettingsStore } from '@/stores/featureSettings'
import { useNotificationsStore } from '@/stores/notifications'
import { useUsersStore } from '@/stores/users'
import { useTenantStore } from '@/stores/tenant'
import { formatDate } from '@/types/admin'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'
import OrgSwitcher from '@/components/OrgSwitcher.vue'

const router = useRouter()
const route = useRoute()
const { mobile } = useDisplay()
const theme = useTheme()

const adminStore = useAdminStore()
const featureStore = useFeatureSettingsStore()
const notifications = useNotificationsStore()
const usersStore = useUsersStore()
const tenantStore = useTenantStore()

// Reactive refs from tenant store
const { currentTenant } = storeToRefs(tenantStore)

// Local state
const drawer = ref(true)

// Computed properties
const {
  stats,
  systemHealth,
  timeRange,
  isLoading,
  error,
  isConnected,
  isHealthy
} = storeToRefs(adminStore);

const isDark = computed(() => theme.global.current.value.dark)

const userDisplayName = computed(() => {
  // Get real user data from the admin store
  return adminStore.user?.username || 'Admin User'
})

const userRole = computed(() => {
  // Get real user role from the admin store
  const role = adminStore.user?.role || 'viewer'
  // Format role for display
  return role.charAt(0).toUpperCase() + role.slice(1)
})

const notificationCount = computed(() => {
  // Placeholder for future notification system
  // TODO: Implement real notification counting from backend
  return 0
})

const navigationItems = computed(() => {
  const slug = currentTenant.value?.slug
  const p = (path) => (slug ? `/${slug}${path}` : path)
  return [
    { name: 'dashboard', title: 'Dashboard', to: p('/'), icon: '$dashboard' },
    { name: 'queries', title: 'Queries', to: p('/queries'), icon: '$search' },
    { name: 'performance', title: 'Performance', to: p('/performance'), icon: '$chart' },
    { name: 'sessions', title: 'Sessions', to: p('/sessions'), icon: '$users' },
    { name: 'knowledge', title: 'Knowledge Base', to: p('/knowledge/sources'), icon: '$knowledge' },
    { name: 'users', title: 'User Management', to: p('/users'), icon: '$account-group' },
    { name: 'settings', title: 'Settings', to: p('/settings/core'), icon: '$settings' }
  ]
})

const currentPageTitle = computed(() => {
  // First try to get title from route meta
  if (route.meta?.title) {
    return route.meta.title;
  }

  // Fallback: Check main navigation items
  const item = navigationItems.value.find(item => item.name === route.name);
  if (item) return item.title;

  return 'Admin Dashboard';
});

const showTimeRangeSelector = computed(() => {
  return ['dashboard', 'performance'].includes(route.name);
});

const connectionToastId = ref(null)

// Toast on error changes
watch(error, (newError) => {
  if (newError) {
    const msg = typeof newError === 'string' ? newError : (newError?.message || 'An error occurred')
    notifications.error(msg)
  }
})

// Connection status toast (persistent)
watch([isConnected, isLoading], ([connected, loading]) => {
  if (!connected && !loading) {
    if (!connectionToastId.value) {
      connectionToastId.value = notifications.warning('Connection to admin API lost. Retrying...', {
        persistent: true,
        actionLabel: 'Retry',
        onAction: () => testConnection()
      })
    }
  } else if (connected && connectionToastId.value) {
    notifications.dismiss(connectionToastId.value)
    connectionToastId.value = null
    notifications.success('Reconnected to admin API', { timeout: 3000 })
  }
})

const formatLastUpdate = computed(() => {
  if (!adminStore.lastUpdate) return 'Never'
  return formatDate(adminStore.lastUpdate)
})

// Methods
const getStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case 'healthy':
    case 'ok':
    case 'running':
      return 'success'
    case 'error':
    case 'failed':
    case 'down':
      return 'error'
    case 'warning':
    case 'degraded':
      return 'warning'
    case 'unknown':
    case 'loading':
      return 'info'
    default:
      return 'grey'
  }
}

const refreshData = async () => {
  await adminStore.refreshData()
}

const setTimeRange = async (newTimeRange) => {
  await adminStore.setTimeRange(newTimeRange)
}

// Error reset handled via store events; no local snackbar state

const testConnection = async () => {
  await adminStore.testConnection()
  if (isConnected.value) {
    await refreshData()
  }
}

const toggleTheme = () => {
  try {
    const newTheme = isDark.value ? 'light' : 'dark'
    theme.change(newTheme)
  } catch (error) {
    console.error('Error toggling theme:', error)
  }
}

const exportData = () => {
  // TODO: Implement export functionality
  // Export data functionality to be implemented
}

const navigateToParent = (item) => {
  // Navigate to the parent route which will redirect to the default child
  if (item.to) {
    router.push(item.to)
  }
}

const handleLogout = async () => {
  try {
    await adminStore.logout()
    router.push({ name: 'login' })
  } catch (error) {
    console.error('Logout failed:', error)
  }
}

// Watch for tenant changes and refresh main dashboard data
watch(
  () => currentTenant.value?.id,
  async (newTenantId, oldTenantId) => {
    // Only refresh if tenant actually changed (not initial load)
    if (oldTenantId && newTenantId && oldTenantId !== newTenantId) {
      const newTenant = currentTenant.value
      console.log(`Tenant switched to ${newTenant?.name}, refreshing dashboard data...`)

      // Clear users store data (since it uses options API)
      usersStore.clearTenantData()

      // Refresh the main admin store data
      // Other composition API stores will automatically clear their data via reactive watchers
      try {
        await Promise.all([
          adminStore.refreshData(),
          featureStore.loadData().catch(() => {})
        ])
        notifications.success(`Switched to ${newTenant?.name}`, { timeout: 3000 })
      } catch (error) {
        console.error('Failed to refresh data after tenant switch:', error)
        notifications.error('Failed to load data for the selected organization')
      }
    }
  }
)

// Lifecycle
onMounted(async () => {
  // Close drawer on mobile by default
  if (mobile.value) {
    drawer.value = false
  }

  // Initialize tenant store
  await tenantStore.initialize()

  // Load feature flags for maintenance banner
  featureStore.loadData().catch(error => console.error('Failed to load feature flags:', error))
})

onUnmounted(() => {
  adminStore.cleanup()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.sidebar-drawer {
  /* Clean drawer without border */
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.modern-header {
  /* Clean header without border */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(10px);
}

.sidebar-header {
  background: rgba(var(--v-theme-primary), 0.03);
}

.brand-title {
  color: rgb(var(--v-theme-primary));
}

.menu-label {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nav-item {
  margin-bottom: 4px;
}

.nav-item.v-list-item--active {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.nav-item.v-list-item--active .v-icon {
  color: rgb(var(--v-theme-primary));
}

.user-profile-section:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.cursor-pointer {
  cursor: pointer;
}
</style>
