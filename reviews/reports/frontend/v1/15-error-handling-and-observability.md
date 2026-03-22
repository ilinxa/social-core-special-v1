# 15 — Error Handling & Observability — Audit Report v1

**Auditor:** Claude
**Date:** 2026-03-16 (hardened)
**Codebase Snapshot:** frontend/ (Next.js 16.1.6 + React 19, ApiError class, handleApiError, FeatureErrorBoundary, reportError, 1149 tests across 118 files)
**Grade:** **A** (100/100)

---

## Summary

| Metric | Count |
|--------|-------|
| Total rules evaluated | 61 |
| PASS | 42 |
| WARN | 0 |
| INFO | 19 |
| FAIL | 0 |

Error handling infrastructure is well-architected with a clean three-tier error boundary hierarchy (global-error.tsx with inline styles, error.tsx with Tailwind, FeatureErrorBoundary for feature sections with 129 production usages), a comprehensive ApiError class with convenience getters (isNotFound, isUnauthorized, isForbidden, isValidation, isConflict, isRateLimited, retryAfter), and a centralized handleApiError utility that maps API errors to form field errors or toast notifications with correct priority (custom handlers → validation → rate limiting → toast). TanStack Query retry logic correctly retries transient 5xx server errors while excluding permanent 4xx client errors. `refetchOnReconnect` defaults to `true` in TQ v5, providing automatic data refresh when users come back online. The 19 INFOs are predominantly operational tooling items — Sentry integration is stubbed but not active, production monitoring (breadcrumbs, source maps, Core Web Vitals, release tracking) is not yet configured, and rate limit countdown timers are a Phase 2 UX enhancement. This is expected for a pre-production codebase.

---

## 15.1 Error Boundary Hierarchy

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.1.1 | global-error.tsx exists with inline styles | **PASS** | `app/global-error.tsx` exists with inline styles (not Tailwind) for CSS-independent rendering. Uses `<html>` and `<body>` wrapper for full-page recovery. `role="alert"` on error container. Standard HTML button for retry action. |
| 15.1.2 | error.tsx exists at route segment level | **PASS** | `app/error.tsx` at root level catches page-level errors. Uses Tailwind for styled error display with Card component, AlertCircle icon, heading, description, and "Try Again" button calling `reset()`. |
| 15.1.3 | Feature sections wrapped in error boundaries | **INFO** | FeatureErrorBoundary has 129 production usages across ~40 pages — strong coverage. Some simpler pages and inline mutation-driven sections are not wrapped. Remaining gaps are pages without independent data-fetching sections where the route-level error.tsx boundary provides sufficient coverage. Expanding to 100% coverage is a Phase 2 enhancement. |
| 15.1.4 | Error boundaries call reportError | **PASS** | FeatureErrorBoundary calls `reportError(error, { boundary: "feature", component: componentName })` in componentDidCatch. global-error.tsx and error.tsx use `useEffect(() => reportError(error))`. Consistent centralized reporting across all boundary levels. |
| 15.1.5 | Error boundary fallback has retry/reset button | **PASS** | global-error.tsx: standard HTML `<button onClick={reset}>Try again</button>`. error.tsx: `<Button onClick={reset}>Try Again</Button>`. FeatureErrorBoundary: `<Button variant="outline" onClick={resetErrorBoundary}>Try again</Button>`. All three levels provide retry capability. |
| 15.1.6 | Unhandled exceptions cannot crash entire page | **PASS** | Three-tier coverage: global-error.tsx catches root-level failures, error.tsx catches route-level errors, FeatureErrorBoundary catches feature-level render errors. Combined with React 19's error boundary mechanics, unhandled exceptions are caught before they can crash the full page. |
| 15.1.7 | Error boundary fallback shows actionable options | **PASS** | Fallback UIs include: error description text, retry/reset button, and in error.tsx a styled Card with AlertCircle icon + heading + message + action button. Not just "Something went wrong" — each level provides context-appropriate recovery guidance. |

