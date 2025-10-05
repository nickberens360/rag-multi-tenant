# Metadata Filter Examples

This document demonstrates the smart retrieval semantics for manual vs inferred metadata in the multi-tenant RAG system.

## Overview

The system treats metadata differently based on its provenance:

- **Manual Metadata** (`provenance='manual'`): Authoritative, user-verified metadata that can be used for strict filtering
- **Inferred Metadata** (`provenance='inferred'`): LLM-generated metadata that serves as a soft signal for reranking

## Filter Semantics

### Strict Filters (Hard Exclusion)
- Applied to documents with `metadata_provenance='manual'` only
- Excludes documents that don't match the filter criteria
- Uses ChromaDB `where` clauses for efficient filtering
- Triggered by keywords: "only", "strictly", "exclusively", "must be", "just"
- Or explicitly with `:strict` suffix in filter strings

### Soft Filters (Reranking/Boosting)
- Applied to all documents (manual and inferred)
- Boosts relevance scores for matching documents
- Manual matches get 1.5x higher boost than inferred matches
- Default behavior when no strict keywords present

## Example Queries

### Natural Language Queries

#### 1. Soft Content Type Filter
```
Query: "Show me some technical documentation"
Filter: content_type:technical (soft)
Behavior:
  - Returns all documents matching the semantic query
  - Boosts ranking for documents with effective_content_type='technical'
  - Manual metadata gets higher boost (0.3) than inferred (0.2)
```

#### 2. Strict Content Type Filter
```
Query: "Only show me technical content"
Filter: content_type:technical:strict
Behavior:
  - ONLY returns documents with:
    - metadata_provenance='manual' AND
    - effective_content_type='technical'
  - Excludes all documents without manual technical classification
```

#### 3. Soft Tag Filter
```
Query: "Tell me about Python projects"
Filter: tags:python (soft)
Behavior:
  - Returns all documents matching the semantic query
  - Boosts ranking for documents with 'python' in effective_tags
  - Manual tags get higher boost than inferred tags
```

#### 4. Strict Tag Filter
```
Query: "Only Python code examples"
Filter: tags:python:strict
Behavior:
  - ONLY returns documents with:
    - metadata_provenance='manual' AND
    - 'python' in effective_tags
  - Excludes all documents without manual Python tag
```

#### 5. Multiple Filters (Mixed)
```
Query: "Show me Vue.js technical documentation"
Filters:
  - content_type:technical (soft)
  - tags:vue (soft)
Behavior:
  - Returns all documents matching the semantic query
  - Boosts ranking for technical content
  - Further boosts ranking for Vue-related content
  - Cumulative boost for documents matching both filters
```

### Explicit Filter Parameters

#### API Request with Soft Filters
```json
POST /api/smart-query
{
  "question": "What are the best practices?",
  "metadata_filters": [
    "content_type:technical",
    "tags:python"
  ]
}
```
**Result**: Soft reranking with boost for technical Python content

#### API Request with Strict Filters
```json
POST /api/smart-query
{
  "question": "Show me code examples",
  "metadata_filters": [
    "content_type:technical:strict",
    "tags:python:strict"
  ]
}
```
**Result**: Hard filter - ONLY returns documents with manual metadata matching both criteria

#### API Request with Mixed Filters
```json
POST /api/smart-query
{
  "question": "Backend development tips",
  "metadata_filters": [
    "content_type:technical:strict",
    "tags:python",
    "tags:fastapi"
  ]
}
```
**Result**:
- Hard filter on content_type (manual only)
- Soft boost for Python and FastAPI tags
- Prioritizes documents with all three characteristics

## Filter Syntax

### String Format
```
field:value[:strict]
```

**Fields**:
- `content_type` → maps to `effective_content_type`
- `tags` → maps to `effective_tags`

**Values**:
- Content types: `technical`, `experience`, `about`, `creative`, `project`
- Tags: Any technology, language, or topic (e.g., `python`, `vue`, `docker`)

**Strict Flag**:
- Omit for soft filtering (default)
- Add `:strict` for hard filtering

### Examples
```
content_type:technical          # Soft filter
content_type:technical:strict   # Strict filter
tags:python                     # Soft filter
tags:python:strict              # Strict filter
```

