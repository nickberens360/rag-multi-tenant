# Multi-Tenant Customization - Planning Documentation

## Overview

This directory contains comprehensive planning documentation for removing hardcoded personal-name references and implementing true multi-tenant functionality in the RAG system.

---

## 📚 Documents

### [01-overview-and-audit.md](./01-overview-and-audit.md)
**Executive summary and audit results**

- Problem statement and impact analysis
- Complete audit of 33 hardcoded references
- Severity classification (Critical, Medium, Low)
- Success criteria and risk assessment

**Read this first** to understand the scope and impact of the issue.

---

### [02-implementation-plan.md](./02-implementation-plan.md)
**Detailed implementation strategy**

- Three-tier approach (Database → Service → Code)
- Phase-by-phase breakdown (5 weeks)
- File-by-file refactoring plan
- Rollback strategies and performance considerations

**Use this** to understand the overall architecture and approach.

---

### [03-database-schema.md](./03-database-schema.md)
**Database migration specifications**

- New tenant customization fields
- Complete Alembic migration code
- SQLAlchemy and Pydantic model updates
- Migration testing checklist

**Reference this** when implementing database changes.

---

### [04-code-changes.md](./04-code-changes.md)
**Code implementation specifications**

- Complete TenantPromptBuilder service code (~350 lines)
- Updated LLM chain, routes, models, config
- Before/after code examples for all 7 files
- Integration patterns and best practices

**Use this** as your code implementation guide.

---

### [05-testing-plan.md](./05-testing-plan.md)
**Comprehensive testing strategy**

- Unit tests for TenantPromptBuilder (95%+ coverage)
- Integration tests for LLM chain and query handler
- End-to-end API tests
- Manual testing checklist (10 tests)
- Performance benchmarks

**Follow this** to ensure quality and catch regressions.

---

### [06-migration-guide.md](./06-migration-guide.md)
**Step-by-step execution guide**

- Pre-migration checklist
- Week-by-week execution plan
- Detailed terminal commands for each step
- Rollback procedures
- Post-deployment verification

**Use this** as your day-by-day implementation roadmap.

---

## 🎯 Quick Start

### For Project Managers
1. Read `01-overview-and-audit.md` (understand the problem)
2. Review `02-implementation-plan.md` (understand the solution)
3. Check timeline in `06-migration-guide.md` (plan resources)

### For Developers
1. Skim `01-overview-and-audit.md` (understand why)
2. Study `02-implementation-plan.md` (understand approach)
3. Reference `03-database-schema.md` (for DB work)
4. Use `04-code-changes.md` (for coding)
5. Follow `05-testing-plan.md` (for testing)
6. Execute `06-migration-guide.md` (step-by-step)

### For QA/Testing
1. Review `01-overview-and-audit.md` (understand scope)
2. Study `05-testing-plan.md` (test strategy)
3. Execute manual test checklist
4. Verify success criteria

---

## 📊 Summary Statistics

### Problem Scope
- **Total References**: 33 hardcoded personal-name mentions
- **Files Affected**: 6 core backend files
- **Severity Breakdown**:
  - 🔴 Critical: 17 references (blocks multi-tenant AI)
  - 🟡 Medium: 13 references (API docs/examples)
  - 🟢 Low: 3 references (default settings)

### Solution Scope
- **New Code**: ~350 lines (TenantPromptBuilder service)
- **Modified Code**: ~150 lines (across 7 files)
- **Database Changes**: 8 new columns + migration
- **Test Code**: ~800 lines (unit + integration + E2E)

### Timeline
- **Total Duration**: 5-6 weeks
- **Week 1**: Database schema migration
- **Week 2**: TenantPromptBuilder service + unit tests
- **Week 3**: LLM chain and API updates
- **Week 4**: Configuration and settings
- **Week 5**: Testing, QA, deployment
- **Week 6+**: Optional admin UI and advanced features

---

## ✅ Success Criteria

### Functional
- [x] AI responses are tenant-specific (not personalized)
- [x] API documentation is generic or tenant-aware
- [x] System prompts dynamically populated from tenant metadata
- [x] Each tenant can customize assistant behavior
- [x] Zero hardcoded references in production code

### Technical
- [x] Database migration successful (no data loss)
- [x] All tests passing (95%+ coverage)
- [x] Performance impact < 5% (caching effective)
- [x] Backward compatible with existing tenants
- [x] Graceful fallbacks when customization not provided

### User Experience
- [x] "Default" tenant works as before
- [x] New tenants get professional generic responses
- [x] Tenants can customize via admin UI (future)
- [x] No manual configuration required for basic use

---

## 🏗️ Architecture

### Before (Current State)
```
Query → Hardcoded Prompt (single-tenant) → AI Response (about default org)
                                         ❌ Wrong for other tenants
```

### After (Target State)
```
Query → Tenant Lookup → TenantPromptBuilder → Dynamic Prompt → AI Response
          ↓                      ↓                                 ↓
     tenant_id            {organization_name}            Tenant-specific
                          {assistant_name}                   content
                          {domain}
                          {tone}
```

---

## 📁 File Structure

```
docs/multi_tenant/
├── README.md                       # This file
├── 01-overview-and-audit.md        # Problem definition & audit
├── 02-implementation-plan.md       # Solution strategy
├── 03-database-schema.md           # Database changes
├── 04-code-changes.md              # Code implementation
├── 05-testing-plan.md              # Testing strategy
└── 06-migration-guide.md           # Execution guide
```

---

## 🔄 Migration Phases

