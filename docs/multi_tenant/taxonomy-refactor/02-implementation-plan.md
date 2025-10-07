# Implementation Plan: Taxonomy System Refactor

## Document Purpose

This document provides a **phase-by-phase implementation guide** optimized for agent-driven development. Each phase includes:
- Specific files to modify
- Exact code changes with before/after examples
- Validation criteria
- Rollback procedures

---

## Phase 1: Remove Hardcoded Defaults + Template System

**Goal**: Stop auto-seeding taxonomy; add optional template bootstrap
**Duration**: 1 week
**Risk Level**: LOW (additive changes, no deletions)

---

### Task 1.1: Create Taxonomy Templates Module

**File**: `backend/core/taxonomy_templates.py` (NEW)

**Action**: CREATE

**Code**:
```python
"""
Taxonomy template library for tenant onboarding.

Provides industry-specific category sets that tenants can optionally use
to bootstrap their taxonomy instead of hardcoded defaults.
"""

from typing import Dict, List, TypedDict


class TaxonomyEntryTemplate(TypedDict):
    """Template for a single taxonomy entry."""
    key: str
    label: str
    synonyms: List[str]
    description: str


# Template definitions
SOFTWARE_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "documentation",
        "label": "Technical Documentation",
        "synonyms": ["docs", "api", "reference", "guide", "manual"],
        "description": "API docs, technical guides, and reference materials"
    },
    {
        "key": "tutorial",
        "label": "Tutorials & How-Tos",
        "synonyms": ["how-to", "guide", "walkthrough", "example"],
        "description": "Step-by-step tutorials and learning resources"
    },
    {
        "key": "code",
        "label": "Source Code",
        "synonyms": ["implementation", "snippet", "sample", "library"],
        "description": "Code samples, libraries, and implementations"
    },
    {
        "key": "changelog",
        "label": "Release Notes",
        "synonyms": ["release", "version", "update", "changelog"],
        "description": "Version history and release notes"
    },
]

LEGAL_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "contract",
        "label": "Contracts & Agreements",
        "synonyms": ["agreement", "terms", "msa", "nda"],
        "description": "Legal contracts and binding agreements"
    },
    {
        "key": "compliance",
        "label": "Compliance Documents",
        "synonyms": ["policy", "regulation", "compliance", "gdpr"],
        "description": "Regulatory compliance and policy documents"
    },
    {
        "key": "case-law",
        "label": "Case Law & Briefs",
        "synonyms": ["precedent", "ruling", "brief", "litigation"],
        "description": "Legal precedents and case briefs"
    },
    {
        "key": "memorandum",
        "label": "Legal Memos",
        "synonyms": ["memo", "opinion", "analysis"],
        "description": "Internal legal analyses and memos"
    },
]

MEDICAL_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "clinical-notes",
        "label": "Clinical Notes",
        "synonyms": ["patient", "diagnosis", "treatment", "exam"],
        "description": "Patient clinical notes and examination records"
    },
    {
        "key": "research",
        "label": "Research & Studies",
        "synonyms": ["study", "trial", "research", "paper"],
        "description": "Medical research papers and clinical trials"
    },
    {
        "key": "protocol",
        "label": "Treatment Protocols",
        "synonyms": ["procedure", "guideline", "standard", "protocol"],
        "description": "Standard treatment protocols and procedures"
    },
    {
        "key": "administrative",
        "label": "Administrative",
        "synonyms": ["admin", "billing", "insurance", "scheduling"],
        "description": "Administrative and operational documents"
    },
]

MARKETING_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "campaign",
        "label": "Campaign Materials",
        "synonyms": ["campaign", "ad", "promotion", "marketing"],
        "description": "Marketing campaigns and promotional materials"
    },
    {
        "key": "content",
        "label": "Content Marketing",
        "synonyms": ["blog", "article", "whitepaper", "ebook"],
        "description": "Blog posts, articles, and educational content"
    },
    {
        "key": "brand",
        "label": "Brand Assets",
        "synonyms": ["logo", "brand", "guidelines", "identity"],
        "description": "Brand guidelines and visual assets"
    },
    {
        "key": "analytics",
        "label": "Analytics & Reports",
        "synonyms": ["report", "metrics", "analytics", "performance"],
        "description": "Marketing analytics and performance reports"
    },
]

# Empty template for custom start
EMPTY_TEMPLATE: List[TaxonomyEntryTemplate] = []

# Template registry
TEMPLATES: Dict[str, List[TaxonomyEntryTemplate]] = {
    "software": SOFTWARE_TEMPLATE,
    "legal": LEGAL_TEMPLATE,
    "medical": MEDICAL_TEMPLATE,
    "marketing": MARKETING_TEMPLATE,
    "empty": EMPTY_TEMPLATE,
}


def get_template(template_key: str) -> List[TaxonomyEntryTemplate]:
    """
    Get a taxonomy template by key.

    Args:
        template_key: Template identifier (software, legal, medical, marketing, empty)

    Returns:
        List of taxonomy entry templates

    Raises:
        KeyError: If template_key is not found
    """
    if template_key not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"Template '{template_key}' not found. Available: {available}")

    return TEMPLATES[template_key]


def list_templates() -> Dict[str, Dict[str, str]]:
    """
    List all available templates with metadata.

    Returns:
        Dictionary mapping template keys to metadata
    """
    return {
        "software": {
            "name": "Software Documentation",
            "description": "For tech companies, developer tools, and SaaS products",
            "category_count": len(SOFTWARE_TEMPLATE),
        },
        "legal": {
            "name": "Legal Documents",
            "description": "For law firms and legal departments",
            "category_count": len(LEGAL_TEMPLATE),
        },
        "medical": {
            "name": "Medical & Healthcare",
            "description": "For hospitals, clinics, and healthcare providers",
            "category_count": len(MEDICAL_TEMPLATE),
        },
        "marketing": {
            "name": "Marketing & Content",
            "description": "For marketing teams and content creators",
            "category_count": len(MARKETING_TEMPLATE),
        },
        "empty": {
            "name": "Start from Scratch",
            "description": "Begin with an empty taxonomy (advanced users)",
            "category_count": 0,
        },
    }
```

