# Document Metadata: User-Defined With LLM Fallback (Multi‑Tenant)

**Implementation Status**: ✅ COMPLETE (All Phases Implemented)

Goal
- Allow admins to set document‑level metadata (e.g., content type, tags) at upload and edit time.
- When metadata is omitted, infer it asynchronously with an LLM and mark provenance as "inferred" with confidence.
- Ensure tenant isolation, auditable overrides, and retrieval that treats manual metadata as authoritative and inferred as hints.

Principles
- Manual > inferred: user input always wins; inference never overwrites manual fields.
- Tenant‑scoped vocabulary: categories/tags are configured per tenant (controlled vocabulary; optional synonyms).
- Asynchronous inference: uploads remain fast; inference runs in background with progress.
- Provenance + confidence: every field carries who/what/when and confidence where applicable.
- Safe retrieval use: inferred metadata is a soft signal (re‑rank), not a hard filter, unless explicitly requested.

Scope (MVP)
- Content type (single select) and optional tags (multi‑select), per file/source.
- UI support in upload dialog and source editor.
- Backend endpoints to accept manual metadata and to retrieve/update it.
- Background LLM inference when nothing is provided.

Out of scope (future)
- Per‑chunk overrides (inherit doc‑level by default; can be added later).
- Complex hierarchies or nested taxonomies.
- Cross‑tenant vocabularies or global governance.

Architecture Overview
- DB: Extend knowledge metadata to store manual vs inferred fields and provenance.
- API:
  - Upload accepts optional `metadata` (content_type, tags[]).
  - Edit/update source metadata endpoint (manual overrides).
  - Background task queues inference for missing items; stores inferred + confidence.
  - Read endpoints return `effective_*` (manual if present else inferred) and `provenance`.
- UI:
  - Upload dialog: pick content type/tags; optional "Suggest tags" toggle displays suggestions once available.
  - Sources/SourcesView: show chips with provenance indicators; allow edit.
  - DocumentsView: display effective metadata + provenance.
- Retrieval:
  - Continue to index documents as today; propagate effective metadata to chunk metadata on reindex.
  - Manual labels can be used as filters; inferred used for scoring bias (no hard exclusion by default).

Data Model (proposed additions)
- Table: `knowledge_files` (existing) — add columns:
  - `manual_content_type` TEXT NULL
  - `manual_tags` JSONB NULL DEFAULT '[]'
  - `inferred_content_type` TEXT NULL
  - `inferred_tags` JSONB NULL DEFAULT '[]'
  - `inferred_confidence` REAL NULL
  - `metadata_provenance` TEXT NOT NULL DEFAULT 'inferred'  -- enum: 'manual' | 'inferred' | 'mixed'
  - `metadata_updated_by` UUID NULL
  - `metadata_updated_at` TIMESTAMPTZ NULL
  - `metadata_version` INT NOT NULL DEFAULT 1
  - Computed effective fields are produced in API responses; storage remains normalized.
- Table: `tenant_taxonomy` (new)
  - `tenant_id` UUID, `key` TEXT, `label` TEXT, `synonyms` JSONB[], `active` BOOL, unique(tenant_id,key)

API Changes (high level)
- POST `/api/admin/knowledge/uploads`: accepts optional multipart form fields:
  - `metadata[content_type]`, `metadata[tags]` (CSV or JSON)
  - If absent, queue inference job.
- PUT `/api/admin/knowledge/sources/{source_path}`: accepts `{ manual_content_type?, manual_tags? }`.
- GET `/api/admin/knowledge/sources`: returns `effective_content_type`, `effective_tags`, and `provenance`.
- POST `/api/admin/knowledge/metadata/infer`: admin trigger to (re)infer batches (dry‑run supported).
- GET/PUT `/api/admin/settings/taxonomy`: manage tenant vocabulary.

Inference Pipeline
- Trigger: upload without metadata (or manual clear) queues background task.
- Worker: reads file content (first N KB + summary), calls LLM, maps to tenant vocabulary; stores `inferred_*` + `confidence`.
- Propagation: on successful inference or manual update, mark file for reindex to stamp chunk metadata with effective values.

Retrieval Semantics
- `effective_*` = manual if present else inferred.
- Manual labels: eligible for strict filter.
- Inferred labels: default to soft reranking; strict filter only when caller opts in (e.g., query param `filter_source=content_type:technical:strict`).

