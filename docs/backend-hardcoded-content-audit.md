# Backend Hardcoded Content Audit and Dynamic Replacement Plan

This audit identifies hardcoded content categories/heuristics in the backend (e.g., "about", "experience", "skills", "creative", "project", "technical") and proposes a plan to replace them with a dynamic, configurable approach aligned with RAG best practices.

## Summary
- Hardcoded topic/category heuristics appear in multiple components (classifiers, router, services).
- These introduce brittleness and drift risk as content evolves, and make tuning difficult without code changes.
- We already have an LLM-powered startup classifier; shifting to dynamic, config-driven taxonomies and metadata-first routing will improve robustness and maintainability.

## Findings (File Locations)

- `backend/core/fast_content_classifier.py`
  - Hardcodes topic dictionaries: `topic_patterns`, `file_topic_hints`, `content_keywords` for categories: `about`, `experience`, `skills`, `creative`, `project`, `technical`.
  - Methods `extract_content_topics_fast`, `calculate_topic_confidence` rely on those lists.

- `backend/core/startup_content_classifier.py`
  - Heuristic file-name hints and content-word checks for `about`, `experience`, `skills`, `creative`, `project` in `_extract_heuristic_topics`.
  - Topic-specific keyword extraction table (`topic_keywords`).

- `backend/core/content_indexer.py`
  - In legacy/fallback path, repeats filename/content heuristics for `about`, `experience`, `skills`, `creative`, `project`.

- `backend/core/content_router.py`
  - `detect_content_types` inspects queries using fixed keyword lists to infer `experience`, `skills`, `about`, `creative`, `project`.
  - Strategies (e.g., `creative_focused`) are coupled to those hardcoded types.

- `backend/core/unified_retriever_old.py` (legacy)
  - Similar hardcoded heuristics for tagging and query routing with `about`, `experience`, `skills`, `creative`, `project`.

- `backend/core/smart_illustration_service.py`
  - Filters search with `filter_content_types=["creative"]`; relies on category rather than solely metadata flags.

- `backend/core/query_router.py`
  - Contains hardcoded keyword lists used to parse/route illustration queries (e.g., includes "about" in ignore words and specific patterns).

- `backend/core/followup_service.py`
  - Default question pools grouped by static categories (`technical`, `personal`, `creative`) with hardcoded prompts like “Tell me about your experience”.

- `backend/core/semantic_searcher.py`
  - Exposes `filter_content_types` as an API; not an issue itself, but downstream callers pass hardcoded type lists.

- `backend/core/llm_chain.py`
  - System prompts reference “skills”, “experience”, etc. This is acceptable for persona/response framing, but it’s worth noting they are not used as dynamic taxonomy.

## Risks with Current Approach
- Brittleness: Adding new content types or synonyms requires code edits and redeploys.
- Coverage gaps: Heuristic lists may miss domain-specific language, leading to misrouting.
- Drift: As knowledge base grows, static lists won’t reflect the evolving taxonomy.
- Coupling: Downstream features (illustration search, follow-ups) assume specific categories.

## Dynamic Replacement Plan

1) Centralize a Configurable Taxonomy
- Create `backend/core/topic_taxonomy.json` (or `.yaml`) defining:
  - `categories`: canonical names (e.g., experience, skills, creative, project, technical, about).
  - `synonyms`: per-category arrays (keywords, phrases).
  - `regex`: optional per-category patterns.
  - `weights`: optional tuning for confidence contributions.
- Load this at startup; hot-reloadable via an admin endpoint or settings DB record.

2) Make Classifiers Config-Driven, Metadata-First
- Update `FastContentClassifier` and `StartupContentClassifier` to read taxonomy from config instead of hardcoded dicts.
- Prioritize LLM startup classification for `content_types`; use config-driven heuristics only as a fallback/booster.
- Emit only tags derived from LLM or configured taxonomy; avoid embedding category names directly in code.

3) Query Routing via Configurable Intents
- Replace `ContentRouter.detect_content_types` hardcoded lists with a taxonomy-backed intent map (synonyms/regex per category loaded from the same config).
- Optional: Introduce a lightweight embedding-based intent classifier for better synonym coverage; keep config as an override.

4) Illustration Search: Prefer Explicit Metadata over Category
- In `SmartIllustrationService`, rely on `is_illustration_data` and `display_path` metadata. Make `filter_content_types` optional or controlled by taxonomy config (e.g., category alias to metadata field mapping).

5) Externalize Follow-up Question Pools
- Move default question pools from `FollowUpService` into the settings DB or a JSON file (e.g., `followup_settings` already supported). Provide an admin route/UI for editing.

6) Admin Controls and Observability
- Add admin endpoints for:
  - Uploading/editing `topic_taxonomy.json`.
  - Toggling classification modes: `fast`, `startup_llm`, `hybrid`.
  - Forcing reindex to apply taxonomy changes.
- Expose a `/content/classification-stats` endpoint returning current topic distributions and confidence metrics (already partially available in `StartupContentClassifier.get_classification_stats`).

7) Migration Steps
- Bootstrap `topic_taxonomy.json` by extracting today’s keywords/regexes from code as the initial seed.
- Implement config loading in classifiers/router behind feature flags; ship dark.
- Reindex the knowledge base with startup LLM classification enabled (`classification_mode: startup_llm` or `hybrid`).
- Verify query routing parity with existing behavior; tune taxonomy where mismatches are found.
- Remove deprecated hardcoded tables once parity is achieved.

## Acceptance Criteria
- No hardcoded category names in classifiers/router; all topic/intent detection comes from LLM metadata and config.
- Admin can update taxonomy without code changes; changes take effect on reindex (or on hot-reload, if implemented).
- Illustration search works from explicit metadata; category filters are optional/configurable.
- Follow-up suggestions source from settings or config, not code.
- Semantic search results remain equal or better on representative queries (resume/skills/about/projects/illustrations).

## Suggested File/Code Changes (High Level)
- Add: `backend/core/topic_taxonomy.json` and loader utility.
- Refactor: `FastContentClassifier`, `StartupContentClassifier`, `ContentRouter`, `SmartIllustrationService`, `FollowUpService` to consume config and/or metadata.
- Config: Add `AppConfig.CLASSIFICATION_MODE` default to `startup_llm` (production) with `fast` only as a perf fallback.
- Admin: Endpoints to manage taxonomy and trigger reindex.

---

If you’d like, I can proceed by scaffolding `topic_taxonomy.json`, wiring a small loader, and refactoring one classifier/router to be config-driven as a first PR slice.

