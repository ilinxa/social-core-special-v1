# 05 — State Management — Audit Report v1

**Auditor:** Claude
**Date:** 2026-03-13
**Codebase Snapshot:** frontend/src/ (2 Zustand stores, 17 mutation hook files, 19 query/mutation test files, centralized query-keys.ts)
**Grade:** **A** (100/100)

---

## Summary

| Metric | Count |
|--------|-------|
| Total rules evaluated | 62 |
| PASS | 57 |
| WARN | 0 |
| INFO | 5 |
| FAIL | 0 |

State management is the strongest area audited so far. The Zustand/TanStack Query boundary is perfectly clean — Zustand holds only auth and navigation state, TQ handles all server data. Selector patterns use `useShallow` correctly, non-React access via `getState()` is properly implemented, and all 17 mutation hooks invalidate targeted query keys on success. Zero FAILs, zero WARNs. The 5 INFOs are architectural notes: no optimistic updates implemented (correct for current complexity), and immer middleware not enabled (stores use only flat `set()` calls).

---

## 5.1 State Architecture

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.1.1 | Client/server state separated | **PASS** | Zustand: auth tokens, user object, membership list. TQ: all API data (business, forms, transactions). Clear boundary. |
| 5.1.2 | No API data duplicated in Zustand | **PASS** | auth-store holds only User (auth context), membership-store holds Membership[] (navigation/quota). No business details, transactions, or other server entities in stores. |
| 5.1.3 | TQ not used for client-side state | **PASS** | Modal open/close, cooldown timers, form submission state all use `useState`. TQ exclusively for server data. |
| 5.1.4 | Form state in react-hook-form | **PASS** | All 13 forms use `useForm()` + `zodResolver`. No Zustand or TQ for form inputs. |
| 5.1.5 | Filters/pagination in URL params | **PASS** | ExplorePage uses `useSearchParams()` → params passed to TQ infinite queries. Page numbers managed by TQ `pageParam`. |
| 5.1.6 | Component-local state uses useState | **PASS** | Dialog open state, button loading, cooldown timers all use `useState`. No UI toggles in Zustand. |
| 5.1.7 | Derived values computed, not stored | **PASS** | `getBusinessMemberships`, `getPlatformMembership` computed on-demand with `useShallow`, not pre-stored. |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 5.2 Zustand Store Design

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.2.1 | Stores typed with state+actions interface | **PASS** | `AuthState` + `AuthActions` → `AuthStore`. `MembershipState` + `MembershipActions` → composed type. Full IntelliSense. |
| 5.2.2 | Immer middleware for immutable updates | **INFO** | `immer@^11.1.4` installed but stores use `devtools` only, not immer wrapping. Both stores (auth-store, membership-store) use exclusively flat `set()` calls with no nested mutations. Immer middleware would add bundle size and complexity without benefit — revisit only if stores grow to need nested draft-style mutations. |
| 5.2.3 | Devtools middleware enabled | **PASS** | Both stores: `devtools(..., { name: "auth-store" })`, `devtools(..., { name: "membership-store" })`. Redux DevTools integration. |
| 5.2.4 | State/actions clearly separated | **PASS** | Explicit interface separation: `AuthState` separate from `AuthActions`, combined via type union. Same for membership. |
| 5.2.5 | Initial state extractable for testing | **PASS** | `const initialState: AuthState = {...}` defined outside `create()`. Tests reset via `useAuthStore.setState(...)`. |
| 5.2.6 | No derived values/redundancy in stores | **PASS** | Membership selectors computed on-demand. No stale copies, no redundant flags. |
| 5.2.7 | Store files in src/stores/ | **PASS** | `src/stores/auth-store.ts`, `src/stores/membership-store.ts`. Correct location. |

**Section: 6 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 5.3 Selector Patterns

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.3.1 | Purpose-specific selector hooks exported | **PASS** | `useUser()`, `useIsAuthenticated()`, `useIsInitialized()`, `useMemberships()`, `useBusinessMemberships()`, `usePlatformMembership()`, `useMembershipsLoaded()`. Focused API. |
| 5.3.2 | No raw store access in components | **PASS** | Components use selector hooks. One exception: BusinessGuard uses `useMembershipStore(s => s.memberships.find(...))` for custom filtering — acceptable for one-time operation. |
| 5.3.3 | useShallow for arrays/objects | **PASS** | `useShallow(getBusinessMemberships)` in membership-store. Sole array-returning selector correctly wrapped. |
| 5.3.4 | Stable selector references | **PASS** | Primary selectors return primitives (`boolean`) or object references (`User`). Array selector uses `useShallow`. No reference leaks. |
| 5.3.5 | .filter()/.map()/.reduce() with useShallow | **PASS** | `getBusinessMemberships` uses `.filter()` and is wrapped with `useShallow`. Correct pattern. |
| 5.3.6 | No pre-stored computed values | **PASS** | Membership filtering computed on-demand. Auth state is raw. Permissions fetched via API. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 5.4 Non-React Access

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.4.1 | getState() accessor available | **PASS** | `getAuthStore()` and `getMembershipStore()` exported using `useStore.getState()`. Used in API client and guards. |
| 5.4.2 | One-time reads, no subscriptions | **PASS** | API client uses one-time `getAccessToken()` in interceptor. Guards use `getState()` for single-shot membership refetch. No subscriptions in non-React code. |
| 5.4.3 | No hooks outside React tree | **PASS** | `api-client.ts` uses module-level `let accessToken` variable with `getAccessToken()`/`setAccessToken()`, not hooks. Guards use `getState()` in effect callbacks. |
| 5.4.4 | API interceptor accesses token | **PASS** | `api-client.ts` maintains in-memory token variable. Request interceptor calls `getAccessToken()` to attach Bearer token. Non-hook access pattern. |
| 5.4.5 | Store actions callable from non-React | **PASS** | Guards: `useMembershipStore.getState().setMemberships(...)`. Auth mutations: `useAuthStore.getState().setUser(...)` in TQ callbacks. |

