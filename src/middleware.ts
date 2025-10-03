import { defineMiddleware } from 'astro:middleware';

/**
 * Tenant resolution middleware
 *
 * Resolves tenant context from:
 * 1. Subdomain (production): acme.site.com → "acme"
 * 2. Path prefix (development): site.com/acme → "acme"
 * 3. Environment default: PUBLIC_TENANT_DEFAULT_SLUG
 *
 * Stores resolved tenant in Astro.locals.tenantSlug for access in pages.
 */
export const onRequest = defineMiddleware(async (context, next) => {
  const { url, locals } = context;

  // Priority 1: Subdomain resolution (production)
  const hostname = url.hostname;
  const parts = hostname.split('.');
  const subdomain = parts.length > 2 ? parts[0] : null;

  // Priority 2: Path prefix resolution (development/fallback)
  const pathMatch = url.pathname.match(/^\/([^\/]+)/);
  const pathTenant = pathMatch?.[1];

  // Priority 3: Environment default
  const defaultSlug = import.meta.env.PUBLIC_TENANT_DEFAULT_SLUG || 'default';

  // Determine tenant (subdomain wins over path)
  let tenantSlug: string;

  // Valid subdomain: not www, localhost, or IP address
  if (subdomain && subdomain !== 'www' && subdomain !== 'localhost' && !hostname.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    tenantSlug = subdomain;
  }
  // Valid path tenant: alphanumeric + hyphens, not a static asset
  else if (pathTenant && pathTenant.match(/^[a-z0-9-]+$/) && !pathTenant.match(/\.(js|css|ico|png|jpg|jpeg|svg|woff|woff2)$/)) {
    tenantSlug = pathTenant;
  }
  // Use default
  else {
    tenantSlug = defaultSlug;
  }

  // Store in Astro.locals for access in pages and layouts
  locals.tenantSlug = tenantSlug;

  // Optionally set header for debugging (development only)
  const response = await next();

  if (import.meta.env.DEV) {
    response.headers.set('X-Tenant-Slug', tenantSlug);
  }

  return response;
});