Security & Isolation
- All CRUD is tenant‑scoped via RLS and middleware; taxonomy is per‑tenant.
- Audit: store `metadata_updated_by` and log to audit trail on manual edits.

Rollout Plan (Early Dev — Always On)
1) Add DB migrations.
2) Implement backend endpoints + background tasks.
3) Add UI fields (always visible in upload and edit flows).
4) Backfill inference for existing files (job + progress).
5) Validate accuracy/latency with seed data; iterate taxonomy/prompt as needed.

Risks & Mitigations
- Mis‑tags harm recall → inferred used as soft signal; manual overrides win.
- Tenant vocab drift → make taxonomy manageable in admin with simple analytics.
- Upload latency → inference is async; queue with status API.

Testing Strategy
- Unit: precedence (manual > inferred), mapping to allowed set, RBAC.
- Integration: tenant isolation, upload+infer flow, reindex propagation, retrieval behavior.
- E2E: upload with/without metadata; edit; verify chips + search behavior.

See `document_metadata_tasks.yaml` for machine‑readable steps.

## Implementation Progress (Phase 1 - Backend Complete)

### ✅ Completed Tasks

**dm_schema**: Database Schema Migration
- Created Alembic migration: `backend/db/versions/20251005_070529_add_document_metadata.py`
- Added metadata columns to `knowledge_files` table:
  - `manual_content_type`, `manual_tags` for user-defined metadata
  - `inferred_content_type`, `inferred_tags`, `inferred_confidence` for LLM-inferred metadata
  - `metadata_provenance`, `metadata_updated_by`, `metadata_updated_at`, `metadata_version` for tracking
- Created `tenant_taxonomy` table for controlled vocabulary with RLS
- Inserted default taxonomy entries for the default tenant

**dm_backend_endpoints**: Backend API Endpoints
- Created `backend/core/metadata_inference.py` - LLM-based metadata inference service
- Created `backend/routes/taxonomy.py` - Tenant taxonomy CRUD endpoints
- Modified `backend/routes/knowledge_uploads.py` to accept optional metadata on upload
- Modified `backend/routes/knowledge.py` to support manual metadata updates and batch inference
- Added methods to `backend/core/knowledge_index_db.py`:
  - `get_file_metadata()` - Returns effective metadata (manual > inferred)
  - `list_files_with_metadata()` - Lists files with metadata fields
- Registered taxonomy routes in `backend/core/app_factory.py`

**dm_inference_worker**: Background Inference Implementation
- Implemented `infer_metadata_background()` background task function
- Integrated with FastAPI BackgroundTasks in upload flow
- Automatic inference trigger when metadata not provided on upload
- LLM-based inference using Claude Haiku (configurable via METADATA_INFERENCE_MODEL env)

**dm_propagation**: Metadata Propagation to Chunks
- Implemented metadata propagation in `backend/core/unified_retriever.py`
- Effective metadata stamped on chunks during indexing
- Files marked for reindex when manual metadata changes

**dm_frontend_upload**: Upload UI Enhancement
- Upload dialog accepts metadata fields
- Metadata sent with file upload requests
- Real-time feedback on metadata validation

**dm_frontend_edit**: Source Editor Enhancement
- Source editor shows current metadata
- Edit dialog allows metadata updates
- Provenance indicators displayed

**dm_retrieval_policy**: Retrieval Semantics
- Filter parsing for metadata queries
- Strict vs. soft filtering modes
- Natural language metadata detection

**dm_audit_telemetry**: Audit and Metrics
- Comprehensive audit logging for metadata operations
- Metrics endpoint for inference coverage and accuracy
- User activity tracking

**dm_docs_tests**: Documentation and Tests ✅
- Comprehensive integration tests (14 tests)
- End-to-end workflow tests (9 tests)
- API reference documentation
- User guide and troubleshooting

---

## User Guide

### How to Use Document Metadata

#### 1. Uploading Files with Metadata

**Via Admin UI (Recommended):**
1. Navigate to Admin Dashboard → Knowledge → Upload
2. Select your file(s)
3. Choose content type from dropdown (e.g., "Technical Documentation", "Creative Content")
4. Add tags using the tag input field (comma-separated or multi-select)
5. Click "Upload"

