"""
FastAPI application factory for creating and configuring the app instance.

This module handles:
- FastAPI app instantiation with metadata
- CORS middleware configuration
- Rate limiter setup and exception handling
- Router registration
- Security middleware application
"""

import logging
from pathlib import Path
from typing import AsyncContextManager, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from .config_v2 import AppConfig
from .security_middleware import add_security_middleware
from .settings_manager import get_settings_manager


# Initialize the limiter - centralized application-wide rate limiting
# Use a test-safe key function that gracefully handles missing client info.
def _safe_key_func(request: Request) -> str:
    try:
        # Prefer Starlette client host if available
        client = getattr(request, "client", None)
        if client and getattr(client, "host", None):
            return client.host
        # Fall back to X-Forwarded-For when behind proxies
        fwd = request.headers.get("x-forwarded-for") if hasattr(request, "headers") else None
        if fwd:
            return fwd.split(",")[0].strip()
    except Exception:
        pass
    # Final fallback for test transports without client info
    return "local-test"


# Check if we're in testing environment to disable rate limiting
import os

_is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in os.environ.get("_", "")

# Create limiter - use dummy storage during testing to effectively disable rate limiting
if _is_testing:
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
else:
    limiter = Limiter(key_func=_safe_key_func)


async def maintenance_mode_middleware(request: Request, call_next):
    """Middleware to check for maintenance mode feature flag with admin bypass and override.

    - Bypasses maintenance for admin routes so admins can log in and toggle it off
    - Honors FORCE_DISABLE_MAINTENANCE env to immediately disable maintenance checks
    """
    try:
        # Allow admin routes during maintenance (so admin can recover)
        path = request.url.path or ""
        if path.startswith("/api/admin") or path.startswith("/admin"):
            return await call_next(request)

        # Emergency override via env var
        import os

        if os.getenv("FORCE_DISABLE_MAINTENANCE", "false").lower() == "true":
            return await call_next(request)

        settings_manager = get_settings_manager()
        if settings_manager.is_feature_enabled("enable_maintenance_mode"):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=503,
                content={
                    "detail": "System is under maintenance. Please try again later.",
                    "message": "We're performing scheduled maintenance to improve your experience.",
                },
            )
    except Exception as e:
        # If feature flag check fails, log but continue normally
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to check maintenance mode feature flag: {e}")

    return await call_next(request)


async def dynamic_rate_limit_middleware(request: Request, call_next):
    """Middleware to apply dynamic rate limiting based on security settings."""
    # Allow hard override via env to quickly bypass rate limiting (useful for local dev/debug)
    import os as _os

    if _os.getenv("DISABLE_RATE_LIMITING", "false").lower() in {"1", "true", "yes"}:
        return await call_next(request)
    # Skip rate limiting during testing
    if _is_testing:
        return await call_next(request)

    # Skip rate limiting for admin routes except login endpoint - they have session-based auth protection
    if (
        request.url.path.startswith("/admin/") or request.url.path.startswith("/api/admin/")
    ) and request.url.path != "/api/admin/auth/login":
        return await call_next(request)

    try:
        settings_manager = get_settings_manager()
        security_settings = settings_manager.get_security_settings()

        if not security_settings.enable_rate_limiting:
            # Rate limiting disabled, skip
            return await call_next(request)

        # Get client IP for rate limiting
        client_ip = _safe_key_func(request)

        # Create a simple in-memory rate limiter check
        # This is a basic implementation - in production you'd want Redis or similar
        import time

        # Check if we have a rate limit store in app state
        if not hasattr(request.app.state, "rate_limit_store"):
            request.app.state.rate_limit_store = {}

        store = request.app.state.rate_limit_store
        current_time = time.time()
        window_start = current_time - security_settings.rate_limit_window

        # Clean old entries
        store[client_ip] = [req_time for req_time in store.get(client_ip, []) if req_time > window_start]

        # Check if rate limit exceeded
        if len(store[client_ip]) >= security_settings.rate_limit_requests:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": security_settings.rate_limit_window,
                },
            )

        # Add current request to store
        store[client_ip].append(current_time)

    except Exception as e:
        # If rate limit check fails, log but continue normally
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to apply dynamic rate limiting: {e}")

    return await call_next(request)


def configure_cors(app: FastAPI):
    """Configure CORS with hardcoded origins from AppConfig."""
    # Always use hardcoded CORS origins from AppConfig
    app.add_middleware(
        CORSMiddleware,
        allow_origins=AppConfig.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers",
            "X-Tenant-Slug",  # Custom header for tenant identification
        ],
        expose_headers=["X-Model-Used", "X-Followup-Questions"],
    )


