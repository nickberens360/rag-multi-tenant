# Migration Execution Guide

## Overview

Step-by-step guide for executing the multi-tenant customization migration.

---

## Pre-Migration Checklist

### ✅ Before You Begin

- [ ] Review all planning documents (01-05)
- [ ] Backup production database
- [ ] Create feature branch: `git checkout -b feature/multi-tenant-customization`
- [ ] Ensure development environment is working
- [ ] All tests currently passing
- [ ] Team notified of upcoming changes

### Environment Check

```bash
# Verify environment
cd /Users/nickberens/Webstorm/rag-multi-tenant

# Check git status
git status

# Verify backend running
curl http://localhost:8001/health

# Verify database connection
podman exec rag-multi-tenant_postgres_1 psql -U postgres -d app_db -c "SELECT COUNT(*) FROM tenants;"

# Backup database
pg_dump -h localhost -p 5433 -U postgres app_db > backup_before_customization_$(date +%Y%m%d).sql
```

---

## Phase 1: Database Migration (Week 1)

### Step 1.1: Create Alembic Migration

```bash
# Generate migration
cd backend
alembic revision -m "add_tenant_customization_fields"

# This creates: backend/alembic/versions/YYYYMMDD_add_tenant_customization_fields.py
```

### Step 1.2: Write Migration Code

Edit the generated file with content from `03-database-schema.md`:

```python
# Copy migration code from section "Alembic Migration" in 03-database-schema.md
```

**Key sections**:
- `upgrade()`: Add columns, constraints, triggers, populate defaults
- `downgrade()`: Remove all changes

### Step 1.3: Test Migration on Dev Database

```bash
# Run migration
alembic upgrade head

# Verify columns added
podman exec rag-multi-tenant_postgres_1 psql -U postgres -d app_db -c "\d tenants"

# Verify data populated
podman exec rag-multi-tenant_postgres_1 psql -U postgres -d app_db -c "
SELECT slug, assistant_name, tone, domain, customization_level FROM tenants;
"

# Check default tenant
podman exec rag-multi-tenant_postgres_1 psql -U postgres -d app_db -c "
SELECT * FROM tenants WHERE slug = 'default';
"
```

**Expected Output**:
```
slug    | assistant_name             | tone     | domain                       | customization_level
--------|----------------------------|----------|------------------------------|--------------------
default | Default Organization AI Assistant   | friendly | software engineering and...  | advanced
test-org| NULL                       | professional | general                  | basic
acme    | NULL                       | professional | general                  | basic
```

### Step 1.4: Test Rollback

```bash
# Test downgrade
alembic downgrade -1

# Verify columns removed
podman exec rag-multi-tenant_postgres_1 psql -U postgres -d app_db -c "\d tenants"

# Re-upgrade
alembic upgrade head

# Verify data restored
podman exec rag-multi-tenant_postgres_1 psql -U postgres -d app_db -c "
SELECT slug, assistant_name FROM tenants;
"
```

### Step 1.5: Update SQLAlchemy Models

Edit `backend/models/tenant.py`:

```python
# Add new fields as shown in 03-database-schema.md
# Update Tenant class with all new columns
```

### Step 1.6: Update Pydantic Schemas

Edit `backend/models/tenant_schemas.py`:

```python
# Add new fields to TenantBase, TenantCreate, TenantUpdate
# Add validators for brand_voice JSON
```

### Step 1.7: Commit Database Changes

```bash
git add backend/alembic/versions/*
git add backend/models/tenant.py
git add backend/models/tenant_schemas.py
git commit -m "feat: Add tenant customization fields to database schema

- Add assistant_name, system_prompt_template, tone, domain fields
- Add brand_voice and api_metadata JSONB fields
- Add customization_level and updated_at
- Populate default tenant with pre-existing default configuration
- Add check constraints and triggers
- Update SQLAlchemy and Pydantic models"
```

---

## Phase 2: Prompt Builder Service (Week 2)

### Step 2.1: Create TenantPromptBuilder Service

```bash
# Create new file
touch backend/core/tenant_prompt_builder.py
```

Edit with content from `04-code-changes.md`:

```python
# Copy complete TenantPromptBuilder class
# ~350 lines of code
```

### Step 2.2: Write Unit Tests

