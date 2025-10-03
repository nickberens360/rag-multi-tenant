from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.security_middleware import SecurityHeadersMiddleware


def create_test_app() -> FastAPI:
    app = FastAPI()
    # Add only the headers middleware to keep test isolated from DB or other services
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/admin/test")
    def admin_test():
        return {"status": "ok"}

    return app


def test_permissions_policy_header_is_string_and_present():
    client = TestClient(create_test_app())
    resp = client.get("/api/health")
    header = resp.headers.get("Permissions-Policy")
    assert isinstance(header, str), "Permissions-Policy header must be a string"
    assert "geolocation=" in header
    assert "camera=" in header


def test_cache_control_applied_on_admin_routes():
    client = TestClient(create_test_app())
    resp = client.get("/api/admin/test")
    cache = resp.headers.get("Cache-Control", "")
    assert cache.startswith("no-store"), "Admin routes should set no-store Cache-Control"