**Section: 5 PASS, 0 WARN, 0 FAIL**

---

## 5.5 TanStack Query Configuration

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.5.1 | QueryClient per-session via useState | **PASS** | `providers.tsx`: `const [queryClient] = useState(() => createQueryClient())`. Per-instance creation, not module singleton. |
| 5.5.2 | Default staleTime configured | **PASS** | `query-client.ts`: `staleTime: 5 * 60 * 1000` (5 minutes). Sensible global default. |
| 5.5.3 | Retry skips 4xx errors | **PASS** | Retry function explicitly skips 400, 401, 403, 404, 409, 422. Only retries network/5xx errors. Max 3 retries. |
| 5.5.4 | refetchOnWindowFocus disabled | **PASS** | Global: `refetchOnWindowFocus: false`. Exception: membership queries use `"always"` with documented justification. |
| 5.5.5 | Mutation retry = 0 | **PASS** | `mutation: { retry: 0 }`. No duplicate side effects. |
| 5.5.6 | throwOnError false for mutations | **PASS** | No explicit `throwOnError` set. TQ v5 defaults to `false` for mutations. Correct behavior. |
| 5.5.7 | gcTime configured | **PASS** | Global `gcTime: 10 * 60 * 1000` (10 min) set in `query-client.ts`. Exceeds staleTime (5 min) to allow back-navigation without re-fetch. Local overrides: membership (30 min). |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 5.6 Query Key Architecture

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.6.1 | Keys centralized in query-keys.ts | **PASS** | All keys defined in `src/lib/query-keys.ts`. All features import from the centralized factory. |
| 5.6.2 | Hierarchical namespace pattern | **PASS** | `queryKeys.auth.sessions()`, `queryKeys.business.detail(slug)`, `queryKeys.explore.businesses(params)`, `queryKeys.members.list()`. Consistent namespace structure. |
| 5.6.3 | Parameters included in keys | **PASS** | `detail(slug)` → `[..., "detail", slug]`, `list(accountType, slug, params)` → `[..., "list", accountType, slug, params]`. Proper cache differentiation. |
| 5.6.4 | No scattered string-literal keys | **PASS** | All query keys use centralized factories from `query-keys.ts`. `requiredForm(transactionId)` factory covers the previously inline `["transactions", "required-form", transactionId]` key used in TransactionDetailPage, AcceptWithFormDialog, and ResubmitFormPanel. |
| 5.6.5 | Keys typed with as const | **PASS** | All factory functions return `[...] as const`. Full type inference. |
| 5.6.6 | Factory functions for parameterized keys | **PASS** | `detail: (slug: string) => [..., "detail", slug] as const`. Typed tuples throughout. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 5.7 Query Hook Patterns

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.7.1 | TQ hooks wrapped in features/*/hooks/ | **PASS** | Direct TQ imports only in hook files. Components import from hooks (e.g., `useTransactionDetail`, `useCreateInvitation`). |
| 5.7.2 | Queries and mutations separated | **PASS** | `use-*-queries.ts` for queries, `use-*-mutations.ts` for mutations. Clear separation across all features. |
| 5.7.3 | useInfiniteQuery for paginated lists | **PASS** | `useInfiniteBusinessSearch()`, `useInfiniteUserSearch()` in explore. Components use `fetchNextPage()` on scroll intersection. |
| 5.7.4 | getNextPageParam handles pagination | **PASS** | Helper `getNextPage()` extracts page number from DRF `next` URL. Returns `undefined` when no next page. Correct for useInfiniteQuery. |
| 5.7.5 | Mutation hooks have callbacks | **PASS** | All mutations use `onSuccess` for invalidation. Some add `onError` for toast notifications. Consistent callback structure. |
| 5.7.6 | Typed query/mutation hooks | **PASS** | Strong type inference from API functions. No `any` types detected. Explicit generic parameters where needed. |
| 5.7.7 | enabled flag for optional params | **PASS** | `enabled: !!slug` (member list/detail), `enabled: !!slug && !!membershipId`, `enabled: (q?.length ?? 0) >= 1` (tag suggestions), `enabled: !!country` (cities). |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 5.8 Cache Invalidation

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.8.1 | Mutations invalidate on success | **PASS** | All 17 mutation hook files implement `onSuccess` with `invalidateQueries`. Example: `useCreateBusiness()` → `queryKeys.business.my()` + `queryKeys.users.memberships()`. |
| 5.8.2 | Cross-feature invalidation via namespaces | **PASS** | `useCreateBusiness()` invalidates business + membership keys. `useArchiveBusiness()` cascades to 3 features. `useLeaveMember()` invalidates members + memberships. |
| 5.8.3 | setQueryData only for data hydration | **PASS** | `setQueryData` in 4 files, all for post-auth hydration or paired with fallback invalidation. No standalone setQueryData without hedging. |
| 5.8.4 | No stale data after mutations | **PASS** | Immediate `onSuccess` invalidations. TQ auto-refetches after invalidation. `queryClient.clear()` on logout (hard reset). |
| 5.8.5 | No global invalidation | **PASS** | All invalidations pass `{ queryKey: ... }`. `queryClient.clear()` only on logout (3 occurrences — intentional). |
| 5.8.6 | List + detail invalidated together | **PASS** | Member mutations: `members.list()` + `members.detail()`. Form mutations: `templates.list()` + `templates.detail()`. Transaction mutations: `transactions.all` + `transactions.detail()`. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 5.9 Optimistic Updates

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.9.1 | Optimistic updates rollback on error | **INFO** | No optimistic updates implemented. All mutations use standard invalidation pattern (onSuccess → invalidateQueries → TQ refetch). |
| 5.9.2 | Optimistic data matches types | **INFO** | N/A — no optimistic updates. |
| 5.9.3 | Complex mutations avoid optimistic | **PASS** | No mutations use optimistic updates. Complex operations (approve transaction, process response) correctly use standard invalidation. |
| 5.9.4 | Instant UI feedback | **INFO** | Loading states via `isPending` + toast notifications provide UX feedback. Standard TQ refresh pattern. |
| 5.9.5 | Seamless rollback | **INFO** | N/A — no optimistic rollback needed. |

**Section: 1 PASS, 0 WARN, 4 INFO, 0 FAIL**

---

## 5.10 State & Store Testing

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 5.10.1 | Store test files exist | **PASS** | `auth-store.test.ts` (118 lines), `membership-store.test.ts` (151 lines). Comprehensive suites. |
| 5.10.2 | State transitions verified | **PASS** | `setUser()`, `clearUser()`, `setInitialized()` all tested with assertion on next state. `setMemberships()`, `clearMemberships()` verified. All actions covered. |
| 5.10.3 | TQ hooks tested with mocks | **PASS** | 19 test files across features. All use `vi.mock()` for API functions. Tests verify calls, mutation behavior, and cache invalidation. |
| 5.10.4 | Store state reset between tests | **PASS** | `beforeEach` with `useAuthStore.setState(...)` resets to initial state. Mutation tests use `vi.clearAllMocks()`. Fresh QueryClient per test. |
| 5.10.5 | Initial state tested | **PASS** | Both stores: "has correct initial state" test verifying `user: null`, `isAuthenticated: false`, `memberships: []`, `isLoaded: false`. |
| 5.10.6 | Side effect actions tested with mocks | **PASS** | Login: mocks `router.push`, verifies `setUser` + `setMemberships`. Logout: mocks `clearUser`, `clearMemberships`, `router.push`. OAuth: mocks `window.location.href`. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## Scorecard

| Section | PASS | WARN | INFO | FAIL |
|---------|------|------|------|------|
| 5.1 State Architecture | 7 | 0 | 0 | 0 |
| 5.2 Zustand Store Design | 6 | 0 | 1 | 0 |
| 5.3 Selector Patterns | 6 | 0 | 0 | 0 |
| 5.4 Non-React Access | 5 | 0 | 0 | 0 |
| 5.5 TanStack Query Configuration | 7 | 0 | 0 | 0 |
| 5.6 Query Key Architecture | 6 | 0 | 0 | 0 |
| 5.7 Query Hook Patterns | 7 | 0 | 0 | 0 |
| 5.8 Cache Invalidation | 6 | 0 | 0 | 0 |
| 5.9 Optimistic Updates | 1 | 0 | 4 | 0 |
| 5.10 State & Store Testing | 6 | 0 | 0 | 0 |
| **Total** | **57** | **0** | **5** | **0** |

---

**Grade: A** — Exceptional state management architecture. Perfect Zustand/TanStack Query boundary, useShallow applied correctly, non-React access patterns safe, all mutations invalidate targeted query keys, comprehensive test coverage across 19 hook test files + 2 store test files, explicit global gcTime configured, and all query keys centralized via factories. Zero WARNs, zero FAILs.
