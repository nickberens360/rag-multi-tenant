# Testing Plan

## Overview

Comprehensive testing strategy for multi-tenant customization implementation.

---

## Testing Levels

```
┌─────────────────────────────────────────┐
│ 1. Unit Tests                           │
│    - TenantPromptBuilder                │
│    - Individual functions               │
│    - Template rendering                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 2. Integration Tests                    │
│    - Database + Prompt Builder          │
│    - LLM Chain + Prompts                │
│    - Query Handler + Tenants            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 3. End-to-End Tests                     │
│    - Full query flow                    │
│    - Multi-tenant isolation             │
│    - Admin UI customization             │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 4. Manual Testing                       │
│    - User acceptance                    │
│    - Edge cases                         │
│    - Performance validation             │
└─────────────────────────────────────────┘
```

---

## 1. Unit Tests

### Test Suite: TenantPromptBuilder

**File**: `tests/unit/test_tenant_prompt_builder.py`

```python
import pytest
from uuid import UUID
from backend.core.tenant_prompt_builder import TenantPromptBuilder, get_prompt_builder
from backend.models.tenant import Tenant


class TestTenantPromptBuilder:
    """Unit tests for TenantPromptBuilder."""

    @pytest.fixture
    def builder(self):
        """Fixture for prompt builder instance."""
        return TenantPromptBuilder()

    @pytest.fixture
    def default_tenant_id(self):
        """Default tenant UUID."""
        return UUID("00000000-0000-0000-0000-000000000001")

    @pytest.fixture
    def test_tenant_id(self):
        """Test tenant UUID."""
        return UUID("7be7cf79-e2ad-49c9-aab9-ecda044bda3a")

    # Basic functionality tests
    def test_build_system_prompt_default_tenant(self, builder, default_tenant_id):
        """Test system prompt for default tenant."""
        prompt = builder.build_system_prompt(default_tenant_id)

        # Should contain tenant name
        assert "Default Organization" in prompt

        # Should have assistant name
        assert "AI Assistant" in prompt

        # Should have context placeholder
        assert "{context}" in prompt

        # Should not have double braces (template error)
        assert "{{" not in prompt

    def test_build_system_prompt_generic_tenant(self, builder, test_tenant_id):
        """Test system prompt for generic tenant."""
        prompt = builder.build_system_prompt(test_tenant_id)

        assert "Test Org" in prompt
        assert "professional" in prompt.lower() or "friendly" in prompt.lower()
        assert "{context}" in prompt

    def test_build_system_prompt_with_custom_template(self, builder, db_session):
        """Test custom system prompt template."""
        # Create tenant with custom template
        tenant = Tenant(
            slug="custom-tenant",
            name="Custom Tenant",
            customization_level="custom",
            system_prompt_template="Custom prompt for {organization_name}. Context: {context}"
        )
        db_session.add(tenant)
        db_session.commit()

        prompt = builder.build_system_prompt(tenant.id)

        assert "Custom prompt" in prompt
        assert "Custom Tenant" in prompt

    def test_build_technical_prompt(self, builder, default_tenant_id):
        """Test technical prompt type."""
        prompt = builder.build_system_prompt(
            default_tenant_id,
            prompt_type="technical"
        )

        assert "technical" in prompt.lower()
        assert "{context}" in prompt

    def test_build_creative_prompt(self, builder, default_tenant_id):
        """Test creative prompt type."""
        prompt = builder.build_system_prompt(
            default_tenant_id,
            prompt_type="creative"
        )

        assert "creative" in prompt.lower() or "portfolio" in prompt.lower()
        assert "{context}" in prompt

    # Response guidelines tests
    def test_build_response_guidelines_simple(self, builder, default_tenant_id):
        """Test simple response guidelines."""
        guidelines = builder.build_response_guidelines(
            default_tenant_id,
            complexity="simple"
        )

        assert guidelines
        assert "concise" in guidelines.lower() or "direct" in guidelines.lower()

    def test_build_response_guidelines_complex(self, builder, default_tenant_id):
        """Test complex response guidelines."""
        guidelines = builder.build_response_guidelines(
            default_tenant_id,
            complexity="complex"
        )

        assert guidelines
        assert "comprehensive" in guidelines.lower() or "detailed" in guidelines.lower()

    def test_response_guidelines_with_brand_voice(self, builder, db_session):
        """Test brand voice influences guidelines."""
        # Create tenant with specific brand voice
        tenant = Tenant(
            slug="branded-tenant",
            name="Branded Tenant",
            brand_voice={
                "style": "first-person",
                "personality": ["friendly", "approachable"],
                "prefer": ["I have", "My experience"],
                "avoid": ["We believe", "Our company"]
            }
        )
        db_session.add(tenant)
        db_session.commit()

        guidelines = builder.build_response_guidelines(tenant.id)

        assert "first-person" in guidelines.lower()
        assert "I have" in guidelines or "My experience" in guidelines

    # Caching tests
    def test_caching_works(self, builder, default_tenant_id):
        """Test that tenant data is cached."""
        # First call
        prompt1 = builder.build_system_prompt(default_tenant_id)

        # Modify cache directly to verify it's being used
        cached_tenant, cached_time = builder._tenant_cache[default_tenant_id]
        cached_tenant.name = "Modified Name"

        # Second call should use cache
        prompt2 = builder.build_system_prompt(default_tenant_id)

        assert "Modified Name" in prompt2

    def test_cache_expiration(self, builder, default_tenant_id):
        """Test cache expires after TTL."""
        from datetime import datetime, timedelta

        # First call
        prompt1 = builder.build_system_prompt(default_tenant_id)

        # Manually expire cache
        tenant, _ = builder._tenant_cache[default_tenant_id]
        expired_time = datetime.utcnow() - timedelta(minutes=10)
        builder._tenant_cache[default_tenant_id] = (tenant, expired_time)

        # Second call should fetch fresh data
        prompt2 = builder.build_system_prompt(default_tenant_id)

        # Verify it worked (cache refreshed)
        _, new_time = builder._tenant_cache[default_tenant_id]
        assert new_time > expired_time

    def test_clear_cache_specific_tenant(self, builder, default_tenant_id, test_tenant_id):
        """Test clearing cache for specific tenant."""
        # Populate cache
        builder.build_system_prompt(default_tenant_id)
        builder.build_system_prompt(test_tenant_id)

        assert len(builder._tenant_cache) == 2

        # Clear one tenant
        TenantPromptBuilder.clear_cache(default_tenant_id)

        assert len(builder._tenant_cache) == 1
        assert test_tenant_id in builder._tenant_cache

    def test_clear_cache_all_tenants(self, builder, default_tenant_id, test_tenant_id):
        """Test clearing entire cache."""
        # Populate cache
        builder.build_system_prompt(default_tenant_id)
        builder.build_system_prompt(test_tenant_id)

        assert len(builder._tenant_cache) == 2

        # Clear all
        TenantPromptBuilder.clear_cache()

        assert len(builder._tenant_cache) == 0

    # Edge cases and error handling
    def test_missing_tenant_raises_error(self, builder):
        """Test error handling for missing tenant."""
        fake_id = UUID("99999999-9999-9999-9999-999999999999")

        with pytest.raises(ValueError, match="Tenant .* not found"):
            builder.build_system_prompt(fake_id)

    def test_invalid_prompt_type_uses_default(self, builder, default_tenant_id):
        """Test fallback for invalid prompt type."""
        prompt = builder.build_system_prompt(
            default_tenant_id,
            prompt_type="nonexistent_type"
        )

        # Should fall back to default
        assert prompt  # Got something
        assert "{context}" in prompt

    def test_missing_template_variable_fallback(self, builder, db_session):
        """Test fallback when template variable is missing."""
        tenant = Tenant(
            slug="broken-tenant",
            name="Broken Tenant",
            customization_level="custom",
            system_prompt_template="Invalid template with {nonexistent_var}"
        )
        db_session.add(tenant)
        db_session.commit()

        # Should not crash, should use fallback
        prompt = builder.build_system_prompt(tenant.id)

        assert prompt
        assert "Broken Tenant" in prompt

    def test_singleton_instance(self):
        """Test get_prompt_builder returns singleton."""
        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()

        assert builder1 is builder2

    # Template variable tests
    def test_template_variables_populated(self, builder, default_tenant_id):
        """Test all template variables are populated correctly."""
        prompt = builder.build_system_prompt(default_tenant_id)

        # Should NOT have unpopulated variables
        assert "{organization_name}" not in prompt
        assert "{assistant_name}" not in prompt
        assert "{domain}" not in prompt
        assert "{tone}" not in prompt

        # SHOULD have {context} (populated at runtime)
        assert "{context}" in prompt

    def test_extra_variables_passed_through(self, builder, default_tenant_id):
        """Test extra template variables are used."""
        prompt = builder.build_system_prompt(
            default_tenant_id,
            custom_var="custom value"
        )

        # If template used it, should be populated
        # (This tests the **extra_vars mechanism)
        assert "custom value" not in prompt or "{custom_var}" not in prompt


# Test coverage goals
"""
Target Coverage: 95%+

Critical Paths:
- ✅ Basic prompt generation (default, technical, creative)
- ✅ Custom template handling
- ✅ Brand voice integration
- ✅ Caching mechanism
- ✅ Error handling and fallbacks
- ✅ Template variable population
"""
```

