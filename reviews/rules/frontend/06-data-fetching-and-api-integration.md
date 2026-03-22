# 06 — Data Fetching & API Integration Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 6.1 API Client Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 6.1.1 | FAIL if no centralized Axios instance exists in lib/api-client.ts with baseURL configured | PASS/FAIL |
| 6.1.2 | FAIL if withCredentials is not set to true on the Axios instance | PASS/FAIL |
| 6.1.3 | FAIL if request interceptor does not attach Bearer token from in-memory store | PASS/FAIL |
| 6.1.4 | FAIL if response interceptor does not transform errors into typed ApiError instances | PASS/FAIL |
| 6.1.5 | FAIL if direct axios or fetch usage exists outside the configured API client | PASS/FAIL |
| 6.1.6 | WARN if the Axios instance is re-created per call instead of being a module-level singleton | PASS/WARN |
| 6.1.7 | FAIL if interceptors do not handle both request (auth headers) and response (error normalization) | PASS/FAIL |

## 6.2 JWT Token Management

| ID | Rule | Verdict |
|----|------|---------|
| 6.2.1 | FAIL if access token is stored anywhere other than a module-level variable in memory | PASS/FAIL |
| 6.2.2 | FAIL if access token appears in localStorage, sessionStorage, URL params, or cookies | PASS/FAIL |
| 6.2.3 | FAIL if refresh token is not in an HttpOnly cookie (set by backend, not readable by JS) | PASS/FAIL |
| 6.2.4 | WARN if proactive refresh is not implemented at ~80% of token lifetime | PASS/WARN |
| 6.2.5 | FAIL if token is not cleared on auth failure (401 after failed refresh) | PASS/FAIL |
| 6.2.6 | FAIL if token access is not encapsulated via setToken/getToken/clearToken functions | PASS/FAIL |
| 6.2.7 | FAIL if JWT payload is decoded/parsed client-side for security decisions | PASS/FAIL |

## 6.3 Token Refresh Flow

| ID | Rule | Verdict |
|----|------|---------|
| 6.3.1 | FAIL if 401 response does not trigger automatic token refresh in interceptor | PASS/FAIL |
| 6.3.2 | FAIL if multiple simultaneous 401s trigger multiple refresh requests (no queue/mutex) | PASS/FAIL |
| 6.3.3 | FAIL if queued requests are not replayed with new token after successful refresh | PASS/FAIL |
| 6.3.4 | FAIL if refresh failure does not clear tokens and redirect to login | PASS/FAIL |
| 6.3.5 | WARN if 429 on refresh endpoint is treated as auth failure instead of rate-limit retry | PASS/WARN |
| 6.3.6 | FAIL if concurrent 401s trigger duplicate refresh attempts (missing deduplication) | PASS/FAIL |
| 6.3.7 | WARN if refresh request uses the same interceptor chain (risk of infinite loops) | PASS/WARN |
| 6.3.8 | WARN if token refresh is visible to calling code (should be transparent) | PASS/WARN |

## 6.4 API Function Layer

| ID | Rule | Verdict |
|----|------|---------|
| 6.4.1 | FAIL if features do not have dedicated api/ directories with API files | PASS/FAIL |
| 6.4.2 | FAIL if API functions return types do not match backend serializer contracts | PASS/FAIL |
| 6.4.3 | WARN if URL formatting and request body construction are not encapsulated in API functions | PASS/WARN |
| 6.4.4 | FAIL if components call apiClient.get/post directly instead of using API functions | PASS/FAIL |
| 6.4.5 | FAIL if API functions have side effects (store mutations, navigation, toasts) | PASS/FAIL |
| 6.4.6 | WARN if API functions do not follow consistent naming (fetchX, createX, updateX, deleteX, searchX) | PASS/WARN |
| 6.4.7 | FAIL if API function parameters are untyped (any, Record<string, unknown>) | PASS/FAIL |

## 6.5 Error Handling Chain

| ID | Rule | Verdict |
|----|------|---------|
| 6.5.1 | FAIL if backend errors are not wrapped in a typed ApiError class | PASS/FAIL |
| 6.5.2 | WARN if ApiError lacks convenience getters (isNotFound, isUnauthorized, isForbidden, etc.) | PASS/WARN |
| 6.5.3 | FAIL if handleApiError does not map validation errors to react-hook-form field errors | PASS/FAIL |
| 6.5.4 | WARN if error handling lacks a priority chain (custom handlers → validation → rate limit → fallback) | PASS/WARN |
| 6.5.5 | WARN if errors are not reported to a centralized reportError function | PASS/WARN |
| 6.5.6 | FAIL if network errors are not wrapped as ApiError(0, "Network error", "network_error") | PASS/FAIL |
| 6.5.7 | WARN if unexpected errors (JSON parse, type errors) are not caught and wrapped | PASS/WARN |