```bash
# Create test file
touch tests/unit/test_tenant_prompt_builder.py
```

Edit with content from `05-testing-plan.md`:

```python
# Copy all unit tests for TenantPromptBuilder
```

### Step 2.3: Run Unit Tests

```bash
# Run tests
pytest tests/unit/test_tenant_prompt_builder.py -v

# Check coverage
pytest tests/unit/test_tenant_prompt_builder.py \
  --cov=backend.core.tenant_prompt_builder \
  --cov-report=html \
  --cov-report=term

# Target: 95%+ coverage
```

### Step 2.4: Fix Failing Tests

```bash
# Iterate until all tests pass
pytest tests/unit/test_tenant_prompt_builder.py -v

# Expected: All green ✅
```

### Step 2.5: Commit Prompt Builder

```bash
git add backend/core/tenant_prompt_builder.py
git add tests/unit/test_tenant_prompt_builder.py
git commit -m "feat: Add TenantPromptBuilder service

- Dynamic tenant-aware prompt generation
- Template system with variable interpolation
- Caching for performance (5min TTL)
- Support for custom, technical, creative prompts
- Brand voice integration
- Comprehensive unit tests (95%+ coverage)"
```

---

## Phase 3: Update LLM Chain (Week 3, Part 1)

### Step 3.1: Backup Current File

```bash
cp backend/core/llm_chain.py backend/core/llm_chain.py.backup
```

### Step 3.2: Update llm_chain.py

Edit `backend/core/llm_chain.py`:

**Changes**:
1. Import `TenantPromptBuilder`
2. Replace `DEFAULT_PROMPTS` with `GENERIC_PROMPT_TEMPLATES`
3. Update `get_default_system_prompt()` → `get_system_prompt(tenant_id, ...)`
4. Update all prompt functions to accept `tenant_id`
5. Remove all hardcoded personal-name references

```python
# See detailed code in 04-code-changes.md
```

### Step 3.3: Update Call Sites

Find all files that call `get_default_system_prompt()`:

```bash
grep -r "get_default_system_prompt" backend/ --include="*.py"
```

Update each to pass `tenant_id`:

```python
# Before
prompt = get_default_system_prompt()

# After
prompt = get_system_prompt(tenant_id=tenant_id)
```

### Step 3.4: Write Integration Tests

```bash
touch tests/integration/test_llm_chain_multi_tenant.py
```

Edit with content from `05-testing-plan.md`.

### Step 3.5: Run Tests

```bash
# Unit tests (should still pass)
pytest tests/unit/ -v

# Integration tests (new)
pytest tests/integration/test_llm_chain_multi_tenant.py -v

# All tests
pytest -v
```

### Step 3.6: Manual Test

```bash
# Start backend
npm run backend:dev

# Test query for default tenant
curl -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the professional background?",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "stream": false
  }'

# Should work and reference Default Organization correctly

# Test query for test-org tenant
curl -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the organization about?",
    "tenant_id": "7be7cf79-e2ad-49c9-aab9-ecda044bda3a",
    "stream": false
  }'

# Should NOT reference any personal names
```

### Step 3.7: Commit LLM Chain Updates

```bash
git add backend/core/llm_chain.py
git add tests/integration/test_llm_chain_multi_tenant.py
git commit -m "feat: Make LLM chain tenant-aware

- Replace hardcoded prompts with TenantPromptBuilder
- Remove all personal-name references from prompts
- Support tenant-specific customization
- Add integration tests
- Maintain backward compatibility for default tenant"
```

---

## Phase 4: Update API Routes and Models (Week 3, Part 2)

### Step 4.1: Update query.py

Edit `backend/routes/query.py`:

**Changes**:
1. Update endpoint summary and description (remove personal-name references)
2. Update response examples to be generic
3. Update docstrings
4. Keep functionality the same

```python
# See detailed code in 04-code-changes.md
```

### Step 4.2: Update request_models.py

Edit `backend/models/request_models.py`:

**Changes**:
1. Update `QueryRequest` field descriptions
2. Replace example questions with generic ones
3. Update JSON schema examples

```python
# See detailed code in 04-code-changes.md
```

### Step 4.3: Test API Documentation