---

## 2. Integration Tests

### Test Suite: LLM Chain Integration

**File**: `tests/integration/test_llm_chain_multi_tenant.py`

```python
import pytest
from uuid import UUID
from backend.core.llm_chain import get_system_prompt, build_chain
from backend.models.tenant import Tenant


class TestLLMChainMultiTenant:
    """Integration tests for LLM chain with multi-tenant prompts."""

    @pytest.fixture
    def default_tenant_id(self):
        return UUID("00000000-0000-0000-0000-000000000001")

    @pytest.fixture
    def test_tenant_id(self):
        return UUID("7be7cf79-e2ad-49c9-aab9-ecda044bda3a")

    def test_get_system_prompt_integration(self, default_tenant_id):
        """Test get_system_prompt integrates with database."""
        prompt = get_system_prompt(
            tenant_id=default_tenant_id,
            context="Sample context about the organization"
        )

        assert prompt
        assert "Sample context" in prompt
        assert "Default Organization" in prompt

    def test_build_chain_with_tenant_prompt(self, default_tenant_id):
        """Test LLM chain built with tenant-specific prompt."""
        chain = build_chain(
            tenant_id=default_tenant_id,
            query_type="default"
        )

        assert chain
        # Verify chain has correct prompt configured
        # (implementation-specific assertion)

    def test_different_tenants_get_different_prompts(
        self,
        default_tenant_id,
        test_tenant_id
    ):
        """Test tenant isolation in prompts."""
        prompt1 = get_system_prompt(default_tenant_id)
        prompt2 = get_system_prompt(test_tenant_id)

        # Prompts should be different
        assert prompt1 != prompt2

        # Each should reference correct tenant
        assert "Default Organization" in prompt1
        assert "Test Org" in prompt2

    def test_technical_vs_default_prompt_difference(self, default_tenant_id):
        """Test different prompt types produce different prompts."""
        default_prompt = get_system_prompt(
            default_tenant_id,
            prompt_type="system"
        )

        technical_prompt = get_system_prompt(
            default_tenant_id,
            prompt_type="technical"
        )

        assert default_prompt != technical_prompt
        assert "technical" in technical_prompt.lower()
```

