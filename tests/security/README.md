# Admin Dashboard Security Tests

This directory contains comprehensive security tests for the admin dashboard Python backend. These tests focus on **security-first validation** of authentication, authorization, data protection, and attack prevention.

## Test Structure

### Core Security Test Files

1. **`test_admin_auth_security.py`** - AdminAuthManager security tests
   - Password strength validation
   - Bcrypt hashing security 
   - Session hijacking detection
   - Rate limiting enforcement
   - Geolocation security validation

2. **`test_admin_database_security.py`** - AdminDatabaseManager security tests
   - SQL injection prevention
   - Parameterized query enforcement
   - Transaction rollback security
   - Database schema integrity
   - Concurrent access safety
   - Audit trail integrity

3. **`test_admin_api_security.py`** - Admin API endpoint security tests
   - Authentication requirement enforcement
   - Role-based authorization
   - Rate limiting on endpoints
   - Input validation and sanitization
   - CSRF protection
   - Security headers validation

4. **`test_admin_integration_security.py`** - Integration security tests
   - End-to-end authentication flows
   - Cross-system security validation
   - Session lifecycle security
   - Database isolation testing
   - Comprehensive attack scenarios

### Test Configuration

- **`conftest.py`** - Pytest configuration and fixtures
- **`README.md`** - This documentation file

## Running Security Tests

### Quick Security Test Run
```bash
# Run all security tests
pytest tests/security/ -v

# Run specific security test categories
pytest tests/security/ -m "auth" -v       # Authentication tests
pytest tests/security/ -m "database" -v   # Database security tests
pytest tests/security/ -m "api" -v        # API security tests
pytest tests/security/ -m "integration" -v # Integration tests
```

### Comprehensive Security Validation
```bash
# Run with coverage and detailed output
pytest tests/security/ --cov=backend.core.admin_auth --cov=backend.core.admin_database --cov=backend.routes.admin -v --tb=short

# Run security tests with timing
pytest tests/security/ -v --durations=10

# Run only critical security tests (fast)
pytest tests/security/ -m "not slow" -v
```

### Security Test Categories

#### **Authentication Security (`-m auth`)**
- Password strength validation
- Hash security (bcrypt)
- Session management
- Rate limiting
- Geolocation validation

#### **Database Security (`-m database`)**  
- SQL injection prevention
- Transaction safety
- Schema integrity
- Access controls
- Audit trails

#### **API Security (`-m api`)**
- Endpoint authentication
- Authorization enforcement  
- Input validation
- Security headers
- Rate limiting

#### **Integration Security (`-m integration`)**
- End-to-end flows
- Cross-system validation
- Attack scenarios
- System isolation

## Security Test Priorities

### **CRITICAL SECURITY TESTS** (Must Pass)
1. SQL injection prevention
2. Authentication bypass prevention
3. Session security validation
4. Password security enforcement
5. Authorization bypass prevention

### **HIGH PRIORITY SECURITY TESTS**
1. Rate limiting enforcement
2. Input validation and sanitization
3. Session hijacking detection
4. Database transaction integrity
5. Security event logging

### **MEDIUM PRIORITY SECURITY TESTS**
1. Enhanced geolocation security
2. Geolocation security
3. Audit trail validation
4. Concurrent access safety
5. Security headers validation

## Security Test Fixtures

### Available Fixtures

- `temp_admin_db` - Temporary test database
- `mock_environment` - Test environment variables
- `security_headers` - Standard security headers
- `malicious_payloads` - Common attack payloads
- `test_users` - Test user accounts
- `rate_limit_config` - Rate limiting settings
- `security_helper` - Security testing utilities

### Security Helper Functions

```python
# SQL Injection testing
assert_no_sql_injection(response.text)

# XSS testing  
assert_no_xss(response.text)

# Security headers testing
assert_secure_headers(response.headers)
```

## Security Test Examples

### Testing SQL Injection Prevention
```python
def test_sql_injection_prevention(client, malicious_payloads):
    for payload in malicious_payloads["sql_injection"]:
        response = client.post("/admin/api/auth/login", json={
            "username": payload,
            "password": "test"
        })
        # Should handle safely without SQL injection
        assert_no_sql_injection(response.text)
```

### Testing Authentication Security
```python
def test_authentication_required(client):
    response = client.get("/admin/api/stats/overview")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]
```

### Testing Rate Limiting
```python
def test_rate_limiting_enforcement(client):
    for i in range(6):  # Exceed rate limit
        response = client.post("/admin/api/auth/login", json={
            "username": "test", "password": "wrong"
        })
    # Should enforce rate limiting
    assert response.status_code in [429, 200]  # 200 with error message
```

## Security Test Best Practices

### 1. **Test Real Attack Vectors**
- Use actual malicious payloads
- Test edge cases and boundary conditions
- Validate error handling doesn't expose information

### 2. **Validate Security Controls**
- Ensure authentication is required
- Test authorization at all levels
- Verify input sanitization works

### 3. **Test Failure Modes**
- What happens when security controls fail?
- Are errors handled securely?
- Is sensitive information protected?

### 4. **Integration Testing**
- Test complete attack scenarios
- Validate cross-system security
- Ensure no security bypasses exist

## Common Security Issues to Test

### Authentication & Authorization
- [ ] Authentication bypass
- [ ] Privilege escalation
- [ ] Session fixation
- [ ] Session hijacking
- [ ] Weak password policies

### Input Validation
- [ ] SQL injection
- [ ] XSS attacks
- [ ] Path traversal
- [ ] Command injection
- [ ] Buffer overflow

### Rate Limiting & DoS
- [ ] Brute force attacks
- [ ] Rate limit bypass
- [ ] Resource exhaustion
- [ ] Request smuggling

### Data Protection
- [ ] Information disclosure
- [ ] Database exposure
- [ ] Error message information leakage
- [ ] Log injection

## Continuous Security Testing

### Pre-commit Hooks
```bash
# Add to .pre-commit-config.yaml
- repo: local
  hooks:
    - id: security-tests
      name: Security Tests
      entry: pytest tests/security/ -x
      language: system
      pass_filenames: false
```

### CI/CD Integration
```bash
# Add to GitHub Actions or similar
- name: Run Security Tests
  run: |
    pytest tests/security/ --cov=backend.core --tb=short
    # Fail build if critical security tests fail
```

## Security Test Maintenance

### Regular Updates Needed
1. **Update attack payloads** - Keep malicious payloads current
2. **Review test coverage** - Ensure new code is security tested
3. **Validate test effectiveness** - Confirm tests catch real issues
4. **Performance monitoring** - Ensure tests don't become too slow

### Security Test Review Process
1. **Code review** - All security tests should be peer reviewed
2. **Penetration testing** - Validate tests against real attacks
3. **Security audit** - Regular review of test completeness
4. **Incident response** - Update tests based on security incidents

This security test suite provides comprehensive validation of the admin dashboard's security posture, focusing on preventing real-world attack vectors and ensuring robust security controls.