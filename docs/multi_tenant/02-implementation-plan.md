# Implementation Plan: Multi-Tenant Reference Removal

## Overview

This document outlines the detailed implementation strategy for removing hardcoded personal-name references and implementing true multi-tenant functionality.

---

## Implementation Strategy

### Three-Tier Approach

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1: Database Schema Enhancement                    │
│ - Add tenant customization fields                      │
│ - Create Alembic migration                             │
│ - Add default values for existing tenants              │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ Tier 2: Dynamic Prompt Engine                          │
│ - Create TenantPromptBuilder service                   │
│ - Implement template population at runtime             │
│ - Add caching for performance                          │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ Tier 3: Code Refactoring                               │
│ - Replace all hardcoded prompts                        │
│ - Update API documentation generators                  │
│ - Update example data generators                       │
│ - Add generic fallback defaults                        │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Database Schema Enhancement

### Objectives
- Add tenant customization fields to `tenants` table
- Preserve existing tenant data
- Provide sensible defaults

### Database Migration

**File**: `backend/alembic/versions/YYYYMMDD_add_tenant_customization.py`

**Fields to Add**:

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `assistant_name` | VARCHAR(255) | Yes | NULL | Custom AI assistant name |
| `system_prompt_template` | TEXT | Yes | NULL | Custom system prompt override |
| `tone` | VARCHAR(100) | Yes | 'professional' | Response tone (friendly, professional, technical) |
| `domain` | VARCHAR(255) | Yes | 'general' | Domain/industry focus |
| `brand_voice` | TEXT | Yes | NULL | Brand voice guidelines (JSON) |

**Migration Steps**:
1. Add new columns to `tenants` table
2. Populate default tenant with its existing brand values (preserve existing behavior)
3. Set generic defaults for other tenants
4. Create indexes if needed

### Default Values Strategy

```python
# Default tenant — preserve existing behavior
DEFAULT_TENANT_VALUES = {
    "assistant_name": "Default Organization AI Assistant",
    "tone": "friendly",
    "domain": "software engineering and design",
    "brand_voice": json.dumps({
        "style": "first-person",
        "personality": "friendly, professional, approachable"
    })
}

# Generic tenant defaults
GENERIC_TENANT_VALUES = {
    "assistant_name": "{organization_name} AI Assistant",
    "tone": "professional",
    "domain": "general",
    "brand_voice": None
}
```

---

## Phase 2: Dynamic Prompt Engine

### Objectives
- Create reusable prompt builder service
- Support template variables
- Implement caching for performance
- Provide fallback mechanisms

### New Service: TenantPromptBuilder

**File**: `backend/core/tenant_prompt_builder.py`

#### Architecture

```
┌─────────────────────────────────────────────────┐
│        TenantPromptBuilder Service              │
├─────────────────────────────────────────────────┤
│                                                 │
│  Input: tenant_id, prompt_type                  │
│         ↓                                       │
│  1. Fetch tenant from cache/DB                  │
│         ↓                                       │
│  2. Get template for prompt_type                │
│         ↓                                       │
│  3. Populate template variables                 │
│         ↓                                       │
│  4. Return customized prompt                    │
│         ↓                                       │
│  Cache result for 5 minutes                     │
└─────────────────────────────────────────────────┘
```

#### Core Functionality

```python
class TenantPromptBuilder:
    """
    Builds tenant-aware prompts by combining:
    1. Tenant metadata (name, domain, tone)
    2. Prompt templates (generic, customizable)
    3. Runtime variables (context, question)
    """

    def build_system_prompt(
        self,
        tenant_id: UUID,
        prompt_type: str = "default"
    ) -> str:
        """
        Build tenant-specific system prompt.

        Args:
            tenant_id: Tenant UUID
            prompt_type: Type of prompt (default, technical, creative)

        Returns:
            Populated system prompt string
        """
        pass

    def build_response_template(
        self,
        tenant_id: UUID,
        complexity: str
    ) -> str:
        """Build response guidelines based on complexity."""
        pass
```

#### Template Variables

Available variables for all prompt templates:

| Variable | Source | Example |
|----------|--------|---------|
| `{organization_name}` | tenant.name | "Acme Corporation" |
| `{assistant_name}` | tenant.assistant_name | "Acme AI Assistant" |
| `{domain}` | tenant.domain | "enterprise software" |
| `{tone}` | tenant.tone | "professional" |
| `{brand_voice}` | tenant.brand_voice | Custom guidelines |

#### Prompt Templates

**Generic System Prompt Template**:
```python
GENERIC_SYSTEM_TEMPLATE = """You are {assistant_name}, an AI assistant for {organization_name}.
You help visitors learn about {organization_name}'s {domain}.

Use the following pieces of context to answer the question. If you don't know the answer
based on the context provided, just say you don't have that information.

Context: {context}

Respond in a {tone} tone. Keep responses concise but informative."""
```

**Technical Query Template**:
```python
TECHNICAL_SYSTEM_TEMPLATE = """You are {assistant_name}, a technical AI assistant for {organization_name}.

You provide detailed, technical information about {organization_name}'s {domain}.

Context: {context}

Provide thorough, technically accurate responses. Include relevant details, code examples
when appropriate, and technical specifications."""
```

**Creative/Portfolio Template**:
```python
CREATIVE_SYSTEM_TEMPLATE = """You are {assistant_name}, showcasing {organization_name}'s creative work.

You help visitors explore and understand {organization_name}'s portfolio, projects, and creative achievements.

Context: {context}

Describe work in an engaging, {tone} manner while maintaining accuracy."""
```

#### Caching Strategy

```python
from functools import lru_cache
from datetime import timedelta

class TenantPromptBuilder:
    _cache_ttl = timedelta(minutes=5)
    _tenant_cache: Dict[UUID, TenantConfig] = {}

    @lru_cache(maxsize=100)
    def _get_tenant_config(self, tenant_id: UUID) -> TenantConfig:
        """Cached tenant config lookup."""
        # Check memory cache first
        if tenant_id in self._tenant_cache:
            if not self._is_cache_expired(tenant_id):
                return self._tenant_cache[tenant_id]

        # Fetch from DB
        tenant = self._fetch_tenant_from_db(tenant_id)
        self._tenant_cache[tenant_id] = tenant
        return tenant
```

---

## Phase 3: Code Refactoring

### File-by-File Refactoring Plan

#### 🔴 Critical: backend/core/llm_chain.py

**Current State**:
```python
DEFAULT_PROMPTS = {
    "system_template": """You are the organization's AI assistant...""",
    # ... more hardcoded prompts
}

def get_default_system_prompt() -> str:
    return DEFAULT_PROMPTS["system_template"]
```

**Target State**:
```python
from backend.core.tenant_prompt_builder import TenantPromptBuilder

# Generic templates (no hardcoded names)
DEFAULT_PROMPT_TEMPLATES = {
    "system_template": """You are {assistant_name}, an AI assistant for {organization_name}.
You help visitors learn about {organization_name}'s {domain}...""",
    "technical_template": """You are {assistant_name}, providing technical information about {organization_name}...""",
}

def get_system_prompt(tenant_id: UUID, prompt_type: str = "default") -> str:
    """Get tenant-specific system prompt."""
    builder = TenantPromptBuilder()
    return builder.build_system_prompt(tenant_id, prompt_type)

def get_response_template(tenant_id: UUID, complexity: str) -> str:
    """Get tenant-specific response guidelines."""
    builder = TenantPromptBuilder()
    return builder.build_response_template(tenant_id, complexity)
```

**Changes Required**:
- Replace 8 hardcoded prompts with template variables
- Update `get_default_system_prompt()` to accept `tenant_id`
- Update all calls to pass `tenant_id` parameter
- Add fallback for when tenant customization not available

---

#### 🔴 Critical: backend/routes/query.py

**Current State**:
```python
@router.post(
    "/query",
    summary="Query Knowledge Base",
    description="""
    **Primary endpoint for querying a tenant's knowledge base using AI.**
    """
)
```

**Target State** (Option 1 - Generic):
```python
@router.post(
    "/query",
    summary="Query Knowledge Base",
    description="""
    **Primary endpoint for querying the AI-powered knowledge base.**

    This endpoint processes natural language questions about:
    - Professional experience and skills
    - Projects and work history
    - Technical expertise and capabilities
    - Portfolio and creative work
    """
)
```

