# Database Schema Changes

## Overview

This document details the database schema modifications required to support tenant customization and remove hardcoded references.

---

## Current Schema

### Existing `tenants` Table

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Current Fields**:
- `id` - UUID primary key
- `slug` - URL-friendly identifier
- `name` - Display name
- `created_at` - Timestamp
- `is_active` - Soft delete flag

---

## Proposed Schema Changes

### New Fields for `tenants` Table

```sql
ALTER TABLE tenants
ADD COLUMN assistant_name VARCHAR(255),
ADD COLUMN system_prompt_template TEXT,
ADD COLUMN tone VARCHAR(100) DEFAULT 'professional',
ADD COLUMN domain VARCHAR(255) DEFAULT 'general',
ADD COLUMN brand_voice JSONB,
ADD COLUMN api_metadata JSONB,
ADD COLUMN customization_level VARCHAR(50) DEFAULT 'basic',
ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
```

### Field Specifications

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `assistant_name` | VARCHAR(255) | Yes | NULL | - | Custom AI assistant display name |
| `system_prompt_template` | TEXT | Yes | NULL | - | Custom system prompt override (advanced) |
| `tone` | VARCHAR(100) | No | 'professional' | CHECK (tone IN ('friendly', 'professional', 'technical', 'casual')) | Response tone preference |
| `domain` | VARCHAR(255) | No | 'general' | - | Business domain/industry |
| `brand_voice` | JSONB | Yes | NULL | Valid JSON | Brand voice guidelines (structured) |
| `api_metadata` | JSONB | Yes | NULL | Valid JSON | API-specific metadata (contact info, etc.) |
| `customization_level` | VARCHAR(50) | No | 'basic' | CHECK (level IN ('basic', 'advanced', 'custom')) | Customization tier |
| `updated_at` | TIMESTAMP TZ | No | NOW() | - | Last modification timestamp |

---

## Field Descriptions

### 1. `assistant_name`

**Purpose**: Custom name for the AI assistant

**Examples**:
```sql
-- Default tenant
assistant_name = 'Default Organization AI Assistant'

-- Acme Corporation tenant
assistant_name = 'Acme Knowledge Bot'

-- Generic tenant (NULL uses default)
assistant_name = NULL  -- Falls back to "{organization_name} Assistant"
```

**Validation**:
- Max length: 255 characters
- Nullable (uses default template if NULL)
- No special characters except spaces, apostrophes

### 2. `system_prompt_template`

**Purpose**: Complete custom system prompt override (advanced users)

**Examples**:
```sql
-- Custom prompt for law firm
system_prompt_template = 'You are a legal AI assistant for {organization_name}.
Provide accurate legal information based on the context. Always include disclaimers
that this is not legal advice. Context: {context}'

-- NULL uses default template
system_prompt_template = NULL
```

**Validation**:
- Must contain `{context}` placeholder
- Can contain any tenant variables: `{organization_name}`, `{domain}`, etc.
- Nullable (uses default if NULL)

**Security Consideration**:
- Sanitize to prevent prompt injection
- Validate template variables
- Maximum length: 10,000 characters

### 3. `tone`

**Purpose**: Response style preference

**Allowed Values**:
- `friendly` - Warm, approachable, conversational
- `professional` - Business-appropriate, formal
- `technical` - Detailed, precise, technical jargon acceptable
- `casual` - Relaxed, informal

**Default**: `professional`

**Examples**:
```sql
-- Tech startup
tone = 'friendly'

-- Enterprise B2B
tone = 'professional'

-- Developer documentation
tone = 'technical'
```

### 4. `domain`

**Purpose**: Business domain/industry context

**Examples**:
```sql
domain = 'software engineering and design'
domain = 'enterprise SaaS solutions'
domain = 'legal services'
domain = 'healthcare technology'
domain = 'general'  -- Default
```

**Validation**:
- Max length: 255 characters
- Lowercase recommended
- Used in prompt: "You help visitors learn about {organization_name}'s {domain}"

