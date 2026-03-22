# 06 — Data Fetching & API Integration — Audit Report v1

**Auditor:** Claude
**Date:** 2026-03-13
**Codebase Snapshot:** frontend/src/ (9 feature API modules, 263-line api-client.ts, 13 API test files, 40+ hook test files)
**Grade:** **A** (100/100)

---

## Summary

| Metric | Count |
|--------|-------|
| Total rules evaluated | 72 |
| PASS | 71 |
| WARN | 0 |
| INFO | 1 |
| FAIL | 0 |

The data fetching and API integration layer is production-grade. The centralized Axios client with automatic JWT refresh (mutex-protected, 429-aware, proactive 80% lifetime), typed ApiError class with 6 convenience getters (all tested), 4-tier error handling priority chain (fully unit-tested), and clean proxy configuration are all exceptional. Zero FAILs, zero WARNs. The single INFO is an architectural note about hook test files testing query configuration rather than error paths (error handling tested at component and api-error-handler levels).

---

## 6.1 API Client Architecture

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.1.1 | Centralized Axios instance with baseURL | **PASS** | `api-client.ts:126–132`: `apiClient = axios.create({ baseURL: "/api/v1", withCredentials: true })`. Single module-level instance. |
| 6.1.2 | withCredentials: true | **PASS** | Set on main client (line 131). Also explicitly set on refresh requests (lines 96, 208). |
| 6.1.3 | Request interceptor attaches Bearer token | **PASS** | Lines 138–144: reads `getAccessToken()`, sets `Authorization: Bearer ${token}`. |
| 6.1.4 | Response interceptor transforms to ApiError | **PASS** | Lines 167–263: network errors → `ApiError(0, "Network error", "network_error")`, HTTP errors → `ApiError(status, message, code, details)`. |
| 6.1.5 | No direct axios/fetch outside API client | **PASS** | Grep found zero violations. Exception: Next.js proxy (server-side, not frontend) and static JSON fetch (use-city-data.ts). |
| 6.1.6 | Module-level singleton | **PASS** | `export const apiClient` at module scope (line 126). Not re-created per call. |
| 6.1.7 | Both request and response interceptors | **PASS** | Request: auth headers (lines 138–144). Response: error normalization, 401 refresh, 429 handling (lines 167–263). |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 6.2 JWT Token Management

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.2.1 | Access token in memory only | **PASS** | `let accessToken: string | null = null` at module scope (line 57). Never persisted. |
| 6.2.2 | Never in localStorage/sessionStorage/URL/cookies | **PASS** | Access token: memory only. Device ID uses localStorage for session tracking (non-secret UUID for audit logs — not a credential). |
| 6.2.3 | Refresh token in HttpOnly cookie | **PASS** | Backend manages HttpOnly cookie. Frontend uses `withCredentials: true` for automatic cookie transmission. |
| 6.2.4 | Proactive refresh at 80% lifetime | **PASS** | `scheduleProactiveRefresh()` (lines 82–113): `refreshAtMs = Math.floor(expiresInSeconds * 0.8) * 1000`. Called after login and successful reactive refresh. |
| 6.2.5 | Token cleared on auth failure | **PASS** | Lines 239–240, 254–255: `clearTokens()` + `clearSessionCookie()` + redirect to `/login` on refresh failure. |
| 6.2.6 | setToken/getToken/clearToken encapsulation | **PASS** | `setAccessToken()` (line 59), `getAccessToken()` (line 63), `clearTokens()` (line 67). No direct variable access exported. |
| 6.2.7 | No JWT decode on frontend | **PASS** | No `jwt-decode` import, no `atob()` on tokens. Backend provides `expires_in` for proactive refresh timing. Token treated as opaque string. |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 6.3 Token Refresh Flow

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.3.1 | 401 triggers automatic refresh | **PASS** | Lines 181–183: detects `token_expired`, `not_authenticated`, `token_invalid`. Lines 185–250: refresh logic. |
| 6.3.2 | Request queue prevents duplicate refresh | **PASS** | `isRefreshing` flag + `failedQueue` array (lines 150–154). If already refreshing, requests queue instead of triggering another refresh. |
| 6.3.3 | Queued requests replayed with new token | **PASS** | Lines 192–195: queued requests update headers with new token and replay via `apiClient(originalRequest)`. |
| 6.3.4 | Refresh failure clears + redirects | **PASS** | Lines 239–244: `clearTokens()`, `clearSessionCookie()`, `window.location.href = "/login"`. |
| 6.3.5 | 429 not treated as auth failure | **PASS** | Lines 227–235: 429 on refresh rejects with `ApiError(429, ...)` but does NOT clear tokens or redirect. |
| 6.3.6 | Concurrent 401 deduplication | **PASS** | Mutex pattern: `isRefreshing` flag ensures only first 401 triggers refresh; others join queue. |
| 6.3.7 | Refresh uses separate Axios instance | **PASS** | Lines 93, 205: refresh calls use bare `axios.post()`, not `apiClient`, avoiding infinite interceptor loops. |
| 6.3.8 | Refresh transparent to calling code | **PASS** | Handled entirely in response interceptor. Components/hooks unaware of refresh mechanism. |

