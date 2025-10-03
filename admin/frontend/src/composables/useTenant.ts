import { useTenantStore } from '@/stores/tenant'

// Simple composable that provides access to the tenant store
// This maintains backward compatibility while using proper Pinia patterns
export function useTenant() {
  const tenantStore = useTenantStore()

  return {
    currentTenant: tenantStore.currentTenant,
    userTenants: tenantStore.userTenants,
    tenantSlug: tenantStore.tenantSlug,
    hasTenant: tenantStore.hasTenant,
    tenantId: tenantStore.tenantId,
    tenantName: tenantStore.tenantName,
    isLoading: tenantStore.isLoading,
    error: tenantStore.error,
    fetchUserTenants: tenantStore.fetchUserTenants,
    switchTenant: tenantStore.switchTenant,
    clearTenant: tenantStore.clearTenant,
    resetError: tenantStore.resetError,
    initialize: tenantStore.initialize
  }
}