**Validation**:
```python
# Test in Python REPL
from backend.core.taxonomy_templates import get_template, list_templates

assert len(get_template("software")) == 4
assert get_template("empty") == []
assert "software" in list_templates()
```

---

### Task 1.2: Add Bootstrap Endpoint

**File**: `backend/routes/taxonomy.py`

**Action**: MODIFY (add new endpoint)

**Location**: After line 366 (after existing endpoints)

**Code to Add**:
```python
@router.post("/taxonomy/bootstrap")
async def bootstrap_taxonomy(
    template_key: str = Query(..., description="Template to use: software, legal, medical, marketing, or empty"),
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """
    Bootstrap tenant taxonomy from a template.

    This is typically called during tenant onboarding. It creates initial
    taxonomy entries based on an industry-specific template.

    Args:
        template_key: Template identifier
        tenant_context: Tenant context from middleware

    Returns:
        Dictionary with created entries count
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")

    try:
        # Import template module
        from backend.core.taxonomy_templates import get_template

        # Get template
        try:
            template_entries = get_template(template_key)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if tenant already has taxonomy entries
        with get_db_session_sync() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            existing = session.execute(
                text("SELECT COUNT(*) FROM tenant_taxonomy WHERE tenant_id = :tid"),
                {"tid": tenant_id}
            ).scalar()

            if existing > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tenant already has {existing} taxonomy entries. Bootstrap is for new tenants only."
                )

        # Create entries from template
        created_count = 0
        for entry in template_entries:
            try:
                # Use existing create_taxonomy_entry logic
                create_req = TaxonomyCreateRequest(
                    key=entry["key"],
                    label=entry["label"],
                    synonyms=entry.get("synonyms", []),
                    active=True,
                )
                # Reuse the existing create logic (defined earlier in this file)
                await create_taxonomy_entry(create_req, tenant_context)
                created_count += 1
            except HTTPException:
                # Skip duplicates
                continue

        logger.info(f"Bootstrapped taxonomy for tenant {tenant_id} with template '{template_key}': {created_count} entries")

        return {
            "template": template_key,
            "entries_created": created_count,
            "tenant_id": str(tenant_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bootstrap taxonomy for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to bootstrap taxonomy")


@router.get("/taxonomy/templates")
async def list_taxonomy_templates() -> Dict[str, Any]:
    """
    List available taxonomy templates for bootstrapping.

    Returns:
        Dictionary of available templates with metadata
    """
    try:
        from backend.core.taxonomy_templates import list_templates
        return {"templates": list_templates()}
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list templates")
```

