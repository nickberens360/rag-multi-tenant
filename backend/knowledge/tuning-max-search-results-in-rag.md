---
title: "Tuning Max Search Results (k) in RAG: Recall, Redundancy, and Latency"
description: "A technical guide to choosing k in a production RAG stack, with code paths that honor runtime settings and expansion multipliers."
pubDate: 2025-01-10
heroImage: "/blog-placeholder-3.jpg"
author: "Nick Berens"
backgroundColor: "#eef2ff"
theme: "light"
tags: ["RAG", "Retrieval", "k", "Latency", "MMR", "Settings"]
---

The `k` you choose for retrieval directly affects recall, redundancy, and runtime. Too low and you miss supporting evidence; too high and you flood the context window or pay unnecessary latency. Here’s how the code surfaces work and how to pick sensible values.

## Where k Comes From

The retriever pulls `max_search_results` from `SearchRetrievalSettings` if available, otherwise falls back to a static default.

```python
# backend/core/semantic_searcher.py (excerpt)
def semantic_search(self, query: str, k: int = None, ...):
    rag_settings = self._get_rag_config_settings()
    sr_settings = self._get_search_retrieval_settings()

    if k is None:
        if sr_settings and getattr(sr_settings, "max_search_results", None):
            k = int(sr_settings.max_search_results)
        else:
            k = AppConfig.DEFAULT_SEARCH_K

    # Get more results than needed for filtering and reranking
    search_k = k * AppConfig.SEARCH_EXPANSION_MULTIPLIER
```

The expansion multiplier pulls extra candidates to allow thresholding and MMR re-ranking without starving the final top-k.

## Interaction with MMR

When MMR is enabled, the retriever uses larger `fetch_k` and a `lambda_mult` to balance relevance and diversity.

```python
# backend/core/semantic_searcher.py (excerpt)
if use_mmr:
    if rag_settings:
        fetch_k = max(search_k, rag_settings.rag_mmr_fetch_k)
        lambda_mult = rag_settings.rag_mmr_lambda_mult
    else:
        fetch_k = max(search_k, AppConfig.RAG_MMR_FETCH_K)
        lambda_mult = AppConfig.RAG_MMR_LAMBDA_MULT

    docs = self.vector_store.max_marginal_relevance_search(
        query, k=search_k, fetch_k=fetch_k, lambda_mult=lambda_mult
    )
```

This pattern gives you diversity among the final `k` results while still honoring `max_search_results` as the target.

## Practical Ranges

- Small, focused corpora: `k = 3–5` (with MMR off or λ ≥ 0.6)
- Medium/general corpora: `k = 6–10` (MMR on, λ ≈ 0.5, fetch_k ≥ 20)
- Long-context models: consider `k = 8–12`, but watch redundancy; prefer MMR

## Evaluation Tactics

- Track answer correctness vs. `k` on a validation set; look for diminishing returns.
- Measure context-window utilization and truncation rates per `k` bucket.
- Latency budget: ensure expansion multiplier + fetch_k stay within SLOs.

## Guardrails

- Always use an expansion multiplier ≥ 2 to allow thresholding to drop weak hits.
- If latency spikes, reduce `fetch_k` first, not the final `k`.
- Avoid `k > 12` unless you have strong de-duplication and summarization in place.