**Target State** (Option 2 - Dynamic):
```python
def generate_api_description(tenant_id: Optional[UUID] = None) -> str:
    """Generate tenant-aware API description."""
    if tenant_id:
        tenant = get_tenant(tenant_id)
        return f"""
        **Query {tenant.name}'s AI-powered knowledge base.**

        Ask questions about {tenant.name}'s {tenant.domain}.
        """
    return "**Query the AI-powered knowledge base.**"

# Use in route definition
@router.post("/query", description=generate_api_description())
```

**Changes Required**:
- Remove 9 personal-name-specific references
- Update endpoint descriptions to be generic
- Update example responses to be generic
- Consider tenant-aware OpenAPI spec generation (advanced)

---

#### 🟡 Medium: backend/models/request_models.py

**Current State**:
```python
class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="The user's question about the organization's experience...",
        examples=[
            "What is the professional background?",
            "Tell me about the organization's experience with Vue.js",
        ]
    )
```

**Target State**:
```python
class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="The user's question or query",
        examples=[
            "What is the professional background?",
            "Tell me about experience with Vue.js",
            "What projects have been completed recently?",
            "What technologies are used for backend development?",
        ]
    )
    tenant_id: UUID = Field(
        ...,
        description="Tenant identifier for multi-tenant isolation"
    )
```

**Changes Required**:
- Remove 7 personal-name-specific references
- Make examples generic
- Update field descriptions

---

#### 🟡 Medium: backend/core/config_v2.py

**Current State**:
```python
APP_TITLE = "Portfolio API"
APP_DESCRIPTION = """
Intelligent API for a Portfolio and Knowledge Base
"""
```

**Target State** (Option 1 - Generic):
```python
APP_TITLE = "RAG Multi-Tenant API"
APP_DESCRIPTION = """
Multi-Tenant AI-Powered Knowledge Base API

This API provides intelligent access to organizational knowledge using advanced
RAG (Retrieval-Augmented Generation) technology.

Features:
- Multi-tenant isolation and security
- AI-powered semantic search
- Customizable AI assistants per tenant
- Real-time streaming responses

Built with FastAPI, Vue.js, and modern AI technologies.
"""
```

**Target State** (Option 2 - Environment Variable):
```python
APP_TITLE = os.getenv("APP_TITLE", "RAG Multi-Tenant API")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", DEFAULT_DESCRIPTION)
```

**Changes Required**:
- Update 4 hardcoded references
- Make app metadata generic or configurable
- Update contact info to be generic

---

#### 🟡 Medium: backend/core/app_factory.py

**Current State**:
```python
contact={
    "name": "System Administrator",
    "url": "https://nickberens.me",
},
description="AI endpoints for the knowledge base"
```

**Target State**:
```python
contact={
    "name": os.getenv("API_CONTACT_NAME", "System Administrator"),
    "url": os.getenv("API_CONTACT_URL", ""),
    "email": os.getenv("API_CONTACT_EMAIL", "admin@localhost"),
},
description="Multi-tenant AI-powered knowledge base API"
```

**Changes Required**:
- Remove 2 hardcoded references
- Use environment variables for contact info
- Update description to be generic

---

#### 🟢 Low: backend/core/settings_manifest.py

**Current State**:
```python
default_value="AI Assistant"
```

**Target State**:
```python
default_value="AI Assistant"  # Generic default
```

**Changes Required**:
- Update 1 default value to be generic

---

#### 🟢 Low: backend/core/settings_schemas.py

**Current State**:
```python
system_name: str = "AI Assistant"
```

**Target State**:
```python
system_name: str = "AI Assistant"
```

**Changes Required**:
- Update 1 default value to be generic

---

## Phase 4: Integration and Testing

### Integration Points

#### 1. Query Handler Integration

**File**: `backend/core/smart_query_handler.py`

**Before**:
```python
def process_query(question: str, tenant_id: UUID):
    system_prompt = get_default_system_prompt()
    # ... rest of logic
```

