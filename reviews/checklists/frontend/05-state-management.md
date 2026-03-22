# 05 — State Management Checklist

## 5.1 State Architecture

- [ ] **Clear separation between client state and server state** — Zustand holds client-only state (auth tokens, UI preferences, active context), TanStack Query holds server-derived state (API data, cached responses)
- [ ] **No server data cached in Zustand** — data fetched from the API (business details, member lists, transaction data) lives in TanStack Query cache, not duplicated into Zustand stores
- [ ] **No TanStack Query used for purely client-side state** — ephemeral UI state (sidebar open/closed, modal visibility, active tab) uses useState or Zustand, not useQuery with a fake query function
- [ ] **Form state managed by react-hook-form** — all form inputs, validation state, dirty tracking, and submission state are handled by useForm(), not stored in Zustand or TanStack Query
- [ ] **URL state managed by searchParams/router** — filter selections, pagination offsets, sort order, and search queries are stored in URL search params, not in Zustand or component state
- [ ] **Component-local state uses useState/useReducer** — toggle states, hover states, open/closed menus, and other UI concerns scoped to a single component use React's built-in state hooks
- [ ] **No state management library for derived/computed values** — values computable from existing state (full name from first + last, filtered list from list + filter) are calculated inline or in selectors, not stored separately

## 5.2 Zustand Store Design

- [ ] **Stores defined with create<StoreType>()** — each store is created with Zustand's create function, typed with a full state + actions interface for IntelliSense and compile-time safety
- [ ] **Immer middleware for immutable updates** — stores use the immer middleware so state updates can use mutable syntax (state.user = newUser) while maintaining immutability under the hood
- [ ] **Devtools middleware enabled for debugging** — the devtools middleware is included in the middleware chain so Zustand state changes are visible in Redux DevTools browser extension
- [ ] **State interface separated from actions interface** — the store type clearly separates state properties (user, token, isAuthenticated) from actions (setUser, clearUser, setToken) for clarity
- [ ] **Initial state is extractable for testing/resetting** — the initial state is defined as a const outside the store creation, allowing tests to reset the store to a known state between test cases
- [ ] **Stores are minimal** — stores contain only essential state; no derived values that could be computed from existing state, no stale copies of server data, no redundant flags
- [ ] **Store files in stores/ directory** — auth-store.ts and membership-store.ts live in src/stores/, not scattered across feature directories or colocated with components

## 5.3 Selector Patterns

- [ ] **Exported selector hooks wrap store access** — useUser(), useIsAuthenticated(), useActiveMembership() are exported from store files, encapsulating the store selection logic
- [ ] **Raw useAuthStore not used directly in components** — components import purpose-specific selector hooks (useUser()) instead of accessing the store directly (useAuthStore(state => state.user))
- [ ] **useShallow used when selectors return arrays/objects** — selectors that return arrays (memberships.filter()), objects (pick(state, ['a', 'b'])), or computed structures use useShallow from zustand/react/shallow to prevent infinite re-renders
- [ ] **Selectors are stable across renders** — selector functions do not create new references on each call; they return primitive values or are wrapped with useShallow to maintain referential equality
- [ ] **.filter() in selectors wrapped with useShallow** — any selector that calls .filter(), .map(), or .reduce() on state arrays is wrapped with useShallow because these methods always create new array references
- [ ] **Computed values derived in selectors, not stored** — values like memberCount, hasActiveSubscription, or isBusinessOwner are computed in selector hooks from raw state, not pre-computed and stored

## 5.4 Non-React Access

- [ ] **getAuthStore() provides store access outside React** — a non-hook accessor function (e.g. useAuthStore.getState()) is available for use in API interceptors, utility functions, and other non-component code
- [ ] **store.getState() used for one-time reads** — non-React code reads the current state snapshot via getState(), not by subscribing to changes that would never trigger a re-render
- [ ] **No Zustand hooks called outside React component tree** — useAuthStore() and other hook-based selectors are never called in plain functions, API clients, or event handlers outside components
- [ ] **API client interceptors use getAuthStore() for token access** — the Axios request interceptor reads the current access token via getAuthStore().token, attaching it to outgoing requests
- [ ] **Zustand actions callable from anywhere via store.getState().action()** — logout, token refresh, and other actions can be triggered from API interceptors or utilities without needing a React component

## 5.5 TanStack Query Configuration

- [ ] **QueryClient created per-session with useState** — the QueryClient is instantiated inside a useState initializer in Providers.tsx, not as a module-level singleton that would be shared across server-side requests
- [ ] **Default staleTime set appropriately** — staleTime is configured (e.g. 5 minutes) so that frequently accessed data is served from cache without unnecessary refetches on every component mount
- [ ] **Retry logic skips 4xx errors** — the retry function returns false for 4xx HTTP status codes (client errors) and only retries on network failures or 5xx server errors
- [ ] **refetchOnWindowFocus disabled** — automatic refetching when the browser tab regains focus is turned off to prevent unexpected data refreshes and to favor explicit refetch triggers
- [ ] **Mutations have retry: 0** — mutation operations (POST, PUT, PATCH, DELETE) do not automatically retry to prevent duplicate side effects (double-creates, double-deletes)
- [ ] **throwOnError: false for graceful error handling** — mutations use throwOnError: false so errors are captured in the mutation result (isError, error) instead of propagating to error boundaries
- [ ] **gcTime configured to avoid memory leaks** — garbage collection time (formerly cacheTime) is set so that unused query data is cleaned up after a reasonable period (e.g. 10 minutes)