def create_app(lifespan: Optional[Callable[[FastAPI], AsyncContextManager]] = None) -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Args:
        lifespan: Optional lifespan context manager for startup/shutdown events

    Returns:
        FastAPI: Configured FastAPI application
    """
    # Create FastAPI app with enhanced metadata and documentation
    app = FastAPI(
        title=AppConfig.APP_TITLE,
        description=AppConfig.APP_DESCRIPTION,
        version=AppConfig.APP_VERSION,
        lifespan=lifespan,
        contact={
            "name": "Nick Berens",
            "url": "https://nickberens.me",
            "email": "hello@nickberens.me",
        },
        license_info={
            "name": "MIT",
        },
        tags_metadata=[
            {
                "name": "Health",
                "description": "System health and status endpoints",
            },
            {
                "name": "Query",
                "description": "AI-powered query endpoints for retrieving information from Nick's knowledge base. Uses Claude and advanced RAG (Retrieval-Augmented Generation) to provide intelligent responses.",
            },
            {
                "name": "Public API",
                "description": "Public endpoints for accessing content, performance metrics, and analytics. No authentication required.",
            },
            {
                "name": "Admin Authentication",
                "description": "Admin login, logout, and user management endpoints. **Authentication required** for all admin operations.",
            },
            {
                "name": "Admin Management",
                "description": "Administrative endpoints for system management, monitoring, and configuration. **Admin authentication required**.",
            },
            {
                "name": "Admin Analytics",
                "description": "Query analytics, performance metrics, and system insights for administrators. **Admin access required**.",
            },
        ],
    )

    # Setup rate limiter - use the centralized limiter instance
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Add CORS middleware FIRST (so it runs last/handles requests first)
    configure_cors(app)

    # Add security middleware
    add_security_middleware(app)

    # Add tenant middleware (if enabled)
    # Note: Always import tenant_middleware to ensure it's available, but only register if enabled
    import os

    from .tenant_middleware import tenant_middleware

    if os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true":
        app.middleware("http")(tenant_middleware)
    else:
        # Even when disabled, apply the middleware but it will use defaults
        app.middleware("http")(tenant_middleware)

    # Add maintenance mode middleware
    app.middleware("http")(maintenance_mode_middleware)

    # Add dynamic rate limiting middleware
    app.middleware("http")(dynamic_rate_limit_middleware)

    # Register routers - import here to avoid circular imports
    from ..routes import (
        admin,
        admin_diagnostics,
        admin_refresh,
        content,
        debug,
        health,
        knowledge,
        knowledge_admin_sync,
        knowledge_public,
        knowledge_uploads,
        performance,
        queries,
        query,
        query_logs,
        smart_query,
        stats,
    )

    # Import tenant routes if multi-tenant is enabled
    if os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true":
        try:
            from ..routes import invitations, tenants

            tenant_routes_available = True
        except ImportError:
            tenant_routes_available = False
    else:
        tenant_routes_available = False

    # Core public routes (no prefix) — kept as temporary aliases (hidden from schema)
    app.include_router(health.router, include_in_schema=False)
    app.include_router(query.router, include_in_schema=False)

    # Standardized public routes under /api
    app.include_router(health.router, prefix="/api")
    app.include_router(query.router, prefix="/api")

    # Multi-tenant path-prefix routes: /{tenant}/api/*
    # These allow tenant-specific routing in development (localhost:4321/test-org/)
    if os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true":
        app.include_router(health.router, prefix="/{tenant}/api", include_in_schema=False)
        app.include_router(query.router, prefix="/{tenant}/api", include_in_schema=False)

    # Dev-only debug endpoints
    try:
        if os.getenv("ENVIRONMENT", "development").lower() not in {"production", "prod"} or os.getenv(
            "ENABLE_DEBUG_ENDPOINTS", "false"
        ).lower() in {"1", "true", "yes"}:
            app.include_router(debug.router, prefix="/api")
            # Support path-prefix style: /{tenant}/api/debug/*
            app.include_router(debug.router, prefix="/{tenant}/api")
    except Exception:
        pass

    # Public API routes — serve under /api (new standard) and keep /api/public as compatibility alias
    app.include_router(smart_query.router, prefix="/api")
    app.include_router(content.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(performance.router, prefix="/api")
    app.include_router(knowledge_public.router, prefix="/api")
    # Path-prefix variants for tenant-scoped routes (optional; may be disabled for tests)
    enable_path_prefix = os.getenv("ENABLE_PATH_PREFIX_ROUTERS", "true").lower() in {"1", "true", "yes"}
    if enable_path_prefix:
        app.include_router(performance.router, prefix="/{tenant}/api")
        app.include_router(performance.router, prefix="/{tenant}/api/admin")
        app.include_router(stats.router, prefix="/{tenant}/api")
        app.include_router(stats.router, prefix="/{tenant}/api/admin")
        app.include_router(queries.router, prefix="/{tenant}/api/admin")
        app.include_router(content.router, prefix="/{tenant}/api")
        app.include_router(content.router, prefix="/{tenant}/api/admin")
        app.include_router(query_logs.router, prefix="/{tenant}/api/admin")
        # Admin refresh endpoints under tenant-prefixed admin path
        app.include_router(admin_refresh.router, prefix="/{tenant}/api/admin")
        # Admin knowledge sync endpoints under tenant-prefixed admin path
        app.include_router(knowledge_admin_sync.router, prefix="/{tenant}/api/admin")
        # Admin knowledge operations (read+write) under tenant-prefixed admin path
        app.include_router(knowledge.router, prefix="/{tenant}/api/admin")
        # Tenant-specific knowledge upload endpoints under tenant-prefixed admin path
        app.include_router(knowledge_uploads.router, prefix="/{tenant}/api/admin")

    # Backward-compatible aliases for one deprecation cycle (hidden from schema)
    app.include_router(smart_query.router, prefix="/api/public", include_in_schema=False)
    app.include_router(content.router, prefix="/api/public", include_in_schema=False)
    app.include_router(stats.router, prefix="/api/public", include_in_schema=False)
    app.include_router(performance.router, prefix="/api/public", include_in_schema=False)
    app.include_router(knowledge_public.router, prefix="/api/public", include_in_schema=False)

    # Add deprecation headers for legacy paths
    @app.middleware("http")
    async def legacy_deprecation_middleware(request: Request, call_next):
        response = await call_next(request)
        try:
            path = request.url.path or ""
            legacy_paths = {
                "/",
                "/status",
                "/health",
                "/rate-limits",
                "/db-paths",
                "/welcome-questions",
                "/query",
                "/default-model",
            }
            if path in legacy_paths or path.startswith("/api/public/"):
                response.headers["Deprecation"] = "true"
                response.headers["Link"] = '</docs/api-routing-standardization-plan.md>; rel="deprecation"'
        except Exception:
            # Best-effort; never block requests on header injection
            pass
        return response

    # Admin API routes - consolidated under /api/admin, with optional {tenant} path prefix variant
    app.include_router(admin.router, prefix="/api/admin")
    if enable_path_prefix:
        app.include_router(admin.router, prefix="/{tenant}/api/admin")
    app.include_router(query_logs.router, prefix="/api/admin")
    app.include_router(admin_refresh.router, prefix="/api/admin")
    app.include_router(queries.router, prefix="/api/admin")
    app.include_router(knowledge.router, prefix="/api/admin")  # Admin operations (read + write)
    app.include_router(stats.router, prefix="/api/admin")  # Admin stats for dashboard
    app.include_router(performance.router, prefix="/api/admin")  # Admin performance metrics
    app.include_router(knowledge_admin_sync.router, prefix="/api/admin")
    # Expose content routes under admin prefix as well for consistent client base
    app.include_router(content.router, prefix="/api/admin")

    # Register tenant routes if available and enabled
    if tenant_routes_available:
        app.include_router(tenants.router)
        app.include_router(invitations.router)

    # Conditionally register admin diagnostics router based on feature flag,
    # with optional environment override for development.
    enable_admin_diagnostics = False
    try:
        settings_manager = get_settings_manager()
        enable_admin_diagnostics = settings_manager.is_feature_enabled("enable_admin_diagnostics")
    except Exception as e:
        # If feature flag check fails, log but continue to env override check
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to check admin diagnostics feature flag: {e}", exc_info=True)

    # Environment override (useful in dev/staging): ENABLE_ADMIN_DIAGNOSTICS=true
    try:
        if not enable_admin_diagnostics and os.getenv("ENABLE_ADMIN_DIAGNOSTICS", "false").lower() in {
            "1",
            "true",
            "yes",
        }:
            enable_admin_diagnostics = True
            logger = logging.getLogger(__name__)
            logger.info("Admin diagnostics router enabled via env override ENABLE_ADMIN_DIAGNOSTICS")
    except Exception:
        pass

    if enable_admin_diagnostics:
        app.include_router(admin_diagnostics.router, prefix="/api/admin")

    # Serve admin frontend static files (mount after API routes to avoid conflicts)
    admin_static_path = Path(__file__).parent.parent.parent / "admin" / "frontend" / "dist"
    if admin_static_path.exists():

        # Mount static assets in two places to handle both absolute and base-relative URLs
        # - Vite production build uses base '/admin/' so assets are requested under '/admin/assets/...'
        # - Some links may still point to '/assets/...'
        app.mount("/assets", StaticFiles(directory=str(admin_static_path / "assets")), name="admin_assets")
        app.mount(
            "/admin/assets",
            StaticFiles(directory=str(admin_static_path / "assets")),
            name="admin_assets_under_admin",
        )

        # Custom admin SPA handler that properly serves index.html for client-side routing
        class SPAStaticFiles(StaticFiles):
            async def get_response(self, path: str, scope):
                try:
                    # Serve real files when they exist
                    return await super().get_response(path, scope)
                except Exception:
                    # Only fallback to index.html for non-asset routes (no file extension)
                    file_name = path.rsplit("/", 1)[-1]
                    if "." in file_name:
                        # Let the original error propagate for missing assets (avoids JS modules getting HTML)
                        raise
                    return await super().get_response("index.html", scope)

        # Mount admin frontend with custom SPA handler
        app.mount("/admin", SPAStaticFiles(directory=str(admin_static_path), html=True), name="admin_frontend")

    return app