The metadata you provide will be marked as "manual" and will take precedence over any AI-inferred metadata.

**Via API:**
```bash
curl -X POST "http://localhost:8000/admin/api/knowledge/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "metadata[content_type]=technical" \
  -F "metadata[tags]=python,tutorial,beginner"
```

**Without Metadata (Auto-Inference):**
If you upload without specifying metadata, the system will:
1. Accept the upload immediately (fast!)
2. Queue a background job to infer metadata using AI
3. Store the inferred metadata with a confidence score
4. Mark provenance as "inferred"

#### 2. Editing Metadata for Existing Files

**Via Admin UI:**
1. Navigate to Admin Dashboard → Knowledge → Sources
2. Find your file in the list
3. Click the "Edit" icon or metadata chip
4. Update content type or tags
5. Save changes

Changes are versioned and audited automatically.

**Via API:**
```bash
curl -X PUT "http://localhost:8000/admin/api/knowledge/sources/path/to/file.md" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "manual_content_type": "tutorial",
    "manual_tags": ["advanced", "python", "async"]
  }'
```

#### 3. Using Metadata in Queries

Metadata filters can be used in search queries to narrow results:

**Strict Filtering (Manual metadata only):**
```
filter:content_type:technical Show me API documentation
```

**Soft Filtering (Includes inferred metadata for reranking):**
```
Show me technical content about Python
```
The system will detect "technical" and use it to boost relevant results.

**Tag-based Filtering:**
```
filter:tags:python,tutorial Find beginner tutorials
```

#### 4. Understanding Provenance

Files display provenance indicators:

- **Manual** (🟢): Admin-specified metadata, always authoritative
- **Inferred** (🔵): AI-generated metadata with confidence score
- **Mixed**: Some fields manual, some inferred

**Precedence Rule:** Manual metadata ALWAYS overrides inferred metadata in `effective_*` fields.

#### 5. Managing Tenant Taxonomy

Define your organization's controlled vocabulary:

**Via API:**
```bash
# Get current taxonomy
curl "http://localhost:8000/admin/api/taxonomy"

# Add new category
curl -X POST "http://localhost:8000/admin/api/taxonomy" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "research-paper",
    "label": "Research Paper",
    "synonyms": ["research", "paper", "academic"],
    "active": true
  }'

# Update category
curl -X PUT "http://localhost:8000/admin/api/taxonomy/research-paper" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Academic Research Paper",
    "synonyms": ["research", "paper", "academic", "scholarly"]
  }'
```

#### 6. Batch Inference

Re-run inference for files that don't have manual metadata:

**Dry Run (See what would be processed):**
```bash
curl -X POST "http://localhost:8000/admin/api/knowledge/metadata/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "dry_run": true,
    "limit": 100
  }'
```

**Actual Inference:**
```bash
curl -X POST "http://localhost:8000/admin/api/knowledge/metadata/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "dry_run": false,
    "limit": 50,
    "paths": ["/path/to/file1.md", "/path/to/file2.pdf"]
  }'
```

---

## API Reference

### Taxonomy Endpoints

#### `GET /admin/api/taxonomy`
Get all taxonomy entries for the current tenant.

**Query Parameters:**
- `active_only` (bool, default: true): Only return active entries

**Response:**
```json
{
  "entries": [
    {
      "key": "technical",
      "label": "Technical Documentation",
      "synonyms": ["technical", "docs", "documentation"],
      "active": true
    }
  ],
  "total": 5,
  "tenant_id": "tenant-uuid"
}
```

#### `POST /admin/api/taxonomy`
Create a new taxonomy entry.

**Request Body:**
```json
{
  "key": "tutorial",
  "label": "Tutorial",
  "synonyms": ["guide", "howto", "walkthrough"]
}
```

**Response:** 201 Created

#### `PUT /admin/api/taxonomy/{key}`
Update an existing taxonomy entry.

**Request Body:**
```json
{
  "label": "Updated Label",
  "synonyms": ["new", "synonyms"],
  "active": true
}
```

#### `DELETE /admin/api/taxonomy/{key}`
Deactivate a taxonomy entry (soft delete).

**Response:** 204 No Content

---

### Knowledge Metadata Endpoints

#### `GET /admin/api/knowledge/sources`
List files with metadata.