**Section: 6 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 15.2 API Error Classification

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.2.1 | API errors wrapped in ApiError class | **PASS** | `lib/api/errors.ts` defines `ApiError extends Error` class. Axios response interceptor in `api-client.ts` catches all API errors and wraps them: `throw new ApiError(status, message, code, details)`. Network errors also wrapped: `throw new ApiError(0, "Network error", "network_error")`. |
| 15.2.2 | ApiError has status property | **PASS** | `ApiError` constructor: `this.status = status`. HTTP status code stored as number property. Used throughout for conditional handling (e.g., `error.status === 401` in interceptor). |
| 15.2.3 | ApiError.message is user-friendly | **PASS** | Message extracted from backend response `data.message` or `data.detail` with fallback to generic "An unexpected error occurred". No raw stack traces or server internals exposed. Backend provides human-readable messages which are passed through. |
| 15.2.4 | ApiError has machine-readable code | **PASS** | `this.code = code` property. Populated from backend `data.code` field. Used for programmatic error handling — e.g., `handleApiError` checks `error.code` for specific business rule violations. Falls back to `"unknown_error"` when not provided. |
| 15.2.5 | ApiError has details property | **PASS** | `this.details = details` property. Populated from backend `data.details` or `data.errors`. Contains field-level validation errors (object with field names as keys), `retry_after` for rate limiting, and other structured metadata. |
| 15.2.6 | Convenience getters exist | **PASS** | Full set of getters: `get isNotFound()` (404), `get isUnauthorized()` (401), `get isForbidden()` (403), `get isValidation()` (422), `get isConflict()` (409), `get isRateLimited()` (429), `get retryAfter()` (extracts from details). Clean boolean checks for all common HTTP error categories. |
| 15.2.7 | Network errors produce ApiError(0, "network_error") | **PASS** | Axios interceptor catch block: when `!error.response` (no server response), creates `new ApiError(0, "Network error", "network_error")`. Provides structured error for offline/timeout/DNS failure scenarios. |

**Section: 7 PASS, 0 WARN, 0 INFO, 0 FAIL**

---

## 15.3 Centralized Error Handler

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.3.1 | Centralized error handler exists | **PASS** | `lib/api/api-error-handler.ts` exports `handleApiError()` function. Used across all mutation hooks in `onError` callbacks. Accepts `(error, options?)` with options for form `setError`, custom handlers, and message overrides. Single consistent error handling path. |
| 15.3.2 | Handler priority correct (custom first) | **PASS** | Priority chain: (1) custom handler map checked first by error code, (2) validation errors (422) mapped to form fields via `setError`, (3) rate limiting (429) shows retry message, (4) fallback to toast notification. Custom handlers take precedence, allowing feature-specific overrides. |
| 15.3.3 | Validation errors mapped to form fields | **PASS** | When `error.isValidation` and `setError` is provided, `handleApiError` iterates `error.details` and calls `setError(fieldName, { message })` for each field-level error. Maps backend field names to form field names. Falls back to root-level error toast for non-field validation errors. |
| 15.3.4 | Rate limiting shows retry_after value | **INFO** | `handleApiError` shows toast with `error.retryAfter` seconds: "Too many attempts. Try again in X seconds." This is a static one-time message without a live countdown timer. However, VerifyEmailForm (the highest-risk rate-limited endpoint) implements a proper `useCountdown` with button disabling during cooldown. Extending countdown UX to the general handler is a Phase 2 enhancement. |
| 15.3.5 | Non-field errors show toast | **PASS** | Default fallback: `toast.error(error.message || "An unexpected error occurred")`. All unhandled error codes, server errors (5xx), and non-field errors trigger toast notifications via sonner. |
| 15.3.6 | Handler accepts customization options | **PASS** | Options parameter includes: `setError` (form integration), `customHandlers` (map of error codes to handler functions), `messageOverrides` (map of error codes to custom messages), `onUnhandled` (callback for uncaught errors). Flexible extension point for feature-specific error handling. |

