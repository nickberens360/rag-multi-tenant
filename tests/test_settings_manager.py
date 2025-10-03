def test_settings_manager_db_fallback_and_cache(monkeypatch):
    from backend.core.settings_manager import SettingKeys, SettingsManager

    calls = {"count": 0}

    def fake_get_admin_setting(key):
        calls["count"] += 1
        return None  # force defaults

    monkeypatch.setattr(
        "backend.core.settings_manager.admin_db_manager.get_admin_setting",
        fake_get_admin_setting,
    )

    sm = SettingsManager(cache_ttl_seconds=3600)

    # First call reads from DB (None -> defaults)
    s1 = sm.get_response_settings()
    assert s1.enable_caching is True
    assert calls["count"] == 1

    # Second call served from cache
    s2 = sm.get_response_settings()
    assert s2 is s1
    assert calls["count"] == 1

    # Invalidate and read again (DB called again)
    sm.invalidate_cache(SettingKeys.RESPONSE_SETTINGS)
    sm.get_response_settings()
    assert calls["count"] == 2


def test_settings_manager_warmup_populates_cache(monkeypatch):
    from backend.core.settings_manager import SettingsManager

    # Return minimal valid JSON for all keys to avoid parse errors
    store = {}

    def fake_get_admin_setting(key):
        return store.get(key)

    monkeypatch.setattr(
        "backend.core.settings_manager.admin_db_manager.get_admin_setting",
        fake_get_admin_setting,
    )

    sm = SettingsManager(cache_ttl_seconds=3600)
    sm.warmup_cache()
    status = sm.get_cache_status()
    assert status["ttl_seconds"] == 3600
    # At least some keys should be cached after warmup
    assert status["cache_size"] >= 5


def test_is_feature_enabled_mapping(monkeypatch):
    from backend.core.settings_manager import SettingsManager
    from backend.core.settings_schemas import (
        FeatureFlags,
        FollowUpSettings,
        QueryRoutingSettings,
        ResponseSettings,
        SecuritySettings,
    )

    sm = SettingsManager()

    # Monkeypatch instance methods to return controlled settings
    monkeypatch.setattr(sm, "get_security_settings", lambda: SecuritySettings(enable_rate_limiting=False))
    monkeypatch.setattr(sm, "get_followup_settings", lambda: FollowUpSettings(enabled=True))
    monkeypatch.setattr(sm, "get_feature_flags", lambda: FeatureFlags(enable_debug_mode=True))
    monkeypatch.setattr(sm, "get_response_settings", lambda: ResponseSettings(enable_caching=False))
    monkeypatch.setattr(sm, "get_routing_settings", lambda: QueryRoutingSettings(enable_smart_routing=False))

    assert sm.is_feature_enabled("enable_rate_limiting") is False
    assert sm.is_feature_enabled("enable_followup_questions") is True
    assert sm.is_feature_enabled("enable_debug_mode") is True
    assert sm.is_feature_enabled("enable_smart_routing") is False
    assert sm.is_feature_enabled("enable_caching") is False
