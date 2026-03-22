# 13 — Security Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 13.1 XSS Prevention

| ID | Rule | Verdict |
|----|------|---------|
| 13.1.1 | FAIL if dangerouslySetInnerHTML is used without content sanitization (DOMPurify or equivalent) | PASS/FAIL |
| 13.1.2 | PASS if user input is rendered via {variable} in JSX relying on React's built-in escaping | PASS/FAIL |
| 13.1.3 | FAIL if attribute values are constructed via string interpolation and injected as HTML | PASS/FAIL |
| 13.1.4 | PASS if backend-provided content is displayed as text nodes, not injected as raw HTML | PASS/FAIL |
| 13.1.5 | FAIL if user-generated URLs are used in href without javascript: protocol validation | PASS/FAIL |
| 13.1.6 | FAIL if HTML is constructed as template literal strings and injected into the DOM | PASS/FAIL |
| 13.1.7 | WARN if user-provided SVG content is rendered without sanitization | PASS/WARN |

## 13.2 Content Security Policy

| ID | Rule | Verdict |
|----|------|---------|
| 13.2.1 | FAIL if CSP header is not defined in next.config.ts security headers | PASS/FAIL |
| 13.2.2 | WARN if script-src allows unsafe-inline in production | PASS/WARN |
| 13.2.3 | PASS if style-src accommodates Tailwind CSS output | PASS/FAIL |
| 13.2.4 | WARN if connect-src is not limited to known backend origins | PASS/WARN |
| 13.2.5 | PASS if frame-ancestors 'none' prevents clickjacking | PASS/FAIL |
| 13.2.6 | WARN if img-src uses wildcard * instead of specific origins | PASS/WARN |
| 13.2.7 | INFO if CSP violations are not reported via report-uri or report-to | PASS/INFO |

## 13.3 Token Security

| ID | Rule | Verdict |
|----|------|---------|
| 13.3.1 | FAIL if access token is stored in localStorage, sessionStorage, or cookies | PASS/FAIL |
| 13.3.2 | FAIL if access token is persisted to any browser storage mechanism | PASS/FAIL |
| 13.3.3 | FAIL if refresh token is not in an HttpOnly, Secure, SameSite cookie | PASS/FAIL |
| 13.3.4 | FAIL if tokens appear in URL query parameters | PASS/FAIL |
| 13.3.5 | WARN if tokens are logged to console or included in error reports | PASS/WARN |
| 13.3.6 | PASS if CSP connect-src prevents token exfiltration to unknown domains | PASS/FAIL |
| 13.3.7 | PASS if has_session cookie is a boolean hint only (no token data) | PASS/FAIL |

## 13.4 Input Sanitization

| ID | Rule | Verdict |
|----|------|---------|
| 13.4.1 | PASS if all user input is validated through Zod schemas before API submission | PASS/FAIL |
| 13.4.2 | PASS if file uploads validate MIME type and size client-side | PASS/FAIL |
| 13.4.3 | FAIL if eval() or new Function() is used with user-provided strings | PASS/FAIL |
| 13.4.4 | FAIL if dynamic import() paths are constructed from user input | PASS/FAIL |
| 13.4.5 | WARN if URL params and search params are used without validation | PASS/WARN |
| 13.4.6 | PASS if API request URLs use Axios params, not string concatenation with user input | PASS/FAIL |

## 13.5 CSRF Protection

| ID | Rule | Verdict |
|----|------|---------|
| 13.5.1 | FAIL if withCredentials is not set on the Axios instance | PASS/FAIL |
| 13.5.2 | PASS if refresh/session cookies use SameSite=Lax or Strict | PASS/FAIL |
| 13.5.3 | PASS if API proxy forwards CSRF tokens when backend requires them | PASS/FAIL |
| 13.5.4 | FAIL if mutations are performed via GET requests | PASS/FAIL |
| 13.5.5 | FAIL if sensitive actions (logout, delete) use GET instead of POST/DELETE | PASS/FAIL |

## 13.6 Dependency Security

| ID | Rule | Verdict |
|----|------|---------|
| 13.6.1 | WARN if npm audit shows critical or high severity vulnerabilities | PASS/WARN |
| 13.6.2 | PASS if package-lock.json pins exact versions | PASS/FAIL |
| 13.6.3 | WARN if dependencies include packages from untrusted or recently-created publishers | PASS/WARN |
| 13.6.4 | WARN if pre-commit hooks do not catch .env files or secrets | PASS/WARN |
| 13.6.5 | INFO if new packages are not evaluated before adding | PASS/INFO |
| 13.6.6 | INFO if automated vulnerability alerts (Dependabot) are not enabled | PASS/INFO |

## 13.7 Sensitive Data Handling

| ID | Rule | Verdict |
|----|------|---------|
| 13.7.1 | FAIL if console.log includes PII (emails, names, phone numbers) in production code | PASS/FAIL |
| 13.7.2 | WARN if error reporting does not scrub passwords, tokens, and PII | PASS/WARN |
| 13.7.3 | FAIL if passwords or tokens appear in URL parameters | PASS/FAIL |
| 13.7.4 | PASS if password inputs use correct autocomplete attributes | PASS/FAIL |
| 13.7.5 | PASS if no secrets exist in URL query parameters or navigation state | PASS/FAIL |
| 13.7.6 | PASS if form state is reset after successful submission | PASS/FAIL |

## 13.8 Open Redirect Prevention

| ID | Rule | Verdict |
|----|------|---------|
| 13.8.1 | FAIL if callbackUrl in login redirect is not validated as same-origin | PASS/FAIL |
| 13.8.2 | FAIL if user-controlled redirect URLs are used without validation | PASS/FAIL |
| 13.8.3 | WARN if router.push targets include user-provided URLs without validation | PASS/WARN |
| 13.8.4 | WARN if external links lack target="_blank" with rel="noopener noreferrer" | PASS/WARN |
| 13.8.5 | PASS if redirect URL params (returnTo, next) are validated against permitted paths | PASS/FAIL |

## 13.9 Client-Side Authorization

| ID | Rule | Verdict |
|----|------|---------|
| 13.9.1 | PASS if <Can> component and guards are UX convenience, not the security boundary | PASS/FAIL |
| 13.9.2 | PASS if hidden UI elements are supplemented by backend enforcement | PASS/FAIL |
| 13.9.3 | PASS if disabled buttons don't substitute for backend authorization | PASS/FAIL |
| 13.9.4 | FAIL if security-critical decisions (pricing, access control) are computed client-side only | PASS/FAIL |
| 13.9.5 | PASS if permission changes reflect on next API response without page reload | PASS/FAIL |

## 13.10 Security Headers

| ID | Rule | Verdict |
|----|------|---------|
| 13.10.1 | FAIL if X-Content-Type-Options: nosniff is not set | PASS/FAIL |
| 13.10.2 | FAIL if X-Frame-Options: DENY is not set | PASS/FAIL |
| 13.10.3 | WARN if Referrer-Policy is not set to strict-origin-when-cross-origin or stricter | PASS/WARN |
| 13.10.4 | WARN if Permissions-Policy does not disable unused browser APIs | PASS/WARN |
| 13.10.5 | INFO if X-XSS-Protection: 0 is not explicitly set | PASS/INFO |
| 13.10.6 | INFO if security headers have not been verified via scanners or DevTools | PASS/INFO |