## 6.6 Type Safety

| ID | Rule | Verdict |
|----|------|---------|
| 6.6.1 | FAIL if request/response types do not match backend API contracts | PASS/FAIL |
| 6.6.2 | FAIL if API types use camelCase instead of snake_case matching backend convention | PASS/FAIL |
| 6.6.3 | FAIL if PaginatedResponse<T> is not used for all list endpoints | PASS/FAIL |
| 6.6.4 | WARN if WithPermissions<T> is not used for detail response types with _permissions | PASS/WARN |
| 6.6.5 | FAIL if any types in the API layer are typed as `any` | PASS/FAIL |
| 6.6.6 | WARN if API function return types are left to inference instead of explicitly declared | PASS/WARN |

## 6.7 Pagination Handling

| ID | Rule | Verdict |
|----|------|---------|
| 6.7.1 | FAIL if PaginatedResponse<T> does not match DRF shape (count, next, previous, results) | PASS/FAIL |
| 6.7.2 | FAIL if paginated lists do not use useInfiniteQuery with getNextPageParam | PASS/FAIL |
| 6.7.3 | WARN if frontend page size does not match backend defaults | PASS/WARN |
| 6.7.4 | FAIL if infinite scroll does not use useInView/IntersectionObserver for triggering | PASS/FAIL |
| 6.7.5 | WARN if client-side pagination is applied to unpaginated data | PASS/WARN |
| 6.7.6 | FAIL if hasNextPage is calculated incorrectly (should be response.next !== null) | PASS/FAIL |

## 6.8 Request Deduplication

| ID | Rule | Verdict |
|----|------|---------|
| 6.8.1 | PASS if TanStack Query's built-in deduplication is relied upon for GET requests | PASS/FAIL |
| 6.8.2 | FAIL if API functions cause side effects when called multiple times | PASS/FAIL |
| 6.8.3 | WARN if parallel identical requests are not deduplicated by TQ | PASS/WARN |
| 6.8.4 | WARN if staleTime is not set to prevent unnecessary refetches | PASS/WARN |
| 6.8.5 | WARN if manual refetch occurs on timers or arbitrary intervals instead of user action/mutation | PASS/WARN |

## 6.9 Loading & Error UI

| ID | Rule | Verdict |
|----|------|---------|
| 6.9.1 | FAIL if data-fetching components do not handle isLoading, isError, and data states | PASS/FAIL |
| 6.9.2 | WARN if error states show raw status codes instead of user-friendly messages | PASS/WARN |
| 6.9.3 | WARN if loading states use spinners instead of skeleton components matching content layout | PASS/WARN |
| 6.9.4 | FAIL if unhandled promise rejections exist in components | PASS/FAIL |
| 6.9.5 | WARN if empty states are not distinguished from loading and error states | PASS/WARN |
| 6.9.6 | WARN if error states lack a retry button (refetch or reset) | PASS/WARN |

## 6.10 API Proxy Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 6.10.1 | FAIL if /api/[...path]/route.ts proxy does not exist | PASS/FAIL |
| 6.10.2 | FAIL if proxy does not preserve authentication cookies (forward + set-cookie) | PASS/FAIL |
| 6.10.3 | FAIL if proxy does not forward Authorization, Content-Type, and other relevant headers | PASS/FAIL |
| 6.10.4 | WARN if media rewrite is not configured in next.config.ts | PASS/WARN |
| 6.10.5 | PASS if no CORS issues exist (same-origin proxy eliminates CORS) | PASS/FAIL |
| 6.10.6 | FAIL if proxy does not handle all HTTP methods (GET, POST, PATCH, PUT, DELETE) | PASS/FAIL |

## 6.11 API Integration Testing

| ID | Rule | Verdict |
|----|------|---------|
| 6.11.1 | WARN if API functions lack unit test coverage | PASS/WARN |
| 6.11.2 | FAIL if tests mock the global axios package instead of the configured API client instance | PASS/FAIL |
| 6.11.3 | WARN if tests do not verify request URL, method, headers, and body | PASS/WARN |
| 6.11.4 | WARN if tests do not verify response transformation to typed objects | PASS/WARN |
| 6.11.5 | WARN if tests do not cover both success and failure paths | PASS/WARN |
| 6.11.6 | WARN if error tests do not verify ApiError structure | PASS/WARN |
| 6.11.7 | WARN if test mock data does not match backend response shape | PASS/WARN |