## Scoring Algorithm

### Soft Reranking Formula
```python
for each document:
    adjusted_score = original_distance_score

    for each matching filter:
        if metadata_provenance == 'manual':
            boost = filter.boost_weight * 1.5  # Higher boost for manual
        else:
            boost = filter.boost_weight        # Lower boost for inferred

        adjusted_score -= boost  # Lower distance = better match

    return adjusted_score
```

### Default Boost Weights
- Content type match: 0.2
- Tag match: 0.3
- Manual metadata multiplier: 1.5x

## ChromaDB Where Clauses

### Strict Content Type Filter
```python
where = {
    "$and": [
        {"metadata_provenance": "manual"},
        {"effective_content_type": "technical"}
    ]
}
```

### Strict Tag Filter
```python
where = {
    "$and": [
        {"metadata_provenance": "manual"},
        {"effective_tags": {"$contains": "python"}}
    ]
}
```

### Multiple Strict Filters
```python
where = {
    "$and": [
        {
            "$and": [
                {"metadata_provenance": "manual"},
                {"effective_content_type": "technical"}
            ]
        },
        {
            "$and": [
                {"metadata_provenance": "manual"},
                {"effective_tags": {"$contains": "python"}}
            ]
        }
    ]
}
```

## Use Cases

### 1. Exploratory Search (Soft Filters)
**Scenario**: User wants to explore Python-related content but doesn't want to exclude potentially relevant results.

**Query**: "Python development best practices"

**Behavior**: Returns all semantically relevant documents, with higher ranking for Python-tagged content.

### 2. Precise Search (Strict Filters)
**Scenario**: User wants ONLY manually verified technical Python documentation.

**Query**: "Only show me Python technical documentation"

**Behavior**: Returns only documents with both manual metadata tags, excluding inferred classifications.

### 3. Quality Control (Strict on Critical, Soft on Optional)
**Scenario**: User wants verified technical content but is flexible on technology tags.

**Request**:
```json
{
  "question": "Backend API development",
  "metadata_filters": [
    "content_type:technical:strict",
    "tags:python",
    "tags:fastapi"
  ]
}
```

**Behavior**:
- Hard filter: Only manual technical content
- Soft boost: Prefers Python and FastAPI content within technical docs

## Validation

### Test Scenarios

1. **Strict filter with manual metadata** → Document included ✅
2. **Strict filter with inferred metadata** → Document excluded ❌
3. **Soft filter with manual metadata** → High ranking boost ⬆️⬆️
4. **Soft filter with inferred metadata** → Low ranking boost ⬆️
5. **No filters** → Standard semantic search 🔍

### Expected Behavior

| Metadata Provenance | Filter Type | Result |
|---------------------|-------------|--------|
| Manual | Strict | ✅ Included (if matches) |
| Inferred | Strict | ❌ Excluded |
| Manual | Soft | ⬆️⬆️ High boost (1.5x) |
| Inferred | Soft | ⬆️ Low boost (1.0x) |
| Any | None | 🔍 Standard search |

## Implementation Details

### Files Modified
1. `backend/models/filter_models.py` - Filter data structures and parsing
2. `backend/core/semantic_searcher.py` - ChromaDB filtering and reranking
3. `backend/core/content_router.py` - Natural language filter detection
4. `backend/core/smart_query_handler.py` - Filter propagation
5. `backend/models/request_models.py` - API parameter support
6. `backend/routes/smart_query.py` - Endpoint integration

### Key Components

- **MetadataFilter**: Single filter specification
- **RetrievalFilters**: Container for all filters
- **parse_filter_string()**: Parse string filters
- **detect_metadata_filters()**: Extract filters from queries
- **_build_where_clause()**: Generate ChromaDB filters
- **_apply_soft_reranking()**: Boost matching documents

## Future Enhancements

1. **User Preferences**: Save preferred filter modes per user
2. **Analytics**: Track filter effectiveness and usage patterns
3. **Advanced Syntax**: Support OR conditions, negation, ranges
4. **Custom Weights**: Allow users to configure boost weights
5. **Filter Suggestions**: Recommend filters based on query analysis