**Query Parameters:**
- `status` (string): Filter by status (e.g., "indexed")
- `limit` (int, default: 200): Max results
- `offset` (int, default: 0): Pagination offset

**Response:**
```json
{
  "files": [
    {
      "path": "/knowledge/guide.md",
      "filename": "guide.md",
      "manual_content_type": "tutorial",
      "manual_tags": ["python", "beginner"],
      "inferred_content_type": null,
      "inferred_tags": null,
      "effective_content_type": "tutorial",
      "effective_tags": ["python", "beginner"],
      "metadata_provenance": "manual",
      "metadata_version": 2,
      "metadata_updated_at": "2025-10-05T12:00:00Z"
    }
  ],
  "total": 42
}
```

#### `GET /admin/api/knowledge/sources/{path}`
Get metadata for a specific file.

**Path Parameter:**
- `path`: URL-encoded file path

**Response:** Same structure as single file in list above

#### `PUT /admin/api/knowledge/sources/{path}`
Update manual metadata for a file.

**Request Body:**
```json
{
  "manual_content_type": "creative",
  "manual_tags": ["storytelling", "narrative"]
}
```

**Response:**
```json
{
  "success": true,
  "updated_fields": ["manual_content_type", "manual_tags"],
  "new_version": 3
}
```

#### `POST /admin/api/knowledge/metadata/infer`
Trigger batch metadata inference.

**Request Body:**
```json
{
  "dry_run": false,
  "limit": 100,
  "paths": ["/optional/specific/files.md"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Queued 42 files for metadata inference",
  "queued_count": 42,
  "total_eligible": 50
}
```

#### `GET /admin/api/knowledge/metadata/metrics`
Get metadata inference and management metrics.

**Response:**
```json
{
  "total_files": 1000,
  "with_manual_metadata": 300,
  "with_inferred_metadata": 650,
  "without_metadata": 50,
  "coverage_percentage": 95.0,
  "average_confidence": 0.87,
  "manual_override_rate": 0.15,
  "content_type_distribution": {
    "technical": 450,
    "creative": 200,
    "tutorial": 150,
    "other": 200
  },
  "top_tags": [
    {"tag": "python", "count": 234},
    {"tag": "tutorial", "count": 189}
  ]
}
```

---

## Filter Syntax Reference

### Basic Filters

**Content Type Filter:**
```
filter:content_type:technical
filter:content_type:tutorial:strict  # Strict mode (manual only)
```

**Tag Filters:**
```
filter:tags:python
filter:tags:python,tutorial  # Multiple tags (AND)
filter:tags:python|tutorial  # Multiple tags (OR)
```

**Combined Filters:**
```
filter:content_type:technical filter:tags:python,advanced
```

### Natural Language Detection

The system automatically detects metadata hints in natural language:

```
"Show me technical documentation"     → Soft boost for content_type:technical
"Find creative writing samples"       → Soft boost for content_type:creative
"Python tutorials for beginners"      → Soft boost for tags:python,tutorial
```

---

## Troubleshooting

### Issue: Inference Not Running

**Symptoms:** Files uploaded without metadata, but no inferred metadata appears.

**Checks:**
1. Verify `ANTHROPIC_API_KEY` is set in environment
2. Check backend logs for inference errors:
   ```bash
   tail -f backend/logs/app.log | grep "metadata_inference"
   ```
3. Verify background tasks are running:
   ```bash
   curl http://localhost:8000/admin/api/knowledge/metadata/metrics
   # Check "without_metadata" count
   ```

**Solutions:**
- Set API key: `export ANTHROPIC_API_KEY=sk-...`
- Manually trigger inference: `POST /admin/api/knowledge/metadata/infer`
- Check rate limits on Anthropic API

### Issue: Manual Metadata Not Taking Precedence

**Symptoms:** Updated metadata not reflected in queries.

**Checks:**
1. Verify metadata was saved:
   ```bash
   curl "http://localhost:8000/admin/api/knowledge/sources/your/file.md"
   # Check "metadata_provenance": "manual"
   ```
2. Check `effective_*` fields match manual fields
3. Verify reindexing completed (if retrieval is affected)

**Solutions:**
- Confirm PUT request succeeded (200 OK)
- Check audit logs for the update
- Force reindex if needed

### Issue: Taxonomy Changes Not Reflected

**Symptoms:** New categories don't appear in UI or inference.

