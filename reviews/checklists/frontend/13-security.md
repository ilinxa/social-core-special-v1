# 13 — Security Checklist

## 13.1 XSS Prevention

- [ ] **No dangerouslySetInnerHTML without content sanitization** — any use of dangerouslySetInnerHTML is accompanied by DOMPurify or equivalent sanitization of the HTML content
- [ ] **User input always escaped by React's default JSX rendering** — text content rendered via {variable} in JSX, relying on React's built-in escaping, not bypassed
- [ ] **No string interpolation into HTML attributes** — attribute values are set via JSX props (href={url}), not constructed via template literals injected into HTML strings
- [ ] **Dynamic content from API rendered as text** — backend-provided content displayed as text nodes, not injected as raw HTML unless explicitly sanitized
- [ ] **User-generated URLs validated before use in href** — URLs from user input or API responses are validated to prevent javascript: protocol injection before rendering as links
- [ ] **No template literals used to construct HTML** — HTML is never built as strings via backticks and then injected into the DOM — JSX is the only rendering path
- [ ] **SVG content from users sanitized before rendering** — user-uploaded or user-provided SVG content is sanitized to remove embedded scripts and event handlers

## 13.2 Content Security Policy

- [ ] **CSP header defined in next.config.ts security headers** — Content-Security-Policy header configured with restrictive defaults in the Next.js configuration
- [ ] **script-src restrictive** — no unsafe-inline in production; nonce-based script loading used if inline scripts are required
- [ ] **style-src allows Tailwind** — style-src configured to accommodate Tailwind CSS output, with unsafe-inline permitted only if CSS-in-JS requires it
- [ ] **connect-src limits API connections to known backend origins** — only the backend API origin and any required third-party services are allowed in connect-src
- [ ] **frame-ancestors 'none' prevents clickjacking** — the application cannot be embedded in iframes on other domains
- [ ] **img-src includes known image sources** — img-src allows self, backend media origin, and any CDN used for images — no wildcard *
- [ ] **CSP violations reported** — report-uri or report-to directive configured to collect and monitor CSP violation reports

## 13.3 Token Security

- [ ] **Access token stored in memory only** — the JWT access token is held in a module-level variable, never written to any persistent browser storage
- [ ] **Never persisted to localStorage, sessionStorage, or cookies** — access tokens are not stored in any browser storage mechanism accessible to JavaScript
- [ ] **Refresh token in HttpOnly cookie** — the refresh token is set by the backend as an HttpOnly, Secure, SameSite cookie, inaccessible to JavaScript
- [ ] **No token in URL query parameters** — tokens are never passed as URL parameters where they could be logged in browser history, server logs, or referrer headers
- [ ] **No token logged to console or error reports** — console.log, Sentry breadcrumbs, and error reports are scrubbed of any token values
- [ ] **CSP prevents token exfiltration via XSS injection** — even if XSS is achieved, connect-src restrictions prevent sending stolen tokens to attacker-controlled domains
- [ ] **has_session cookie is a boolean hint only** — the has_session cookie contains no token data, serving only as a signal to middleware for auth-aware routing

## 13.4 Input Sanitization

- [ ] **All user input validated through Zod schemas before submission** — form data passes through Zod validation before being sent to the API, rejecting malformed input client-side
- [ ] **File uploads validate type and size client-side** — file inputs enforce allowed MIME types and maximum file size before upload, with clear error messages
- [ ] **No eval() of user-provided strings** — eval, new Function, and other dynamic code execution methods are never used with user input
- [ ] **No dynamic import() with user-controlled paths** — import paths are always static strings, never constructed from user input or URL parameters
- [ ] **URL params and search params validated before use** — useSearchParams values are validated and sanitized before being used in API calls, DOM rendering, or navigation
- [ ] **User input in API requests is parameterized** — API request URLs are constructed using Axios params, not string concatenation with user input

## 13.5 CSRF Protection

- [ ] **API requests include credentials** — withCredentials: true set on the Axios instance to send cookies (including refresh token) with cross-origin API requests
- [ ] **SameSite cookie policy set** — refresh token and session cookies use SameSite=Lax or SameSite=Strict to prevent cross-site request attachment
- [ ] **API proxy forwards CSRF tokens if backend requires them** — the Next.js API proxy passes through any CSRF token headers required by the Django backend
- [ ] **State-changing operations use POST/PUT/PATCH/DELETE** — no mutations are performed via GET requests, which could be triggered by image tags or link prefetching
- [ ] **No sensitive actions performed via GET requests** — logout, account deletion, and other destructive operations require explicit POST/DELETE with proper authentication

