/**
 * Composable for making tenant-aware API calls
 *
 * Automatically extracts tenant slug from current URL and includes
 * it in X-Tenant-Slug header for all backend API requests.
 *
 * @example
 * const { fetchWithTenant, getTenantSlug } = useTenantAPI();
 * const response = await fetchWithTenant('http://localhost:8000/welcome-questions');
 */
export function useTenantAPI() {
  /**
   * Extract tenant slug from current page URL
   *
   * Checks URL patterns in order:
   * 1. Path-based: /tenant-slug/... → "tenant-slug"
   * 2. Subdomain: tenant.domain.com → "tenant"
   * 3. Default: fallback to 'default'
   *
   * @returns {string} Tenant slug
   */
  const getTenantSlug = () => {
    // Try path-based first (e.g., /default, /acme, /demo)
    const path = window.location.pathname;
    const pathMatch = path.match(/^\/([^/]+)/);

    if (pathMatch) {
      const segment = pathMatch[1];

      // Exclude common non-tenant routes
      if (!['blog', 'api', 'admin', 'assets', 'static', '_astro'].includes(segment)) {
        return segment;
      }
    }

    // Try subdomain (e.g., tenant.example.com)
    const hostname = window.location.hostname;
    const parts = hostname.split('.');

    if (parts.length >= 3) {
      const subdomain = parts[0];

      // Exclude common non-tenant subdomains
      if (!['www', 'api', 'admin', 'mail', 'ftp', 'localhost'].includes(subdomain)) {
        return subdomain;
      }
    }

    // Fallback to default tenant
    return 'default';
  };

  /**
   * Fetch wrapper that automatically includes tenant context header
   *
   * @param {string} url - API endpoint URL
   * @param {object} options - Fetch options (method, body, headers, etc)
   * @returns {Promise<Response>} Fetch response
   */
  const fetchWithTenant = async (url, options = {}) => {
    const tenantSlug = getTenantSlug();

    const headers = {
      ...options.headers,
      'X-Tenant-Slug': tenantSlug,
    };

    return fetch(url, { ...options, headers });
  };

  return {
    fetchWithTenant,
    getTenantSlug
  };
}
