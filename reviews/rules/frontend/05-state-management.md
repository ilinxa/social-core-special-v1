# 05 — State Management Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 5.1 State Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 5.1.1 | FAIL if client state (auth, UI) and server state (API data) are not clearly separated between Zustand and TanStack Query | PASS/FAIL |
| 5.1.2 | FAIL if API-fetched data (business details, member lists, transactions) is duplicated into Zustand stores instead of living in TQ cache | PASS/FAIL |
| 5.1.3 | WARN if TanStack Query is used for purely client-side state (sidebar open, modal visibility, active tab) | PASS/WARN |
| 5.1.4 | FAIL if form state (inputs, validation, dirty tracking) is managed by Zustand or TQ instead of react-hook-form | PASS/FAIL |
| 5.1.5 | WARN if filter selections, pagination, sort order, or search queries are stored in component state or Zustand instead of URL search params | PASS/WARN |
| 5.1.6 | WARN if component-local UI state (toggles, hover, open/closed) uses Zustand instead of useState/useReducer | PASS/WARN |
| 5.1.7 | WARN if derived/computed values (fullName, filteredList) are stored separately instead of calculated inline or in selectors | PASS/WARN |

## 5.2 Zustand Store Design

| ID | Rule | Verdict |
|----|------|---------|
| 5.2.1 | FAIL if Zustand stores are not typed with full state + actions interface | PASS/FAIL |
| 5.2.2 | WARN if stores do not use immer middleware for immutable updates | PASS/WARN |
| 5.2.3 | WARN if devtools middleware is not enabled for debugging | PASS/WARN |
| 5.2.4 | WARN if state properties and actions are not clearly separated in the store type | PASS/WARN |
| 5.2.5 | FAIL if initial state is not extractable for testing/resetting (hardcoded inside create()) | PASS/FAIL |
| 5.2.6 | WARN if stores contain derived values, stale server data copies, or redundant flags | PASS/WARN |
| 5.2.7 | WARN if store files are not in src/stores/ directory | PASS/WARN |

## 5.3 Selector Patterns

| ID | Rule | Verdict |
|----|------|---------|
| 5.3.1 | FAIL if stores do not export purpose-specific selector hooks (useUser, useIsAuthenticated) | PASS/FAIL |
| 5.3.2 | WARN if components access the raw store directly (useAuthStore(state => state.user)) instead of using selector hooks | PASS/WARN |
| 5.3.3 | FAIL if selectors returning arrays/objects do not use useShallow from zustand/react/shallow | PASS/FAIL |
| 5.3.4 | WARN if selector functions create new references on each call without useShallow | PASS/WARN |
| 5.3.5 | FAIL if .filter()/.map()/.reduce() in selectors is not wrapped with useShallow (causes infinite re-renders) | PASS/FAIL |
| 5.3.6 | WARN if computed values are pre-stored instead of derived in selector hooks | PASS/WARN |

## 5.4 Non-React Access

| ID | Rule | Verdict |
|----|------|---------|
| 5.4.1 | FAIL if no non-hook accessor (getState()) is available for use in API interceptors and utilities | PASS/FAIL |
| 5.4.2 | WARN if non-React code subscribes to store changes instead of using one-time getState() reads | PASS/WARN |
| 5.4.3 | FAIL if Zustand hooks (useAuthStore) are called outside the React component tree | PASS/FAIL |
| 5.4.4 | FAIL if API client interceptors cannot access the current auth token without a React hook | PASS/FAIL |
| 5.4.5 | WARN if store actions (logout, token refresh) cannot be triggered from non-React code | PASS/WARN |

## 5.5 TanStack Query Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 5.5.1 | FAIL if QueryClient is a module-level singleton instead of created per-session in useState | PASS/FAIL |
| 5.5.2 | WARN if no default staleTime is configured (causes unnecessary refetches on mount) | PASS/WARN |
| 5.5.3 | WARN if retry logic does not skip 4xx client errors (should only retry network/5xx) | PASS/WARN |
| 5.5.4 | WARN if refetchOnWindowFocus is not disabled | PASS/WARN |
| 5.5.5 | WARN if mutations have retry > 0 (risk of duplicate side effects) | PASS/WARN |
| 5.5.6 | WARN if throwOnError is not false for mutations (errors should be in mutation result, not boundary) | PASS/WARN |
| 5.5.7 | WARN if gcTime is not configured (risk of memory leaks from unused cache entries) | PASS/WARN |

