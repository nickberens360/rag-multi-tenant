# Code Changes Specification

## Overview

This document provides detailed code examples for all changes required to remove hardcoded references and implement tenant-aware functionality.

---

## New Service: TenantPromptBuilder

### File: `backend/core/tenant_prompt_builder.py`

**Purpose**: Central service for building tenant-aware prompts

```python
"""
Tenant-aware prompt builder service.

This module provides dynamic prompt generation based on tenant configuration,
replacing hardcoded references with tenant-specific customization.
"""

from typing import Dict, Optional
from uuid import UUID
from functools import lru_cache
from datetime import datetime, timedelta
import logging

from backend.models.tenant import Tenant
from backend.db.session import get_db

logger = logging.getLogger(__name__)


class TenantPromptBuilder:
    """
    Builds customized prompts for each tenant.

    Features:
    - Template-based prompt generation
    - Tenant metadata interpolation
    - Caching for performance
    - Fallback to generic defaults
    """

    # Cache TTL (5 minutes)
    CACHE_TTL = timedelta(minutes=5)

    # Template cache (in-memory)
    _tenant_cache: Dict[UUID, tuple[Tenant, datetime]] = {}

    # Default templates
    GENERIC_TEMPLATES = {
        "system": """You are {assistant_name}, an AI assistant for {organization_name}.
You help visitors learn about {organization_name}'s {domain}.

Use the following pieces of context to answer the question. If you don't know the answer
based on the context provided, just say you don't have that information.

Context: {context}

Respond in a {tone} tone. Keep responses concise but informative.""",

        "technical": """You are {assistant_name}, a technical AI assistant for {organization_name}.

You provide detailed, technical information about {organization_name}'s {domain}.

Context: {context}

Provide thorough, technically accurate responses. Include relevant details, code examples
when appropriate, and technical specifications.""",

        "creative": """You are {assistant_name}, showcasing {organization_name}'s creative work.

You help visitors explore and understand {organization_name}'s portfolio, projects, and
creative achievements.

Context: {context}

Describe work in an engaging, {tone} manner while maintaining accuracy.""",

        "simple_response": """Answer the question directly and concisely about {organization_name}.
If the information is in the context, provide it clearly. If not, say you don't have that information.

Context: {context}""",

        "detailed_response": """Provide a comprehensive answer about {organization_name}'s {domain}.
Use all relevant information from the context. Structure your response clearly with:
- Main points
- Supporting details
- Examples when available

Context: {context}""",
    }

    def __init__(self):
        """Initialize the prompt builder."""
        self.db = next(get_db())

    def _get_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Get tenant from cache or database.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant object

        Raises:
            ValueError: If tenant not found
        """
        # Check cache
        if tenant_id in self._tenant_cache:
            tenant, cached_at = self._tenant_cache[tenant_id]
            if datetime.utcnow() - cached_at < self.CACHE_TTL:
                return tenant

        # Fetch from database
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Cache it
        self._tenant_cache[tenant_id] = (tenant, datetime.utcnow())

        return tenant

    def _get_template_variables(self, tenant: Tenant) -> Dict[str, str]:
        """
        Build template variables from tenant metadata.

        Args:
            tenant: Tenant object

        Returns:
            Dictionary of template variables
        """
        return {
            "organization_name": tenant.name,
            "assistant_name": tenant.get_assistant_name(),
            "domain": tenant.domain or "general information",
            "tone": tenant.tone or "professional",
        }

    def build_system_prompt(
        self,
        tenant_id: UUID,
        prompt_type: str = "system",
        **extra_vars
    ) -> str:
        """
        Build tenant-specific system prompt.

        Args:
            tenant_id: Tenant UUID
            prompt_type: Type of prompt (system, technical, creative, etc.)
            **extra_vars: Additional template variables

        Returns:
            Populated system prompt string

        Example:
            >>> builder = TenantPromptBuilder()
            >>> prompt = builder.build_system_prompt(
            ...     tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            ...     prompt_type="system"
            ... )
            >>> print(prompt)
            "You are {Organization} AI Assistant, an AI assistant for Default Organization..."
        """
        tenant = self._get_tenant(tenant_id)

        # Check for custom template
        if tenant.customization_level == "custom" and tenant.system_prompt_template:
            template = tenant.system_prompt_template
            logger.info(f"Using custom prompt template for tenant {tenant.slug}")
        else:
            # Use generic template
            template = self.GENERIC_TEMPLATES.get(prompt_type, self.GENERIC_TEMPLATES["system"])
            logger.debug(f"Using generic '{prompt_type}' template for tenant {tenant.slug}")

        # Build variables
        variables = self._get_template_variables(tenant)
        variables.update(extra_vars)

        # Populate template
        try:
            prompt = template.format(**variables)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            # Fallback to simple template
            prompt = f"You are an AI assistant for {tenant.name}. Context: {{context}}"

        return prompt

    def build_response_guidelines(
        self,
        tenant_id: UUID,
        complexity: str = "simple"
    ) -> str:
        """
        Build response format guidelines based on query complexity.

        Args:
            tenant_id: Tenant UUID
            complexity: Query complexity (simple, moderate, complex)

        Returns:
            Response formatting guidelines
        """
        tenant = self._get_tenant(tenant_id)

        # Apply brand voice if available
        brand_voice = tenant.get_brand_voice()

        guidelines = []

        # Complexity-based guidelines
        if complexity == "simple":
            template_key = "simple_response"
        else:
            template_key = "detailed_response"

        base_guideline = self.GENERIC_TEMPLATES[template_key]
        variables = self._get_template_variables(tenant)

        try:
            base_formatted = base_guideline.format(**variables)
            guidelines.append(base_formatted)
        except KeyError:
            pass

        # Add brand voice guidelines
        if brand_voice.get("style") == "first-person":
            guidelines.append("Use first-person perspective when appropriate.")
        elif brand_voice.get("style") == "third-person":
            guidelines.append("Always use third-person perspective.")

        if brand_voice.get("prefer"):
            prefer_phrases = ", ".join(brand_voice["prefer"][:3])
            guidelines.append(f"Prefer phrases like: {prefer_phrases}")

        if brand_voice.get("avoid"):
            avoid_phrases = ", ".join(brand_voice["avoid"][:3])
            guidelines.append(f"Avoid phrases like: {avoid_phrases}")

        return "\n\n".join(guidelines)

    def get_followup_prompt(self, tenant_id: UUID) -> str:
        """
        Get prompt for generating follow-up questions.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Follow-up question generation prompt
        """
        tenant = self._get_tenant(tenant_id)
        variables = self._get_template_variables(tenant)

        template = """Based on the conversation about {organization_name}, generate 2-3 relevant
follow-up questions that would help the user learn more about {organization_name}'s {domain}.

Questions should be:
- Specific and actionable
- Related to the current topic
- Appropriate for a {tone} conversation"""

        return template.format(**variables)

    @classmethod
    def clear_cache(cls, tenant_id: Optional[UUID] = None):
        """
        Clear prompt cache.

        Args:
            tenant_id: Specific tenant to clear, or None for all
        """
        if tenant_id:
            cls._tenant_cache.pop(tenant_id, None)
        else:
            cls._tenant_cache.clear()


# Singleton instance
_prompt_builder = None


def get_prompt_builder() -> TenantPromptBuilder:
    """Get singleton TenantPromptBuilder instance."""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = TenantPromptBuilder()
    return _prompt_builder
```

