# Taxonomy System Refactor Documentation

## Overview

This directory contains the complete implementation plan for refactoring the RAG system's taxonomy architecture from hardcoded defaults to a flexible, hybrid controlled vocabulary + folksonomy approach.

---

## Problem Statement (TL;DR)

The current system has:
- ❌ **4 hardcoded categories** (technical, creative, experience, personal) forced on all tenants
- ❌ **Two separate taxonomy systems** that must be manually synced
- ❌ **No user-created tags** (folksonomy) support
- ❌ **No onboarding templates** for industry-specific vocabularies

This blocks multi-tenant flexibility and violates industry best practices.

---

## Solution (TL;DR)

Implement a **4-phase refactor**:

1. **Remove hardcoded defaults** → Optional template bootstrap
2. **Consolidate taxonomies** → Single source of truth in `tenant_taxonomy`
3. **Add folksonomy** → User-created tags + promotion workflow
4. **Polish UX** → Onboarding wizard, tag analytics, typo detection

Result: Flexible, tenant-specific taxonomies that evolve naturally from usage.

---

## Document Structure

| Document | Purpose | Audience |
|----------|---------|----------|
| `01-overview-and-audit.md` | Problem analysis, impact assessment, success criteria | **Product/Architecture** |
| `02-implementation-plan.md` | Detailed phase-by-phase tasks with code examples | **Code Agents/Developers** |
| `03-database-schema.md` *(TODO)* | Schema changes, migrations, data model | **Database/Backend** |
| `04-api-changes.md` *(TODO)* | New endpoints, request/response models | **API/Backend** |
| `05-ui-changes.md` *(TODO)* | Frontend components, user flows | **Frontend** |
| `06-testing-strategy.md` *(TODO)* | Test cases, validation procedures | **QA** |
| `07-migration-guide.md` *(TODO)* | Step-by-step execution guide | **DevOps** |

---

## Quick Start (For Agents)

### 1. Read the Overview
```bash
cat 01-overview-and-audit.md
```
**Why**: Understand the problem, risks, and success criteria

### 2. Review Implementation Plan
```bash
cat 02-implementation-plan.md
```
**Why**: Get specific file changes and validation steps

### 3. Execute Phase 1 (Quick Win)
- Create `backend/core/taxonomy_templates.py`
- Add bootstrap endpoint to `backend/routes/taxonomy.py`
- Comment out migration seeding
- Test with new tenant

### 4. Validate Phase 1
```bash
# Should return 5 templates
curl "http://localhost:8001/acme/api/admin/taxonomy/templates"

# Should create 4 categories
curl -X POST "http://localhost:8001/new-tenant/api/admin/taxonomy/bootstrap?template_key=software"
```

### 5. Continue to Phase 2
See `02-implementation-plan.md` Phase 2 section

---

## Key Decisions

### Why Remove Hardcoded Defaults?

**Current**: All tenants get `{technical, creative, experience, personal}`
**Problem**: Doesn't fit legal firms, hospitals, manufacturers, etc.
**Solution**: Optional templates (software, legal, medical, marketing, empty)

### Why Consolidate Two Taxonomies?

**Current**:
- `tenant_taxonomy` (document metadata)
- `admin_settings.taxonomy_settings` (query routing)

**Problem**: Duplication, sync burden, confusion
**Solution**: Merge into `tenant_taxonomy` with regex column for routing

### Why Add Folksonomy?

**Current**: Only admins can create categories
**Problem**: Can't innovate, no natural evolution
**Solution**: User-created tags with promotion workflow (like SharePoint, Confluence)

---

## Implementation Timeline

```
Week 1: Phase 1 - Remove Hardcoded Defaults
├─ Day 1-2: Templates module + bootstrap endpoint
├─ Day 3: Migration changes
├─ Day 4-5: Testing + validation
└─ Week 1 Complete: New tenants use templates ✅

Week 2: Phase 2 - Consolidate Taxonomies
├─ Day 1-2: Database migrations (regex column + data migration)
├─ Day 3-4: Update content_router.py
├─ Day 5: Testing + validation
└─ Week 2 Complete: Single taxonomy system ✅

Week 3-4: Phase 3 - Folksonomy Support
├─ Week 3: Backend (tag autocomplete, analytics, promotion)
├─ Week 4: Frontend (UI components, workflows)
└─ Week 4 Complete: User-created tags working ✅

Week 5: Phase 4 - Polish
├─ Day 1-2: Onboarding wizard UI
├─ Day 3: Tag suggestions ML
├─ Day 4-5: Performance optimization
└─ Week 5 Complete: Production-ready ✅
```

---

## Success Criteria

### Functional

- [ ] No hardcoded category defaults
- [ ] Single unified taxonomy system
- [ ] User-created tags supported
- [ ] Tag promotion workflow exists
- [ ] Onboarding template system works
- [ ] Tag analytics dashboard available

### Technical

- [ ] All tests pass
- [ ] No breaking API changes
- [ ] Performance <100ms for tag autocomplete
- [ ] Database migration reversible

### UX

- [ ] New tenant completes onboarding in <3 minutes
- [ ] Tag autocomplete shows existing tags
- [ ] Admin can promote user tags to official taxonomy
- [ ] Visual distinction between official and user-created tags

---

## Research & References

This refactor is based on industry best practices from:

- **Microsoft SharePoint**: Managed Metadata + Enterprise Keywords (hybrid approach)
- **Confluence**: Controlled labels + user tags
- **Notion**: Database properties + tag suggestions
- **BBC**: Social tagging promoted to formal taxonomy

### Academic Sources

- _"Taxonomies and controlled vocabularies best practices"_ (Springer, Journal of DAM)
- _"Know Your RAG: Dataset Taxonomy and Generation Strategies"_ (arXiv 2024)
- _"Taxonomy 101: Best Practices"_ (Nielsen Norman Group)

---

## FAQ

### Q: Will this break existing tenants?

**A**: No. Existing tenants with taxonomy already seeded are marked as `taxonomy_bootstrapped=true` and remain unchanged.

### Q: What if a tenant doesn't want templates?

**A**: They can use `template_key=empty` to start with an empty taxonomy.

### Q: Can tenants edit template categories after bootstrap?

**A**: Yes. Templates are just starting points. All categories are editable via `/taxonomy` endpoints.

### Q: What happens to the legacy `topic_taxonomy.json` file?

**A**: It remains as a fallback for backward compatibility but is deprecated. Phase 2 migrates all data to the database.

### Q: How does folksonomy prevent tag spam?

**A**: Usage thresholds, admin review UI, and promotion workflow ensure quality. Tags used only once are flagged as "orphans" for review.

---

## Status Tracking

| Phase | Status | Completion Date |
|-------|--------|-----------------|
| Phase 1: Remove Defaults | 🟡 Planned | TBD |
| Phase 2: Consolidate | 🟡 Planned | TBD |
| Phase 3: Folksonomy | 🟡 Planned | TBD |
| Phase 4: Polish | 🟡 Planned | TBD |

Legend: 🟡 Planned | 🔵 In Progress | 🟢 Complete | 🔴 Blocked

---

## Contact & Feedback

For questions about this refactor:
- **Architecture Review**: See `01-overview-and-audit.md`
- **Implementation Details**: See `02-implementation-plan.md`
- **Code Agent Instructions**: Each task in `02-implementation-plan.md` has validation steps

---

**Last Updated**: 2025-10-05
**Document Version**: 1.0
**Status**: Planning Complete, Ready for Implementation
