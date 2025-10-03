---
title: "Calibrating Fuzzy and Semantic Thresholds in RAG"
description: "A technical deep dive into distance vs. similarity thresholds, semantic post-filters, and calibrating fuzzy matching for search UX."
pubDate: 2025-01-10
heroImage: "/blog-placeholder-6.jpg"
author: "Nick Berens"
backgroundColor: "#fef3f2"
theme: "light"
tags: ["RAG", "Thresholds", "Similarity", "Fuzzy Matching", "Evaluation"]
---

Two knobs govern what qualifies as a “relevant” hit in a hybrid RAG system:

- A distance-based filter at the vector store level (lower distance = closer in embedding space)
- A semantic similarity post-filter in application space (convert distance to a normalized similarity)

This post covers both, and how to set them alongside fuzzy keyword thresholds for a predictable UX.

## Distance Threshold (Vector Store)

The retriever filters candidates by distance. In Chroma’s L2 distance, lower is better; good matches are typically `< 1.0`.

```python
# backend/core/semantic_searcher.py (excerpt)
docs_and_scores = self.vector_store.similarity_search_with_score(query, k=search_k)

if score_threshold == 0.0:
    filtered_docs = [doc for doc, score in docs_and_scores]  # no filtering
else:
    filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
```

The `score_threshold` comes from `RagConfigurationSettings.rag_score_threshold` when configured at runtime.

## Semantic Post-Filter (Similarity in 0..1)

For a human-friendly notion of “similar enough”, map distances to a pseudo-similarity and filter again.

```python
# backend/core/semantic_searcher.py (excerpt)
if sr_settings and getattr(sr_settings, "semantic_similarity_threshold", None) is not None:
    sim_thr = float(sr_settings.semantic_similarity_threshold)
    if sim_thr > 0.0:
        def _sim_from_distance(d: float) -> float:
            return 1.0 / (1.0 + float(d))

        filtered_docs = [doc for (doc, dist) in docs_and_scores if _sim_from_distance(dist) >= sim_thr]
```

This second gate lets you talk in “similarity ≥ 0.7” while the store still operates in distances.

## Fuzzy Thresholds (Keyword Path)

In the routing layer, fuzzy matching is activated in the keyword fallback and can be constrained with its own threshold.

```python
# backend/core/settings_schemas.py (excerpt)
@dataclass
class QueryRoutingSettings:
    similarity_threshold: float = 0.5
    fuzzy_threshold: float = 0.6
    enable_fuzzy_matching: bool = True
```

Combine this with the fallback behavior:

```python
# backend/core/query_router.py (excerpt)
return {
    "strategy": "keyword_matching",
    "use_fuzzy_matching": fuzzy_enabled,
    ...
}
```

## Calibration Playbook

- Start with `rag_score_threshold` ≈ 0.8 (distance) and `semantic_similarity_threshold` ≈ 0.7.
- Keep fuzzy off for internal users; enable for public-facing UX with `fuzzy_threshold` in 0.5–0.7.
- Periodically audit: plot answer quality vs. thresholds; adjust to hit recall/precision targets.
- If you enable MMR, you can safely raise thresholds slightly to reduce redundancy without starving recall.

## Failure Modes to Watch

- Distance-only tuning can be unintuitive; add the semantic post-filter for explainability.
- Overly permissive fuzzy settings can swamp the context with low-value hits; cap k tightly in the keyword path.
- Avoid threshold coupling: adjust one knob at a time and track impact with A/B logging.

