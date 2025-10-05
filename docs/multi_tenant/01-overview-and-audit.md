# Multi-Tenant Hardcoded Reference Remediation Plan

## Executive Summary

**Project**: Remove hardcoded personal-name references from multi-tenant RAG system
**Date**: October 4, 2025
**Status**: Planning Phase
**Priority**: HIGH - Blocks true multi-tenant functionality

---

## Problem Statement

The rag-multi-tenant system contains 33 hardcoded personal-name references across 6 core backend files. These references prevent the system from being truly multi-tenant, as:

1. **AI responses are personalized to a single tenant/person** regardless of which tenant queries
2. **API documentation references a specific person** in examples
3. **System prompts force the AI to act as a specific person's assistant** for all tenants
4. **Configuration metadata is personalized** throughout

### Real-World Impact

When a user from "Acme Corporation" tenant queries the system:

```json
{
  "question": "What is our company's mission?",
  "tenant_id": "b58eccce-2f0d-4901-bae3-5f193ed10d1b"
}
```

**Current Behavior (Broken):**
```
AI Response: "I don't have that information in my knowledge base about the default tenant."
```

**Expected Behavior:**
```
AI Response: "Based on Acme Corporation's knowledge base, your mission is..."
```

---

## Audit Results

### Summary Statistics

- **Total References Found**: 33
- **Files Affected**: 6 core backend files
- **Knowledge Base Files**: Multiple `.md` and `.json` files (acceptable - tenant-specific content)

### Severity Classification

| Severity | Count | Impact |
|----------|-------|--------|
| 🔴 CRITICAL | 17 | Blocks multi-tenant AI functionality |
| 🟡 MEDIUM | 13 | Breaks API documentation and examples |
| 🟢 LOW | 3 | Default settings (minor UX impact) |

---

## Files Affected (Detailed)

### 🔴 CRITICAL SEVERITY

#### 1. `backend/core/llm_chain.py` (8 references)
- **Lines**: 86, 93, 144, 149, 155, 166, 175-191
- **Impact**: System prompts force AI to respond as a specific person's assistant
- **Affected Functions**:
  - `DEFAULT_PROMPTS` dictionary
  - `get_default_system_prompt()`
  - All LLM conversation templates

**Example Issue (before):**
```python
"system_template": """You are the organization's AI assistant. You help visitors learn
about the organization's background, skills, experience, and interests."""
```

#### 2. `backend/routes/query.py` (9 references)
- **Lines**: 65, 69, 78, 82, 89, 90, 91, 97, 99
- **Impact**: API documentation references a specific person exclusively
- **Affected Endpoints**:
  - `POST /api/query` - Primary query endpoint
  - OpenAPI/Swagger documentation
  - Response examples

**Example Issue (before):**
```python
summary="Query Knowledge Base",
description="""
**Primary endpoint for querying a tenant's knowledge base using AI.**
"""
```

---

### 🟡 MEDIUM SEVERITY

#### 3. `backend/models/request_models.py` (7 references)
- **Lines**: 16, 19-23, 37
- **Impact**: All example queries mention a specific person
- **Affected Models**:
  - `QueryRequest` - Main request model
  - Field descriptions and examples

**Example Issue**:
```python
examples=[
    "What is the professional background?",
    "Tell me about the organization's experience with Vue.js",
    "Show me some illustrations",
]
```

#### 4. `backend/core/config_v2.py` (4 references)
- **Lines**: 573, 575, 577, 580
- **Impact**: App metadata is personalized to a specific person
- **Affected Config**:
  - `APP_TITLE`
  - `APP_DESCRIPTION`

**Example Issue**:
```python
APP_TITLE = "Portfolio API"
APP_DESCRIPTION = """
Intelligent API for a Portfolio and Knowledge Base
"""
```

#### 5. `backend/core/app_factory.py` (2 references)
- **Lines**: 67, 68
- **Impact**: OpenAPI contact info and descriptions
- **Affected Sections**:
  - Contact information
  - API description text

---