**Validation**:
```bash
# Test bootstrap endpoint
curl -X POST "http://localhost:8001/acme/api/admin/taxonomy/bootstrap?template_key=software"

# Expected response:
{
  "template": "software",
  "entries_created": 4,
  "tenant_id": "b58eccce-2f0d-4901-bae3-5f193ed10d1b"
}

# Test template list
curl "http://localhost:8001/acme/api/admin/taxonomy/templates"
```

---

### Task 1.3: Remove Migration Seeding

**File**: `backend/db/versions/20251005_070529_add_document_metadata.py`

**Action**: MODIFY (comment out seeding, keep table creation)

**Location**: Lines 210-249

**Before**:
```python
    # Insert default taxonomy entries for the default tenant
    # These will be visible across all tenants as a starting point
    op.execute(
        sa.text(
            """
            INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms)
            SELECT
                id as tenant_id,
                'technical' as key,
                'Technical Documentation' as label,
                '["documentation", "docs", "guide", "reference"]'::jsonb as synonyms
            FROM tenants
            WHERE slug = 'default'
            UNION ALL
            ...
            """
        )
    )
```

**After**:
```python
    # NOTE: Taxonomy seeding removed in favor of optional template bootstrap
    # New tenants should use POST /api/admin/taxonomy/bootstrap to populate taxonomy
    # from industry-specific templates (software, legal, medical, marketing, or empty).
    #
    # Existing tenants with taxonomy already seeded are unaffected.
    # See: docs/multi_tenant/taxonomy-refactor/02-implementation-plan.md

    # LEGACY SEEDING (DISABLED):
    # The following INSERT was removed to allow flexible tenant-specific taxonomies.
    # If you need to re-enable for development, uncomment the block below.

    # op.execute(
    #     sa.text(
    #         """
    #         INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms)
    #         SELECT id, 'technical', 'Technical Documentation', '["docs"]'::jsonb
    #         FROM tenants WHERE slug = 'default';
    #         """
    #     )
    # )
```

**Validation**:
```bash
# Run migration on a TEST database first
alembic upgrade head

# Verify tenant_taxonomy table exists but is empty for new tenants
psql -d app_db -c "SELECT * FROM tenant_taxonomy WHERE tenant_id = (SELECT id FROM tenants WHERE slug='new-tenant');"
# Should return 0 rows
```

---

### Task 1.4: Remove Hardcoded Fallback in Inference

**File**: `backend/core/metadata_inference.py`

**Action**: MODIFY (remove fallback defaults)

**Location**: Lines 134-142

**Before**:
```python
        # Load tenant taxonomy
        taxonomy = self.get_tenant_taxonomy(tenant_id)
        if not taxonomy:
            logger.warning(f"No taxonomy found for tenant {tenant_id}, using defaults")
            taxonomy = {
                "technical": {"label": "Technical Documentation", "synonyms": ["docs", "documentation"]},
                "experience": {"label": "Experience & Projects", "synonyms": ["portfolio", "work"]},
                "creative": {"label": "Creative Content", "synonyms": ["blog", "writing"]},
                "personal": {"label": "Personal Information", "synonyms": ["bio", "about"]},
            }
```