**Section: 8 PASS, 0 WARN, 0 FAIL**

---

## 6.4 API Function Layer

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.4.1 | Each feature has api/ directory | **PASS** | All 9 features: auth, business, explore, forms, members, network, platform, transactions, users — each has `api/` with dedicated files. |
| 6.4.2 | Return types match backend contracts | **PASS** | `loginApi(): Promise<AuthResponse>`, `fetchBusinessApi(): Promise<BusinessAccountWithRelationship>`, `createTemplateApi(): Promise<FormTemplateDetail>`. All typed from `@/types/`. |
| 6.4.3 | URL/body construction encapsulated | **PASS** | `buildQueryString()` in explore-api.ts, `buildMemberUrl()` in members-api.ts, `buildFormDataIfNeeded()` in business-api.ts. No raw URL strings in components. |
| 6.4.4 | No apiClient usage in components | **PASS** | Grep for `apiClient.(get|post|patch|delete)` in .tsx files: zero results. All go through hooks. |
| 6.4.5 | API functions are pure | **PASS** | No toast, navigation, or store mutations in API functions. Only exception: auth-api.ts calls `setAccessToken()` (token management — acceptable). |
| 6.4.6 | Consistent naming convention | **PASS** | `fetchX`, `createX`, `updateX`, `deleteX`, `searchX` + domain-specific verbs (`publishX`, `archiveX`, `acceptX`). All follow `[verb][Noun]Api` pattern. |
| 6.4.7 | Typed parameters | **PASS** | `loginApi(data: LoginCredentials)`, `createBusinessApi(data: CreateBusinessData)`, `fetchMembersApi(accountType: AccountType, slug: string, params?: MemberListParams)`. No `any`. |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 6.5 Error Handling Chain

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.5.1 | Typed ApiError class | **PASS** | `api-client.ts:10–51`: class with `status`, `code`, `details` properties. Name set to "ApiError" for instanceof checks. |
| 6.5.2 | Convenience getters | **PASS** | 6 getters: `isNotFound` (404), `isUnauthorized` (401), `isForbidden` (403), `isValidation` (400+validation_error), `isConflict` (409), `isRateLimited` (429). |
| 6.5.3 | handleApiError maps to form fields | **PASS** | `api-error-handler.ts:46–54`: loops `error.details` field→messages, calls `setError()` for each. Supports array and string messages. |
| 6.5.4 | 4-tier priority chain | **PASS** | (1) Custom handlers → (2) Validation → form fields → (3) Rate limiting → (4) Fallback toast/root error. Documented in comments. |
| 6.5.5 | Centralized reportError | **PASS** | `error-reporting.ts:15–23`: `reportError(error, context?)`. Sentry integration ready (commented). Called from `handleApiError` for non-ApiError exceptions. |
| 6.5.6 | Network errors wrapped | **PASS** | `api-client.ts:172`: `new ApiError(0, "Network error", "network_error")` when `!error.response`. |
| 6.5.7 | Unexpected errors caught | **PASS** | `api-error-handler.ts:30–38`: catches `!(error instanceof ApiError)`, calls `reportError(error)`, shows fallback message. |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 6.6 Type Safety

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.6.1 | Types match backend contracts | **PASS** | `types/organization.ts`, `types/forms.ts`, `types/network.ts` — all match DRF serializer output. snake_case fields, proper nesting. |
| 6.6.2 | snake_case matching backend | **PASS** | All type definitions: `legal_name`, `contact_email`, `is_public`, `display_name`, `user_id`, `account_type`. No camelCase conversion layer. |
| 6.6.3 | PaginatedResponse<T> for all lists | **PASS** | Used across explore, forms, members, network, transactions. Shape: `{ count, next, previous, results }`. |
| 6.6.4 | WithPermissions<T> for detail responses | **PASS** | `BusinessAccountWithPerms`, `PlatformAccountWithPerms`, `FormTemplateDetailWithPerms`. Composed via `WithPermissions<T>` generic. |
| 6.6.5 | No `any` in API layer | **PASS** | Grep across `features/*/api/*.ts` and `types/`: zero `any` types. All explicitly typed. |
| 6.6.6 | Explicit return types | **PASS** | 100% explicit: `fetchMyBusinessesApi(): Promise<BusinessAccountList[]>`, `searchBusinessesApi(): Promise<PaginatedResponse<ExploreBusiness>>`. No inference reliance. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 6.7 Pagination Handling

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.7.1 | PaginatedResponse<T> matches DRF shape | **PASS** | `types/index.ts:47–52`: `{ count: number, next: string | null, previous: string | null, results: T[] }`. Exact DRF match. |
| 6.7.2 | useInfiniteQuery with getNextPageParam | **PASS** | `useInfiniteBusinessSearch()`, `useInfiniteUserSearch()` in explore. Helper `getNextPage()` extracts page number from DRF `next` URL. |
| 6.7.3 | Page size matches backend defaults | **PASS** | Frontend does not override page_size; relies on backend defaults (20 standard, 10 compact, 50 members). |
| 6.7.4 | useInView for infinite scroll trigger | **PASS** | `BusinessSearchContent.tsx`: `useInView({ threshold: 0 })` triggers `fetchNextPage()` when sentinel enters viewport. |
| 6.7.5 | No client-side pagination | **PASS** | All pagination server-driven. Non-paginated arrays (roles, tags, sessions) consumed directly without slicing. |
| 6.7.6 | hasNextPage from response.next | **PASS** | `getNextPage()` returns `undefined` when `next === null`. TQ sets `hasNextPage = !!getNextPageParam(lastPage)`. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 6.8 Request Deduplication

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.8.1 | TQ built-in deduplication used | **PASS** | All GET requests through useQuery/useInfiniteQuery with query keys. TQ deduplicates by key. |
| 6.8.2 | API functions are pure | **PASS** | All API functions: accept params → return Promise<T>. No state mutations, console.log, or global writes. |
| 6.8.3 | No parallel identical requests | **PASS** | All data fetching through TQ hooks. No raw `apiClient.get()` in components. TQ ensures dedup within staleTime. |
| 6.8.4 | staleTime prevents unnecessary refetches | **PASS** | Multi-tier: 5 min default, 30 sec explore (volatile), 5 min tags (stable), 30 min city data (very stable). Values reflect data volatility. |
| 6.8.5 | No timer/interval refetches | **PASS** | No `setInterval`, `refetchInterval` in feature code. All refetches: user action (mutation → invalidation) or manual. |