### 5. `brand_voice`

**Purpose**: Structured brand voice guidelines (JSON)

**Schema**:
```json
{
  "style": "first-person|third-person|mixed",
  "personality": ["adjective1", "adjective2"],
  "avoid": ["phrase1", "phrase2"],
  "prefer": ["phrase1", "phrase2"],
  "dos": ["guideline1"],
  "donts": ["guideline1"]
}
```

**Examples**:

**Default tenant**:
```json
{
  "style": "first-person",
  "personality": ["friendly", "professional", "approachable"],
  "prefer": ["I have experience in", "My background includes"],
  "avoid": ["We think", "In our opinion"]
}
```

**Enterprise tenant**:
```json
{
  "style": "third-person",
  "personality": ["authoritative", "trustworthy", "expert"],
  "prefer": ["Our organization", "We specialize in"],
  "avoid": ["I think", "Maybe"]
}
```

**Validation**:
- Valid JSON
- Max size: 5KB
- Optional fields

### 6. `api_metadata`

**Purpose**: API-specific configuration (contact info, etc.)

**Schema**:
```json
{
  "contact": {
    "name": "string",
    "email": "string",
    "url": "string"
  },
  "title": "string",
  "description": "string",
  "version": "string"
}
```

**Example**:
```json
{
  "contact": {
    "name": "Acme Support",
    "email": "support@acme.com",
    "url": "https://acme.com"
  },
  "title": "Acme Knowledge Base API",
  "description": "AI-powered access to Acme's knowledge"
}
```

### 7. `customization_level`

**Purpose**: Tenant customization tier/complexity

**Allowed Values**:
- `basic` - Uses name, tone, domain only (simple)
- `advanced` - Uses brand_voice and api_metadata (moderate)
- `custom` - Uses custom system_prompt_template (advanced)

**Default**: `basic`

**Usage**:
```python
if tenant.customization_level == 'custom' and tenant.system_prompt_template:
    # Use custom template
    prompt = tenant.system_prompt_template
elif tenant.customization_level == 'advanced':
    # Use advanced template with brand voice
    prompt = build_advanced_prompt(tenant)
else:
    # Use basic template
    prompt = build_basic_prompt(tenant)
```

---

## Alembic Migration

### Migration File

**Filename**: `backend/alembic/versions/20251004_add_tenant_customization.py`

```python
"""Add tenant customization fields

Revision ID: 20251004_add_tenant_customization
Revises: <previous_revision>
Create Date: 2025-10-04 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers
revision = '20251004_add_tenant_customization'
down_revision = '<previous_revision>'  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Add tenant customization fields"""

    # Add new columns
    op.add_column('tenants', sa.Column('assistant_name', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('system_prompt_template', sa.Text(), nullable=True))
    op.add_column('tenants', sa.Column('tone', sa.String(100), nullable=False, server_default='professional'))
    op.add_column('tenants', sa.Column('domain', sa.String(255), nullable=False, server_default='general'))
    op.add_column('tenants', sa.Column('brand_voice', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tenants', sa.Column('api_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tenants', sa.Column('customization_level', sa.String(50), nullable=False, server_default='basic'))
    op.add_column('tenants', sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                                       nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

    # Add check constraints
    op.create_check_constraint(
        'tenants_tone_check',
        'tenants',
        "tone IN ('friendly', 'professional', 'technical', 'casual')"
    )

    op.create_check_constraint(
        'tenants_customization_level_check',
        'tenants',
        "customization_level IN ('basic', 'advanced', 'custom')"
    )

    # Create trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_tenants_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_update_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW
        EXECUTE FUNCTION update_tenants_updated_at();
    """)

    # Populate default tenant with existing behavior
    op.execute("""
        UPDATE tenants
        SET
            assistant_name = 'Default Organization AI Assistant',
            tone = 'friendly',
            domain = 'software engineering and design',
            brand_voice = '{"style": "first-person", "personality": ["friendly", "professional", "approachable"]}',
            api_metadata = '{"contact": {"name": "System Administrator", "email": "admin@example.com", "url": "https://example.com"}}',
            customization_level = 'advanced'
        WHERE slug = 'default';
    """)

    # Set generic defaults for other tenants
    op.execute("""
        UPDATE tenants
        SET
            tone = 'professional',
            domain = 'general',
            customization_level = 'basic'
        WHERE slug != 'default' AND assistant_name IS NULL;
    """)


def downgrade():
    """Remove tenant customization fields"""

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trigger_update_tenants_updated_at ON tenants;")
    op.execute("DROP FUNCTION IF EXISTS update_tenants_updated_at();")

    # Drop check constraints
    op.drop_constraint('tenants_tone_check', 'tenants')
    op.drop_constraint('tenants_customization_level_check', 'tenants')

    # Drop columns
    op.drop_column('tenants', 'updated_at')
    op.drop_column('tenants', 'customization_level')
    op.drop_column('tenants', 'api_metadata')
    op.drop_column('tenants', 'brand_voice')
    op.drop_column('tenants', 'domain')
    op.drop_column('tenants', 'tone')
    op.drop_column('tenants', 'system_prompt_template')
    op.drop_column('tenants', 'assistant_name')
```

