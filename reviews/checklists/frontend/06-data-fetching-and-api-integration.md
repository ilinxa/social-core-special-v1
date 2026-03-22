# 06 — Data Fetching & API Integration Checklist

## 6.1 API Client Architecture

- [ ] **Axios instance defined in lib/api-client.ts** — single configured instance with baseURL set to "/api/v1" for all backend communication
- [ ] **withCredentials: true on every request** — ensures HttpOnly cookies (refresh token) are sent with all API calls through the proxy
- [ ] **Request interceptor attaches Bearer token** — reads access token from in-memory store and sets Authorization header before each request
- [ ] **Response interceptor transforms errors to ApiError** — all non-2xx responses are caught and wrapped in a typed ApiError instance with status, message, code, and details
- [ ] **No direct axios or fetch usage outside the API client** — all HTTP communication flows through the configured Axios instance, never raw fetch() or a separate axios import
- [ ] **API client is a singleton module** — the Axios instance is created once at module scope and exported, not re-instantiated per call or per component
- [ ] **Interceptors handle both request and response** — request interceptor for auth headers, response interceptor for error normalization and token refresh

## 6.2 JWT Token Management

- [ ] **Access token stored in memory only** — module-level variable in the auth module, never persisted to any browser storage mechanism
- [ ] **Never in localStorage, sessionStorage, URL params, or cookies** — access token exists only in JavaScript memory for the duration of the tab session
- [ ] **Refresh token in HttpOnly cookie** — set by the backend, not readable or writable by client-side JavaScript, sent automatically with withCredentials
- [ ] **Proactive refresh at 80% of token lifetime** — for a 15-minute token, refresh triggers around the 12-minute mark to prevent expired-token requests
- [ ] **Token cleared on auth failure** — a 401 response after a failed refresh attempt clears the in-memory token and redirects to login
- [ ] **setToken/getToken/clearToken functions encapsulate access** — all token reads and writes go through these functions, no direct variable access from outside the module
- [ ] **No token payload parsed client-side for security decisions** — JWT claims are not decoded or inspected in the frontend; the backend is the authority on permissions

## 6.3 Token Refresh Flow

- [ ] **401 response triggers automatic refresh** — the response interceptor detects 401, attempts a refresh via the HttpOnly cookie endpoint before failing the request
- [ ] **Failed request queue prevents duplicate refresh requests** — when multiple requests fail with 401 simultaneously, only one refresh is initiated while others wait in a queue
- [ ] **Queued requests replayed with new token on successful refresh** — after obtaining a new access token, all queued requests are retried with the updated Authorization header
- [ ] **Refresh failure clears tokens and redirects to login** — if the refresh endpoint returns an error, the user is logged out and sent to the login page
- [ ] **429 on refresh endpoint is not treated as auth failure** — rate-limiting on the refresh endpoint retries or shows a message rather than logging the user out
- [ ] **Concurrent 401s don't trigger multiple refresh attempts** — a mutex or flag ensures only the first 401 initiates a refresh; subsequent 401s join the existing refresh promise
- [ ] **Refresh uses separate Axios instance** — the refresh request does not pass through the same interceptor chain, preventing infinite retry loops
- [ ] **Token refresh is transparent to calling code** — components and hooks that make API calls are unaware of the refresh mechanism; it happens silently in the interceptor layer

## 6.4 API Function Layer

- [ ] **Each feature has an api/ directory with a dedicated API file** — features/auth/api/auth-api.ts, features/business/api/business-api.ts, etc., isolating API logic per domain
- [ ] **API functions return typed responses matching backend serializer contracts** — return types correspond exactly to the backend's JSON output shape
- [ ] **API functions handle request body construction and URL formatting** — parameter assembly, URL interpolation, and query string building are encapsulated in the API function
- [ ] **No inline API calls in components** — components never call apiClient.get() or apiClient.post() directly; they use API functions or mutation/query hooks
- [ ] **API functions are pure** — they take parameters, make a request, and return a result with no side effects, no store mutations, and no navigation
- [ ] **Consistent naming convention** — fetchXApi for GET, createXApi for POST, updateXApi for PATCH/PUT, deleteXApi for DELETE, searchXApi for search endpoints
- [ ] **API functions accept typed parameters** — input parameters are typed interfaces or explicit arguments, not raw objects or Record<string, unknown>

## 6.5 Error Handling Chain

- [ ] **ApiError class wraps all backend errors** — every error from the API client is an instance of ApiError with status, message, code, and details properties
- [ ] **Convenience getters for common error types** — isNotFound, isUnauthorized, isForbidden, isValidation, isConflict, isRateLimited provide quick checks without comparing status codes
- [ ] **handleApiError maps errors to form setError calls** — in api-error-handler.ts, validation errors from the backend are mapped to react-hook-form field errors
- [ ] **Priority chain for error handling** — custom handlers by error code first, then validation field mapping, then rate limiting with countdown, then fallback toast notification
- [ ] **Error reporting goes to reportError** — centralized error tracking function captures errors for monitoring, separate from user-facing error display
- [ ] **Network errors produce ApiError(0, "Network error", "network_error")** — connection failures, timeouts, and DNS errors are wrapped consistently, not thrown as raw AxiosError
- [ ] **Non-API errors are caught and wrapped** — unexpected errors (JSON parse failures, type errors) are caught in the interceptor and converted to ApiError instances

