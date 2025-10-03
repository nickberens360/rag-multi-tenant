---
name: Quick win — Add minimal typing to core composables
about: Convert key composables/stores to TypeScript with minimal types
title: "refactor(frontend): add minimal TS to composables + tests"
labels: ["frontend", "typescript", "good first issue"]
assignees: []
---

Summary
- Improve type safety for critical frontend boundaries.

Scope (initial)
- Convert `src/composables/useChatAPI.js` to `useChatAPI.ts` with minimal interfaces for API responses and callbacks.
- Convert `src/stores/ui.js` to `ui.ts` with typed structures for nav/font/blog items.
- Add 1–2 Vitest tests for `useChatAPI` basic flows (status check, rate-limits parse).

Acceptance Criteria
- Builds pass (`npm run dev`/`build`).
- Vitest passes (new tests).
- No behavior changes (type-only refactor).

Notes
- Keep types lightweight; focus on external API shapes.

