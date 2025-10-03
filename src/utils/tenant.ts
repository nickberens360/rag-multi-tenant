import type { AstroGlobal } from 'astro';

/**
 * Extract tenant slug from Astro context
 *
 * Checks multiple sources in priority order:
 * 1. Astro.locals.tenantSlug (set by middleware)
 * 2. Astro.params.tenant (from [tenant] route param)
 * 3. Environment default
 *
 * @param Astro - Astro global context
 * @returns Tenant slug string
 */
export function tenantFromAstro(Astro: AstroGlobal): string {
  // Prefer middleware-resolved tenant
  if (Astro.locals.tenantSlug) {
    return Astro.locals.tenantSlug;
  }

  // Fallback to path param (for [tenant] pages)
  if (Astro.params.tenant) {
    return Astro.params.tenant;
  }

  // Ultimate fallback to environment default
  return import.meta.env.PUBLIC_TENANT_DEFAULT_SLUG || 'default';
}

/**
 * Generate tenant-aware href for links
 *
 * Automatically prefixes paths with tenant slug when using path-based routing.
 * In subdomain mode, returns path as-is.
 *
 * @param Astro - Astro global context
 * @param path - Target path (e.g., "/about")
 * @returns Tenant-prefixed path (e.g., "/acme/about") or original path
 *
 * @example
 * // In subdomain mode (acme.site.com):
 * tenantHref(Astro, '/about') // Returns: '/about'
 *
 * // In path mode (site.com/acme):
 * tenantHref(Astro, '/about') // Returns: '/acme/about'
 */
export function tenantHref(Astro: AstroGlobal, path: string): string {
  const tenant = tenantFromAstro(Astro);

  // Normalize path to start with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  // Check if we're in subdomain mode
  const hostname = Astro.url.hostname;
  const subdomain = hostname.split('.')[0];

  // If subdomain matches tenant, we're in subdomain mode - don't prefix
  if (subdomain === tenant && subdomain !== 'www' && subdomain !== 'localhost') {
    return normalizedPath;
  }

  // Otherwise, use path prefix mode
  return `/${tenant}${normalizedPath}`;
}

/**
 * Validate tenant slug format
 *
 * Ensures slug contains only lowercase alphanumeric characters and hyphens,
 * and is within length limits.
 *
 * @param slug - Tenant slug to validate
 * @returns True if valid, false otherwise
 */
export function isValidTenantSlug(slug: string | undefined | null): boolean {
  if (!slug) return false;
  return /^[a-z0-9-]{1,80}$/.test(slug);
}

/**
 * Extract tenant from subdomain
 *
 * @param hostname - Full hostname (e.g., "acme.site.com")
 * @returns Tenant slug or null if not a valid subdomain
 */
export function extractTenantFromSubdomain(hostname: string): string | null {
  const parts = hostname.split('.');

  // Need at least 3 parts for a subdomain (subdomain.domain.tld)
  if (parts.length < 3) return null;

  const subdomain = parts[0];

  // Exclude common non-tenant subdomains
  if (['www', 'api', 'admin', 'mail', 'ftp'].includes(subdomain)) {
    return null;
  }

  // Exclude localhost and IPs
  if (subdomain === 'localhost' || hostname.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    return null;
  }

  return isValidTenantSlug(subdomain) ? subdomain : null;
}

/**
 * Extract tenant from path
 *
 * @param pathname - URL pathname (e.g., "/acme/about")
 * @returns Tenant slug or null if not found
 */
export function extractTenantFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/([^\/]+)/);
  const segment = match?.[1];

  if (!segment) return null;

  // Exclude static assets and known routes
  if (segment.match(/\.(js|css|ico|png|jpg|jpeg|svg|woff|woff2)$/)) {
    return null;
  }

  return isValidTenantSlug(segment) ? segment : null;
}
