# 15 — Error Handling & Observability Checklist

## 15.1 Error Boundary Hierarchy

- [ ] **global-error.tsx catches root-level errors** — the root error boundary uses inline styles (not Tailwind) because the CSS framework may not be loaded when a root error occurs
- [ ] **error.tsx at route segments catches page-level errors** — each route segment has an error.tsx that catches rendering errors within that segment, using Tailwind and shadcn for styled UI
- [ ] **FeatureErrorBoundary wraps feature-level sections within pages** — individual features within a page are wrapped in error boundaries so one feature's failure does not crash the entire page
- [ ] **Error boundaries call reportError for centralized tracking** — all error boundaries send caught errors to the centralized error reporting function before rendering fallback UI
- [ ] **Error boundaries show reset and retry button** — fallback UI includes a retry button that calls reset() to attempt re-rendering the failed component tree
- [ ] **No unhandled exceptions crash the entire page** — every level of the component tree is covered by an error boundary, preventing white-screen crashes
- [ ] **Error boundaries render useful fallback UI** — fallback messages explain what happened and provide actionable options (retry, navigate home), not just "Something went wrong"

## 15.2 API Error Classification

- [ ] **ApiError class wraps all backend errors** — every API error is transformed into an ApiError instance with structured properties for consistent handling
- [ ] **status property holds HTTP status code** — the numeric HTTP status (400, 401, 403, 404, 409, 422, 429, 500) is available for programmatic error routing
- [ ] **message property holds user-friendly error message** — the error message is suitable for display to users, not a raw server error or stack trace
- [ ] **code property holds machine-readable error code** — a string code (validation_error, not_found, rate_limited, network_error) enables precise error handling logic
- [ ] **details property holds additional context** — field-level validation errors, retry_after seconds, and other structured data are available in the details object
- [ ] **Convenience getters for common status checks** — isNotFound, isUnauthorized, isForbidden, isValidation, isConflict, isRateLimited provide readable boolean checks
- [ ] **Network errors produce ApiError with status 0** — connection failures, timeouts, and DNS errors are wrapped as ApiError(0, "Network error", "network_error")

## 15.3 Centralized Error Handler

- [ ] **handleApiError maps errors to appropriate actions** — a single function in api-error-handler.ts routes errors to the correct UI treatment based on error type
- [ ] **Handler priority is correct** — custom handlers by error code are checked first, then validation field mapping, then rate limiting, then generic toast fallback
- [ ] **Validation errors map to form fields via setError** — 422 responses with field-level errors are mapped to react-hook-form setError for inline field display
- [ ] **Rate limiting shows countdown with retry_after** — 429 responses display "Too many attempts. Please try again in X seconds" with the countdown from the error details
- [ ] **Toast notifications for non-field errors** — errors that cannot be mapped to specific form fields are displayed as toast notifications via sonner
- [ ] **Handler accepts options for customization** — call sites can pass custom error handlers, message overrides, or field mappings to tailor error handling per context

## 15.4 User-Facing Error Messages

- [ ] **Error messages are human-readable and actionable** — messages tell users what happened and what they can do about it, not just that something failed
- [ ] **No technical details shown to users** — stack traces, error codes, raw JSON, and server internals are never displayed in the UI
- [ ] **Rate limiting shows clear countdown** — "Too many attempts. Please try again in X seconds" with the actual seconds remaining from the backend response
- [ ] **Validation errors appear inline with the relevant field** — field-level errors are displayed directly below or beside the input they relate to, not in a generic error banner
- [ ] **404 errors show "Not found" with navigation options** — missing resources display a clear message with links to navigate back or to the home page
- [ ] **Generic fallback message for unexpected errors** — errors that cannot be classified show "Something went wrong. Please try again." rather than cryptic technical messages

## 15.5 Error Reporting

- [ ] **reportError is the single entry point for all error logging** — a centralized function in error-reporting.ts handles all error reporting decisions (dev console vs. production Sentry)
- [ ] **Production integrates with Sentry** — Sentry.captureException is called in production builds for all unhandled and boundary-caught errors
- [ ] **Error context includes boundary name, component, and user action** — Sentry events include structured context about where the error occurred and what the user was doing
- [ ] **console.error used in development for immediate visibility** — development builds log errors to the console for developer convenience without sending to external services
- [ ] **No silent error swallowing** — catch blocks always log or report the error, never silently discarding exceptions
- [ ] **Error breadcrumbs capture user actions leading to the error** — Sentry breadcrumbs record navigation, clicks, and API calls preceding the error for reproduction context
- [ ] **Source maps uploaded to Sentry for production stack traces** — production builds upload source maps so Sentry errors show readable TypeScript stack traces, not minified code