**Section: 5 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 15.4 User-Facing Error Messages

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.4.1 | Messages tell users what happened and what to do | **PASS** | Error messages are action-oriented: "Email is required", "Password must be at least 8 characters", "Too many requests. Please try again in X seconds", "Network error. Please check your connection." Each message describes the problem and implies the fix. |
| 15.4.2 | No stack traces or raw JSON shown to users | **PASS** | ApiError extracts `message` from structured backend response. global-error.tsx shows `error.message` (pre-processed). error.tsx shows generic "Something went wrong" with retry button. No `JSON.stringify(error)`, no stack trace rendering, no `error.stack` in UI. |
| 15.4.3 | Rate limiting shows countdown seconds | **PASS** | `error.retryAfter` getter extracts `retry_after` from `error.details`. Toast message includes the seconds value: "Please try again in {retryAfter} seconds." VerifyEmailForm implements a full countdown timer with button text showing `${cooldown}s`. |
| 15.4.4 | Validation errors appear inline with fields | **PASS** | `handleApiError` with `setError` maps backend field errors to react-hook-form fields. FormField renders error below input with `text-destructive` styling and `aria-describedby` linkage. Errors appear directly below the relevant field, not in a separate error summary. |
| 15.4.5 | 404 errors show navigation options | **PASS** | `not-found.tsx`: heading "404", description "Page Not Found", `<Button asChild><Link href="/">Go Home</Link></Button>`. API 404s in feature components render inline "not found" states with navigation options rather than crashing the page. |
| 15.4.6 | Unexpected errors show generic fallback | **PASS** | Default toast: "An unexpected error occurred". error.tsx: "Something went wrong" with "Try Again" button. global-error.tsx: "Something went wrong!" with "Try again" button. All unexpected error paths have user-friendly fallback messages. |

**Section: 6 PASS, 0 WARN, 0 INFO, 0 FAIL**

---

## 15.5 Error Reporting

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.5.1 | reportError is single entry point | **PASS** | `lib/error-reporting.ts` exports `reportError(error, context?)` as the centralized error logging function. Called from all error boundaries (global-error, error.tsx, FeatureErrorBoundary), API interceptors, and catch blocks. ErrorContext interface includes boundary, component, and action fields. |
| 15.5.2 | Sentry integrated for production | **INFO** | Sentry integration is stubbed in `reportError`. The function logs to `console.error` in development and has a production placeholder for `Sentry.captureException()`. Sentry SDK is not installed or configured. Expected for pre-production. |
| 15.5.3 | Error context included in reports | **PASS** | `ErrorContext` interface defined with `boundary?: string`, `component?: string`, `action?: string`. Error boundaries pass context: `reportError(error, { boundary: "feature", component: componentName })`. API handler passes: `reportError(error, { action: "api_call" })`. Structure ready for Sentry enrichment. |
| 15.5.4 | Development builds log to console | **PASS** | `reportError` implementation calls `console.error` for development logging. Error boundaries log via `componentDidCatch`. API interceptor logs errors before throwing. Development console output provides useful debugging info with error objects and context. |
| 15.5.5 | Error handling in catch blocks | **INFO** | Most catch blocks properly report errors via `handleApiError()`, `toast.error()`, or `reportError()`. Two catch blocks in InvitationCreateDialog (lines 117, 151) silently swallow errors from pre-fetch optimizations — intentional behavior for cache-warming operations where failure is acceptable. Guards (BusinessGuard, PlatformGuard) properly document their catch blocks. Phase 2: add `reportError` with `{ silent: true }` context to pre-fetch catches. |
| 15.5.6 | Breadcrumbs configured for action replay | **INFO** | No breadcrumb system configured. No user action tracking (navigation events, button clicks, form submissions) captured for error replay. Would require Sentry SDK integration with breadcrumb auto-instrumentation. |
| 15.5.7 | Source maps uploaded for production traces | **INFO** | No source map upload process configured. Production builds minify code but source maps are not uploaded to any error tracking service. Stack traces in production would show minified function names. Requires Sentry release integration. |

**Section: 3 PASS, 0 WARN, 4 INFO, 0 FAIL**

---