**After**:
```python
        # Load tenant taxonomy
        taxonomy = self.get_tenant_taxonomy(tenant_id)
        if not taxonomy:
            logger.warning(
                f"No taxonomy found for tenant {tenant_id}. "
                "Tenant should bootstrap taxonomy via POST /api/admin/taxonomy/bootstrap. "
                "Skipping metadata inference."
            )
            # Return empty inference instead of forcing hardcoded categories
            return None, [], 0.0
```

**Validation**:
```python
# Test with tenant that has no taxonomy
service = MetadataInferenceService()
content_type, tags, confidence = service.infer_metadata(
    path="test.md",
    tenant_id="<tenant-with-no-taxonomy>",
    content_sample="Sample content"
)

assert content_type is None
assert tags == []
assert confidence == 0.0
```

---

### Task 1.5: Add Onboarding Flag to Tenants Table

**File**: `backend/db/versions/NEW_add_taxonomy_bootstrapped_flag.py` (NEW MIGRATION)

**Action**: CREATE

**Code**:
```python
"""Add taxonomy_bootstrapped flag to track onboarding status

Revision ID: add_taxonomy_bootstrapped_flag
Revises: add_document_metadata
Create Date: 2025-10-05
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_taxonomy_bootstrapped_flag"
down_revision = "add_document_metadata"
branch_labels = None
depends_on = None


def upgrade():
    """Add taxonomy_bootstrapped column to tenants table"""

    # Add column to track if tenant has completed taxonomy setup
    op.add_column(
        "tenants",
        sa.Column(
            "taxonomy_bootstrapped",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )

    # Mark existing tenants with taxonomy as bootstrapped
    op.execute(
        sa.text(
            """
            UPDATE tenants
            SET taxonomy_bootstrapped = true
            WHERE id IN (
                SELECT DISTINCT tenant_id FROM tenant_taxonomy
            );
            """
        )
    )


def downgrade():
    """Remove taxonomy_bootstrapped column"""
    op.drop_column("tenants", "taxonomy_bootstrapped")
```

**Validation**:
```bash
# Run migration
alembic upgrade head

# Check column exists
psql -d app_db -c "\d tenants" | grep taxonomy_bootstrapped
```

---

### Phase 1 Completion Checklist

- [ ] `taxonomy_templates.py` module created with 5 templates
- [ ] `/taxonomy/bootstrap` endpoint added and tested
- [ ] `/taxonomy/templates` endpoint added and tested
- [ ] Migration seeding removed (commented with explanation)
- [ ] Inference fallback removed
- [ ] `taxonomy_bootstrapped` flag added to tenants table
- [ ] All existing tenants marked as `taxonomy_bootstrapped=true`
- [ ] New tenant can bootstrap with `POST /taxonomy/bootstrap?template_key=software`
- [ ] Empty template works (`template_key=empty`)
- [ ] Documentation updated

**Success Criteria**:
```bash
# Test 1: New tenant with software template
curl -X POST "http://localhost:8001/new-tenant/api/admin/taxonomy/bootstrap?template_key=software"
# Should return: entries_created=4

# Test 2: Existing tenant (should fail)
curl -X POST "http://localhost:8001/default/api/admin/taxonomy/bootstrap?template_key=software"
# Should return: 400 "Tenant already has N taxonomy entries"

# Test 3: List templates
curl "http://localhost:8001/acme/api/admin/taxonomy/templates"
# Should return: 5 templates (software, legal, medical, marketing, empty)
```

---

## Phase 2: Consolidate Taxonomy Systems

**Goal**: Merge query routing taxonomy into `tenant_taxonomy`
**Duration**: 1 week
**Risk Level**: MEDIUM (affects search routing)

### Task 2.1: Add Regex Column to tenant_taxonomy

**File**: `backend/db/versions/NEW_add_taxonomy_regex.py` (NEW MIGRATION)

**Action**: CREATE