---

## Data Migration Examples

### Before Migration

```sql
SELECT id, slug, name FROM tenants;
```

Output:
```
id                                   | slug     | name
-------------------------------------|----------|----------------------
00000000-0000-0000-0000-000000000001 | default  | Default Organization
7be7cf79-e2ad-49c9-aab9-ecda044bda3a | test-org | Test Org
b58eccce-2f0d-4901-bae3-5f193ed10d1b | acme     | Acme
```

### After Migration

```sql
SELECT id, slug, name, assistant_name, tone, domain, customization_level
FROM tenants;
```

Output:
```
id                | slug     | name      | assistant_name           | tone         | domain                  | level
------------------|----------|-----------|--------------------------|--------------|-------------------------|----------
00000000...000001 | default  | Default   | Default Organization AI Assistant | friendly     | software engineering... | advanced
7be7cf79...bda3a | test-org | Test Org  | NULL                     | professional | general                 | basic
b58eccce...10d1b | acme     | Acme      | NULL                     | professional | general                 | basic
```

---

## SQLAlchemy Model Updates

### Updated Tenant Model

**File**: `backend/models/tenant.py`

```python
from sqlalchemy import Column, String, Boolean, TIMESTAMP, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

class Tenant(Base):
    __tablename__ = "tenants"

    # Existing fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # New customization fields
    assistant_name = Column(String(255), nullable=True)
    system_prompt_template = Column(Text, nullable=True)
    tone = Column(
        String(100),
        nullable=False,
        server_default='professional'
    )
    domain = Column(
        String(255),
        nullable=False,
        server_default='general'
    )
    brand_voice = Column(JSONB, nullable=True)
    api_metadata = Column(JSONB, nullable=True)
    customization_level = Column(
        String(50),
        nullable=False,
        server_default='basic'
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "tone IN ('friendly', 'professional', 'technical', 'casual')",
            name='tenants_tone_check'
        ),
        CheckConstraint(
            "customization_level IN ('basic', 'advanced', 'custom')",
            name='tenants_customization_level_check'
        ),
    )

    def get_assistant_name(self) -> str:
        """Get assistant name with fallback to default."""
        return self.assistant_name or f"{self.name} Assistant"

    def get_brand_voice(self) -> dict:
        """Get brand voice guidelines with defaults."""
        default_voice = {
            "style": "third-person",
            "personality": ["professional", "helpful"],
            "prefer": [],
            "avoid": []
        }
        return self.brand_voice or default_voice

    def get_api_contact(self) -> dict:
        """Get API contact metadata with defaults."""
        if self.api_metadata and 'contact' in self.api_metadata:
            return self.api_metadata['contact']
        return {
            "name": "System Administrator",
            "email": "admin@localhost",
            "url": ""
        }
```

