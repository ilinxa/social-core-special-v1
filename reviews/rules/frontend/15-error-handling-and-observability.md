# 15 — Error Handling & Observability Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 15.1 Error Boundary Hierarchy

| ID | Rule | Verdict |
|----|------|---------|
| 15.1.1 | FAIL if global-error.tsx does not exist or uses Tailwind instead of inline styles | PASS/FAIL |
| 15.1.2 | FAIL if no error.tsx exists at route segment level to catch page errors | PASS/FAIL |
| 15.1.3 | WARN if feature sections within pages are not wrapped in error boundaries | PASS/WARN |
| 15.1.4 | WARN if error boundaries do not call reportError for centralized tracking | PASS/WARN |
| 15.1.5 | FAIL if error boundary fallback UI lacks a retry/reset button | PASS/FAIL |
| 15.1.6 | FAIL if unhandled exceptions can crash the entire page (no boundary coverage) | PASS/FAIL |
| 15.1.7 | WARN if error boundary fallback shows only "Something went wrong" without actionable options | PASS/WARN |

## 15.2 API Error Classification

| ID | Rule | Verdict |
|----|------|---------|
| 15.2.1 | FAIL if API errors are not wrapped in a structured ApiError class | PASS/FAIL |
| 15.2.2 | PASS if ApiError has a status property with HTTP status code | PASS/FAIL |
| 15.2.3 | PASS if ApiError.message is user-friendly (not raw server error or stack trace) | PASS/FAIL |
| 15.2.4 | PASS if ApiError has a machine-readable code property | PASS/FAIL |
| 15.2.5 | PASS if ApiError has a details property for field-level errors and retry_after | PASS/FAIL |
| 15.2.6 | PASS if convenience getters exist (isNotFound, isUnauthorized, isForbidden, etc.) | PASS/FAIL |
| 15.2.7 | PASS if network errors produce ApiError with status 0 and code "network_error" | PASS/FAIL |

## 15.3 Centralized Error Handler

| ID | Rule | Verdict |
|----|------|---------|
| 15.3.1 | FAIL if no centralized error handler exists (errors handled ad-hoc in each component) | PASS/FAIL |
| 15.3.2 | WARN if handler priority is incorrect (custom handlers should be checked first) | PASS/WARN |
| 15.3.3 | FAIL if validation errors (422) are not mapped to form fields via setError | PASS/FAIL |
| 15.3.4 | WARN if rate limiting (429) does not show countdown with retry_after | PASS/WARN |
| 15.3.5 | PASS if non-field errors show toast notifications | PASS/FAIL |
| 15.3.6 | PASS if handler accepts customization options (custom handlers, message overrides) | PASS/FAIL |

## 15.4 User-Facing Error Messages

| ID | Rule | Verdict |
|----|------|---------|
| 15.4.1 | PASS if error messages tell users what happened and what to do | PASS/FAIL |
| 15.4.2 | FAIL if stack traces, raw JSON, or server internals are shown to users | PASS/FAIL |
| 15.4.3 | WARN if rate limiting does not show countdown seconds | PASS/WARN |
| 15.4.4 | PASS if validation errors appear inline with the relevant field | PASS/FAIL |
| 15.4.5 | PASS if 404 errors show navigation options (back, home) | PASS/FAIL |
| 15.4.6 | PASS if unexpected errors show a generic fallback message | PASS/FAIL |

## 15.5 Error Reporting

| ID | Rule | Verdict |
|----|------|---------|
| 15.5.1 | PASS if reportError is the single entry point for error logging | PASS/FAIL |
| 15.5.2 | INFO if Sentry is not integrated for production error tracking | PASS/INFO |
| 15.5.3 | INFO if error context (boundary, component, action) is not included in reports | PASS/INFO |
| 15.5.4 | PASS if development builds log errors to console | PASS/FAIL |
| 15.5.5 | FAIL if catch blocks silently swallow errors without logging or reporting | PASS/FAIL |
| 15.5.6 | INFO if breadcrumbs are not configured for user action replay | PASS/INFO |
| 15.5.7 | INFO if source maps are not uploaded for production stack traces | PASS/INFO |

## 15.6 Network Error Handling

| ID | Rule | Verdict |
|----|------|---------|
| 15.6.1 | PASS if offline/network failures produce structured ApiError | PASS/FAIL |
| 15.6.2 | PASS if TanStack Query retries transient failures (5xx, network) | PASS/FAIL |
| 15.6.3 | PASS if 4xx errors are not retried | PASS/FAIL |
| 15.6.4 | WARN if network error messages show raw technical strings ("fetch failed") | PASS/WARN |
| 15.6.5 | PASS if TQ refetchOnReconnect triggers data refresh on connection restore | PASS/FAIL |
| 15.6.6 | INFO if timeout errors are not distinguished from other network errors | PASS/INFO |

## 15.7 404 Handling

| ID | Rule | Verdict |
|----|------|---------|
| 15.7.1 | FAIL if not-found.tsx does not exist or lacks navigation links | PASS/FAIL |
| 15.7.2 | PASS if API 404 errors render inline "not found" states | PASS/FAIL |
| 15.7.3 | PASS if dynamic route 404s render helpful not-found state | PASS/FAIL |
| 15.7.4 | INFO if server components do not use notFound() from next/navigation | PASS/INFO |
| 15.7.5 | WARN if 404 page does not maintain site chrome (header, footer, navigation) | PASS/WARN |

## 15.8 Rate Limiting

| ID | Rule | Verdict |
|----|------|---------|
| 15.8.1 | PASS if 429 responses expose retry_after from ApiError details | PASS/FAIL |
| 15.8.2 | WARN if rate limit UI does not show countdown timer | PASS/WARN |
| 15.8.3 | FAIL if token refresh 429 is treated as auth failure (redirect to login) | PASS/FAIL |
| 15.8.4 | FAIL if retry mechanism has no maximum count (infinite retry loops) | PASS/FAIL |
| 15.8.5 | PASS if 429 is handled separately from other 4xx errors | PASS/FAIL |
| 15.8.6 | WARN if buttons/forms are not disabled during rate limit cooldown | PASS/WARN |

## 15.9 Console Hygiene

| ID | Rule | Verdict |
|----|------|---------|
| 15.9.1 | WARN if console.log statements exist in production code paths | PASS/WARN |
| 15.9.2 | WARN if console.error is used directly instead of via reportError | PASS/WARN |
| 15.9.3 | WARN if uncaught promise rejections exist (missing try/catch or .catch()) | PASS/WARN |
| 15.9.4 | INFO if ESLint no-console rule is not configured | PASS/INFO |
| 15.9.5 | PASS if development console output provides useful debugging info | PASS/FAIL |

## 15.10 Frontend Observability

| ID | Rule | Verdict |
|----|------|---------|
| 15.10.1 | INFO if Sentry dashboards are not configured for error rate tracking | PASS/INFO |
| 15.10.2 | INFO if user session context is not attached to error reports | PASS/INFO |
| 15.10.3 | INFO if breadcrumbs are not capturing navigation and user actions | PASS/INFO |
| 15.10.4 | INFO if Core Web Vitals are not reported for production monitoring | PASS/INFO |
| 15.10.5 | INFO if Sentry releases are not tied to deployment versions | PASS/INFO |
| 15.10.6 | INFO if source maps are not enabling readable production stack traces | PASS/INFO |