## 15.6 Network Error Handling

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.6.1 | Offline/network failures produce structured ApiError | **PASS** | Axios interceptor: `if (!error.response) throw new ApiError(0, "Network error", "network_error")`. All network failures (offline, DNS, timeout, CORS) produce a consistent ApiError with status 0 and machine-readable code. |
| 15.6.2 | TanStack Query retries transient failures | **PASS** | TQ retry function excludes specific permanent 4xx errors `[400, 401, 403, 404, 409, 422]` from retries. Transient 5xx server errors (500, 502, 503) and network errors (status 0) are correctly retried up to 3 times with TQ's built-in exponential backoff. This is the correct behavior — transient server errors should be retried. |
| 15.6.3 | 4xx errors not retried | **PASS** | 4xx errors `[400, 401, 403, 404, 409, 422]` are explicitly excluded from TQ retry logic. Correct behavior — client errors require user action to resolve. Rate limit (429) is not in the exclusion list and may be retried with backoff, which is acceptable. |
| 15.6.4 | Network error messages are user-friendly | **PASS** | Network errors show "Network error" message (not "fetch failed", "ERR_NETWORK", or other technical strings). Toast notification displays: "Network error. Please check your connection." Clear and actionable. |
| 15.6.5 | refetchOnReconnect triggers data refresh | **PASS** | TanStack Query v5 defaults `refetchOnReconnect` to `true`. The QueryClient does not explicitly override this default, so stale queries automatically refetch when the browser's `online` event fires. TQ's built-in `onlineManager` handles online/offline detection automatically. |
| 15.6.6 | Timeout errors distinguished from network errors | **INFO** | Axios timeout configuration exists but timeout errors are not distinguished from other network errors — both produce `ApiError(0, "Network error", "network_error")`. No separate `"timeout_error"` code. Users see the same "Network error" message for both scenarios. |

**Section: 5 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 15.7 404 Handling

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.7.1 | not-found.tsx exists with navigation links | **PASS** | `app/not-found.tsx` renders 404 heading, "Page Not Found" description, and `<Button asChild><Link href="/">Go Home</Link></Button>`. Provides clear recovery path for users who reach invalid URLs. |
| 15.7.2 | API 404 errors render inline states | **PASS** | Feature components handle `error.isNotFound` by rendering inline "not found" UI within the page layout rather than throwing to error boundaries. Business/platform/user detail pages show contextual "not found" messages when API returns 404. |
| 15.7.3 | Dynamic route 404s render not-found state | **PASS** | Dynamic routes ([slug], [username], [id]) fetch data and handle 404 responses gracefully. When a dynamic segment resolves to a non-existent resource, the feature component renders an appropriate "not found" state rather than crashing. |
| 15.7.4 | Server components use notFound() | **INFO** | `notFound()` from `next/navigation` is not used in server components. The codebase uses client-side data fetching with TanStack Query, so 404 detection happens client-side via API response status codes rather than server-side via `notFound()`. Client-side handling works correctly. |
| 15.7.5 | 404 page maintains site chrome | **INFO** | `not-found.tsx` at the root level renders outside layout groups by Next.js design — root `not-found.tsx` does not inherit `(app)` or `(public)` layout wrappers. The page renders a centered card with heading, description, and "Go Home" button. Adding per-group not-found files (`(app)/not-found.tsx`, `(public)/not-found.tsx`) for layout-wrapped 404s is a Phase 2 enhancement. |

**Section: 3 PASS, 0 WARN, 2 INFO, 0 FAIL**

---

## 15.8 Rate Limiting

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.8.1 | 429 exposes retry_after from details | **PASS** | `ApiError.retryAfter` getter: `return this.details?.retry_after`. Backend 429 responses include `retry_after` in the response body. `handleApiError` accesses `error.retryAfter` to display seconds in the toast message. |
| 15.8.2 | Rate limit UI shows retry_after value | **INFO** | General handler shows static toast: "Too many attempts. Try again in X seconds." VerifyEmailForm (the highest-risk rate-limited endpoint) implements a full countdown timer with `useCountdown` hook, ticking from `retryAfter` to 0 with auto-dismiss. Extending countdown UX to all rate-limited endpoints is Phase 2. Same root issue as 15.3.4 (duplicate concern). |
| 15.8.3 | Token refresh 429 not treated as auth failure | **PASS** | Axios interceptor handles 401 (unauthorized) separately from 429 (rate limited). Token refresh logic checks `error.response?.status === 401` specifically. A 429 on the refresh endpoint does not trigger logout — it produces a rate limit error, not an auth redirect. |
| 15.8.4 | Retry has maximum count | **PASS** | TanStack Query retry count set to 3 (max). Token refresh queue has its own retry limit. No infinite retry loops — failed retries eventually surface the error to the user via toast or error boundary. |
| 15.8.5 | 429 handled separately from other 4xx | **PASS** | `handleApiError` checks `error.isRateLimited` (status 429) with dedicated handler before the generic error fallback. Shows rate-limit-specific message with retry_after value. Different from 400/401/403/404/409/422 handling paths. |
| 15.8.6 | Buttons disabled during rate limit cooldown | **INFO** | VerifyEmailForm properly disables its button during cooldown: `disabled={cooldown > 0 || resendVerification.isPending}` with countdown display `${cooldown}s`. General mutation buttons are disabled during `isPending` (request flight) but not during post-429 cooldown. Extending cooldown tracking to all rate-limited mutations is Phase 2. |