---

## Updated: backend/core/llm_chain.py

### Changes Required

**Before**:
```python
DEFAULT_PROMPTS = {
    "system_template": """You are the organization's AI assistant. You help visitors learn
about the organization's professional background, skills, experience, and interests...""",
    # ... more hardcoded prompts
}

def get_default_system_prompt() -> str:
    return DEFAULT_PROMPTS["system_template"]
```

**After**:
```python
from uuid import UUID
from backend.core.tenant_prompt_builder import get_prompt_builder

# Keep generic templates for backward compatibility/fallback
GENERIC_PROMPT_TEMPLATES = {
    "system_template": """You are {assistant_name}, an AI assistant for {organization_name}.
You help visitors learn about {organization_name}'s {domain}.

Use the following pieces of context to answer the question. If you don't know the answer
based on the context provided, just say you don't have that information.

Context: {context}

Respond in a {tone} tone. Keep responses concise but informative.""",

    "technical_template": """You are {assistant_name}, providing technical information about {organization_name}.

You offer detailed, accurate technical guidance about {organization_name}'s {domain}.

Context: {context}

Provide technically accurate responses with relevant details.""",
}


def get_system_prompt(
    tenant_id: UUID,
    prompt_type: str = "system",
    context: str = ""
) -> str:
    """
    Get tenant-specific system prompt.

    Args:
        tenant_id: Tenant UUID
        prompt_type: Type of prompt (system, technical, creative)
        context: RAG context to include

    Returns:
        Customized system prompt
    """
    builder = get_prompt_builder()

    try:
        prompt = builder.build_system_prompt(
            tenant_id=tenant_id,
            prompt_type=prompt_type,
            context=context
        )
        return prompt
    except Exception as e:
        logger.error(f"Error building prompt for tenant {tenant_id}: {e}")
        # Fallback to generic
        return GENERIC_PROMPT_TEMPLATES["system_template"].format(
            assistant_name="AI Assistant",
            organization_name="our organization",
            domain="general information",
            tone="professional",
            context=context
        )


def get_response_guidelines(tenant_id: UUID, complexity: str) -> str:
    """
    Get response formatting guidelines.

    Args:
        tenant_id: Tenant UUID
        complexity: Query complexity (simple, moderate, complex)

    Returns:
        Response guidelines
    """
    builder = get_prompt_builder()
    return builder.build_response_guidelines(tenant_id, complexity)


# Update existing functions to accept tenant_id
def build_chain(tenant_id: UUID, query_type: str = "default"):
    """
    Build LangChain with tenant-specific prompts.

    Args:
        tenant_id: Tenant UUID
        query_type: Type of query (default, technical, creative)

    Returns:
        Configured LangChain
    """
    system_prompt = get_system_prompt(tenant_id, query_type)

    # Rest of chain building logic...
    # (use system_prompt instead of hardcoded prompt)
```