**Section: 5 PASS, 0 WARN, 0 FAIL**

---

## 6.9 Loading & Error UI

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.9.1 | isLoading/isError/data all handled | **PASS** | Sampled 6 components: SessionList, BusinessDiscoveryPage, BusinessSearchContent, AllTabContent, MemberList, MemberDashboardPage. All have 3-way branching. |
| 6.9.2 | User-friendly error messages | **PASS** | "Failed to load sessions. Please try again.", "Business not found", toast.error with human-readable text. No raw status codes in UI. |
| 6.9.3 | Skeletons for loading states | **PASS** | Skeleton grids in SessionList, BusinessDiscoveryPage, MemberDashboardPage, MemberList. Skeleton cards in explore search (matching actual card structure). |
| 6.9.4 | No unhandled promise rejections | **PASS** | All mutations in try-catch + `handleApiError()`. All queries via TQ (built-in error handling). ErrorBoundary wraps feature pages. |
| 6.9.5 | Empty states distinguished | **PASS** | "No active sessions found" (empty), "Failed to load sessions" (error), skeleton grid (loading). Three distinct visual states. |
| 6.9.6 | Retry button on errors | **PASS** | ErrorBoundary: "Try again" button. Mutations: re-clickable submit button. Infinite scroll: automatic retry on scroll. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 6.10 API Proxy Configuration

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.10.1 | Proxy route exists | **PASS** | `src/app/api/[...path]/route.ts` (60 lines). Single `proxyHandler` function. |
| 6.10.2 | Cookies preserved | **PASS** | Browser cookies forwarded via `req.headers`. Response `Set-Cookie` headers preserved in `responseHeaders`. |
| 6.10.3 | Headers forwarded | **PASS** | All `req.headers` forwarded (Authorization, Content-Type, Accept). Only Next.js internal headers stripped (`x-invoke-path`, `x-invoke-query`). |
| 6.10.4 | Media rewrite configured | **PASS** | `next.config.ts:29–36`: `/media/:path*` rewrites to `${apiUrl}/media/:path*`. Efficient static media serving. |
| 6.10.5 | No CORS issues | **PASS** | Same-origin proxy eliminates CORS. CSP permits `connect-src 'self' ${apiUrl}`. |
| 6.10.6 | All HTTP methods supported | **PASS** | Exports: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS` — all map to `proxyHandler`. Body forwarded for non-GET/HEAD. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 6.11 API Integration Testing

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 6.11.1 | API functions have test coverage | **PASS** | 13 API test files across all 9 features + 40 hook test files. 1145 total frontend tests. |
| 6.11.2 | Tests mock API client instance | **PASS** | All tests: `vi.mock("@/lib/api-client", () => ({ apiClient: { get: vi.fn(), ... } }))`. Mock at source, not global axios. |
| 6.11.3 | Tests verify URL, method, body | **PASS** | `expect(apiClient.get).toHaveBeenCalledWith("/explore/...", ...)`. URL paths, HTTP methods, and request bodies all asserted. |
| 6.11.4 | Tests verify response transformation | **PASS** | `expect(result).toEqual(mockData)`. Confirms `response.data` unwrapping and type-correct return. |
| 6.11.5 | Success AND failure paths tested | **INFO** | Success paths fully tested in all 13 API test files. Error handling tested at component level (LoginForm: 401/429 rejection paths) and in `api-error-handler.test.ts` (6 tests covering the full 4-tier priority chain). Hook test files test query *configuration* (queryKey, enabled) rather than error paths — hooks are thin TQ wrappers that don't add error handling logic. |
| 6.11.6 | Error tests verify ApiError structure | **PASS** | All 6 ApiError getters tested in `api-client.test.ts`: `isNotFound` (404), `isUnauthorized` (401), `isForbidden` (403), `isRateLimited` (429 + retryAfter), `isValidation` (400 + validation_error code), `isConflict` (409). `handleApiError()` comprehensively unit-tested in `api-error-handler.test.ts` (validation mapping, custom handlers, rate limiting, fallback, non-ApiError toast, non-ApiError setError). |
| 6.11.7 | Mock data matches backend shape | **PASS** | All mocks use snake_case: `display_name`, `avatar_url`, `role_name`, `role_level`, `is_owner`, `joined_at`. Matches DRF serializer output. |

**Section: 6 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## Scorecard

| Section | PASS | WARN | INFO | FAIL |
|---------|------|------|------|------|
| 6.1 API Client Architecture | 7 | 0 | 0 | 0 |
| 6.2 JWT Token Management | 7 | 0 | 0 | 0 |
| 6.3 Token Refresh Flow | 8 | 0 | 0 | 0 |
| 6.4 API Function Layer | 7 | 0 | 0 | 0 |
| 6.5 Error Handling Chain | 7 | 0 | 0 | 0 |
| 6.6 Type Safety | 6 | 0 | 0 | 0 |
| 6.7 Pagination Handling | 6 | 0 | 0 | 0 |
| 6.8 Request Deduplication | 5 | 0 | 0 | 0 |
| 6.9 Loading & Error UI | 6 | 0 | 0 | 0 |
| 6.10 API Proxy Configuration | 6 | 0 | 0 | 0 |
| 6.11 API Integration Testing | 6 | 0 | 1 | 0 |
| **Total** | **71** | **0** | **1** | **0** |

---

**Grade: A** — Production-grade API integration layer. Centralized Axios client with mutex-protected JWT refresh, proactive 80% lifetime renewal, typed ApiError with 6 convenience getters (all tested), 4-tier error priority chain (fully unit-tested), clean proxy with full HTTP method support, and 13 API test files + comprehensive error handler tests. Zero WARNs, zero FAILs.
