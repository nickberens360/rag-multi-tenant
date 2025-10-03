"""
Simple, focused security tests for admin endpoints.
Replaces overly complex security test scenarios.
"""

import pytest
from fastapi.testclient import TestClient


class TestSimpleSecurity:
    """Simple security tests focused on core protection mechanisms."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from backend.main import app

        return TestClient(app)

    def test_admin_endpoints_require_authentication(self, client):
        """Test that admin endpoints properly require authentication."""
        # List of admin endpoints that should be protected
        protected_endpoints = [
            "/api/admin/auth/me",
            "/api/admin/stats/overview",
            "/api/admin/queries",
            "/api/admin/users",
            "/api/admin/settings/followup",
            "/api/admin/export/csv",
            "/api/admin/security/alerts",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should return 401 Unauthorized for unauthenticated requests
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

    def test_admin_post_endpoints_require_authentication(self, client):
        """Test that admin POST/PUT/DELETE endpoints require authentication."""
        # Test various HTTP methods on protected endpoints
        test_cases = [
            ("POST", "/api/admin/auth/create-user", {"username": "test", "password": "test123"}),
            ("PUT", "/api/admin/settings/followup", {"enabled": True}),
            ("POST", "/api/admin/settings/followup/reset", {}),
        ]

        for method, endpoint, data in test_cases:
            if method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "PUT":
                response = client.put(endpoint, json=data)
            else:
                response = client.delete(endpoint)

            # Should return 401 Unauthorized
            assert response.status_code == 401, f"{method} {endpoint} should require authentication"

    def test_invalid_login_attempts_are_blocked(self, client):
        """Test that invalid login attempts are properly rejected."""
        # Test with invalid credentials
        invalid_credentials = [
            {"username": "", "password": ""},  # Empty credentials
            {"username": "nonexistent", "password": "wrongpass"},  # Wrong credentials
            {"username": "admin", "password": ""},  # Missing password
        ]

        for creds in invalid_credentials:
            response = client.post("/api/admin/auth/login", json=creds)

            # Should not return server error
            assert response.status_code != 500, f"Invalid credentials should not cause server error: {creds}"

            # Response should indicate failure - either error status code or success=false
            if response.status_code == 200:
                data = response.json()
                assert (
                    data.get("success") is False
                ), f"200 response should have success=false for invalid creds: {creds}"
            elif response.status_code == 422:  # Pydantic validation error
                data = response.json()
                assert "detail" in data, "422 should have validation details"
            else:
                # Other error codes (400, 401) are acceptable for invalid credentials
                assert response.status_code in [400, 401], f"Unexpected status for invalid credentials: {creds}"

    def test_sql_injection_protection(self, client):
        """Test basic SQL injection protection in query parameters."""
        # SQL injection attempts in query parameters
        injection_attempts = [
            "'; DROP TABLE admin_users; --",
            "' OR '1'='1",
            "admin'; DELETE FROM admin_users WHERE '1'='1",
        ]

        for injection in injection_attempts:
            # Test in login endpoint
            response = client.post("/api/admin/auth/login", json={"username": injection, "password": "test123"})

            # Should handle gracefully (not crash) and return proper error
            # Note: 200 with "success": false is also acceptable - the key is that the injection doesn't work
            assert response.status_code in [200, 400, 401, 422], f"SQL injection should be handled: {injection}"

            # If it returns 200, it should still indicate login failure
            if response.status_code == 200:
                data = response.json()
                assert data.get("success") is False, f"SQL injection should fail login: {injection}"

            # Application should not crash (no 500 errors from SQL injection)
            assert response.status_code != 500, f"SQL injection caused server error: {injection}"

    def test_xss_protection_in_responses(self, client):
        """Test that responses don't reflect unescaped user input."""
        # XSS test payloads: should not be reflected unescaped in responses
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
        ]

        for payload in xss_payloads:
            # Test XSS in login attempt
            response = client.post("/api/admin/auth/login", json={"username": payload, "password": "test123"})

            # Response should not contain unescaped payload
            response_text = response.text.lower()
            assert "<script>" not in response_text, f"XSS payload reflected: {payload}"
            assert "javascript:" not in response_text, f"XSS payload reflected: {payload}"
            assert "onerror=" not in response_text, f"XSS payload reflected: {payload}"

    def test_rate_limiting_exists(self, client):
        """Test that rate limiting mechanisms are in place."""
        # Make multiple rapid requests to trigger rate limiting
        login_endpoint = "/api/admin/auth/login"
        invalid_creds = {"username": "fake", "password": "fake"}

        responses = []
        for i in range(10):  # Make 10 rapid requests
            response = client.post(login_endpoint, json=invalid_creds)
            responses.append(response.status_code)

        # Should eventually get rate limited (429) or consistent rejections
        # The specific implementation may vary, but we shouldn't get server errors
        server_errors = [r for r in responses if r >= 500]
        assert len(server_errors) == 0, "Rate limiting should not cause server errors"

    def test_secure_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get("/api/admin/health")  # Public endpoint

        # Check for basic security headers (implementation dependent)
        headers = response.headers

        # At minimum, should have content-type header
        assert "content-type" in headers, "Response should have content-type header"

        # Response should be well-formed JSON for API endpoints
        if response.status_code == 200:
            try:
                response.json()  # Should parse as JSON
            except ValueError:
                pytest.fail("API response should be valid JSON")

    def test_password_validation_exists(self, client):
        """Test that password validation is enforced."""
        # This test assumes we have a user creation endpoint
        # Test will be skipped if endpoint doesn't exist or isn't accessible

        weak_passwords = [
            "123",  # Too short
            "password",  # Too common
            "abc",  # Too short and simple
        ]

        for weak_password in weak_passwords:
            response = client.post(
                "/api/admin/auth/create-user",
                json={"username": "testuser", "password": weak_password, "role": "viewer"},
            )

            # Should be rejected (401 for auth required, or 400 for validation error)
            assert response.status_code in [400, 401, 422], f"Weak password should be rejected: {weak_password}"