## 6.6 Type Safety

- [ ] **Request/response types in types/ match backend API contracts exactly** — field names, nesting, and optionality mirror the backend serializer output
- [ ] **Field names use snake_case matching backend convention** — no camelCase transformation layer; the frontend uses snake_case for API types to maintain a 1:1 mapping
- [ ] **PaginatedResponse<T> generic used for all list endpoints** — standard shape with count, next, previous, and results matching Django REST Framework pagination
- [ ] **WithPermissions<T> composes permission types on detail responses** — detail endpoint types include _permissions with evaluated boolean permissions from the backend
- [ ] **No any types in the API layer** — every API function parameter and return type is explicitly typed, no any or unknown used as an escape hatch
- [ ] **API function return types are explicit** — return types are declared in the function signature, not left to TypeScript inference which could drift from the intended contract

## 6.7 Pagination Handling

- [ ] **PaginatedResponse<T> matches backend shape** — {count, next, previous, results} corresponds to Django REST Framework's LimitOffsetPagination or PageNumberPagination output
- [ ] **useInfiniteQuery with getNextPageParam handles pagination** — TanStack Query's infinite query pattern is used for all paginated lists, extracting the next page URL from response.next
- [ ] **Page size consistent with backend defaults** — frontend requests use the same limit/page_size as the backend's default to avoid unnecessary parameter passing
- [ ] **Infinite scroll uses useInView from react-intersection-observer** — a sentinel element at the bottom of the list triggers fetchNextPage when it enters the viewport
- [ ] **No client-side pagination of unpaginated data** — if the backend returns all results, the frontend does not artificially paginate them; pagination is always server-driven
- [ ] **hasNextPage correctly determined from response.next** — the next page exists if and only if the response.next URL is non-null, not calculated from count vs. results.length

## 6.8 Request Deduplication

- [ ] **TanStack Query built-in deduplication prevents duplicate GET requests** — multiple components requesting the same query key share a single in-flight request
- [ ] **API functions are pure with no side effects** — calling an API function multiple times does not cause module-level state mutations or duplicate event dispatches
- [ ] **No parallel identical requests for the same data** — components that mount simultaneously and need the same data rely on TanStack Query deduplication, not independent fetches
- [ ] **staleTime prevents unnecessary refetches** — query configurations set appropriate staleTime values to avoid refetching data that is still considered fresh
- [ ] **Manual refetch only when user-initiated or after mutations** — invalidateQueries is called after mutations or explicit user actions (pull-to-refresh), not on timers or arbitrary intervals

## 6.9 Loading & Error UI

- [ ] **Every data-fetching component handles isLoading, isError, and data states** — all three states have explicit UI branches; no state is left unhandled or silently ignored
- [ ] **Error states show user-friendly messages from ApiError.message** — error displays use the backend's message field, not raw status codes or technical error names
- [ ] **Loading states use skeleton components matching content layout** — skeleton placeholders mirror the shape and size of the expected content to reduce layout shift
- [ ] **No unhandled promise rejections in components** — all async operations have error handling; rejected promises never bubble up uncaught to the console
- [ ] **Empty states distinguished from loading and error** — when data loads successfully but results are empty (data.length === 0), a distinct "no results" message is shown
- [ ] **Retry button provided on error states** — error UI includes a retry action that calls refetch() or resets the error boundary, allowing users to recover without navigation

## 6.10 API Proxy Configuration

- [ ] **Next.js /api/[...path]/route.ts proxies to backend** — all API requests from the browser go through the Next.js server, which forwards them to the Django backend
- [ ] **Proxy preserves authentication cookies** — HttpOnly cookies from the browser are forwarded to the backend and set-cookie headers from the backend are passed back to the browser
- [ ] **Proxy forwards relevant request headers** — Authorization, Content-Type, Accept, and other necessary headers are passed through to the backend
- [ ] **Media rewrite in next.config.ts proxies to backend media URL** — uploaded media files served by the backend are accessible through the frontend's domain via URL rewriting
- [ ] **No CORS issues between frontend and proxy** — since the proxy is same-origin, no CORS preflight requests occur; the backend's CORS settings apply only to direct access
- [ ] **Proxy handles all HTTP methods** — GET, POST, PATCH, PUT, DELETE, and OPTIONS are all forwarded correctly through the proxy route handler

## 6.11 API Integration Testing

- [ ] **Every API function has unit tests** — each function in the api/ directory has corresponding test coverage for its request construction and response handling
- [ ] **Tests mock Axios at the instance level** — vi.mock is used on the API client module, not on the global axios package, ensuring the configured instance is what gets mocked
- [ ] **Tests verify request URL, method, headers, and body** — assertions check that the API function constructs the correct HTTP request with all expected parameters
- [ ] **Tests verify response transformation to typed objects** — assertions confirm that the raw response data is correctly returned as the expected TypeScript type
- [ ] **Tests cover both success and failure paths** — each API function is tested with a 2xx success response and at least one error scenario (4xx, 5xx, network error)
- [ ] **Tests verify error transformation to ApiError** — error path tests confirm that failed requests produce properly structured ApiError instances with correct status and message
- [ ] **Mock data matches backend response shape** — test fixtures use the same field names, types, and nesting as the actual backend API responses
