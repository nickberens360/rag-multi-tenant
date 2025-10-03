# Admin Frontend Notifications — Standardization Plan

## Summary
- Goal: Standardize all admin notifications to a single, global, toast-style UI (upper-right) powered by a Pinia store and a reusable Vue component.
- Scope: Replace ad-hoc `v-snackbar` usages and static banners used for action feedback across admin views with the new global system.
- Placement: Mount the global notification component at the root admin app level (`admin/frontend/src/App.vue`) so it covers all routes (including login) and avoids duplication.

## Current State (Findings)
- Multiple patterns coexist:
  - Local `v-snackbar` in components (e.g., `ContentGapsTable.vue`, `ApiKeysSettings.vue`).
  - Error and connectivity snackbars in `AdminLayout.vue`.
  - A local composable `useNotifications.js` with an in-memory `ref([])` and a container component `SettingsNotifications.vue` using it.
- Pinia is already configured (`main.js`). No centralized notification store exists yet.

## Design Overview
- Pinia store: `admin/frontend/src/stores/notifications.ts` (or `.js` to match repo style)
  - State: `notifications: Notification[]`
  - Notification shape:
    - `id: string`
    - `type: 'success' | 'info' | 'warning' | 'error'`
    - `message: string`
    - `timeout?: number` (default 4000, error 6000)
    - `dismissible?: boolean` (default true)
    - `persistent?: boolean` (overrides timeout, e.g., connectivity)
    - `actionLabel?: string` and `onAction?: () => void` (optional CTA)
    - `meta?: Record<string, unknown>` (optional; for future needs)
  - Actions:
    - `notify(payload)` generic
    - `success(message, opts?)`, `info(message, opts?)`, `warning(message, opts?)`, `error(message, opts?)`
    - `dismiss(id)`, `clear()`
    - Optional: `setMaxStack(n)` and trim oldest when exceeding
  - Behavior:
    - De-dup logic optional (e.g., collapse identical message within N ms)
    - Auto-dismiss by timeout unless `persistent`

- Global component: `admin/frontend/src/components/NotificationMessage.vue`
  - Renders a stack of `v-snackbar` toasts bound to the store state.
  - Location: `top right`. Stacks vertically with small spacing.
  - Color map (Vuetify): success → `success`, info → `info`, warning → `warning`, error → `error`.
  - Each toast has close action; supports optional CTA via `actionLabel`/`onAction`.
  - Z-index and pointer-events configured so toasts float over content but do not block the app when not hovered.

- Mount point: `App.vue`
  - Import and mount `<NotificationMessage />` once under the root `<v-app>` so it is available on every route (including routes that do not use `AdminLayout`).
  - Rationale: A single source of truth and consistent presentation across authenticated and unauthenticated screens.

- Composability: `useNotifications.js`
  - Migrate the existing composable to delegate to the Pinia store for backward compatibility. Keep its function names (e.g., `showSuccess`, `showError`, etc.) to minimize refactors; internally it will call store actions.
  - Mark the composable as a thin wrapper and deprecate direct state management in it.

## Migration Plan
1. Add the new Pinia store (`stores/notifications.js`) and the global component (`components/NotificationMessage.vue`).
2. Mount `<NotificationMessage />` in `App.vue` beneath `<router-view />` or as a sibling under `<v-app>`.
3. Update `useNotifications.js` to use the Pinia store internally (preserve the existing API: `showSuccess`, `showError`, `showInfo`, `showWarning`, `dismiss`, `clear`).
4. Replace ad-hoc snackbars:
   - `ContentGapsTable.vue`: remove local `snackbar` state and `v-snackbar`; use store calls (e.g., `notifications.success(...)`).
   - `ApiKeysSettings.vue`: replace inline validation result snackbar with store-based toast calls.
   - `AdminLayout.vue`: route `error` and connection warnings through the store. For persistent connection warnings, use `persistent: true` and custom message. If keeping a special banner is desired for visibility, also emit a toast on state changes for consistency.
   - `settings/SettingsNotifications.vue`: mark as deprecated; either remove or refactor to simply render the global component (prefer removal after verifying no direct references remain).
5. Grep for remaining `v-snackbar` usage in admin frontend and convert to the store.
6. QA pass:
   - Verify stacking, auto-dismiss, persistent behavior, and CTA actions.
   - Check focus/keyboard accessibility and contrast across themes.
   - Ensure no duplicate toasts for the same event if events fire quickly.

## Usage Examples
- In a component after an action:
  ```js
  import { useNotificationsStore } from '@/stores/notifications'
  const notifications = useNotificationsStore()
  notifications.success('Content gap marked as resolved')
  notifications.error('Failed to save', { timeout: 6000 })
  notifications.info('Connection restored', { timeout: 3000 })
  ```

- With existing composable (backward compatible):
  ```js
  import { useNotifications } from '@/composables/useNotifications'
  const { showSuccess, showError } = useNotifications()
  showSuccess('Saved settings')
  showError('Failed to fetch data')
  ```

## Implementation Notes
- File naming aligns with repo conventions (`PascalCase.vue` for components, stores in `src/stores/`).
- Keep store in JavaScript to match current store files, unless TypeScript is desired later.
- Default stack limit: 3–5 toasts visible; older toasts are removed when exceeded.
- Consider a small debounce window (e.g., 500ms) to de-duplicate identical messages.

## Out of Scope / Follow-ups
- Server-driven notifications (push/WebSocket) integration.
- Persisted notifications history.
- Per-user notification preferences.

## Rollout Steps
- Implement store and component; mount globally.
- Convert a representative set of components (2–3) to validate API and UX.
- Convert remaining components in small PRs to keep diffs focused.
- Remove deprecated `SettingsNotifications.vue` once no longer referenced.