**Lines Changed**:
- Line 86-96: Replace hardcoded prompts with template
- Line 101-196: Update all prompt functions to accept `tenant_id`
- Add import for `TenantPromptBuilder`

---

## Updated: backend/routes/query.py

### Changes Required

**Before**:
```python
@router.post(
    "/query",
    summary="Query Knowledge Base",
    description="""
    **Primary endpoint for querying a tenant's knowledge base using AI.**

    This endpoint processes natural language questions about:
    - Professional experience and skills
    - Projects and work history
    ...
    """,
    response_description="Intelligent response based on the tenant's knowledge base..."
)
async def query_knowledge_base(request: QueryRequest):
    # ... implementation
```

**After**:
```python
@router.post(
    "/query",
    summary="Query Knowledge Base",
    description="""
    **AI-powered knowledge base query endpoint.**

    This endpoint processes natural language questions using advanced
    RAG (Retrieval-Augmented Generation) technology.

    ### Capabilities
    - Semantic search across knowledge base
    - Contextual AI-generated responses
    - Multi-tenant data isolation
    - Streaming responses for real-time interaction

    ### Query Types
    - Professional experience and background
    - Technical expertise and skills
    - Projects and portfolio
    - Documentation and resources

    ### Multi-Tenant
    Each query is processed within the context of the specified tenant,
    ensuring data isolation and customized responses.
    """,
    response_description="AI-generated response based on knowledge base context",
    responses={
        200: {
            "description": "Successful query response",
            "content": {
                "application/json": {
                    "examples": {
                        "simple_query": {
                            "summary": "Simple information query",
                            "value": {
                                "answer": "Based on the knowledge base, the organization specializes in...",
                                "sources": ["document1.md", "document2.md"],
                                "confidence": 0.95
                            }
                        },
                        "technical_query": {
                            "summary": "Technical details query",
                            "value": {
                                "answer": "The technical stack includes: Python, FastAPI, Vue.js...",
                                "sources": ["tech-stack.md"],
                                "confidence": 0.98
                            }
                        }
                    }
                }
            }
        }
    }
)
async def query_knowledge_base(request: QueryRequest):
    """
    Process AI-powered knowledge base query.

    This endpoint:
    1. Routes query to appropriate knowledge sources
    2. Retrieves relevant context via semantic search
    3. Generates AI response using tenant-specific prompts
    4. Returns streaming or complete response

    Args:
        request: Query request with question and tenant_id

    Returns:
        Streaming or JSON response with answer
    """
    # Implementation uses tenant_id for customization
    # ... existing logic, now tenant-aware
```