**Code**:
```python
"""Add regex patterns to tenant_taxonomy for query routing

Revision ID: add_taxonomy_regex
Revises: add_taxonomy_bootstrapped_flag
Create Date: 2025-10-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "add_taxonomy_regex"
down_revision = "add_taxonomy_bootstrapped_flag"
branch_labels = None
depends_on = None


def upgrade():
    """Add regex column for query pattern matching"""

    # Add regex patterns column (JSONB array of regex strings)
    op.add_column(
        "tenant_taxonomy",
        sa.Column(
            "regex",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Regex patterns for query routing (e.g., ['\\\\bproject\\\\b', '\\\\bbuilt\\\\b'])",
        ),
    )

    # Add user_created flag for folksonomy tracking (Phase 3)
    op.add_column(
        "tenant_taxonomy",
        sa.Column(
            "user_created",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="True if created by user (folksonomy), false if official taxonomy",
        ),
    )

    # Add usage_count for analytics (Phase 3)
    op.add_column(
        "tenant_taxonomy",
        sa.Column(
            "usage_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Number of documents tagged with this category",
        ),
    )


def downgrade():
    """Remove added columns"""
    op.drop_column("tenant_taxonomy", "usage_count")
    op.drop_column("tenant_taxonomy", "user_created")
    op.drop_column("tenant_taxonomy", "regex")
```

**Validation**:
```bash
alembic upgrade head
psql -d app_db -c "\d tenant_taxonomy" | grep regex
```

---

### Task 2.2: Migrate Legacy Taxonomy Data

**File**: `backend/db/versions/NEW_migrate_legacy_taxonomy.py` (NEW MIGRATION)

**Action**: CREATE (data migration)

**Code**:
```python
"""Migrate data from admin_settings.taxonomy_settings to tenant_taxonomy

Revision ID: migrate_legacy_taxonomy
Revises: add_taxonomy_regex
Create Date: 2025-10-05
"""

import json
from alembic import op
from sqlalchemy import text

revision = "migrate_legacy_taxonomy"
down_revision = "add_taxonomy_regex"
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate legacy taxonomy from admin_settings to tenant_taxonomy.

    This consolidates the dual taxonomy system into a single source of truth.
    """

    conn = op.get_bind()

    # Read legacy taxonomy from admin_settings
    result = conn.execute(
        text(
            """
            SELECT tenant_id, setting_value
            FROM admin_settings
            WHERE setting_key = 'taxonomy_settings'
            """
        )
    )

    for row in result:
        tenant_id = row[0]
        taxonomy_json = row[1]

        try:
            taxonomy_data = json.loads(taxonomy_json)
            categories = taxonomy_data.get("categories", {})

            for category_key, category_data in categories.items():
                synonyms = category_data.get("synonyms", [])
                regex_patterns = category_data.get("regex", [])

                # Check if entry already exists in tenant_taxonomy
                existing = conn.execute(
                    text(
                        """
                        SELECT key FROM tenant_taxonomy
                        WHERE tenant_id = :tid AND key = :key
                        """
                    ),
                    {"tid": tenant_id, "key": category_key}
                ).fetchone()

                if existing:
                    # Update existing entry with regex patterns
                    conn.execute(
                        text(
                            """
                            UPDATE tenant_taxonomy
                            SET regex = :regex::jsonb,
                                synonyms = :synonyms::jsonb
                            WHERE tenant_id = :tid AND key = :key
                            """
                        ),
                        {
                            "tid": tenant_id,
                            "key": category_key,
                            "regex": json.dumps(regex_patterns),
                            "synonyms": json.dumps(synonyms),
                        }
                    )
                else:
                    # Insert new entry
                    conn.execute(
                        text(
                            """
                            INSERT INTO tenant_taxonomy
                              (tenant_id, key, label, synonyms, regex, active)
                            VALUES
                              (:tid, :key, :label, :synonyms::jsonb, :regex::jsonb, true)
                            """
                        ),
                        {
                            "tid": tenant_id,
                            "key": category_key,
                            "label": category_key.replace("_", " ").title(),
                            "synonyms": json.dumps(synonyms),
                            "regex": json.dumps(regex_patterns),
                        }
                    )

        except json.JSONDecodeError:
            # Skip invalid JSON
            continue


def downgrade():
    """
    Reverting this migration doesn't restore admin_settings entries.
    The data remains in tenant_taxonomy with regex patterns.
    """
    pass
```