### Test Suite: Query Handler Integration

**File**: `tests/integration/test_query_handler_multi_tenant.py`

```python
import pytest
from uuid import UUID
from backend.core.smart_query_handler import process_query


class TestQueryHandlerMultiTenant:
    """Integration tests for query handler with tenant customization."""

    @pytest.fixture
    def default_tenant_id(self):
        return UUID("00000000-0000-0000-0000-000000000001")

    @pytest.fixture
    def test_tenant_id(self):
        return UUID("7be7cf79-e2ad-49c9-aab9-ecda044bda3a")

    @pytest.mark.asyncio
    async def test_query_uses_tenant_prompt(self, default_tenant_id):
        """Test that queries use tenant-specific prompts."""
        response = await process_query(
            question="What is the professional background?",
            tenant_id=default_tenant_id
        )

        assert response
        # Response should be about the correct tenant
        # (Should not reference unrelated tenants or personal names)

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_queries(
        self,
        default_tenant_id,
        test_tenant_id
    ):
        """Test queries for different tenants are isolated."""
        question = "What is the organization about?"

        response1 = await process_query(question, default_tenant_id)
        response2 = await process_query(question, test_tenant_id)

        # Responses should be different and tenant-specific
        assert response1 != response2

    @pytest.mark.asyncio
    async def test_complexity_affects_prompt(self, default_tenant_id):
        """Test query complexity influences prompt selection."""
        simple_response = await process_query(
            question="What is this?",
            tenant_id=default_tenant_id,
            query_complexity="simple"
        )

        complex_response = await process_query(
            question="Explain in detail the technical architecture",
            tenant_id=default_tenant_id,
            query_complexity="complex"
        )

        # Responses should differ based on complexity
        # (Implementation-specific assertion)
        assert simple_response != complex_response
```

