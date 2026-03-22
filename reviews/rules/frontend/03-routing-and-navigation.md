# 03 — Routing & Navigation Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 3.1 Route Group Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 3.1.1 | FAIL if unauthenticated pages (home, explore, business/[slug]) are not under (public) route group | PASS/FAIL |
| 3.1.2 | FAIL if auth flows (login, register, forgot-password) are not under (auth) route group | PASS/FAIL |
| 3.1.3 | FAIL if authenticated routes (dashboard, bconsole, pconsole, admin) are not under (app) route group | PASS/FAIL |
| 3.1.4 | WARN if nested sub-groups are not correctly scoped ((user), bconsole/[slug], pconsole, admin) | PASS/WARN |
| 3.1.5 | FAIL if two route groups resolve to the same URL path (parallel conflict) | PASS/FAIL |
| 3.1.6 | FAIL if parenthesized route group names appear in URLs | PASS/FAIL |
| 3.1.7 | FAIL if any route group is missing a layout.tsx file | PASS/FAIL |
| 3.1.8 | WARN if route group boundaries do not align with guard requirements (app→AuthGuard, bconsole→BusinessGuard) | PASS/WARN |

## 3.2 Middleware

| ID | Rule | Verdict |
|----|------|---------|
| 3.2.1 | FAIL if middleware.ts is not at src/ root | PASS/FAIL |
| 3.2.2 | FAIL if middleware reads/decodes JWTs instead of checking has_session cookie | PASS/FAIL |
| 3.2.3 | FAIL if authenticated users on auth pages are not redirected to /home | PASS/FAIL |
| 3.2.4 | FAIL if unauthenticated users on protected routes are not redirected to /login | PASS/FAIL |
| 3.2.5 | FAIL if matcher does not exclude _next/static, _next/image, favicon.ico, api/ | PASS/FAIL |
| 3.2.6 | FAIL if middleware performs database queries, external API calls, or heavy computation | PASS/FAIL |
| 3.2.7 | FAIL if middleware accesses database or external services | PASS/FAIL |
| 3.2.8 | WARN if callbackUrl is not properly encoded in redirect | PASS/WARN |

## 3.3 Layout Hierarchy

| ID | Rule | Verdict |
|----|------|---------|
| 3.3.1 | FAIL if root layout.tsx does not wrap children in Providers component | PASS/FAIL |
| 3.3.2 | FAIL if (auth) layout is not a clean centered shell (no sidebar/topbar) | PASS/FAIL |
| 3.3.3 | FAIL if (app) layout does not provide sidebar + topbar + bottom nav shell | PASS/FAIL |
| 3.3.4 | WARN if bconsole layout does not extract slug and provide business-scoped nav | PASS/WARN |
| 3.3.5 | WARN if pconsole layout does not provide platform-specific navigation | PASS/WARN |
| 3.3.6 | WARN if layout files contain inline business logic instead of delegating to components | PASS/WARN |
| 3.3.7 | WARN if layouts perform data fetching that should be in page components | PASS/WARN |

## 3.4 Route Guards

| ID | Rule | Verdict |
|----|------|---------|
| 3.4.1 | FAIL if AuthGuard does not check both has_session cookie and auth store initialization | PASS/FAIL |
| 3.4.2 | FAIL if BusinessGuard does not validate active membership for current [slug] | PASS/FAIL |
| 3.4.3 | FAIL if PlatformGuard does not validate platform membership | PASS/FAIL |
| 3.4.4 | WARN if AdminGuard does not check admin role permissions | PASS/WARN |
| 3.4.5 | FAIL if guards show blank screen instead of loading skeleton during initialization | PASS/FAIL |
| 3.4.6 | WARN if guards do not redirect with callbackUrl on failure | PASS/WARN |
| 3.4.7 | FAIL if guards flash-render protected content before authorization confirmed | PASS/FAIL |
| 3.4.8 | WARN if guard test suites do not cover both authorized and unauthorized cases | PASS/WARN |

## 3.5 Dynamic Routes

| ID | Rule | Verdict |
|----|------|---------|
| 3.5.1 | WARN if [slug] param is not validated before use in API calls | PASS/WARN |
| 3.5.2 | WARN if user profile pages mix [id] and [username] for the same resource | PASS/WARN |
| 3.5.3 | WARN if [id] params for detail pages are not validated as UUID format | PASS/WARN |
| 3.5.4 | WARN if dynamic params are typed as any or unknown instead of { slug: string } | PASS/WARN |
| 3.5.5 | WARN if notFound() is not called for invalid/non-existent dynamic params | PASS/WARN |
| 3.5.6 | FAIL if unescaped user input is used in route construction | PASS/FAIL |
| 3.5.7 | FAIL if catch-all [...path] is used for content pages instead of only API proxy | PASS/FAIL |