---

### Task 2.3: Update Content Router to Use Unified Taxonomy

**File**: `backend/core/content_router.py`

**Action**: MODIFY (replace taxonomy_loader with database query)

**Search for**: `from .taxonomy_loader import get_topic_taxonomy`

**Replace entire function** that uses `get_topic_taxonomy()` with:

```python
def get_tenant_taxonomy(tenant_id: str) -> Dict[str, Dict]:
    """
    Load taxonomy from tenant_taxonomy table (unified source).

    Replaces legacy taxonomy_loader.get_topic_taxonomy() with database query.

    Args:
        tenant_id: Tenant UUID

    Returns:
        Dictionary mapping category keys to {synonyms, regex} data
    """
    from .db_session import get_db_session_sync
    from sqlalchemy import text

    taxonomy = {}

    try:
        with get_db_session_sync() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})

            rows = session.execute(
                text(
                    """
                    SELECT key, label, synonyms, regex
                    FROM tenant_taxonomy
                    WHERE tenant_id = :tid AND active = true
                    """
                ),
                {"tid": tenant_id}
            ).fetchall()

            for row in rows:
                taxonomy[row[0]] = {
                    "label": row[1],
                    "synonyms": row[2] if row[2] else [],
                    "regex": row[3] if row[3] else [],
                }

    except Exception as e:
        logger.error(f"Failed to load taxonomy for tenant {tenant_id}: {e}")

    return taxonomy
```

**Then update all calls**:

**Before**:
```python
taxonomy = get_topic_taxonomy()
```

**After**:
```python
taxonomy = get_tenant_taxonomy(tenant_id)
```

---

### Phase 2 Completion Checklist

- [ ] Regex column added to `tenant_taxonomy`
- [ ] User_created and usage_count columns added
- [ ] Legacy taxonomy data migrated
- [ ] `content_router.py` updated to use unified taxonomy
- [ ] `taxonomy_loader.py` deprecated (add deprecation comment)
- [ ] Query routing works with database taxonomy
- [ ] All tests pass

---

## Phase 3: Folksonomy Support

**Duration**: 2 weeks
**Risk Level**: LOW (new features, no breaking changes)

See `05-ui-changes.md` for frontend implementation details.

### Backend Tasks (Summary)

1. Tag autocomplete endpoint
2. Tag analytics endpoint
3. Tag promotion endpoint
4. Usage tracking (increment usage_count on document save)
5. Typo detection (fuzzy matching)

---

## Phase 4: Templates & Polish

**Duration**: 1 week
**Risk Level**: LOW

### Tasks

1. Add more templates (education, finance, manufacturing)
2. Build onboarding wizard UI
3. Tag suggestion ML model
4. Performance optimization

---

## Rollback Procedures

### Phase 1 Rollback

```bash
# If bootstrap fails, restore migration seeding:
# 1. Uncomment lines 210-249 in 20251005_070529_add_document_metadata.py
# 2. Run migration again on affected tenants

# If tenant has broken taxonomy:
DELETE FROM tenant_taxonomy WHERE tenant_id = '<affected-tenant-id>';
# Then re-run bootstrap
```

### Phase 2 Rollback

```bash
# Revert to file-based taxonomy:
# 1. Restore taxonomy_loader.get_topic_taxonomy() calls in content_router.py
# 2. Keep database taxonomy for document metadata (dual system)
```

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Hardcoded categories | 4 (all tenants) | 0 (template-based) |
| Taxonomy systems | 2 | 1 |
| New tenant onboarding | 0 clicks (auto) | 2 clicks (template select) |
| Customization flexibility | Low | High |

---

**Next Document**: `03-database-schema.md` (detailed schema changes)