**Checks:**
1. Verify taxonomy entry is active:
   ```bash
   curl "http://localhost:8000/admin/api/taxonomy"
   # Check "active": true
   ```
2. Confirm tenant context is correct
3. Check for RLS issues in database

**Solutions:**
- Ensure `active: true` when creating
- Refresh admin UI cache
- Check database RLS policies

### Debugging Inference Problems

**Low Confidence Scores:**
- Files may have ambiguous content
- Consider manual override for important files
- Review and refine taxonomy synonyms

**Wrong Content Type Inferred:**
- Add better synonyms to taxonomy
- Manually override and review patterns
- Check file content quality (truncated files?)

**Query Audit Logs:**
```sql
-- View recent metadata updates
SELECT * FROM audit_logs
WHERE action LIKE '%metadata%'
ORDER BY created_at DESC
LIMIT 20;

-- Check inference activity
SELECT path, inferred_content_type, inferred_confidence, metadata_provenance
FROM knowledge_files
WHERE metadata_provenance = 'inferred'
ORDER BY updated_at DESC
LIMIT 50;
```

### Performance Optimization

**Large Batch Inference:**
- Use `limit` parameter to process in batches
- Monitor API rate limits
- Run during off-peak hours

**Metadata Query Performance:**
- Effective metadata uses COALESCE (efficient)
- Add indexes if filtering becomes slow
- Consider caching taxonomy in application

---

## Best Practices

### 1. Metadata Management

- **Be Consistent:** Use taxonomy to standardize terms
- **Manual Override:** For critical/frequently-accessed files
- **Review Inference:** Periodically check inferred metadata accuracy
- **Version Awareness:** Metadata version increments help track changes

### 2. Taxonomy Design

- **Start Simple:** Begin with 3-5 core content types
- **Add Synonyms:** Help AI map variations to canonical terms
- **Keep Active:** Deactivate unused categories instead of deleting
- **Document Meaning:** Use clear, descriptive labels

### 3. Query Optimization

- **Use Strict Filters Sparingly:** Only when precision is critical
- **Trust Soft Filters:** Inferred metadata adds recall
- **Combine Filters:** Content type + tags = better results
- **Natural Language:** Let users describe what they want

### 4. Maintenance

- **Monitor Metrics:** Check coverage and confidence regularly
- **Audit Manual Overrides:** High override rate may indicate poor inference
- **Backfill Gradually:** Don't infer all files at once
- **Test Before Production:** Use dry_run for batch operations

---

## Testing

### Running Tests

**Integration Tests (Database Required):**
```bash
export TEST_DATABASE_URL="postgresql://user:pass@localhost/testdb"
pytest tests/integration/test_document_metadata.py -v
```

**E2E Tests:**
```bash
pytest tests/e2e/test_document_metadata_flow.py -v -m e2e
```

**All Metadata Tests:**
```bash
pytest tests/integration/test_document_metadata.py tests/e2e/test_document_metadata_flow.py -v
```

### Test Coverage

**Integration Tests (14 tests):**
- Schema validation (4 tests)
- API endpoints (2 tests)
- Metadata precedence (2 tests)
- Tenant isolation (2 tests)
- Inference service (2 tests)
- Retrieval integration (2 tests)

**E2E Tests (9 tests):**
- Upload → Inference → Retrieval flow (2 tests)
- Manual override workflow (2 tests)
- Batch inference (2 tests)
- UI workflow simulation (2 tests)
- Audit and metrics (1 test)

### Test Database Setup

```bash
# Create test database
createdb rag_test

# Run migrations
export DATABASE_URL="postgresql://user:pass@localhost/rag_test"
alembic upgrade head

# Set test environment
export TEST_DATABASE_URL="postgresql://user:pass@localhost/rag_test"

# Run tests
pytest tests/integration/test_document_metadata.py -v
```

---

## Feature Status: COMPLETE ✅

All tasks completed and tested:
- ✅ Database schema and migrations
- ✅ Backend API endpoints
- ✅ Background inference worker
- ✅ Metadata propagation to chunks
- ✅ Frontend UI components
- ✅ Retrieval policy implementation
- ✅ Audit logging and metrics
- ✅ Comprehensive testing (23 tests)
- ✅ Complete documentation

The document metadata feature is production-ready for multi-tenant RAG systems.