## 15.6 Network Error Handling

- [ ] **Offline and network failures produce structured errors** — connection failures are wrapped as ApiError(0, "Network error", "network_error") for consistent handling
- [ ] **TanStack Query retries transient failures** — 5xx and network errors are retried up to 3 times with exponential backoff before displaying an error to the user
- [ ] **4xx errors are not retried** — client errors (400, 401, 403, 404, 422) are deterministic and are not retried, preventing unnecessary failed requests
- [ ] **Users see meaningful messages for network errors** — network failures display "Unable to connect. Please check your internet connection." not "fetch failed" or "TypeError"
- [ ] **Connection restored detection triggers refetch** — TanStack Query's refetchOnReconnect or a custom online listener triggers data refresh when connectivity is restored
- [ ] **Timeout errors distinguished from other network errors** — request timeouts have a distinct error message ("Request timed out") separate from general network failures

## 15.7 404 Handling

- [ ] **not-found.tsx provides a useful 404 page** — the global 404 page includes a clear message, navigation links to home and back, and maintains site chrome (header, footer)
- [ ] **API 404 errors display inline "not found" states** — missing resources in API responses render component-level empty states, not page-level 404 redirects
- [ ] **Dynamic route 404s handled gracefully** — invalid [slug] or [id] parameters that return 404 from the API render a helpful not-found state within the page layout
- [ ] **notFound() used in server components** — server components that fail to find data call notFound() from next/navigation to trigger the not-found.tsx boundary
- [ ] **404 pages maintain site chrome** — the 404 page includes header and footer navigation so users can navigate away without using the browser back button

## 15.8 Rate Limiting

- [ ] **429 responses include retry_after from ApiError details** — the retry_after value from the backend is extracted and available for countdown display
- [ ] **Rate limit messages show countdown timer** — users see a live countdown of seconds remaining before they can retry the action
- [ ] **Token refresh 429 is not treated as auth failure** — a rate-limited token refresh does not redirect to login or clear the session — it retries after the cooldown
- [ ] **No infinite retry loops on 429** — the retry mechanism respects retry_after and has a maximum retry count, preventing infinite request loops
- [ ] **Rate limiting distinguished from other 4xx errors** — 429 errors are handled separately from validation (422) and authorization (403) errors, with different UI treatment
- [ ] **User feedback during rate limit** — buttons and forms are disabled with a visible countdown, preventing repeated submissions during the cooldown period

## 15.9 Console Hygiene

- [ ] **No console.log in production code** — all console.log statements are removed or guarded behind development-only checks before production builds
- [ ] **console.error only via reportError** — errors are reported through the centralized reporting function, not directly via console.error scattered throughout the codebase
- [ ] **No uncaught promise rejections** — all async operations have error handling (try/catch, .catch(), or TanStack Query onError), preventing unhandled rejection warnings
- [ ] **ESLint no-console rule considered** — the no-console ESLint rule is enabled or evaluated to catch accidental console statements before they reach production
- [ ] **Development console output is useful** — console output in development mode provides meaningful debugging information, not noise from excessive logging

## 15.10 Frontend Observability

- [ ] **Error rates trackable via Sentry dashboards** — Sentry project configured with alerts for error rate spikes, enabling proactive issue detection
- [ ] **User session context attached to error reports** — Sentry events include user ID and email (where available) for correlating errors with specific user experiences
- [ ] **Breadcrumbs capture navigation and user actions** — Sentry breadcrumbs record page navigations, button clicks, and API calls for error reproduction context
- [ ] **Performance monitoring via Core Web Vitals reporting** — LCP, INP, and CLS metrics collected and reported for production performance tracking
- [ ] **Sentry release tracking tied to deployment version** — each deployment creates a Sentry release, enabling error attribution to specific deployments and regression detection
- [ ] **Source maps enable readable production stack traces** — uploaded source maps translate minified production errors into original TypeScript file names and line numbers