## 5.6 Query Key Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 5.6.1 | FAIL if query keys are not centralized in a single file (lib/query-keys.ts) | PASS/FAIL |
| 5.6.2 | FAIL if keys do not follow hierarchical namespace pattern (queryKeys.feature.operation) | PASS/FAIL |
| 5.6.3 | FAIL if parameterized keys do not include parameters for cache differentiation | PASS/FAIL |
| 5.6.4 | FAIL if string-literal query keys are scattered in hook files instead of using centralized factory | PASS/FAIL |
| 5.6.5 | WARN if queryKeys object is not typed with as const for compile-time safety | PASS/WARN |
| 5.6.6 | WARN if parameterized keys do not use factory functions returning typed tuples | PASS/WARN |

## 5.7 Query Hook Patterns

| ID | Rule | Verdict |
|----|------|---------|
| 5.7.1 | FAIL if TanStack Query hooks are used directly in components instead of wrapped in features/*/hooks/ | PASS/FAIL |
| 5.7.2 | WARN if query and mutation hooks are mixed in a single large file instead of separated | PASS/WARN |
| 5.7.3 | FAIL if paginated/infinite-scroll lists do not use useInfiniteQuery | PASS/FAIL |
| 5.7.4 | FAIL if getNextPageParam does not correctly handle cursor/offset pagination or return undefined at end | PASS/FAIL |
| 5.7.5 | WARN if mutation hooks lack onSuccess/onError/onSettled callbacks | PASS/WARN |
| 5.7.6 | FAIL if query/mutation hooks return untyped (any/unknown) data | PASS/FAIL |
| 5.7.7 | WARN if queries depending on a parameter do not use enabled: !!param | PASS/WARN |

## 5.8 Cache Invalidation

| ID | Rule | Verdict |
|----|------|---------|
| 5.8.1 | FAIL if mutations do not invalidate relevant query keys on success | PASS/FAIL |
| 5.8.2 | WARN if cross-feature invalidation does not use query key namespaces | PASS/WARN |
| 5.8.3 | WARN if manual queryClient.setQueryData is used outside of optimistic updates | PASS/WARN |
| 5.8.4 | FAIL if stale data is visible after mutations (no invalidation/refetch) | PASS/FAIL |
| 5.8.5 | FAIL if queryClient.invalidateQueries() is called with no arguments (global invalidation) | PASS/FAIL |
| 5.8.6 | WARN if related queries (list + detail) are not invalidated together after mutations | PASS/WARN |

## 5.9 Optimistic Updates

| ID | Rule | Verdict |
|----|------|---------|
| 5.9.1 | FAIL if optimistic updates do not rollback on error (missing onMutate/onError pair) | PASS/FAIL |
| 5.9.2 | WARN if optimistic data does not match the full TypeScript type of the query response | PASS/WARN |
| 5.9.3 | WARN if complex multi-step mutations use optimistic updates | PASS/WARN |
| 5.9.4 | WARN if optimistic updates do not provide instant UI feedback | PASS/WARN |
| 5.9.5 | WARN if rollback causes visible flicker or jarring layout change | PASS/WARN |

## 5.10 State & Store Testing

| ID | Rule | Verdict |
|----|------|---------|
| 5.10.1 | FAIL if Zustand stores do not have dedicated test files | PASS/FAIL |
| 5.10.2 | FAIL if tests do not verify state transitions for all store actions | PASS/FAIL |
| 5.10.3 | WARN if TanStack Query hooks are not tested with mock API responses | PASS/WARN |
| 5.10.4 | FAIL if tests do not reset store state between test cases (cross-test pollution) | PASS/FAIL |
| 5.10.5 | WARN if store initial state is not tested explicitly | PASS/WARN |
| 5.10.6 | WARN if store actions with side effects (logout, navigation) are not tested with mocks | PASS/WARN |