**After**:
```python
def process_query(question: str, tenant_id: UUID):
    system_prompt = get_system_prompt(tenant_id)
    # ... rest of logic
```

#### 2. Settings Manager Integration

**File**: `backend/core/settings_manager.py`

Add methods to manage tenant customization:

```python
def get_tenant_assistant_settings(self, tenant_id: UUID) -> dict:
    """Get assistant configuration for tenant."""
    return {
        "assistant_name": self.get_setting("assistant_name", tenant_id),
        "tone": self.get_setting("tone", tenant_id),
        "domain": self.get_setting("domain", tenant_id),
    }

def update_tenant_assistant_settings(self, tenant_id: UUID, settings: dict):
    """Update assistant configuration for tenant."""
    for key, value in settings.items():
        self.update_setting(key, value, tenant_id)
```

#### 3. Admin Dashboard Integration

Add UI for tenant customization in admin dashboard:

**New Admin View**: `admin/frontend/src/views/settings/AssistantSettings.vue`

Features:
- Edit assistant name
- Choose tone (friendly, professional, technical)
- Set domain/industry
- Preview AI responses with current settings

---

## Implementation Order

### Recommended Sequence

1. ✅ **Week 1: Database Foundation**
   - Day 1-2: Create Alembic migration
   - Day 2-3: Test migration on dev database
   - Day 3-4: Populate default values
   - Day 4-5: Add database tests

2. ✅ **Week 2: Prompt Engine**
   - Day 1-3: Build TenantPromptBuilder service
   - Day 3-4: Add template system
   - Day 4-5: Implement caching
   - Day 5: Integration tests

3. ✅ **Week 3: Critical Refactoring**
   - Day 1-2: Refactor llm_chain.py
   - Day 3-4: Refactor query.py
   - Day 5: Integration testing

4. ✅ **Week 4: Medium Priority Refactoring**
   - Day 1: Refactor request_models.py
   - Day 2: Refactor config_v2.py
   - Day 3: Refactor app_factory.py
   - Day 4-5: Settings refactoring

5. ✅ **Week 5: Admin UI and Final Testing**
   - Day 1-3: Build admin UI for customization
   - Day 4-5: End-to-end testing
   - Day 5: Documentation

---

## Rollback Strategy

### Database Rollback

```bash
# If migration fails or causes issues
alembic downgrade -1
```

### Code Rollback

```bash
# Revert to previous commit
git revert <commit-hash>

# Or use feature flag
ENABLE_TENANT_CUSTOMIZATION=false
```

### Emergency Fallback

If tenant customization breaks functionality:

```python
# In TenantPromptBuilder
EMERGENCY_FALLBACK = True  # Force use of generic defaults

if EMERGENCY_FALLBACK or tenant.custom_prompt is None:
    return DEFAULT_GENERIC_PROMPT
```

---

## Performance Considerations

### Caching Strategy

1. **Tenant Config Cache**: 5-minute TTL, LRU cache size 100
2. **Prompt Cache**: 10-minute TTL, per-tenant
3. **Template Cache**: Indefinite (templates don't change at runtime)

### Expected Performance Impact

| Operation | Before | After | Change |
|-----------|--------|-------|--------|
| Query processing | 100ms | 102ms | +2% (negligible) |
| Prompt generation | 1ms | 3ms | +2ms (cached) |
| Database queries | 5ms | 6ms | +1ms (join) |

**Conclusion**: Performance impact is minimal due to aggressive caching.

---

## Success Metrics

### Before Implementation
- ❌ 33 hardcoded personal-name references
- ❌ All tenants get single-tenant-specific responses
- ❌ No tenant customization possible

### After Implementation
- ✅ 0 hardcoded references in code
- ✅ Each tenant gets personalized responses
- ✅ Tenants can customize assistant behavior
- ✅ Generic defaults for new tenants
- ✅ Backward compatible with existing tenants

---

## Next Documents

- See `03-database-schema.md` for detailed database schema changes
- See `04-code-changes.md` for detailed code examples and patterns
- See `05-testing-plan.md` for comprehensive test strategy
- See `06-migration-guide.md` for step-by-step execution
