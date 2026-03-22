# 03 — Routing & Navigation Checklist

## 3.1 Route Group Architecture

- [ ] **(public) group contains unauthenticated routes** — home, about, explore, business/[slug], platform/[slug], user/[username] are all accessible without a session cookie
- [ ] **(auth) group contains authentication flows** — login, register, forgot-password, reset-password, verify-email pages are scoped to the auth layout with a clean centered shell
- [ ] **(app) group contains authenticated routes** — personal dashboard, settings, bconsole/[slug], pconsole, admin pages all require authentication
- [ ] **Nested sub-groups are correctly scoped** — (user) for personal pages, bconsole/[slug] for business console with slug context, pconsole for platform console, admin for admin panel
- [ ] **No two route groups resolve to the same URL path** — verified that no parallel route conflict exists (e.g. app/page.tsx and app/(public)/page.tsx both mapping to /)
- [ ] **Route groups do not create URL segments** — parenthesized names ((public), (auth), (app)) are organizational only; the URL for (public)/explore is /explore, not /public/explore
- [ ] **Each route group has an appropriate layout.tsx** — (auth) layout provides a minimal centered shell, (app) layout provides sidebar + topbar, bconsole layout provides business-scoped navigation
- [ ] **Route group boundaries align with guard requirements** — (app) layout wraps children in AuthGuard, bconsole layout wraps in BusinessGuard, pconsole wraps in PlatformGuard

## 3.2 Middleware

- [ ] **middleware.ts located at src/ root** — the middleware file is at the correct location for Next.js App Router to detect it (src/middleware.ts or middleware.ts)
- [ ] **Checks has_session cookie, not JWT** — middleware inspects the has_session cookie flag for auth status; it never reads, decodes, or validates JWTs (JWTs are in-memory only)
- [ ] **Authenticated users on auth pages get redirected** — users with has_session visiting /login or /register are redirected to /home to prevent re-authentication
- [ ] **Unauthenticated users on protected routes get redirected** — users without has_session visiting (app) routes are redirected to /login with a callbackUrl query parameter preserving the intended destination
- [ ] **Matcher excludes static assets** — the config.matcher array excludes _next/static, _next/image, favicon.ico, api/ routes, and other non-page resources
- [ ] **No heavy computation in middleware** — middleware runs on Edge Runtime; it performs only cookie checks and redirects, no database queries, no external API calls, no complex logic
- [ ] **Middleware does not access database or external services** — all middleware logic is self-contained using only the request object, cookies, and NextResponse
- [ ] **callbackUrl is properly encoded** — the redirect URL encodes the original path correctly so the login page can redirect back after successful authentication

## 3.3 Layout Hierarchy

- [ ] **Root layout.tsx wraps Providers** — the top-level app/layout.tsx imports and renders the Providers component, sets html lang, applies global font className
- [ ] **Auth layout provides a clean shell** — (auth)/layout.tsx renders a centered card-style layout without sidebar or topbar, appropriate for login/register flows
- [ ] **App layout provides sidebar + topbar** — (app)/layout.tsx renders the main application shell with Sidebar (desktop), TopNavbar, BottomNavbar (mobile), and content area
- [ ] **bconsole layout provides business-scoped nav** — bconsole/[slug]/layout.tsx extracts the slug param, renders business-specific navigation items, and provides business context
- [ ] **pconsole layout provides platform navigation** — pconsole/layout.tsx renders platform-specific navigation items for platform management
- [ ] **Each layout is minimal and delegates to components** — layout files are thin wrappers that import and compose navigation/shell components, no inline business logic
- [ ] **No data fetching in layouts that should be in pages** — layouts handle structural concerns (navigation, guards); data fetching for content happens in page components or feature hooks

## 3.4 Route Guards

- [ ] **AuthGuard requires has_session cookie + initialized auth store** — checks both the cookie (for initial server render) and the Zustand auth store (for client-side state), shows loading skeleton until initialized
- [ ] **BusinessGuard requires active business membership** — checks the membership store for an active membership matching the current [slug] parameter, redirects if not a member
- [ ] **PlatformGuard requires platform membership** — validates the user has a platform-level membership before rendering platform console routes
- [ ] **AdminGuard requires admin role** — checks the user's role against admin permissions, redirects non-admins to a forbidden page or home
- [ ] **All guards show loading skeleton during initialization** — guards render a skeleton UI (not a blank screen or spinner) while auth state and membership data are being loaded
- [ ] **Guards redirect with callbackUrl on failure** — when a guard denies access, it redirects to /login (or /home for role-based denial) with the original URL as callbackUrl
- [ ] **Guards do not render children until authorization confirmed** — the protected content is never flash-rendered before the guard check completes, preventing unauthorized content flicker
- [ ] **Guard tests verify both redirect and render behavior** — test suites for each guard cover the authorized case (renders children) and unauthorized case (redirects with correct URL)

## 3.5 Dynamic Routes

- [ ] **[slug] for business accounts is validated before use** — the slug parameter is checked against a valid format and the business is confirmed to exist before rendering the detail page
- [ ] **[username] for user profiles follows consistent patterns** — user profile pages use [username] consistently, not mixing [id] and [username] for the same resource
- [ ] **[id] for resource detail pages uses UUID format** — members, transactions, forms detail pages use UUID-formatted [id] params, validated for format before API calls
- [ ] **Dynamic params are properly typed** — params are typed as { slug: string } or { id: string } in page component props, not left as any or unknown
- [ ] **not-found handling for invalid dynamic params** — when a dynamic route receives an invalid or non-existent param, notFound() is called to render the 404 page
- [ ] **No unescaped user input in route construction** — route paths constructed with dynamic segments use proper encoding (encodeURIComponent) to prevent injection
- [ ] **Catch-all [...path] used only for API proxy** — the catch-all route pattern is restricted to the API proxy route handler, not used for content pages