## 3.6 Navigation Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 3.6.1 | FAIL if navigation items are not centrally defined in a config file | PASS/FAIL |
| 3.6.2 | WARN if nav items do not have permission gates for visibility control | PASS/WARN |
| 3.6.3 | FAIL if slug interpolation does not work in bconsole route hrefs | PASS/FAIL |
| 3.6.4 | WARN if isNavActive does not handle both exact and prefix matching | PASS/WARN |
| 3.6.5 | WARN if no AccountSwitcher for context switching between accounts | PASS/WARN |
| 3.6.6 | WARN if sidebar is not visible on desktop (md+) breakpoints | PASS/WARN |
| 3.6.7 | WARN if bottom navbar is not visible on mobile (sm) breakpoints | PASS/WARN |
| 3.6.8 | WARN if no mobile menu sheet for tablet navigation | PASS/WARN |

## 3.7 Page Components

| ID | Rule | Verdict |
|----|------|---------|
| 3.7.1 | WARN if page.tsx files exceed 30 lines (thin wrapper principle) | PASS/WARN |
| 3.7.2 | WARN if pages do not export metadata for SEO | PASS/WARN |
| 3.7.3 | FAIL if pages contain business logic (API calls, state management, complex rendering) | PASS/FAIL |
| 3.7.4 | WARN if "use client" is blanket-applied to all pages instead of only where needed | PASS/WARN |
| 3.7.5 | WARN if pages access useParams directly instead of passing params as props | PASS/WARN |
| 3.7.6 | WARN if pages contain inline styles or complex JSX | PASS/WARN |
| 3.7.7 | INFO if server component pages do not leverage server-side data fetching where appropriate | PASS/INFO |

## 3.8 Loading & Error States

| ID | Rule | Verdict |
|----|------|---------|
| 3.8.1 | WARN if loading.tsx is missing at key route segments (root, (user), bconsole, pconsole) | PASS/WARN |
| 3.8.2 | WARN if error.tsx is missing at key route segments with no reset functionality | PASS/WARN |
| 3.8.3 | WARN if not-found.tsx does not provide useful content and link back to home | PASS/WARN |
| 3.8.4 | FAIL if global-error.tsx relies on Tailwind CSS instead of inline styles | PASS/FAIL |
| 3.8.5 | WARN if error boundaries do not call reportError for error tracking | PASS/WARN |
| 3.8.6 | WARN if loading skeletons do not match eventual content layout (CLS risk) | PASS/WARN |
| 3.8.7 | FAIL if blank screens occur during navigation transitions | PASS/FAIL |

## 3.9 API Proxy Route

| ID | Rule | Verdict |
|----|------|---------|
| 3.9.1 | FAIL if no catch-all API proxy route exists at /api/[...path]/route.ts | PASS/FAIL |
| 3.9.2 | FAIL if proxy does not preserve authentication cookies | PASS/FAIL |
| 3.9.3 | WARN if proxy does not forward relevant headers (Authorization, Content-Type, Accept) | PASS/WARN |
| 3.9.4 | FAIL if proxy does not handle all HTTP methods (GET, POST, PUT, PATCH, DELETE) | PASS/FAIL |
| 3.9.5 | WARN if large uploads/downloads are buffered entirely in memory instead of streamed | PASS/WARN |
| 3.9.6 | FAIL if proxy error responses leak internal backend URLs to the client | PASS/FAIL |

## 3.10 Redirects & Rewrites

| ID | Rule | Verdict |
|----|------|---------|
| 3.10.1 | WARN if /dashboard does not redirect to /home | PASS/WARN |
| 3.10.2 | WARN if /business/:slug/* does not redirect to /bconsole/:slug/* | PASS/WARN |
| 3.10.3 | WARN if /platform/:path does not redirect to /pconsole/:path with profile exception | PASS/WARN |
| 3.10.4 | FAIL if /media/* does not rewrite to backend media URL | PASS/FAIL |
| 3.10.5 | FAIL if redirect loops exist | PASS/FAIL |
| 3.10.6 | WARN if permanent redirects (308) are used for routes that may change | PASS/WARN |