**Lines Changed**:
- Line 65: Update summary
- Line 66-100: Replace all personal-name-specific documentation
- Update response examples to be generic
- Add multi-tenant documentation

---

## Updated: backend/models/request_models.py

### Changes Required

**Before**:
```python
class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="The user's question or request about the organization's experience, skills, projects, or illustrations",
        examples=[
            "What is the professional background?",
            "Tell me about the organization's experience with Vue.js",
            "Show me some illustrations",
            "What projects have been worked on recently?",
            "What technologies are used for backend development?",
        ]
    )
    tenant_id: UUID = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the background in software engineering?",
                "tenant_id": "00000000-0000-0000-0000-000000000001"
            }
        }
```

**After**:
```python
class QueryRequest(BaseModel):
    """Request model for knowledge base queries."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language question or query",
        examples=[
            "What is the professional background?",
            "Tell me about experience with Vue.js and Python",
            "What projects have been completed recently?",
            "What technologies are used for backend development?",
            "Show me examples of creative work",
            "What services does the organization offer?",
        ]
    )

    tenant_id: UUID = Field(
        ...,
        description="Tenant identifier for multi-tenant data isolation"
    )

    stream: bool = Field(
        default=True,
        description="Whether to stream the response in real-time"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "example_1": {
                        "summary": "Professional query",
                        "value": {
                            "question": "What is the professional background?",
                            "tenant_id": "00000000-0000-0000-0000-000000000001",
                            "stream": True
                        }
                    },
                    "example_2": {
                        "summary": "Technical query",
                        "value": {
                            "question": "What technologies are used?",
                            "tenant_id": "00000000-0000-0000-0000-000000000001",
                            "stream": False
                        }
                    }
                }
            ]
        }
```

**Lines Changed**:
- Line 16: Update field description
- Line 19-23: Replace all example questions
- Line 37: Update example JSON
- Add better documentation

---

## Updated: backend/core/config_v2.py

### Changes Required

**Before**:
```python
APP_TITLE = "Portfolio API"
APP_DESCRIPTION = """
Intelligent API for a portfolio and knowledge base

This API provides AI-powered access to professional experience, skills,
projects, and creative work using advanced RAG (Retrieval-Augmented Generation) technology.

Built with ❤️ using FastAPI, Vue.js, and modern AI technologies.
"""
```