### 🟢 LOW SEVERITY

#### 6. `backend/core/settings_manifest.py` (1 reference)
- **Line**: 40
- **Impact**: Default assistant name in settings
- **Default Value**: `"AI Assistant"`

#### 7. `backend/core/settings_schemas.py` (1 reference)
- **Line**: 66
- **Impact**: System name default
- **Default Value**: `system_name: str = "AI Assistant"`

---

## Acceptable References (Not Requiring Changes)

### Knowledge Base Content Files
The following files contain tenant-specific content and are **acceptable** as they represent per-tenant knowledge:

- `backend/knowledge/tenants/default/documents/*.md`
- `backend/knowledge/tenants/default/documents/*.json`
- Examples: `about.md`, `projects.json`, `resume.json`

**Rationale**: These are actual content files for the "default" tenant and should remain as-is. Other tenants have their own knowledge base directories.

---

## Impact Analysis

### Current State
```
┌─────────────────────────────────────────────────┐
│          RAG System (Current)                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Any Tenant Query                               │
│         ↓                                       │
│  System Prompt: "You are the organization's assistant..."   │
│         ↓                                       │
│  AI Response: About default tenant              │
│         ↓                                       │
│  ❌ Wrong for other tenants                     │
└─────────────────────────────────────────────────┘
```

### Target State
```
┌─────────────────────────────────────────────────┐
│          RAG System (Target)                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  Tenant Query (tenant_id = "acme")              │
│         ↓                                       │
│  Lookup tenant: Acme Corporation                │
│         ↓                                       │
│  System Prompt: "You are Acme's assistant..."   │
│         ↓                                       │
│  AI Response: About Acme                        │
│         ↓                                       │
│  ✅ Correct for all tenants                     │
└─────────────────────────────────────────────────┘
```

---

## Success Criteria

### Functional Requirements
1. ✅ AI responses are tenant-specific (not personalized to a single tenant)
2. ✅ API documentation is generic or tenant-aware
3. ✅ Example queries are generic
4. ✅ System prompts dynamically populate from tenant metadata
5. ✅ Each tenant can customize their assistant's behavior

### Technical Requirements
1. ✅ No breaking changes to existing API contracts
2. ✅ Backward compatible with current tenants
3. ✅ Database migration successfully adds tenant customization fields
4. ✅ All tests pass after implementation
5. ✅ Default fallbacks exist when tenant customization not provided

### User Experience Requirements
1. ✅ "Default" tenant continues to work as before
2. ✅ New tenants get generic, professional responses
3. ✅ Tenants can customize assistant name, tone, and behavior
4. ✅ No manual configuration required for basic functionality

---

## Risk Assessment

### High Risk
- **LLM Prompt Changes**: Could affect AI response quality if not carefully implemented
- **Database Migration**: Must not fail or corrupt existing tenant data

### Medium Risk
- **API Documentation**: Changes might confuse existing API consumers
- **Testing Coverage**: Need comprehensive tests for tenant-aware behavior

### Low Risk
- **Configuration Updates**: Straightforward changes with clear fallbacks
- **Example Updates**: No runtime impact

### Mitigation Strategies
1. **Comprehensive Testing**: Unit tests for all prompt templates
2. **Gradual Rollout**: Implement critical changes first, test, then continue
3. **Rollback Plan**: Database migration with rollback script
4. **Feature Flag**: Optional tenant customization (can be disabled if issues arise)

---

## Next Steps

1. Review detailed implementation plan (see `02-implementation-plan.md`)
2. Review database schema changes (see `03-database-schema.md`)
3. Review code changes (see `04-code-changes.md`)
4. Approve and begin implementation
5. Execute in phases with testing between each phase

---

## Related Documents

- `02-implementation-plan.md` - Detailed implementation strategy
- `03-database-schema.md` - Database migration specifications
- `04-code-changes.md` - Code change specifications with examples
- `05-testing-plan.md` - Testing strategy and test cases
- `06-migration-guide.md` - Step-by-step migration execution guide
