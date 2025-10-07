import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '@/components/AdminLayout.vue'
import { useAdminStore } from '@/stores/admin'
import { useTenantStore } from '@/stores/tenant'

// Define admin children once so we can mount under both '/' and '/:tenant'
const adminChildren = [
  {
    path: '',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Dashboard', icon: 'dashboard' }
  },
  {
    path: 'queries',
    name: 'queries',
    component: () => import('@/views/QueriesView.vue'),
    meta: { title: 'Queries', icon: 'search' }
  },
  {
    path: 'performance',
    name: 'performance',
    component: () => import('@/views/PerformanceView.vue'),
    meta: { title: 'Performance', icon: 'chart' }
  },
  {
    path: 'sessions',
    name: 'sessions',
    component: () => import('@/views/SessionsView.vue'),
    meta: { title: 'Sessions', icon: 'users' }
  },
  {
    path: 'knowledge',
    name: 'knowledge',
    component: () => import('@/views/KnowledgeView.vue'),
    meta: { title: 'Knowledge Base', icon: '$knowledge' },
    children: [
      { path: '', name: 'knowledge-overview', redirect: 'sources' },
      {
        path: 'documents',
        name: 'knowledge-documents',
        component: () => import('@/views/knowledge/DocumentsView.vue'),
        meta: { title: 'Indexed Documents' }
      },
      {
        path: 'sources',
        name: 'knowledge-sources',
        component: () => import('@/views/knowledge/SourcesView.vue'),
        meta: { title: 'Knowledge Sources' }
      },
      {
        path: 'consistency',
        name: 'knowledge-consistency',
        component: () => import('@/views/knowledge/ConsistencyView.vue'),
        meta: { title: 'Consistency & Reconciliation' }
      },
      {
        path: 'gaps',
        name: 'knowledge-gaps',
        component: () => import('@/views/knowledge/GapsView.vue'),
        meta: { title: 'Content Gaps' }
      },
      {
        path: 'stats',
        name: 'knowledge-stats',
        component: () => import('@/views/knowledge/StatsView.vue'),
        meta: { title: 'Knowledge Statistics' }
      },
      {
        path: 'analytics',
        name: 'knowledge-analytics',
        component: () => import('@/views/knowledge/TaxonomyAnalyticsView.vue'),
        meta: { title: 'Tag Analytics' }
      },
      {
        path: 'manage-taxonomy',
        name: 'knowledge-manage-taxonomy',
        component: () => import('@/views/knowledge/ManageTaxonomyView.vue'),
        meta: { title: 'Manage Taxonomy' }
      },
      {
        path: 'bootstrap',
        name: 'knowledge-bootstrap',
        component: () => import('@/views/knowledge/BootstrapTaxonomyView.vue'),
        meta: { title: 'Bootstrap Taxonomy' }
      }
    ]
  },
  {
    path: 'users',
    name: 'users',
    component: () => import('@/views/UsersView.vue'),
    meta: { title: 'User Management', icon: '$users' }
  },
  {
    path: 'user-settings',
    name: 'user-settings',
    component: () => import('@/views/UserSettingsView.vue'),
    meta: { title: 'User Settings', icon: '$account' }
  },
  {
    path: 'change-password',
    name: 'change-password',
    component: () => import('@/views/ChangePassword.vue'),
    meta: { title: 'Change Password', icon: '$lock' }
  },
  {
    path: 'settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: 'Settings', icon: '$settings' },
    children: [
      { path: '', name: 'settings-overview', redirect: 'core' },
      {
        path: 'core',
        name: 'settings-core',
        component: () => import('@/views/settings/CoreSettings.vue'),
        meta: { title: 'Core Settings', description: 'General system configuration' }
      },
      {
        path: 'search-retrieval',
        name: 'settings-search-retrieval',
        component: () => import('@/views/settings/SearchRetrievalSettings.vue'),
        meta: { title: 'Search & Retrieval', description: 'Retrieval and scoring settings' }
      },
      {
        path: 'knowledge',
        name: 'settings-knowledge',
        component: () => import('@/views/settings/KnowledgeSettings.vue'),
        meta: { title: 'Knowledge', description: 'Indexing & synchronization settings' }
      },
      {
        path: 'taxonomy',
        name: 'settings-taxonomy',
        component: () => import('@/views/settings/TaxonomySettings.vue'),
        meta: { title: 'Search & Taxonomy', description: 'Manage categories, synonyms, and regex patterns' }
      },
      {
        path: 'response',
        name: 'settings-response',
        component: () => import('@/views/settings/ResponseSettings.vue'),
        meta: { title: 'Response Settings', description: 'Response formatting and caching' }
      },
      {
        path: 'security',
        name: 'settings-security',
        component: () => import('@/views/settings/SecuritySettings.vue'),
        meta: { title: 'Security & Monitoring', description: 'Security settings and analytics' }
      },
      {
        path: 'features',
        name: 'settings-features',
        component: () => import('@/views/settings/FeatureSettings.vue'),
        meta: { title: 'Feature Flags', description: 'System and UX feature toggles' }
      },
      {
        path: 'ux',
        name: 'settings-ux',
        component: () => import('@/views/settings/UXSettings.vue'),
        meta: { title: 'User Experience', description: 'Welcome messages and user-facing features' }
      }
    ]
  },
  // Development-only routes
  ...(import.meta.env.DEV
    ? [
        {
          path: 'typography-demo',
          name: 'typography-demo',
          component: () => import('@/components/TypographyDemo.vue'),
          meta: { title: 'Typography Demo', icon: 'article', hidden: true }
        },
        {
          path: 'accordion-test',
          name: 'accordion-test',
          component: () => import('@/components/FollowupAccordion.vue'),
          meta: { title: 'Accordion Test', icon: 'list', hidden: true }
        }
      ]
    : [])
]

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { title: 'Login', public: true } },
  // Root path exists only to trigger guard-based redirect to '/{tenant}/'
  { path: '/', component: AdminLayout, meta: { requiresAuth: true } },
  // Tenant-prefixed routes
  { path: '/:tenant', component: AdminLayout, meta: { requiresAuth: true }, children: adminChildren },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  // Update document title
  document.title = to.meta.title ? `${to.meta.title} - RAG Admin` : 'RAG Admin Dashboard'

  const adminStore = useAdminStore()

  // Check if route requires authentication
  if (to.meta.requiresAuth) {
    if (!adminStore.isAuthenticated) {
      try {
        await adminStore.checkAuth()
      } catch (error) {
        console.debug('Auth check failed, redirecting to login')
      }
    }

    if (!adminStore.isAuthenticated) {
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }

    // After authentication, if visiting root '/', redirect to first available tenant
    // This makes deep links shareable with an explicit tenant in the URL.
    if (to.path === '/' && !to.params.tenant) {
      try {
        const tenantStore = useTenantStore()
        if (!tenantStore.userTenants?.length && !tenantStore.isLoading) {
          await tenantStore.fetchUserTenants()
        }
        const target = tenantStore.currentTenant || (tenantStore.userTenants && tenantStore.userTenants[0])
        if (target?.slug) {
          next({ path: `/${target.slug}/`, replace: true })
          return
        }
      } catch (e) {
        // Non-blocking; continue navigation
      }
    }

    // Ensure tenant store is initialized before tenant-scoped routes
    try {
      const tenantStore = useTenantStore()
      if (!tenantStore.initialized) {
        await tenantStore.initialize()
      }

      // Preload data for knowledge views to avoid flicker and races
      if (typeof to.name === 'string' && to.name.startsWith('knowledge-')) {
        await tenantStore.loadDataForView(to.name)
      }
    } catch (e) {
      // Non-blocking; navigation continues
    }
  }

  // If going to login but already authenticated, redirect away
  if (to.name === 'login' && adminStore.isAuthenticated) {
    const raw = to.query.redirect
    const redirect =
      typeof raw === 'string' &&
      raw.startsWith('/') &&
      !raw.startsWith('//') &&
      !/[^a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]/.test(raw)
        ? raw
        : '/'
    next({ path: redirect })
    return
  }

  next()
})

export default router
