import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export interface Tenant {
  id: string
  slug: string
  name: string
  role: string
}

export function useTenant() {
  const route = useRoute()
  const router = useRouter()

  const currentTenant = ref<Tenant | null>(null)
  const userTenants = ref<Tenant[]>([])

  // Parse tenant from URL
  const tenantSlug = computed(() => {
    // Check subdomain
    const subdomain = window.location.hostname.split('.')[0]
    if (subdomain && !['www', 'localhost', 'api', 'admin'].includes(subdomain)) {
      return subdomain
    }

    // Check path prefix
    const pathMatch = route.path.match(/^\/([^\/]+)/)
    if (pathMatch) {
      return pathMatch[1]
    }

    return null
  })

  // Fetch user's tenants
  async function fetchUserTenants() {
    const response = await fetch('/api/admin/tenants/mine', {
      credentials: 'include'
    })
    if (response.ok) {
      userTenants.value = await response.json()

      // Set current tenant if slug matches
      if (tenantSlug.value) {
        currentTenant.value = userTenants.value.find(
          t => t.slug === tenantSlug.value
        ) || null
      }
    }
  }

  // Switch tenant
  async function switchTenant(tenant: Tenant) {
    if (window.location.hostname.includes('localhost')) {
      // Use path prefix in dev
      await router.push(`/${tenant.slug}`)
    } else {
      // Use subdomain in prod
      window.location.href = `https://${tenant.slug}.${window.location.hostname.split('.').slice(1).join('.')}`
    }
  }

  // Watch for route changes
  watch(() => route.path, () => {
    if (tenantSlug.value && userTenants.value.length > 0) {
      currentTenant.value = userTenants.value.find(
        t => t.slug === tenantSlug.value
      ) || null
    }
  })

  return {
    currentTenant,
    userTenants,
    tenantSlug,
    fetchUserTenants,
    switchTenant
  }
}