**After**:
```python
import os

# Allow configuration via environment variables
APP_TITLE = os.getenv(
    "APP_TITLE",
    "Multi-Tenant RAG API"
)

APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    """
Multi-Tenant AI-Powered Knowledge Base API

This API provides intelligent access to organizational knowledge using advanced
RAG (Retrieval-Augmented Generation) technology.

## Features

- **Multi-Tenant Architecture**: Complete data isolation per organization
- **AI-Powered Search**: Semantic search with contextual understanding
- **Customizable Assistants**: Each tenant can configure their AI assistant
- **Real-Time Streaming**: Live response generation
- **Comprehensive Analytics**: Query logs, performance metrics, and insights

## Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Astro, Vue.js 3, Vuetify 3
- **AI**: Claude (Anthropic), Gemini (Google)
- **Vector DB**: ChromaDB
- **Database**: PostgreSQL with Row-Level Security (RLS)
- **Cache**: Redis

## Multi-Tenant Support

Each tenant has isolated:
- Knowledge base and documents
- Query logs and analytics
- AI assistant customization
- API keys and settings
- User access control

Built with modern AI and web technologies.
"""
)

# API contact info (configurable per deployment)
API_CONTACT_NAME = os.getenv("API_CONTACT_NAME", "System Administrator")
API_CONTACT_EMAIL = os.getenv("API_CONTACT_EMAIL", "admin@localhost")
API_CONTACT_URL = os.getenv("API_CONTACT_URL", "")
```

**Lines Changed**:
- Line 573: Update APP_TITLE
- Line 575-580: Replace description with generic multi-tenant version
- Add environment variable support for customization

---

## Updated: backend/core/app_factory.py

### Changes Required

**Before**:
```python
app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    version=config.API_VERSION,
    contact={
        "name": "System Administrator",
        "url": "https://example.com",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)
```

**After**:
```python
from backend.core.config_v2 import (
    APP_TITLE,
    APP_DESCRIPTION,
    API_VERSION,
    API_CONTACT_NAME,
    API_CONTACT_EMAIL,
    API_CONTACT_URL,
)

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=API_VERSION,
    contact={
        "name": API_CONTACT_NAME,
        "email": API_CONTACT_EMAIL,
        "url": API_CONTACT_URL,
    } if API_CONTACT_NAME else None,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "query",
            "description": "AI-powered knowledge base queries"
        },
        {
            "name": "admin",
            "description": "Administrative endpoints (authentication required)"
        },
        {
            "name": "tenants",
            "description": "Multi-tenant management"
        }
    ]
)
```

**Lines Changed**:
- Line 67-68: Use config variables instead of hardcoded values
- Add proper imports
- Add OpenAPI tags for better documentation

---

## Updated: backend/core/settings_manifest.py

### Changes Required

**Before**:
```python
{
    "key": "system_name",
    "category": "general",
    "display_name": "System Name",
    "description": "Display name for the AI assistant",
    "value_type": "string",
    "default_value": "AI Assistant",
    "validation": {"min_length": 1, "max_length": 255},
    "tenant_specific": True,
}
```

**After**:
```python
{
    "key": "system_name",
    "category": "general",
    "display_name": "System Name",
    "description": "Display name for the AI assistant (defaults to '{Organization} Assistant')",
    "value_type": "string",
    "default_value": "AI Assistant",
    "validation": {"min_length": 1, "max_length": 255},
    "tenant_specific": True,
    "placeholder": "{organization_name} Assistant",
}
```

**Lines Changed**:
- Line 40: Change default from personalized assistant name to "AI Assistant"
- Add placeholder hint

---

## Updated: backend/core/settings_schemas.py

### Changes Required

**Before**:
```python
class GeneralSettings(BaseModel):
    system_name: str = "AI Assistant"
    # ... other settings
```

**After**:
```python
class GeneralSettings(BaseModel):
    system_name: str = "AI Assistant"
    # ... other settings
```

**Lines Changed**:
- Line 66: Update default value

---

## Integration: backend/core/smart_query_handler.py

### Changes Required

**Before**:
```python
async def process_query(
    question: str,
    tenant_id: UUID,
    # ... other params
):
    # Hardcoded or generic prompt
    system_prompt = get_default_system_prompt()

    # ... rest of logic
```

