# Metadata Filter API Examples

Example API requests demonstrating the metadata filter feature.

## 1. Soft Content Type Filter (Natural Language)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me some technical documentation"
  }'
```

**Behavior:**
- Detects `content_type:technical` filter from query
- Applies soft reranking (boosts technical content)
- Returns all relevant documents with technical content ranked higher

---

## 2. Strict Content Type Filter (Natural Language)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Only show me technical content"
  }'
```

**Behavior:**
- Detects `content_type:technical:strict` filter from "only" keyword
- Applies strict filtering (excludes non-technical content)
- Returns ONLY documents with `metadata_provenance='manual'` AND `effective_content_type='technical'`

---

## 3. Explicit Soft Filter

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the best practices?",
    "metadata_filters": ["content_type:technical"]
  }'
```

**Behavior:**
- Explicitly applies soft content_type filter
- Boosts technical content in ranking
- Includes all semantically relevant documents

---

## 4. Explicit Strict Filter

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me code examples",
    "metadata_filters": ["content_type:technical:strict"]
  }'
```

**Behavior:**
- Explicitly applies strict content_type filter
- Excludes all non-technical content
- Only returns manually verified technical documents

---

## 5. Tag Filter (Soft)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Python development tips",
    "metadata_filters": ["tags:python"]
  }'
```

**Behavior:**
- Applies soft tag filter for Python
- Boosts Python-tagged content
- Returns all relevant development tips with Python content ranked higher

---

## 6. Tag Filter (Strict)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Code examples",
    "metadata_filters": ["tags:python:strict"]
  }'
```

**Behavior:**
- Applies strict tag filter for Python
- Excludes non-Python content
- Only returns documents with manual Python tags

---

## 7. Multiple Filters (All Soft)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Backend development best practices",
    "metadata_filters": [
      "content_type:technical",
      "tags:python",
      "tags:fastapi"
    ]
  }'
```

**Behavior:**
- Applies three soft filters
- Boosts technical content
- Boosts Python-tagged content
- Boosts FastAPI-tagged content
- Cumulative boost for documents matching all criteria
- All documents included, ranked by relevance + boosts

---

## 8. Multiple Filters (All Strict)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me examples",
    "metadata_filters": [
      "content_type:technical:strict",
      "tags:python:strict"
    ]
  }'
```

**Behavior:**
- Applies two strict filters
- ONLY returns documents with:
  - `metadata_provenance='manual'` AND
  - `effective_content_type='technical'` AND
  - `'python' in effective_tags`
- Very selective, only manually verified technical Python content

---

## 9. Mixed Filters (Strict + Soft)

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "API development tutorials",
    "metadata_filters": [
      "content_type:technical:strict",
      "tags:python",
      "tags:fastapi"
    ]
  }'
```

**Behavior:**
- Strict filter on content_type (manual technical only)
- Soft filters on tags (boost Python and FastAPI)
- Returns only manual technical content
- Within technical content, ranks Python and FastAPI higher

---

## 10. Natural Language with Multiple Keywords

**Request:**
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Only show me Vue.js technical documentation"
  }'
```

**Behavior:**
- Detects "only" → strict mode enabled
- Detects "technical" → `content_type:technical:strict`
- Detects "Vue.js" → `tags:vue:strict`
- Returns ONLY documents with manual metadata for both criteria

---

## Testing Filter Behavior

### Test 1: Verify Strict Filtering Works
```bash
# Request with strict filter
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Code examples",
    "metadata_filters": ["content_type:technical:strict"]
  }' | jq '.documents_found'

# Should return ONLY documents with manual technical metadata
```

### Test 2: Verify Soft Reranking Works
```bash
# Request with soft filter
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Development best practices",
    "metadata_filters": ["content_type:technical"]
  }' | jq '.contexts[].metadata'

# Should return all documents, with technical content ranked first
```

### Test 3: Compare Strict vs Soft Results
```bash
# Strict filter
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{"question": "Examples", "metadata_filters": ["tags:python:strict"]}' \
  | jq '.documents_found'

# Soft filter
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{"question": "Examples", "metadata_filters": ["tags:python"]}' \
  | jq '.documents_found'

# Soft filter should return MORE documents than strict
```

---

## Response Format

All endpoints return metadata about filters applied:

```json
{
  "query": "Only show me technical Python content",
  "intent_analysis": { ... },
  "documents_found": 5,
  "smart_routing_info": {
    "routing_method": "automatic",
    "content_types_detected": ["technical"],
    "query_complexity": "simple",
    "filters_applied": {
      "strict": ["content_type:technical", "tags:python"],
      "soft": []
    }
  },
  "contexts": [
    {
      "index": 1,
      "content": "...",
      "metadata": {
        "effective_content_type": "technical",
        "effective_tags": "[\"python\", \"fastapi\"]",
        "metadata_provenance": "manual",
        "file_name": "python_guide.md"
      }
    }
  ]
}
```

---

## Performance Notes

1. **Strict Filters**: Apply at ChromaDB query time → very efficient
2. **Soft Filters**: Apply post-retrieval → minimal overhead (~10-20ms)
3. **Mixed Filters**: Strict filters reduce result set, soft filters rerank → optimal performance
4. **Cache**: Results cached per query + filters → subsequent requests instant

---

## Error Handling

### Invalid Filter Syntax
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Examples",
    "metadata_filters": ["invalid_field:value"]
  }'

# Returns 200 OK, silently ignores invalid filters
# Logs warning: "Unknown filter field: invalid_field"
```

### No Results with Strict Filters
```bash
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Examples",
    "metadata_filters": ["tags:nonexistent:strict"]
  }'

# Returns 200 OK with empty contexts
# Response: {"documents_found": 0, "contexts": []}
```