---

## Pydantic Schema Updates

### Updated Tenant Schemas

**File**: `backend/models/tenant_schemas.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class TenantBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    assistant_name: Optional[str] = Field(None, max_length=255)
    tone: str = Field('professional', regex='^(friendly|professional|technical|casual)$')
    domain: str = Field('general', max_length=255)
    brand_voice: Optional[Dict[str, Any]] = None
    api_metadata: Optional[Dict[str, Any]] = None
    customization_level: str = Field('basic', regex='^(basic|advanced|custom)$')

    @validator('brand_voice')
    def validate_brand_voice(cls, v):
        if v is not None:
            required_fields = ['style', 'personality']
            if not all(field in v for field in required_fields):
                raise ValueError(f'brand_voice must contain: {required_fields}')
        return v


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    pass


class TenantUpdate(BaseModel):
    """Schema for updating tenant (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    assistant_name: Optional[str] = Field(None, max_length=255)
    tone: Optional[str] = Field(None, regex='^(friendly|professional|technical|casual)$')
    domain: Optional[str] = Field(None, max_length=255)
    brand_voice: Optional[Dict[str, Any]] = None
    api_metadata: Optional[Dict[str, Any]] = None
    customization_level: Optional[str] = Field(None, regex='^(basic|advanced|custom)$')
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    """Schema for tenant responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
```

---

## Migration Execution Plan

### Step-by-Step Execution

1. **Pre-Migration Checks**
```bash
# Backup database
pg_dump -h localhost -p 5433 -U postgres app_db > backup_pre_customization.sql

# Check current revision
alembic current

# Verify no pending changes
alembic check
```

2. **Run Migration**
```bash
# Apply migration
alembic upgrade head

# Verify success
alembic current
```

3. **Post-Migration Validation**
```sql
-- Verify columns added
\d tenants

-- Verify data populated
SELECT slug, assistant_name, tone, domain FROM tenants;

-- Verify constraints
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'tenants';

-- Verify trigger
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'tenants';
```

4. **Rollback Plan**
```bash
# If issues occur
alembic downgrade -1

# Restore from backup if needed
psql -h localhost -p 5433 -U postgres app_db < backup_pre_customization.sql
```

---

## Index Recommendations

### Suggested Indexes

```sql
-- Index on tone for filtering tenants by tone
CREATE INDEX idx_tenants_tone ON tenants(tone) WHERE is_active = TRUE;

-- Index on customization_level for admin queries
CREATE INDEX idx_tenants_customization_level ON tenants(customization_level);

-- Composite index for active tenants
CREATE INDEX idx_tenants_active_updated ON tenants(is_active, updated_at DESC);

-- GIN index on JSONB columns for searching
CREATE INDEX idx_tenants_brand_voice_gin ON tenants USING GIN (brand_voice);
CREATE INDEX idx_tenants_api_metadata_gin ON tenants USING GIN (api_metadata);
```

**Rationale**:
- Filtering by tone: Common in admin UI
- Customization level: Used in prompt builder logic
- Active + updated: For dashboard "recently updated" queries
- JSONB indexes: For querying nested brand_voice properties

---

## Testing Checklist

### Database Tests

- [ ] Migration runs successfully
- [ ] All columns created with correct types
- [ ] Check constraints enforced
- [ ] Default values populated
- [ ] Trigger updates `updated_at`
- [ ] NULL values handled correctly
- [ ] JSONB validation works
- [ ] Downgrade migration works
- [ ] Data integrity maintained
- [ ] Foreign key constraints still valid

---

## Next Steps

1. Review this schema design
2. Create Alembic migration file
3. Test on development database
4. See `04-code-changes.md` for code implementation
5. See `05-testing-plan.md` for test specifications