**After**:
```python
from backend.core.tenant_prompt_builder import get_prompt_builder

async def process_query(
    question: str,
    tenant_id: UUID,
    query_complexity: str = "simple",
    # ... other params
):
    # Get tenant-specific prompt
    prompt_builder = get_prompt_builder()

    # Determine prompt type based on query routing
    prompt_type = "technical" if query_complexity == "complex" else "system"

    # Build prompt with retrieved context
    system_prompt = prompt_builder.build_system_prompt(
        tenant_id=tenant_id,
        prompt_type=prompt_type,
        context=retrieved_context  # From RAG retrieval
    )

    # Get response guidelines
    response_guidelines = prompt_builder.build_response_guidelines(
        tenant_id=tenant_id,
        complexity=query_complexity
    )

    # Include guidelines in prompt if needed
    full_prompt = f"{system_prompt}\n\nResponse Guidelines:\n{response_guidelines}"

    # ... rest of logic using full_prompt
```

---

## Environment Variables (.env)

### New Optional Variables

```bash
# API Metadata (Optional - for custom deployments)
APP_TITLE="Custom RAG API"
APP_DESCRIPTION="Custom description..."
API_CONTACT_NAME="Support Team"
API_CONTACT_EMAIL="support@example.com"
API_CONTACT_URL="https://example.com"

# Default Assistant Settings (Optional)
DEFAULT_ASSISTANT_TONE="professional"
DEFAULT_ASSISTANT_DOMAIN="general"
```

---

## Testing Examples

### Unit Test: Prompt Builder

**File**: `tests/unit/test_tenant_prompt_builder.py`

```python
import pytest
from uuid import UUID
from backend.core.tenant_prompt_builder import TenantPromptBuilder

def test_build_system_prompt_with_defaults():
    """Test prompt building with default tenant config."""
    builder = TenantPromptBuilder()

    # Test tenant (no customization)
    tenant_id = UUID("7be7cf79-e2ad-49c9-aab9-ecda044bda3a")  # test-org

    prompt = builder.build_system_prompt(tenant_id)

    assert "Test Org" in prompt
    assert "AI Assistant" in prompt or "Test Org Assistant" in prompt
    assert "professional" in prompt.lower()
    assert "{context}" in prompt  # Placeholder preserved


def test_build_system_prompt_with_custom_config():
    """Test prompt building with custom tenant config."""
    builder = TenantPromptBuilder()

    # Default tenant (has customization)
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")

    prompt = builder.build_system_prompt(tenant_id)

    assert "Default Organization" in prompt
    assert "AI Assistant" in prompt
    assert "{context}" in prompt


def test_cache_functionality():
    """Test that tenant data is cached."""
    builder = TenantPromptBuilder()
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")

    # First call - fetches from DB
    prompt1 = builder.build_system_prompt(tenant_id)

    # Second call - should use cache
    prompt2 = builder.build_system_prompt(tenant_id)

    assert prompt1 == prompt2

    # Clear cache
    TenantPromptBuilder.clear_cache(tenant_id)

    # Third call - fetches from DB again
    prompt3 = builder.build_system_prompt(tenant_id)

    assert prompt1 == prompt3
```

---

## Summary of Changes

### Files Created (1)
- ✅ `backend/core/tenant_prompt_builder.py` - New service

### Files Modified (7)
- ✅ `backend/core/llm_chain.py` - Replace hardcoded prompts
- ✅ `backend/routes/query.py` - Generic API documentation
- ✅ `backend/models/request_models.py` - Generic examples
- ✅ `backend/core/config_v2.py` - Generic app metadata
- ✅ `backend/core/app_factory.py` - Configurable contact info
- ✅ `backend/core/settings_manifest.py` - Generic defaults
- ✅ `backend/core/settings_schemas.py` - Generic defaults

### Lines of Code
- **New code**: ~350 lines (TenantPromptBuilder)
- **Modified code**: ~150 lines (across 7 files)
- **Removed code**: ~50 lines (hardcoded prompts)
- **Net change**: +450 lines

### Complexity
- **Low risk**: Settings defaults, config variables
- **Medium risk**: Request models, API docs
- **High risk**: LLM prompt chain (requires testing)

---

## Next Steps

1. Review these code examples
2. Implement TenantPromptBuilder service
3. Update each file incrementally
4. Test after each file change
5. See `05-testing-plan.md` for test specifications