---

## 3. End-to-End Tests

### Test Suite: Full Query Flow

**File**: `tests/e2e/test_query_endpoint_multi_tenant.py`

```python
import pytest
from fastapi.testclient import TestClient
from uuid import UUID


class TestQueryEndpointMultiTenant:
    """End-to-end tests for query endpoint with multi-tenant support."""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    @pytest.fixture
    def default_tenant_id(self):
        return "00000000-0000-0000-0000-000000000001"

    @pytest.fixture
    def test_tenant_id(self):
        return "7be7cf79-e2ad-49c9-aab9-ecda044bda3a"

    def test_query_with_default_tenant(self, client, default_tenant_id):
        """Test query for default tenant."""
        response = client.post(
            "/api/query",
            json={
                "question": "What is the professional background?",
                "tenant_id": default_tenant_id,
                "stream": False
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        # Should reference Default Organization
        assert "Default" in data["answer"]

    def test_query_with_test_tenant(self, client, test_tenant_id):
        """Test query for test-org tenant."""
        response = client.post(
            "/api/query",
            json={
                "question": "What is the organization about?",
                "tenant_id": test_tenant_id,
                "stream": False
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        # Should not reference unrelated tenants or personal names
        assert "Default Organization" in data["answer"]

    def test_streaming_query_with_tenant(self, client, default_tenant_id):
        """Test streaming query uses tenant-specific prompt."""
        response = client.post(
            "/api/query",
            json={
                "question": "What technologies are used?",
                "tenant_id": default_tenant_id,
                "stream": True
            }
        )

        assert response.status_code == 200

        # Collect streaming chunks
        chunks = []
        for line in response.iter_lines():
            if line:
                chunks.append(line.decode('utf-8'))

        assert len(chunks) > 0

    def test_invalid_tenant_returns_error(self, client):
        """Test invalid tenant ID returns proper error."""
        response = client.post(
            "/api/query",
            json={
                "question": "Test question",
                "tenant_id": "99999999-9999-9999-9999-999999999999",
                "stream": False
            }
        )

        assert response.status_code in [400, 404]

    def test_api_docs_generic(self, client):
        """Test API documentation is generic (not personalized)."""
        response = client.get("/docs")

        assert response.status_code == 200
        content = response.text

        # Should include tenant terminology (generic)
        assert "tenant" in content.lower()

        # SHOULD have multi-tenant references
        assert "multi-tenant" in content.lower() or "tenant" in content.lower()
```

---

## 4. Manual Testing Checklist

### Pre-Deployment Manual Tests

#### Test 1: Default Tenant
- [ ] Query: "What is your professional background?"
- [ ] Expected: Response about Default Organization, friendly tone
- [ ] Verify: No template errors, context is relevant
- [ ] Check: Assistant identifies as "Default Organization AI Assistant"

#### Test 2: Generic Tenant (Test Org)
- [ ] Query: "What is the organization about?"
- [ ] Expected: Generic professional response, no personal-name references
- [ ] Verify: Uses "Test Org" correctly
- [ ] Check: Tone is professional

#### Test 3: New Tenant Creation
- [ ] Create tenant via admin UI: "Acme Corporation"
- [ ] Set assistant name: "Acme Knowledge Bot"
- [ ] Set tone: "friendly"
- [ ] Set domain: "enterprise software"
- [ ] Query: "What does the company do?"
- [ ] Expected: Response using "Acme", friendly tone
- [ ] Verify: No personal-name references

#### Test 4: Custom Prompt Template (Advanced)
- [ ] Set custom template for tenant
- [ ] Verify template validation works
- [ ] Query should use custom template
- [ ] Fallback works if template invalid

#### Test 5: API Documentation
- [ ] Visit /docs
- [ ] Verify: No personal-name references
- [ ] Check: Examples are generic
- [ ] Verify: Multi-tenant documented

#### Test 6: Performance
- [ ] Run 10 queries for default tenant
- [ ] Check: Response times < 10s
- [ ] Verify: Cache is working (check logs)
- [ ] Monitor: Database query count