## 3.6 Navigation Configuration

- [ ] **navigation-config.ts defines items for all contexts** — personal navigation, business console navigation, and platform console navigation items are centrally defined with labels, hrefs, and icons
- [ ] **Nav items have permission gates** — navigation items include permission requirements (can_view_members, can_manage_forms, can_view_transactions) that control visibility based on the user's _permissions
- [ ] **resolveHref handles slug interpolation** — bconsole routes like /bconsole/:slug/members correctly substitute the active business slug into the href at render time
- [ ] **isNavActive handles exact and prefix matching** — the active state detection correctly highlights both exact matches (/home) and prefix matches (/bconsole/acme/members/*)
- [ ] **AccountSwitcher allows context switching** — users can switch between personal account, business accounts, and platform accounts via the switcher component
- [ ] **Sidebar renders on desktop viewports** — the sidebar component is visible on md+ breakpoints with full navigation items and account switcher
- [ ] **BottomNavbar renders on mobile viewports** — a fixed bottom navigation bar appears on sm breakpoints with the most essential navigation items
- [ ] **MobileMenuSheet provides tablet navigation** — a slide-out sheet provides full navigation on tablet-sized viewports, triggered by a hamburger menu button

## 3.7 Page Components

- [ ] **Pages are thin wrappers under 30 lines** — page.tsx files in app/ import a feature component and render it, with minimal props extraction from params/searchParams
- [ ] **Pages export metadata for SEO** — each page exports a metadata object or generateMetadata function providing title, description, and OpenGraph properties
- [ ] **Pages do not contain business logic** — no API calls, no state management, no complex conditional rendering in page files; all logic lives in feature components
- [ ] **Client pages use "use client" only when necessary** — the "use client" directive is added only to pages that use hooks or browser APIs, not blanket-applied to all pages
- [ ] **Pages pass params and searchParams to feature components** — URL parameters are extracted in the page and passed as props to the feature component, not accessed inside feature components via useParams
- [ ] **No inline styles or complex JSX in pages** — page files are clean delegates, not places for layout hacking or one-off styling
- [ ] **Server component pages leverage server-side data fetching** — when appropriate, page components use async/await to fetch data server-side before rendering, avoiding client-side loading states

## 3.8 Loading & Error States

- [ ] **loading.tsx exists at appropriate route segments** — route groups and major sections have loading.tsx files that show skeleton UIs during navigation transitions
- [ ] **error.tsx exists at route segments with reset functionality** — error boundaries at key segments catch runtime errors and provide a "Try again" button that calls reset()
- [ ] **not-found.tsx provides useful 404 content** — the 404 page includes a friendly message, a link back to home, and optionally a search suggestion
- [ ] **global-error.tsx uses inline styles** — the global error boundary cannot rely on Tailwind CSS being loaded, so it uses inline style={{}} attributes for layout and typography
- [ ] **Error boundaries call reportError for tracking** — error.tsx components forward the error to an error tracking service (Sentry, LogRocket) before displaying the fallback UI
- [ ] **Loading states match eventual content layout** — skeleton UIs have the same dimensions and structure as the content they replace, preventing Cumulative Layout Shift (CLS)
- [ ] **No blank screens during navigation** — every route transition shows either a loading skeleton, a suspense fallback, or instant content — never a blank white screen

## 3.9 API Proxy Route

- [ ] **Proxy route at /api/[...path]/route.ts** — a single catch-all API route forwards all requests to the backend, keeping the backend URL private from the browser
- [ ] **Proxy preserves authentication cookies** — withCredentials or equivalent is set so that session cookies are forwarded to the backend on proxied requests
- [ ] **Proxy forwards relevant request headers** — Authorization, Content-Type, Accept, and custom headers are passed through to the backend; Host and Origin are correctly set
- [ ] **Proxy handles all HTTP methods** — GET, POST, PUT, PATCH, DELETE handlers are all exported from the route handler, not just GET
- [ ] **No request/response body buffering issues** — large file uploads and downloads are streamed, not buffered entirely in memory on the Next.js server
- [ ] **Proxy does not expose internal backend URLs** — error responses from the proxy do not leak the NEXT_PUBLIC_API_URL or internal backend hostname to the client

## 3.10 Redirects & Rewrites

- [ ] **/dashboard redirects to /home** — legacy dashboard URL is permanently redirected to the new home route so bookmarks and external links continue working
- [ ] **/business/:slug/* redirects to /bconsole/:slug/** — old business console URLs are redirected to the new bconsole route structure
- [ ] **/platform/:path redirects to /pconsole/:path with profile exception** — platform routes redirect to pconsole, but /platform/[slug]/profile is excluded via path-to-regexp negative lookahead (:path((?!profile).+))
- [ ] **/media/* rewrites to backend media URL** — media file requests are transparently rewritten to the backend media server without a visible redirect to the client
- [ ] **No redirect loops exist** — verified that no redirect chain creates a cycle (e.g. /a -> /b -> /a) by testing all redirect paths
- [ ] **Redirects use permanent: false during development** — non-permanent redirects (307/308) are used during development for flexibility; permanent redirects applied only when routes are stable