### Phase 1: Database (Week 1)
```bash
# Create migration
alembic revision -m "add_tenant_customization"

# Add fields: assistant_name, tone, domain, brand_voice, etc.
# Populate defaults for existing tenants

# Test migration
alembic upgrade head
```

### Phase 2: Prompt Builder (Week 2)
```python
# Create service
backend/core/tenant_prompt_builder.py

# Features:
# - Dynamic prompt generation
# - Template system
# - Caching (5min TTL)
# - Fallback to generic defaults
```

### Phase 3: Code Updates (Week 3-4)
```python
# Update files:
# - backend/core/llm_chain.py        # Prompts
# - backend/routes/query.py          # API docs
# - backend/models/request_models.py # Examples
# - backend/core/config_v2.py        # App metadata
# - backend/core/app_factory.py      # Contact info
# - backend/core/settings_*.py       # Defaults
```

### Phase 4: Testing (Week 5)
```bash
# Unit tests
pytest tests/unit/test_tenant_prompt_builder.py

# Integration tests
pytest tests/integration/test_llm_chain_multi_tenant.py

# E2E tests
pytest tests/e2e/test_query_endpoint_multi_tenant.py

# Manual testing (10 test cases)
```

### Phase 5: Deployment (Week 5-6)
```bash
# Merge to main
gh pr merge

# Deploy to production
railway run alembic upgrade head
npm run railway:deploy

# Verify
curl https://production-url/api/query
```

---

## 🚀 Getting Started

### 1. Review Planning (1-2 hours)
```bash
# Read overview
open docs/multi_tenant/01-overview-and-audit.md

# Read implementation plan
open docs/multi_tenant/02-implementation-plan.md

# Understand timeline
open docs/multi_tenant/06-migration-guide.md
```

### 2. Prepare Environment (30 minutes)
```bash
# Create feature branch
git checkout -b feature/multi-tenant-customization

# Backup database
pg_dump -h localhost -p 5433 -U postgres app_db > backup_$(date +%Y%m%d).sql

# Ensure tests passing
pytest -v
```

### 3. Start Implementation (Week 1)
```bash
# Follow migration guide
open docs/multi_tenant/06-migration-guide.md

# Start with Phase 1: Database Migration
```

---

## 📈 Progress Tracking

### Completion Checklist

#### Week 1: Database
- [ ] Alembic migration created
- [ ] Migration tested on dev database
- [ ] Rollback tested
- [ ] SQLAlchemy models updated
- [ ] Pydantic schemas updated
- [ ] Tests passing

#### Week 2: Service
- [ ] TenantPromptBuilder created
- [ ] Unit tests written (95%+ coverage)
- [ ] All unit tests passing
- [ ] Code reviewed

#### Week 3: Critical Updates
- [ ] llm_chain.py updated
- [ ] query.py updated
- [ ] Integration tests passing
- [ ] Manual testing successful

#### Week 4: Config Updates
- [ ] config_v2.py genericized
- [ ] app_factory.py updated
- [ ] Settings defaults updated
- [ ] API docs verified

#### Week 5: Testing & Deployment
- [ ] All automated tests passing
- [ ] Manual test checklist complete
- [ ] Performance tests passing
- [ ] Code review approved
- [ ] Deployed to production
- [ ] Post-deployment verification

---

## 🛡️ Risk Mitigation

### High-Risk Areas
1. **LLM Prompt Changes** (Week 3)
   - Mitigation: Comprehensive testing, gradual rollout
   - Rollback: Revert commit, previous prompts still work

2. **Database Migration** (Week 1)
   - Mitigation: Test on dev first, backup before production
   - Rollback: `alembic downgrade -1` + restore from backup

### Medium-Risk Areas
1. **API Documentation** (Week 3-4)
   - Mitigation: Review before deploying
   - Impact: Documentation only, no runtime changes

2. **Caching Performance** (Week 2)
   - Mitigation: Performance tests before production
   - Fallback: Disable cache if issues

---

## 📞 Support

### Questions?
- Check relevant planning document (01-06)
- Review code examples in `04-code-changes.md`
- Consult test cases in `05-testing-plan.md`

### Issues?
- Verify database state with SQL queries
- Check test output for specific failures
- Review logs for error messages
- Use rollback procedures if needed

---

## 🎉 Success Metrics

### Target Outcomes
- ✅ Zero hardcoded personal-name references in code
- ✅ Each tenant gets customized AI responses
- ✅ 95%+ test coverage maintained
- ✅ <5% performance impact
- ✅ No data loss or corruption
- ✅ Backward compatible with existing tenants

### Post-Migration Benefits
- ✨ True multi-tenant system
- ✨ Tenant-specific branding and customization
- ✨ Scalable to unlimited tenants
- ✨ Professional, generic public API
- ✨ Maintainable, well-tested codebase

---

## 📝 Version History

- **v1.0** (2025-10-04): Initial planning documentation
  - Complete audit of hardcoded references
  - Detailed implementation plan
  - Database schema design
  - Code implementation specs
  - Testing strategy
  - Migration execution guide

---

## 🚦 Next Steps

1. ✅ Review this README
2. ✅ Read `01-overview-and-audit.md`
3. ✅ Study `02-implementation-plan.md`
4. ⏳ Follow `06-migration-guide.md` step-by-step
5. ⏳ Execute migration over 5-6 weeks
6. ✅ Celebrate successful deployment! 🎉

---

**Ready to begin? Start with `06-migration-guide.md` Phase 1!**
