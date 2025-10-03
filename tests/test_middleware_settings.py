from starlette.testclient import TestClient


def test_maintenance_mode_enforced_and_bypass(monkeypatch):
    # Patch settings manager lookup to enable maintenance mode
    class FakeSettingsManager:
        def is_feature_enabled(self, name: str) -> bool:
            return name == "enable_maintenance_mode"

    from fastapi import FastAPI

    from backend.core.app_factory import maintenance_mode_middleware

    # Monkeypatch to control feature flag behavior
    monkeypatch.setattr(
        "backend.core.app_factory.get_settings_manager",
        lambda: FakeSettingsManager(),
    )

    # Build a minimal app with the middleware
    app = FastAPI()
    app.middleware("http")(maintenance_mode_middleware)

    @app.get("/api/status")
    def status():
        return {"ok": True}

    @app.get("/api/admin/auth/me")
    def admin_me():
        return {"user": "admin"}

    with TestClient(app) as client:
        # Non-admin path should be blocked with 503
        r = client.get("/api/status")
        assert r.status_code == 503

        # Admin paths should bypass maintenance check
        r2 = client.get("/api/admin/auth/me")
        assert r2.status_code == 200

        # Env override should disable maintenance immediately
        monkeypatch.setenv("FORCE_DISABLE_MAINTENANCE", "true")
        r3 = client.get("/api/status")
        assert r3.status_code == 200