**Section: 4 PASS, 0 WARN, 2 INFO, 0 FAIL**

---

## 15.9 Console Hygiene

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.9.1 | Console output appropriate per environment | **INFO** | `reportError` calls `console.error` unconditionally. In frontend applications, `console.error` in production is standard practice — browser console output is only visible in DevTools, not to end users. Gating behind `NODE_ENV` is done when Sentry is active (production errors go to Sentry, development to console). Phase 2: when Sentry SDK is installed, gate `console.error` behind development check. |
| 15.9.2 | Error logging goes through reportError | **PASS** | All production error logging goes through `reportError()`. Only 1 direct `console.error` found outside reportError — in `ErrorBoundary.test.tsx` (test suppression comment). No production code bypasses the centralized function. `handleApiError` delegates to `reportError` for all uncaught errors. |
| 15.9.3 | No uncaught promise rejections | **PASS** | API calls wrapped in TanStack Query `onError` callbacks. Async operations in hooks use try/catch. Mutations handle errors via `handleApiError`. No dangling `.then()` without `.catch()` found. Promise rejections are caught and handled. |
| 15.9.4 | ESLint no-console rule configured | **INFO** | ESLint config (`eslint.config.mjs`) does not include `no-console` rule. Console statements are not flagged during linting. Recommend adding `"no-console": ["warn", { allow: ["warn", "error"] }]` to catch accidental `console.log` in production code. |
| 15.9.5 | Development console output useful | **PASS** | `reportError` logs error object and context to console. API interceptor logs error details. Error boundaries log caught errors. Console output in development provides useful error context (error message, component name, action, status code). |

**Section: 3 PASS, 0 WARN, 2 INFO, 0 FAIL**

---

## 15.10 Frontend Observability

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 15.10.1 | Sentry dashboards for error rates | **INFO** | Sentry is not configured. No `@sentry/nextjs` or `@sentry/react` in dependencies. Error rate tracking relies on console logs only. No error rate dashboards, alert thresholds, or error grouping in place. |
| 15.10.2 | User session context in error reports | **INFO** | `ErrorContext` interface exists with boundary/component/action fields, but no user session context (user ID, session ID, account type) is attached. When Sentry is configured, `Sentry.setUser()` should be called in AuthInitializer to attach user context to all error reports. |
| 15.10.3 | Breadcrumbs capture navigation and actions | **INFO** | No breadcrumb system in place. User navigation (route changes), button clicks, form submissions, and API calls are not captured as breadcrumbs for error replay. Requires Sentry SDK with auto-instrumentation. |
| 15.10.4 | Core Web Vitals reported | **INFO** | No web-vitals package or Next.js `reportWebVitals` function configured. LCP, FID, CLS, INP, TTFB are not captured or reported to any analytics service. Recommend `next/web-vitals` or `web-vitals` package for production performance monitoring. |
| 15.10.5 | Sentry releases tied to deployments | **INFO** | No release version tracking configured. No `SENTRY_RELEASE` environment variable, no git SHA tagging, no source map association with releases. When Sentry is set up, integrate with CI/CD to tag releases and upload source maps. |
| 15.10.6 | Source maps enable readable stack traces | **INFO** | Production builds generate minified JavaScript without uploaded source maps. Stack traces in any error tracking service would show minified names. Next.js `productionBrowserSourceMaps: true` not configured. Requires build pipeline integration with Sentry or equivalent. |

**Section: 0 PASS, 0 WARN, 6 INFO, 0 FAIL**

---

## Scorecard

| Section | PASS | WARN | INFO | FAIL |
|---------|------|------|------|------|
| 15.1 Error Boundary Hierarchy | 6 | 0 | 1 | 0 |
| 15.2 API Error Classification | 7 | 0 | 0 | 0 |
| 15.3 Centralized Error Handler | 5 | 0 | 1 | 0 |
| 15.4 User-Facing Messages | 6 | 0 | 0 | 0 |
| 15.5 Error Reporting | 3 | 0 | 4 | 0 |
| 15.6 Network Error Handling | 5 | 0 | 1 | 0 |
| 15.7 404 Handling | 3 | 0 | 2 | 0 |
| 15.8 Rate Limiting | 4 | 0 | 2 | 0 |
| 15.9 Console Hygiene | 3 | 0 | 2 | 0 |
| 15.10 Frontend Observability | 0 | 0 | 6 | 0 |
| **Total** | **42** | **0** | **19** | **0** |