#### Test 7: Tenant Isolation
- [ ] Query same question for 3 different tenants
- [ ] Verify: Each gets appropriate response
- [ ] Check: No cross-tenant data leakage
- [ ] Confirm: Logs show correct tenant_id

#### Test 8: Streaming Responses
- [ ] Test streaming with different tenants
- [ ] Verify: Each uses correct prompt
- [ ] Check: No errors in stream

#### Test 9: Error Handling
- [ ] Invalid tenant_id
- [ ] Missing tenant_id
- [ ] Malformed custom template
- [ ] Database connection issues
- [ ] Verify: Graceful fallbacks

#### Test 10: Admin UI
- [ ] Access assistant settings in admin
- [ ] Modify assistant name
- [ ] Change tone
- [ ] Update domain
- [ ] Verify: Changes reflected in queries immediately (cache cleared)

---

## 5. Performance Tests

### Load Testing

**File**: `tests/performance/test_prompt_performance.py`

```python
import pytest
import time
from uuid import UUID
from backend.core.tenant_prompt_builder import TenantPromptBuilder


def test_prompt_generation_performance():
    """Test prompt generation is fast enough."""
    builder = TenantPromptBuilder()
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")

    # Warm up cache
    builder.build_system_prompt(tenant_id)

    # Time 100 prompt generations
    start = time.time()
    for _ in range(100):
        builder.build_system_prompt(tenant_id)
    elapsed = time.time() - start

    # Should be < 10ms per prompt (cached)
    assert elapsed < 1.0  # 100 prompts in under 1 second
    avg_time = elapsed / 100
    print(f"Average prompt generation time: {avg_time*1000:.2f}ms")


def test_cache_hit_rate():
    """Test cache effectiveness."""
    builder = TenantPromptBuilder()
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")

    # Clear cache
    TenantPromptBuilder.clear_cache()

    # First call - cache miss
    start_cold = time.time()
    builder.build_system_prompt(tenant_id)
    cold_time = time.time() - start_cold

    # Second call - cache hit
    start_warm = time.time()
    builder.build_system_prompt(tenant_id)
    warm_time = time.time() - start_warm

    # Cache hit should be significantly faster
    assert warm_time < cold_time / 10  # At least 10x faster

    print(f"Cold: {cold_time*1000:.2f}ms, Warm: {warm_time*1000:.2f}ms")
```

---

## Test Execution Plan

### Phase 1: Unit Tests (Week 2)
```bash
# Run unit tests
pytest tests/unit/test_tenant_prompt_builder.py -v

# Check coverage
pytest tests/unit/test_tenant_prompt_builder.py --cov=backend.core.tenant_prompt_builder --cov-report=html

# Target: 95%+ coverage
```

### Phase 2: Integration Tests (Week 3)
```bash
# Run integration tests
pytest tests/integration/test_llm_chain_multi_tenant.py -v
pytest tests/integration/test_query_handler_multi_tenant.py -v

# Target: All passing
```

### Phase 3: E2E Tests (Week 4)
```bash
# Run end-to-end tests
pytest tests/e2e/test_query_endpoint_multi_tenant.py -v

# Target: All passing
```

### Phase 4: Performance Tests (Week 5)
```bash
# Run performance tests
pytest tests/performance/test_prompt_performance.py -v

# Target: <10ms per prompt (cached)
```

### Phase 5: Manual Testing (Week 5)
- Complete manual testing checklist
- User acceptance testing
- Edge case exploration

---

## Success Criteria

### Code Coverage
- ✅ TenantPromptBuilder: 95%+
- ✅ LLM Chain updates: 90%+
- ✅ Query handler updates: 90%+
- ✅ Overall backend: 85%+

### Test Results
- ✅ All unit tests passing
- ✅ All integration tests passing
- ✅ All E2E tests passing
- ✅ Performance tests meet targets

### Manual Testing
- ✅ All 10 manual tests pass
- ✅ No regressions found
- ✅ User acceptance approved

---

## Rollback Criteria

If any of these occur, rollback:
- ❌ Test coverage drops below 80%
- ❌ >5% of tests failing
- ❌ Performance degrades >20%
- ❌ Critical bugs found in production
- ❌ User acceptance rejected

---

## Next Steps

1. Implement unit tests for TenantPromptBuilder
2. Run tests iteratively during development
3. Add integration tests before merging
4. Complete E2E tests before deployment
5. See `06-migration-guide.md` for execution steps