## 13.6 Dependency Security

- [ ] **npm audit run periodically** — no known critical or high severity vulnerabilities in production dependencies
- [ ] **Dependencies version-pinned in package-lock.json** — exact versions locked to prevent supply chain attacks via semver range exploitation
- [ ] **No dependencies from untrusted sources** — all packages are from well-known publishers on npm, not obscure or recently-created packages
- [ ] **Husky pre-commit hooks prevent committing secrets** — .env files, private keys, and API tokens are caught by pre-commit checks before reaching the repository
- [ ] **Dependencies reviewed before adding** — new packages are evaluated for license compatibility, maintenance status, bundle size impact, and security track record
- [ ] **Dependabot or similar automated vulnerability alerts enabled** — automated scanning monitors dependencies for newly disclosed vulnerabilities

## 13.7 Sensitive Data Handling

- [ ] **No PII logged to console in production code** — user emails, names, phone numbers, and other personal data are not written to console.log in production builds
- [ ] **Error reporting scrubs sensitive fields before sending** — Sentry or equivalent error reporting is configured to strip passwords, tokens, and PII from error context
- [ ] **No passwords or tokens in URL parameters** — authentication credentials are never included in URLs where they could be logged or leaked via referrer headers
- [ ] **Autocomplete attributes set correctly on password fields** — password inputs use autocomplete="current-password" or autocomplete="new-password" as appropriate
- [ ] **Sensitive data not stored in browser history** — no secrets in URL query parameters, no sensitive form data in navigation state
- [ ] **Form data cleared from memory after submission** — form state is reset after successful submission, not persisted in component state or Zustand stores

## 13.8 Open Redirect Prevention

- [ ] **callbackUrl in login redirect validated** — post-login redirect URLs are verified to be same-origin, preventing redirection to attacker-controlled sites
- [ ] **No user-controlled redirect URLs without validation** — any URL parameter used for redirection is validated against an allowlist of safe destinations
- [ ] **router.push targets are static routes or validated** — programmatic navigation uses only known internal routes, never user-provided URLs without validation
- [ ] **External links use target="_blank" with rel="noopener noreferrer"** — links opening external sites prevent window.opener access and referrer leakage
- [ ] **Redirect destinations from URL params are allowlisted** — URL parameters like returnTo, next, or redirect are validated against a list of permitted internal paths

## 13.9 Client-Side Authorization

- [ ] **UI permission gates are convenience only** — <Can> component and guards improve UX but are not the security boundary — the backend enforces all authorization
- [ ] **Hidden UI elements are not the security boundary** — elements hidden via _permissions are not accessible, but even if revealed, the backend would reject unauthorized requests
- [ ] **Disabled buttons don't prevent API calls** — disabled UI controls are a UX signal, not a security mechanism — the backend rejects unauthorized requests regardless
- [ ] **No security-critical decisions made client-side** — pricing calculations, discount eligibility, and access control are computed server-side, not trusted from the client
- [ ] **User role and permission changes reflect immediately** — when a user's permissions are revoked, the UI updates on the next API response without requiring a full page reload

## 13.10 Security Headers

- [ ] **X-Content-Type-Options: nosniff** — prevents browsers from MIME-sniffing responses away from the declared Content-Type
- [ ] **X-Frame-Options: DENY** — prevents the page from being loaded in iframes, redundant with CSP frame-ancestors but provides backward compatibility
- [ ] **Referrer-Policy: strict-origin-when-cross-origin** — limits referrer information sent to external sites, preventing URL leakage
- [ ] **Permissions-Policy disables unused APIs** — camera, microphone, geolocation, and other browser APIs disabled unless explicitly needed by the application
- [ ] **X-XSS-Protection: 0** — explicitly disabled because the browser's XSS auditor can introduce vulnerabilities; CSP is the modern replacement
- [ ] **Security headers verified via browser DevTools or scanners** — response headers checked with securityheaders.com or browser network tab to confirm all headers are set correctly