```bash
# Start backend
npm run backend:dev

# Visit API docs
open http://localhost:8001/docs

# Verify:
# - No personal-name mentions
# - Examples are generic
# - Multi-tenant documented
```

### Step 4.4: Run E2E Tests

```bash
touch tests/e2e/test_query_endpoint_multi_tenant.py

# Copy E2E tests from 05-testing-plan.md

pytest tests/e2e/test_query_endpoint_multi_tenant.py -v
```

### Step 4.5: Commit API Updates

```bash
git add backend/routes/query.py
git add backend/models/request_models.py
git add tests/e2e/test_query_endpoint_multi_tenant.py
git commit -m "feat: Update API documentation to be multi-tenant

- Remove personal-name references from endpoint docs
- Make example queries generic
- Update request model examples
- Add E2E tests for multi-tenant queries
- Improve OpenAPI documentation"
```

---

## Phase 5: Update Configuration (Week 4)

### Step 5.1: Update config_v2.py

Edit `backend/core/config_v2.py`:

**Changes**:
1. Update `APP_TITLE` to be generic
2. Update `APP_DESCRIPTION` to describe multi-tenant system
3. Add environment variable support
4. Add contact info variables

```python
# See detailed code in 04-code-changes.md
```

### Step 5.2: Update app_factory.py

Edit `backend/core/app_factory.py`:

**Changes**:
1. Use config variables instead of hardcoded values
2. Import contact info from config
3. Add OpenAPI tags

```python
# See detailed code in 04-code-changes.md
```

### Step 5.3: Update .env.example

Add new optional variables:

```bash
# Multi-Tenant API Configuration (Optional)
APP_TITLE="Custom RAG API"
APP_DESCRIPTION="Custom description..."
API_CONTACT_NAME="Support Team"
API_CONTACT_EMAIL="support@example.com"
API_CONTACT_URL="https://example.com"
```

### Step 5.4: Update Settings Defaults

Edit `backend/core/settings_manifest.py`:
- Change default from tenant-personalized assistant name to "AI Assistant"

Edit `backend/core/settings_schemas.py`:
- Change default from tenant-personalized assistant name to "AI Assistant"

### Step 5.5: Test Configuration

```bash
# Restart backend
npm run backend:stop
npm run backend:dev

# Check API title/description
curl http://localhost:8001/docs | grep -i "multi-tenant"

# Should see multi-tenant references
```

### Step 5.6: Commit Configuration Updates

```bash
git add backend/core/config_v2.py
git add backend/core/app_factory.py
git add backend/core/settings_manifest.py
git add backend/core/settings_schemas.py
git add .env.example
git commit -m "feat: Update configuration for multi-tenant deployment

- Make APP_TITLE and APP_DESCRIPTION generic
- Add environment variable support
- Update contact info to be configurable
- Remove hardcoded personal-name references
- Update default settings values"
```

---

## Phase 6: Final Testing and Cleanup (Week 5)

### Step 6.1: Run Full Test Suite

```bash
# All tests
pytest -v

# With coverage
pytest --cov=backend --cov-report=html --cov-report=term

# Target: 85%+ overall coverage
```

### Step 6.2: Manual Testing Checklist

Execute all 10 manual tests from `05-testing-plan.md`:

```bash
# Test 1: Default tenant query
curl -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is your professional background?",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "stream": false
  }'

# Expected: Response about Default Organization ✅

# Test 2: Generic tenant query
curl -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the organization about?",
    "tenant_id": "7be7cf79-e2ad-49c9-aab9-ecda044bda3a",
    "stream": false
  }'

# Expected: Generic response, no personal-name references ✅

# ... continue with all 10 tests
```

### Step 6.3: Performance Testing

```bash
# Run performance tests
pytest tests/performance/test_prompt_performance.py -v

# Target: <10ms per prompt (cached)
```

### Step 6.4: Code Quality

```bash
# Run linter
make lint

# Run formatter
make lint-fix

# Check for any remaining personal-name references
grep -r "\b[A-Z][a-z]+\s[A-Z][a-z]+\b" backend/ --include="*.py" | \
  grep -v "knowledge/" | \
  grep -v "__pycache__" | \
  grep -v "test_"

# Should be 0 results (or only in tests/knowledge)
```