## 5.6 Query Key Architecture

- [ ] **All query keys centralized in lib/query-keys.ts** — a single queryKeys object defines every query key used in the application, preventing key collisions and enabling find-all-references
- [ ] **Keys are hierarchical** — query keys follow a namespace pattern (queryKeys.auth.user, queryKeys.business.detail(slug), queryKeys.members.list(businessSlug)) for organized cache management
- [ ] **Keys include parameters for cache differentiation** — parameterized keys (queryKeys.business.detail(slug)) produce unique cache entries for each slug, not sharing a single cache across all businesses
- [ ] **No string-literal query keys scattered in hook files** — hooks never use inline string arrays (['business', slug]); all keys come from the centralized queryKeys factory
- [ ] **queryKeys object exported as const** — the query keys object is typed with as const for full type inference, ensuring key typos are caught at compile time
- [ ] **Key factory pattern used consistently** — parameterized keys use factory functions (detail: (slug: string) => [..., slug]) that return typed tuples, not manually constructed arrays

## 5.7 Query Hook Patterns

- [ ] **Hooks in features/*/hooks/ wrap useQuery and useMutation** — each feature module has hook files (use-business-queries.ts, use-member-mutations.ts) that encapsulate TanStack Query usage
- [ ] **Each hook file is focused** — query hooks and mutation hooks are in separate files or clearly separated sections, not mixed together in a single large file
- [ ] **useInfiniteQuery used for paginated/infinite-scroll lists** — explore results, member lists, transaction lists, and other paginated data use useInfiniteQuery with proper page parameter handling
- [ ] **getNextPageParam handles cursor/offset pagination correctly** — the getNextPageParam function extracts the next page token or offset from the API response, returning undefined when no more pages exist
- [ ] **Mutation hooks include onSuccess/onError/onSettled callbacks** — mutations handle success (invalidate queries, show toast, navigate), error (show error toast), and settled (reset loading state) appropriately
- [ ] **Query hooks return typed data** — all useQuery and useMutation hooks have explicit TypeScript generic parameters or inferred types, never returning any or unknown data
- [ ] **enabled option used to conditionally fetch** — queries that depend on a parameter being available (slug, userId) use enabled: !!slug to prevent fetching with undefined/null parameters

## 5.8 Cache Invalidation

- [ ] **Mutations invalidate relevant query keys on success** — after a successful mutation (create member, update business), onSuccess calls queryClient.invalidateQueries with the appropriate query keys
- [ ] **Cross-feature invalidation uses query key namespaces** — when a mutation in one feature affects another feature's data, the broader namespace key is invalidated (queryKeys.members.all invalidates all member queries)
- [ ] **No manual queryClient.setQueryData unless for optimistic updates** — cache is updated by invalidation (refetch from server), not by manually setting data which could become stale or inconsistent
- [ ] **No stale data visible after mutations** — after creating, updating, or deleting a resource, the UI immediately reflects the change (via invalidation + refetch or optimistic update)
- [ ] **Invalidation is targeted, not global** — queryClient.invalidateQueries() is always called with a specific queryKey or queryFilter, never with no arguments (which would refetch everything)
- [ ] **Related queries invalidated together** — when a business is updated, both queryKeys.business.detail(slug) and queryKeys.business.list are invalidated to keep list and detail views consistent

## 5.9 Optimistic Updates

- [ ] **Optimistic updates rollback on error** — onMutate saves the previous cache value, onError restores it using queryClient.setQueryData with the saved value, ensuring seamless rollback
- [ ] **Optimistic data maintains correct types** — the optimistically inserted/updated data matches the full TypeScript type of the query response, no partial objects or missing required fields
- [ ] **No optimistic updates on complex multi-step mutations** — multi-step operations (create business + initialize RBAC + create membership) do not use optimistic updates due to partial-failure complexity
- [ ] **UI shows optimistic state immediately** — when an optimistic update is applied, the UI reflects the change without waiting for the server response, providing instant feedback
- [ ] **Rollback is seamless with no flicker** — if the mutation fails and rolls back, the UI transitions back to the previous state without a visible flash or jarring layout change

## 5.10 State & Store Testing

- [ ] **Zustand stores have dedicated test files** — auth-store.test.ts and membership-store.test.ts exist with comprehensive test coverage for all state transitions and actions
- [ ] **Tests verify state transitions** — each store action is tested to confirm it produces the correct next state (setUser updates user and isAuthenticated, clearUser resets to initial state)
- [ ] **TanStack Query hooks tested with mock API responses** — query hooks are tested using MSW or manual fetch mocks to verify data fetching, caching, error handling, and refetch behavior
- [ ] **Tests reset store state between test cases** — each test case starts from a clean initial state using store.setState(initialState) or by recreating the store, preventing cross-test pollution
- [ ] **Store initial state is tested** — a test verifies that a freshly created store has the expected default values (user: null, isAuthenticated: false, token: null)
- [ ] **Store actions with side effects are tested** — actions that trigger navigation, API calls, or other stores (e.g. logout clears auth + membership stores) are tested with appropriate mocks