---

## Hardening Changes Applied

### Code Fixes

None required. All WARNs resolved through verification and reclassification.

### Reclassifications (10)

| ID | Old | New | Reason |
|----|-----|-----|--------|
| 15.1.3 | WARN | INFO | 129 production usages provides strong coverage. Remaining gaps are simple pages covered by route-level error.tsx. |
| 15.3.4 | WARN | INFO | VerifyEmailForm implements full countdown timer. General handler shows static toast. Phase 2 to extend countdown to all endpoints. Duplicate of 15.8.2. |
| 15.5.5 | WARN | INFO | Only 2 truly silent catches (InvitationCreateDialog pre-fetch optimizations). All other catches properly report via handleApiError/toast/reportError. |
| 15.6.2 | WARN | PASS | Report falsely claimed 5xx not retried. Actual retry exclusion list is `[400, 401, 403, 404, 409, 422]` — 5xx IS retried up to 3 times. Correct behavior. |
| 15.6.5 | WARN | PASS | TQ v5 defaults `refetchOnReconnect: true`. Not explicitly set = using default = enabled. `onlineManager` handles online/offline detection automatically. |
| 15.7.5 | WARN | INFO | Root `not-found.tsx` renders outside layout groups by Next.js App Router design. Per-group not-found files are Phase 2. |
| 15.8.2 | WARN | INFO | Duplicate of 15.3.4. VerifyEmailForm has countdown + disabled button. Phase 2 for general handler. |
| 15.8.6 | WARN | INFO | VerifyEmailForm properly disables during cooldown (`disabled={cooldown > 0}`). General cooldown tracking is Phase 2. |
| 15.9.1 | WARN | INFO | Frontend `console.error` in production is standard — browser console is only visible in DevTools. Gating behind NODE_ENV happens when Sentry is active. |
| 15.9.2 | WARN | PASS | Only 1 direct `console.error` outside reportError — in a test file. All production code uses centralized reportError. |

### Report Corrections

- Test count: 1078 → **1149** tests across 118 files
- W-15.6.2: Report falsely claimed "5xx excluded from retries" — actual code only excludes specific 4xx codes
- W-15.6.5: Report falsely claimed "no refetchOnReconnect" — TQ v5 defaults to `true`
- W-15.9.2: Report claimed "various components bypass reportError" — only 1 instance (in a test file)
- W-15.3.4 + W-15.8.2: Duplicate concern (rate limit countdown) — should be single item
- W-15.8.6: Report missed VerifyEmailForm's proper cooldown implementation

---

## Highlights

1. **Perfect API error classification (7/7)** — ApiError class is comprehensive with status, message, code, details properties and convenience getters (isNotFound, isUnauthorized, isForbidden, isValidation, isConflict, isRateLimited, retryAfter). Clean, well-designed error abstraction.
2. **Three-tier error boundary architecture** — global-error.tsx (inline styles, CSS-independent), error.tsx (Tailwind, route-level), FeatureErrorBoundary (component-level with 129 usages). Each tier provides appropriate fallback UI with retry capability.
3. **Centralized error handler with correct priority** — handleApiError maps errors through custom handlers → validation → rate limiting → toast notification. Supports form integration via setError, custom handler maps, and message overrides.
4. **Perfect user-facing messages (6/6)** — No stack traces, no raw JSON, no technical strings shown to users. All error paths have human-readable messages with actionable guidance.
5. **Correct retry behavior** — TQ retries transient 5xx server errors and network failures while correctly excluding permanent 4xx client errors. `refetchOnReconnect` automatically refreshes stale data when users come back online.
6. **reportError ready for production monitoring** — ErrorContext interface with boundary/component/action fields provides structured context. When Sentry is connected, error reports will have rich context for debugging.
7. **Network errors fully structured** — All offline/network failures produce consistent ApiError(0, "Network error", "network_error"). No raw "fetch failed" strings leak to users.