### Step 6.5: Update Documentation

```bash
# Update CLAUDE.md with new features
# Update README if exists
# Update API documentation
```

### Step 6.6: Final Commit

```bash
git add .
git commit -m "docs: Update project documentation for multi-tenant features

- Document tenant customization capabilities
- Update architecture overview
- Add tenant management guide
- Update development setup instructions"
```

---

## Phase 7: Deployment

### Step 7.1: Create Pull Request

```bash
# Push feature branch
git push origin feature/multi-tenant-customization

# Create PR
gh pr create \
  --title "feat: Multi-tenant customization and hardcoded reference removal" \
  --body "$(cat docs/multi_tenant/01-overview-and-audit.md)"

# Or via GitHub UI
```

### Step 7.2: Code Review

- [ ] Team reviews all changes
- [ ] Address feedback
- [ ] Update tests as needed
- [ ] Verify all tests pass in CI

### Step 7.3: Merge to Main

```bash
# After approval
gh pr merge --squash

# Or via GitHub UI
```

### Step 7.4: Deploy to Production

```bash
# Pull latest main
git checkout main
git pull

# Run production database migration
# (Railway or production environment)
railway run alembic upgrade head

# Verify migration
railway run alembic current

# Deploy backend
npm run railway:deploy

# Monitor logs
railway logs
```

### Step 7.5: Post-Deployment Verification

```bash
# Test production endpoints
curl https://your-production-url.railway.app/health
curl https://your-production-url.railway.app/api/status

# Test query for default tenant
curl -X POST https://your-production-url.railway.app/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the professional background?",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "stream": false
  }'

# Verify: Works as expected
```

### Step 7.6: Monitor

- [ ] Check error logs
- [ ] Monitor query performance
- [ ] Watch for any issues
- [ ] Verify tenant isolation working

---

## Rollback Procedure

### If Issues Occur

```bash
# 1. Revert code deployment
git revert <merge-commit-hash>
git push origin main
npm run railway:deploy

# 2. Rollback database migration
railway run alembic downgrade -1

# 3. Verify system operational
curl https://your-production-url.railway.app/health

# 4. Investigate issue
# 5. Fix and redeploy when ready
```

---

## Post-Migration Tasks

### Week 6+

1. **Admin UI for Customization** (Optional)
   - Build Vue component for tenant assistant settings
   - Add UI to admin dashboard
   - Allow tenants to customize their assistant

2. **Advanced Features** (Future)
   - Custom logo/branding per tenant
   - Custom color schemes
   - Tenant-specific rate limits
   - Usage analytics per tenant

3. **Documentation**
   - User guide for tenant customization
   - API documentation updates
   - Admin guide for managing tenants

4. **Monitoring**
   - Add metrics for prompt generation time
   - Track cache hit rates
   - Monitor tenant-specific query patterns

---

## Success Checklist

### ✅ Migration Complete When:

- [ ] All tests passing (95%+ coverage)
- [ ] Zero hardcoded personal-name references in code
- [ ] Database migration successful
- [ ] TenantPromptBuilder service working
- [ ] All API endpoints updated
- [ ] Configuration genericized
- [ ] Documentation updated
- [ ] Production deployment successful
- [ ] No regressions detected
- [ ] Performance meets targets
- [ ] Team sign-off received

---

## Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Database Migration | Schema updated, tests passing |
| 2 | Prompt Builder | Service created, unit tests 95%+ |
| 3 | LLM & API Updates | Integration tests passing |
| 4 | Configuration | All config genericized |
| 5 | Testing & QA | All manual tests pass, E2E complete |
| 6+ | Deployment | Production live, monitoring active |

---

## Support

### Questions or Issues?

- Review planning documents in `docs/multi_tenant/`
- Check test outputs for specific failures
- Verify database state with SQL queries
- Review logs for error messages

### Need Help?

- Consult `04-code-changes.md` for code examples
- Reference `05-testing-plan.md` for test cases
- Check `03-database-schema.md` for DB questions

---

## Congratulations! 🎉

Once all checklists are complete, your multi-tenant RAG system will be:
- ✅ Fully generic and reusable
- ✅ Tenant-specific and customizable
- ✅ Well-tested and documented
- ✅ Production-ready

Good luck with the migration!
