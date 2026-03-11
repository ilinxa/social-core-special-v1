# Frontend Foundation — Implementation Reference

**Version:** v1
**Last Updated:** 2026-03-01
**Status:** Implemented
**Plan:** `C:\Users\AsiaData\.claude\plans\hazy-roaming-sunrise.md`
**Builds on:** `docs/implementations/frontend/api-authentication.md` (auth system v1)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  EDGE (middleware.ts)                                               │
│  has_session cookie → redirect auth/protected routes                │
│  Thin: auth-only checks. No membership/permission logic.            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  PROVIDERS (Providers.tsx → root layout.tsx)                        │
│  QueryClientProvider > ThemeProvider > AuthInitializer > App        │
│                                       │                             │
│  AuthInitializer:                                                   │
│    silentRefresh → Promise.all(fetchUser, fetchMemberships)         │
│    → setUser + setMemberships (both Zustand stores)                 │
│    → setInitialized (always, even on failure)                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  ROUTE GROUPS                                                       │
│                                                                     │
│  (auth)/       Login, register, verify, etc. (no sidebar)           │
│  (public)/     Landing page (no sidebar)                            │
│  (app)/        Protected — AuthGuard + sidebar layout               │
│    ├── (user)/ Dashboard, profile, settings, sessions               │
│    ├── business/[slug]/  BusinessGuard → business routes            │
│    ├── platform/         PlatformGuard → platform routes            │
│    └── admin/            AdminGuard → admin routes                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  GUARD COMPONENTS (components/guards/)                              │
│                                                                     │
│  AuthGuard      → isAuthenticated check from auth-store             │
│  BusinessGuard  → membership check by slug + retry-on-miss          │
│  PlatformGuard  → platform membership check + retry-on-miss         │
│  AdminGuard     → is_staff || is_superuser (no retry)               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  STATE MANAGEMENT                                                   │
│                                                                     │
│  ┌─────────────────────┐  ┌──────────────────────┐                  │
│  │ Zustand: auth-store │  │ Zustand: membership  │                  │
│  │ user, isAuth, isInit│  │ memberships[], isLoad │                  │
│  └─────────────────────┘  └──────────────────────┘                  │
│          │                         │                                │
│  ┌───────▼─────────────────────────▼──────────────────────────┐     │
│  │ TanStack Query (server state)                              │     │
│  │ users.me() | users.memberships() | business.detail(slug)   │     │
│  │ business.my() | platform.account() | auth.sessions()       │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  API MODULES (features/{domain}/api/)                               │
│                                                                     │
│  auth-api.ts      15 functions (login, register, refresh, etc.)     │
│  membership-api.ts 1 function (fetchMyMembershipsApi)               │
│  users-api.ts     6 functions (profile, avatar CRUD)                │
│  business-api.ts  5 functions (my, get, create, update, delete)     │
│  platform-api.ts  3 functions (account, profile, settings)          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  API CLIENT (lib/api-client.ts)                                     │
│  Axios + JWT interceptor + refresh queue                            │
│  Access token: in-memory (never localStorage)                       │
│  Refresh token: HttpOnly cookie (browser-managed)                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts & Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Business/platform context | URL-based (`/business/{slug}/...`, `/platform/...`) | Explicit, self-documenting, shareable URLs |
| 2 | When to fetch memberships | On auth init (parallel with user fetch) | Small payload (<10 items), needed for sidebar nav |
| 3 | Route access enforcement | Middleware = auth only; Layout guards = membership/permission | Edge middleware can't call backend; guards use cached Zustand state |
| 4 | Active context for API calls | Explicit params (pass slug/id to functions) | No hidden state; URL is source of truth |
| 5 | Permission checking | Client-side for UI, backend for enforcement | `useHasPermission()` checks cache; backend is final authority |
| 6 | Global mutation error handling | No global `onError` toast | Every mutation explicitly handles its errors; no double-toast |
| 7 | Membership freshness | Event-driven invalidation, not timer-based | Memberships change through discrete events, not on a clock |
| 8 | State management split | Zustand = client state, TanStack Query = server state | Zustand for auth/membership (bootstrapped once), TQ for data fetching |

---

## 3. Three-Tier Authorization Model

> **Core principle:** The backend is the sole security authority. All frontend authorization is a UX optimization.

### Tier 1 — Navigation Hints (cached, can be stale)

**Purpose:** Sidebar links, tab visibility, conditional UI rendering.
**Source:** Zustand membership store selectors.
**Freshness:** Best-effort from last fetch. Can be stale.
**Performance:** Zero API calls.

Hooks: `useBusinessMemberships()`, `usePlatformMembership()`, `useHasPermission()`, `useIsMember()`, `useIsOwner()`

Worst case if stale: user sees a link that leads to a guard denial or 403 — both handled gracefully.

### Tier 2 — Route Guards (cached + single retry on miss)

**Purpose:** Deciding whether to render a route or show "Access Denied."
**Source:** Zustand membership store, with one retry-fetch on cache miss.
**Performance:** Zero API calls in common case. One API call on cache miss (rare).

Guard flow (BusinessGuard / PlatformGuard):
1. Check cached memberships for match
2. If found with `status === "active"` → allow instantly
3. If NOT found and memberships are loaded → call `fetchMyMembershipsApi()` → update Zustand store
4. If still not found after fresh fetch → show "Access Denied"

AdminGuard: simple cached check (`user.is_staff || user.is_superuser`), no retry.

### Tier 3 — Action Enforcement (always backend)

**Purpose:** Can this user perform this specific action?
**Source:** Backend API response (200 = allowed, 403 = denied).
**Performance:** One API call per action (already required for the mutation).

If `useHasPermission()` cache is stale and a button is visible that shouldn't be, the backend returns 403 and `handleApiError()` shows an appropriate message.

### Invalidation Events

| Event | Trigger | Mechanism |
|-------|---------|-----------|
| User logs in | Auth init | `fetchMyMembershipsApi()` in `AuthInitializer` |
| User's own mutation | Join/leave/create business | `invalidateMemberships(queryClient)` in `onSuccess` |
| Route guard cache miss | Direct link to new business | Guard triggers single refetch before denying |
| User returns to tab | Window/tab focus | TanStack Query `refetchOnWindowFocus: "always"` |

---

## 4. Data Layer

### 4.1 API Functions

#### Auth (`features/auth/api/auth-api.ts`)

| Function | Method | Endpoint | Side Effects |
|----------|--------|----------|-------------|
| `loginApi` | POST | `/auth/login/` | setAccessToken, setSessionCookie |
| `registerApi` | POST | `/auth/register/` | setAccessToken, setSessionCookie |
| `silentRefreshApi` | POST | `/auth/refresh/` | setAccessToken, setSessionCookie |
| `logoutApi` | POST | `/auth/logout/` | clearTokens, clearSessionCookie |
| `logoutAllApi` | POST | `/auth/logout-all/` | clearTokens, clearSessionCookie |
| `verifyEmailApi` | POST | `/auth/verify-email/` | — |
| `resendVerificationApi` | POST | `/auth/resend-verification/` | — |
| `passwordResetApi` | POST | `/auth/password/reset/` | — |
| `passwordResetConfirmApi` | POST | `/auth/password/reset/confirm/` | — |
| `passwordChangeApi` | POST | `/auth/password/change/` | — |
| `fetchSessionsApi` | GET | `/auth/sessions/` | — |
| `revokeSessionApi` | DELETE | `/auth/sessions/{id}/` | — |
| `fetchCurrentUserApi` | GET | `/users/me/` | — |
| `googleOAuthInitApi` | GET | `/auth/oauth/google/` | — |
| `appleOAuthInitApi` | GET | `/auth/oauth/apple/` | — |

#### Memberships (`features/auth/api/membership-api.ts`)

| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `fetchMyMembershipsApi` | GET | `/users/me/memberships/` | `Membership[]` (plain array, NOT paginated) |

#### Users (`features/users/api/users-api.ts`)

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchCurrentUserApi` | GET | `/users/me/` |
| `updateUsernameApi` | PATCH | `/users/me/` |
| `fetchProfileApi` | GET | `/users/me/profile/` |
| `updateProfileApi` | PATCH | `/users/me/profile/` |
| `uploadAvatarApi` | POST | `/users/me/avatar/` (multipart) |
| `deleteAvatarApi` | DELETE | `/users/me/avatar/` |

#### Business (`features/business/api/business-api.ts`)

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchMyBusinessesApi` | GET | `/business/my/` |
| `fetchBusinessApi` | GET | `/business/{slug}/` |
| `createBusinessApi` | POST | `/business/` |
| `updateBusinessApi` | PATCH | `/business/{slug}/` |
| `deleteBusinessApi` | DELETE | `/business/{slug}/` |

#### Platform (`features/platform/api/platform-api.ts`)

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchPlatformAccountApi` | GET | `/platform/account/` |
| `updatePlatformProfileApi` | PATCH | `/platform/profile/` |
| `updatePlatformSettingsApi` | PATCH | `/platform/settings/` |

### 4.2 Query Keys

```typescript
queryKeys = {
  auth: {
    all: ["auth"],
    sessions: () => ["auth", "sessions"],
  },
  users: {
    all: ["users"],
    me: () => ["users", "me"],
    memberships: () => ["users", "memberships"],
  },
  business: {
    all: ["business"],
    list: () => ["business", "list"],
    my: () => ["business", "my"],
    detail: (slug) => ["business", "detail", slug],
    roles: (slug) => ["business", slug, "roles"],
    members: (slug) => ["business", slug, "members"],
  },
  platform: {
    all: ["platform"],
    account: () => ["platform", "account"],
    roles: () => ["platform", "roles"],
    members: () => ["platform", "members"],
  },
}
```

---

## 5. Types & Interfaces

### User (`types/index.ts`)

```typescript
interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
  is_complete: boolean;
  can_create_business: boolean;   // Added in this overhaul
  is_staff: boolean;              // Added in this overhaul
  is_superuser: boolean;          // Added in this overhaul
  date_joined: string;
  last_login: string | null;
  profile: UserProfile;
}
```

### RBAC (`types/rbac.ts`)

```typescript
type AccountType = "business" | "platform";
type MembershipStatus = "active" | "suspended" | "left" | "removed" | "banned";

interface MembershipPermission { code: string; scope: string; }

interface Role {
  id: string; name: string; account_type: AccountType; account_id: string;
  level: number; is_system_role: boolean; description: string;
  created_at: string; updated_at: string;
}

interface Membership {
  id: string; account_type: AccountType; account_id: string;
  account_name: string; account_slug: string;   // Added via backend serializer
  role: Role; is_owner: boolean; status: MembershipStatus;
  joined_at: string; permissions: MembershipPermission[];
}
```

### Organization (`types/organization.ts`)

```typescript
// BusinessAccount — full detail (GET /business/{slug}/)
interface BusinessAccount {
  id: string; slug: string; legal_name: string;
  registration_number: string; tax_id: string; country: string;
  legal_address: string; business_type: string; business_type_display: string;
  status: string; status_display: string;
  verification_status: string; verification_status_display: string;
  verified_at: string | null; settings: Record<string, unknown>;
  profile: BusinessProfile; created_at: string; updated_at: string;
}

// BusinessAccountList — compact list item (GET /business/my/)
interface BusinessAccountList {
  id: string; slug: string; legal_name: string; country: string;
  business_type: string; status: string; verification_status: string;
  profile: BusinessProfile; created_at: string;
}

// PlatformAccount (GET /platform/account/)
interface PlatformAccount {
  id: string; is_configured: boolean; settings: Record<string, unknown>;
  profile: PlatformProfile; created_at: string; updated_at: string;
}
```

---

## 6. State Management

### 6.1 Auth Store (`stores/auth-store.ts`)

Zustand store for authentication state. No persist — bootstrapped fresh via AuthInitializer.

| State | Type | Description |
|-------|------|-------------|
| `user` | `User \| null` | Current user object |
| `isAuthenticated` | `boolean` | Whether user is logged in |
| `isInitialized` | `boolean` | Whether auth bootstrap completed |

**Selector hooks:** `useUser()`, `useIsAuthenticated()`, `useIsInitialized()`
**Non-React:** `getAuthStore()`

### 6.2 Membership Store (`stores/membership-store.ts`)

Zustand store for user's RBAC memberships. No persist — populated alongside auth.

| State | Type | Description |
|-------|------|-------------|
| `memberships` | `Membership[]` | All user memberships |
| `isLoaded` | `boolean` | Whether memberships have been fetched |

**Selector hooks:**
- `useMemberships()` — raw list
- `useBusinessMemberships()` — active business memberships (uses `useShallow` to avoid infinite re-renders)
- `usePlatformMembership()` — active platform membership or null
- `useMembershipsLoaded()` — loaded flag

**Non-React:** `getMembershipStore()`, `getMembershipForAccount(state, accountType, accountId)`

### 6.3 TanStack Query

| Hook | Query Key | staleTime | Notes |
|------|-----------|-----------|-------|
| `useCurrentUser()` | `users.me()` | 5 min | Standard |
| `useSessions()` | `auth.sessions()` | default | Standard |
| `useMembershipsQuery()` | `users.memberships()` | `Infinity` | Event-driven invalidation |
| `useMyBusinesses()` | `business.my()` | 5 min | Standard |
| `useBusiness(slug)` | `business.detail(slug)` | 5 min | `enabled: !!slug` |
| `usePlatformAccount()` | `platform.account()` | 5 min | Standard |
| `useProfile()` | `users.me.profile` | 5 min | Standard |

---

## 7. Hooks

### 7.1 Auth Mutations (`features/auth/hooks/use-auth-mutations.ts`)

| Hook | Store Side Effects | Navigation |
|------|-------------------|------------|
| `useLogin()` | setUser, setMemberships (async), setQueryData | callbackUrl or `/dashboard` |
| `useRegister()` | setUser, setMemberships([]) | `/verify-email` |
| `useLogout()` | clearUser, clearMemberships, queryClient.clear() | `/login` |
| `useLogoutAll()` | clearUser, clearMemberships, queryClient.clear() | `/login` |
| `useVerifyEmail()` | — | `/login` (on success) |
| `useResendVerification()` | — | — |
| `usePasswordReset()` | — | — |
| `usePasswordResetConfirm()` | — | `/login` |
| `usePasswordChange()` | — (form reset) | — |
| `useRevokeSession()` | invalidate sessions query | — |
| `useGoogleOAuth()` | — | `window.location.href` (OAuth redirect) |
| `useAppleOAuth()` | — | `window.location.href` (OAuth redirect) |

### 7.2 Permission Hooks (`hooks/use-has-permission.ts`)

| Hook | Signature | Description |
|------|-----------|-------------|
| `useHasPermission` | `(code, accountType, accountId) → boolean` | Check cached permission |
| `useIsMember` | `(accountType, accountId) → boolean` | Check active membership |
| `useIsOwner` | `(accountType, accountId) → boolean` | Check ownership flag |

---

## 8. Components

### 8.1 Guard Components (`components/guards/`)

| Component | Tier | Auth Source | Cache Miss Strategy |
|-----------|------|-----------|-------------------|
| `AuthGuard` | — | `auth-store.isAuthenticated` | Redirect to `/login?callbackUrl=...` |
| `BusinessGuard` | 2 | `membership-store` by `slug` | Single `fetchMyMembershipsApi()` → update store |
| `PlatformGuard` | 2 | `membership-store` platform type | Single `fetchMyMembershipsApi()` → update store |
| `AdminGuard` | — | `auth-store.user.is_staff/is_superuser` | No retry (uses user object, not memberships) |

All guards show `<Skeleton>` during loading and an "Access Denied" `<Card>` with "Back to Dashboard" link on denial.

### 8.2 Error Handling Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `FeatureErrorBoundary` | `components/common/ErrorBoundary.tsx` | Wraps feature sections with Card fallback + retry button |

### 8.3 App Layout (`app/(app)/layout.tsx`)

Client component wrapping all protected routes with:
- `AuthGuard` — redirects unauthenticated users
- Desktop sidebar (hidden on mobile) with:
  - **Personal** section: Dashboard, Profile, Settings, Security
  - **Businesses** section: list from `useBusinessMemberships()` → `NavLink` per business
  - **Platform** section: shown if `usePlatformMembership()` returns non-null
  - **Admin** section: shown if `user.is_staff || user.is_superuser`
  - Footer: user email + logout button
- Mobile `Sheet` sidebar triggered by hamburger menu

### 8.4 Auth Form Components

All forms use `react-hook-form` + `zodResolver` + `handleApiError<T>()`:

| Component | Custom Error Handlers |
|-----------|----------------------|
| `LoginForm` | `invalid_credentials`, `account_not_verified`, `account_inactive` |
| `RegisterForm` | `conflict` |
| `VerifyEmailForm` | `not_found` |
| `ForgotPasswordForm` | (none) |
| `ResetPasswordForm` | `not_found` |
| `ChangePasswordForm` | `invalid_credentials`, `business_rule_violation` |
| Resend verification page | (none) |

---

## 9. Centralized Error Handling

### `handleApiError<T>()` (`lib/api-error-handler.ts`)

```typescript
handleApiError<T extends FieldValues>(
  error: unknown,
  options?: {
    setError?: UseFormSetError<T>;
    showToast?: boolean;
    handlers?: Partial<Record<ApiErrorCode, () => void>>;
  }
): void
```

**Priority chain:**
1. Custom handlers per error code → call handler function
2. `validation_error` → map `details.fields` to form field errors via `setError`
3. `rate_limit_exceeded` → set root error with retry-after countdown
4. All other ApiErrors → set root error with message
5. Non-ApiError → `reportError()` + generic root error

**Error reporting:** `reportError(error, context?)` in `lib/error-reporting.ts` — structured console logging ready for Sentry integration.

---

## 10. Pages & Routes

### Route Tree

| Route | Group | Guard | Page Component |
|-------|-------|-------|---------------|
| `/` | `(public)` | — | `LandingPage` |
| `/login` | `(auth)` | — | `LoginForm` |
| `/register` | `(auth)` | — | `RegisterForm` |
| `/verify-email` | `(auth)` | — | `VerifyEmailForm` |
| `/forgot-password` | `(auth)` | — | `ForgotPasswordForm` |
| `/reset-password` | `(auth)` | — | `ResetPasswordForm` |
| `/resend-verification` | `(auth)` | — | Inline form |
| `/dashboard` | `(app)/(user)` | AuthGuard | `DashboardPage` |
| `/profile` | `(app)/(user)` | AuthGuard | `ProfilePage` (placeholder) |
| `/settings` | `(app)/(user)` | AuthGuard | `SettingsPage` (placeholder) |
| `/sessions` | `(app)/(user)` | AuthGuard | `SessionsPage` (SessionList + ChangePasswordForm) |
| `/business/{slug}/dashboard` | `(app)/business/[slug]` | AuthGuard + BusinessGuard | `BusinessDashboard` (placeholder) |
| `/business/{slug}/members` | `(app)/business/[slug]` | AuthGuard + BusinessGuard | `MembersPage` (placeholder) |
| `/business/{slug}/roles` | `(app)/business/[slug]` | AuthGuard + BusinessGuard | `RolesPage` (placeholder) |
| `/business/{slug}/settings` | `(app)/business/[slug]` | AuthGuard + BusinessGuard | `SettingsPage` (placeholder) |
| `/platform/dashboard` | `(app)/platform` | AuthGuard + PlatformGuard | `PlatformDashboard` (placeholder) |
| `/platform/members` | `(app)/platform` | AuthGuard + PlatformGuard | `MembersPage` (placeholder) |
| `/platform/roles` | `(app)/platform` | AuthGuard + PlatformGuard | `RolesPage` (placeholder) |
| `/platform/settings` | `(app)/platform` | AuthGuard + PlatformGuard | `SettingsPage` (placeholder) |
| `/admin` | `(app)/admin` | AuthGuard + AdminGuard | `AdminDashboard` (placeholder) |

### Route Protection

| Path Pattern | Anonymous | Authenticated | Staff/Superuser |
|-------------|-----------|---------------|-----------------|
| `/` | Pass through | Pass through | Pass through |
| `/login`, `/register`, etc. | Pass through | Redirect → `/dashboard` | Redirect → `/dashboard` |
| `/dashboard`, `/profile`, etc. | Redirect → `/login` | Pass through | Pass through |
| `/business/{slug}/*` | Redirect → `/login` | BusinessGuard check | BusinessGuard check |
| `/platform/*` | Redirect → `/login` | PlatformGuard check | PlatformGuard check |
| `/admin` | Redirect → `/login` | AdminGuard (denied) | Pass through |

---

## 11. Middleware (`middleware.ts`)

Thin, auth-only edge middleware:

```typescript
AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password",
               "/verify-email", "/verify-success", "/resend-verification"]
PUBLIC_ROUTES = ["/", ...AUTH_ROUTES]

// Route matching: exact match OR prefix with "/" (prevents /login matching /login-callback)
pathname === route || pathname.startsWith(route + "/")
```

**Rules:**
1. Authenticated + auth route → redirect to `/dashboard`
2. Unauthenticated + protected route → redirect to `/login?callbackUrl=...`
3. Everything else → pass through

**Matcher:** Excludes `_next/static`, `_next/image`, `favicon.ico`, `api`.

---

## 12. Security

### Content Security Policy (`next.config.ts`)

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval';   // Required for Next.js dev HMR
style-src 'self' 'unsafe-inline';                    // Required for Tailwind
img-src 'self' data: blob: https:;
font-src 'self';
connect-src 'self' ${NEXT_PUBLIC_API_URL};           // Backend API (cross-origin in dev/Vercel)
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

> **Note:** `connect-src` must include the backend URL because the frontend makes direct cross-origin API calls. A Next.js rewrite proxy was evaluated but abandoned — see Gotchas #8.

### Other Security Headers

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

### Token Security

- Access token: **in-memory variable only** (never localStorage/sessionStorage)
- Refresh token: **HttpOnly cookie** (browser-managed, never accessible to JS)
- Session indicator: `has_session` cookie for middleware route checks (non-sensitive)

---

## 13. Key Flows

### Flow 1: App Bootstrap (AuthInitializer)

```
Mount → check didRun ref → skip if already ran
  → silentRefreshApi() (POST /auth/refresh/ with HttpOnly cookie)
  → Promise.all(fetchCurrentUserApi(), fetchMyMembershipsApi())
  → setUser(user) + setMemberships(memberships)
  → setInitialized()

On error at any step:
  → clearUser() + clearMemberships()
  → setInitialized()  ← ALWAYS, even on failure
```

### Flow 2: Login with callbackUrl

```
User lands on /dashboard (unauthenticated)
  → middleware redirects to /login?callbackUrl=/dashboard
  → LoginForm renders
  → User submits → loginApi() → setUser + fetchMemberships
  → Read searchParams.callbackUrl → validate starts with "/"
  → router.push("/dashboard")
```

### Flow 3: Business Route Guard (retry-on-miss)

```
User navigates to /business/acme-corp/dashboard
  → AuthGuard checks isAuthenticated (pass)
  → BusinessGuard reads slug "acme-corp" from useParams()
  → Checks membership-store for account_slug === "acme-corp" && status === "active"

  Cache HIT: → render children immediately

  Cache MISS:
    → setIsRevalidating(true) → show Skeleton
    → fetchMyMembershipsApi() → update Zustand store
    → setHasRevalidated(true)
    → Re-check store
    → Found: render children
    → Not found: show "Access Denied" card
```

### Flow 4: Form Error Handling

```
User submits form → mutateAsync(values)
  → catch (error) → handleApiError<FormType>(error, { setError, handlers })

  1. Check handlers[error.code] → call custom handler (e.g., set specific field error)
  2. Check validation_error → map details.fields to setError per field
  3. Check rate_limit_exceeded → set root error with retry countdown
  4. Fallback → set root error with error.message
  5. Non-ApiError → reportError() + generic error
```

### Flow 5: Logout

```
User clicks logout → useLogout().mutate()
  → logoutApi() (POST /auth/logout/) → clearTokens + clearSessionCookie
  → clearUser() + clearMemberships() + queryClient.clear()
  → router.push("/login")

  On error: same cleanup (always clear state even if API fails)
```

---

## 14. Backend Changes

Two backward-compatible serializer additions:

### `UserOutputSerializer` (`apps/users/serializers.py`)

Added fields: `can_create_business`, `is_staff`, `is_superuser`

### `MyMembershipOutputSerializer` (`apps/rbac/serializers.py`)

Added `SerializerMethodField`s:
- `account_name` — `BusinessAccount.legal_name` for business, `"Platform"` for platform
- `account_slug` — `BusinessAccount.slug` for business, `""` for platform

Lookup: `apps.organization.business.models.BusinessAccount`

### `REFRESH_TOKEN_COOKIE_SAMESITE` (`backend_core/settings/base.py`)

Configurable refresh token cookie SameSite policy for flexible deployment:
- `"Strict"` (default) — same-origin deployments (frontend behind same reverse proxy / domain)
- `"None"` — cross-origin deployments (frontend on Vercel, backend on separate server; requires HTTPS)

Production override via env var in `production.py`:
```python
REFRESH_TOKEN_COOKIE_SAMESITE = os.getenv("REFRESH_TOKEN_COOKIE_SAMESITE", "Strict")
```

All 3 `set_cookie` calls in `auth/views.py` (register, login, refresh) use `settings.REFRESH_TOKEN_COOKIE_SAMESITE`.

---

## 15. Testing

### Test Summary

| Module | File | Tests | Status |
|--------|------|-------|--------|
| Auth API | `auth-api.test.ts` | 15 | Pass |
| Auth Store | `auth-store.test.ts` | 7 | Pass |
| Membership Store | `membership-store.test.ts` | 8 | Pass |
| Membership API | `membership-api.test.ts` | 2 | Pass |
| Permission Hooks | `use-has-permission.test.ts` | 7 | Pass |
| Validations | `validations/auth.test.ts` | 20 | Pass |
| API Error Handler | `api-error-handler.test.ts` | 6 | Pass |
| API Client | `api-client.test.ts` | 8 | Pass |
| Middleware | `middleware.test.ts` | 6 | Pass |
| AuthGuard | `AuthGuard.test.tsx` | 4 | Pass |
| BusinessGuard | `BusinessGuard.test.tsx` | 5 | Pass |
| PlatformGuard | `PlatformGuard.test.tsx` | 4 | Pass |
| AdminGuard | `AdminGuard.test.tsx` | 4 | Pass |
| AuthInitializer | `AuthInitializer.test.tsx` | 6 | Pass |
| LoginForm | `LoginForm.test.tsx` | 6 | Pass |
| RegisterForm | `RegisterForm.test.tsx` | 4 | Pass |
| VerifyEmailForm | `VerifyEmailForm.test.tsx` | 4 | Pass |
| SessionList | `SessionList.test.tsx` | 6 | Pass |
| ResetPasswordForm | `ResetPasswordForm.test.tsx` | 5 | Pass |
| ChangePasswordForm | `ChangePasswordForm.test.tsx` | 4 | Pass |
| **Total** | **20 files** | **131** | **All Pass** |

### Running Tests

```bash
cd frontend && npm run test       # Run all tests
npx tsc --noEmit                  # TypeScript check (zero errors)
```

---

## 16. File Summary

### New Files (53)

| File | Description |
|------|-------------|
| `src/types/rbac.ts` | AccountType, MembershipStatus, Role, Membership, MembershipPermission |
| `src/types/organization.ts` | BusinessAccount, BusinessAccountList, BusinessProfile, PlatformAccount, PlatformProfile |
| `src/stores/membership-store.ts` | Zustand store for memberships + selector hooks |
| `src/hooks/use-has-permission.ts` | Permission, member, owner checking hooks |
| `src/features/auth/api/membership-api.ts` | `fetchMyMembershipsApi()` |
| `src/features/auth/hooks/use-membership-queries.ts` | TanStack Query options + `invalidateMemberships()` |
| `src/lib/api-error-handler.ts` | Centralized `handleApiError<T>()` |
| `src/lib/error-reporting.ts` | Updated with typed `ErrorContext` |
| `src/components/common/ErrorBoundary.tsx` | `FeatureErrorBoundary` with react-error-boundary |
| `src/components/guards/AuthGuard.tsx` | Auth check + redirect |
| `src/components/guards/BusinessGuard.tsx` | Business membership check + retry |
| `src/components/guards/PlatformGuard.tsx` | Platform membership check + retry |
| `src/components/guards/AdminGuard.tsx` | Staff/superuser check |
| `src/app/(public)/layout.tsx` | Clean public layout (no sidebar) |
| `src/app/(public)/page.tsx` | Landing page |
| `src/app/(app)/(user)/layout.tsx` | User routes passthrough |
| `src/app/(app)/(user)/dashboard/page.tsx` | Personal dashboard |
| `src/app/(app)/(user)/profile/page.tsx` | Profile page (placeholder) |
| `src/app/(app)/(user)/settings/page.tsx` | Settings page (placeholder) |
| `src/app/(app)/(user)/sessions/page.tsx` | SessionList + ChangePasswordForm |
| `src/app/(app)/(user)/loading.tsx` | User routes skeleton |
| `src/app/(app)/business/[slug]/layout.tsx` | BusinessGuard wrapper |
| `src/app/(app)/business/[slug]/dashboard/page.tsx` | Business dashboard (placeholder) |
| `src/app/(app)/business/[slug]/members/page.tsx` | Members page (placeholder) |
| `src/app/(app)/business/[slug]/roles/page.tsx` | Roles page (placeholder) |
| `src/app/(app)/business/[slug]/settings/page.tsx` | Settings page (placeholder) |
| `src/app/(app)/business/[slug]/loading.tsx` | Business routes skeleton |
| `src/app/(app)/platform/layout.tsx` | PlatformGuard wrapper |
| `src/app/(app)/platform/dashboard/page.tsx` | Platform dashboard (placeholder) |
| `src/app/(app)/platform/members/page.tsx` | Members page (placeholder) |
| `src/app/(app)/platform/roles/page.tsx` | Roles page (placeholder) |
| `src/app/(app)/platform/settings/page.tsx` | Settings page (placeholder) |
| `src/app/(app)/platform/loading.tsx` | Platform routes skeleton |
| `src/app/(app)/admin/layout.tsx` | AdminGuard wrapper |
| `src/app/(app)/admin/page.tsx` | Admin dashboard (placeholder) |
| `src/features/users/api/users-api.ts` | User profile API (6 functions) |
| `src/features/users/hooks/use-user-queries.ts` | TanStack Query hooks for users |
| `src/features/business/api/business-api.ts` | Business API (5 functions) |
| `src/features/business/hooks/use-business-queries.ts` | TanStack Query hooks for businesses |
| `src/features/platform/api/platform-api.ts` | Platform API (3 functions) |
| `src/features/platform/hooks/use-platform-queries.ts` | TanStack Query hooks for platform |
| `src/stores/membership-store.test.ts` | 8 tests |
| `src/hooks/use-has-permission.test.ts` | 7 tests |
| `src/features/auth/api/membership-api.test.ts` | 2 tests |
| `src/lib/api-error-handler.test.ts` | 6 tests |
| `src/components/guards/AuthGuard.test.tsx` | 4 tests |
| `src/components/guards/BusinessGuard.test.tsx` | 5 tests |
| `src/components/guards/PlatformGuard.test.tsx` | 4 tests |
| `src/components/guards/AdminGuard.test.tsx` | 4 tests |
| `src/features/auth/components/AuthInitializer.test.tsx` | 6 tests |
| `src/middleware.test.ts` | 6 tests |
| `src/lib/api-client.test.ts` | 8 tests |
| `src/features/auth/components/ResetPasswordForm.test.tsx` | 5 tests |
| `src/features/auth/components/ChangePasswordForm.test.tsx` | 4 tests |

### Modified Files (26)

| File | Change |
|------|--------|
| `src/lib/query-client.ts` | Removed global `onError` toast (BUG-F01) |
| `src/middleware.ts` | Fixed AUTH_ROUTES matching (BUG-F02), expanded routes |
| `src/features/auth/hooks/use-auth-mutations.ts` | callbackUrl (BUG-F03), membership store integration |
| `src/features/auth/api/auth-api.ts` | Added `setSessionCookie()` to silentRefresh (BUG-F04) |
| `src/features/auth/components/VerifyEmailForm.tsx` | Use form value for resend (BUG-F05) |
| `src/features/auth/components/SessionList.tsx` | Fixed button label (BUG-F06) |
| `src/types/index.ts` | Added `can_create_business`, `is_staff`, `is_superuser` to User |
| `src/features/auth/components/AuthInitializer.tsx` | Parallel fetch user + memberships |
| `src/features/auth/components/LoginForm.tsx` | Use `handleApiError` |
| `src/features/auth/components/RegisterForm.tsx` | Use `handleApiError` |
| `src/features/auth/components/ForgotPasswordForm.tsx` | Use `handleApiError` |
| `src/features/auth/components/ResetPasswordForm.tsx` | Use `handleApiError` |
| `src/features/auth/components/ChangePasswordForm.tsx` | Use `handleApiError` |
| `src/app/(auth)/resend-verification/page.tsx` | Use `handleApiError` |
| `src/app/(app)/layout.tsx` | Real sidebar with AuthGuard + membership nav |
| `src/test/utils.tsx` | (already existed, unchanged) |
| `src/features/auth/api/auth-api.test.ts` | Updated mockUser with 3 new fields |
| `src/stores/auth-store.test.ts` | Updated mockUser with 3 new fields |
| `next.config.ts` | Added CSP header |
| `backend/apps/users/serializers.py` | Added 3 fields to UserOutputSerializer |
| `backend/apps/rbac/serializers.py` | Added account_name, account_slug to MyMembershipOutputSerializer |
| `backend/apps/rbac/tests/test_views.py` | Added test for new membership fields |
| `backend/apps/users/tests/test_views.py` | Updated assertions for new user fields |

### Deleted Files

| File | Reason |
|------|--------|
| `src/app/page.tsx` | Conflicted with `(public)/page.tsx` — both resolved to `/` |
| `src/app/(app)/dashboard/page.tsx` | Superseded by `(app)/(user)/dashboard/page.tsx` |

---

## 17. Configuration & Gotchas

### Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API base URL. Also used in CSP `connect-src` |

### Deployment Configuration

Two supported deployment topologies:

| Variable | Vercel + separate backend | Same server (nginx) |
|----------|--------------------------|---------------------|
| `NEXT_PUBLIC_API_URL` | `https://api.example.com` | `https://example.com` |
| `CORS_ALLOWED_ORIGINS` (backend) | `https://app.example.com` | `https://example.com` |
| `REFRESH_TOKEN_COOKIE_SAMESITE` (backend) | `None` | `Strict` |

### Gotchas

1. **Zustand `.filter()` in selectors** creates new array ref → infinite re-render. Wrap with `useShallow` from `zustand/react/shallow`.

2. **Guard retry-on-miss** must call `fetchMyMembershipsApi()` directly and update Zustand store. Using `invalidateQueries()` only updates TanStack Query cache, which guards don't read.

3. **Next.js route groups**: `app/page.tsx` and `app/(public)/page.tsx` both resolve to `/`. Only keep one — we kept `(public)/page.tsx`.

4. **BUG-F02 pattern**: `pathname.startsWith("/login")` matches `/login-callback`. Fix: use `pathname === route || pathname.startsWith(route + "/")`.

5. **`has_session` cookie** is not a security token — it's a hint for the middleware. The actual auth uses in-memory access token + HttpOnly refresh cookie.

6. **AuthInitializer `didRun` ref** prevents double init in React StrictMode (development double-mount).

7. **Membership invalidation** is event-driven (`staleTime: Infinity`), not timer-based. Always call `invalidateMemberships(queryClient)` in mutation `onSuccess` when user's memberships change.

8. **Next.js rewrite proxy does NOT work with Django.** The `:path*` capture in `next.config.ts` rewrites strips trailing slashes from URLs. Django requires trailing slashes for POST endpoints and cannot auto-redirect POST without losing the request body. Use direct cross-origin API calls instead, with proper CSP (`connect-src`) and CORS configuration.

---

## 18. Reusable Patterns

These patterns are established for any new feature to follow:

| Pattern | How To Use |
|---------|-----------|
| **Feature module** | `features/{name}/api/`, `hooks/`, `components/` |
| **Typed API function** | Wrap `apiClient.get/post/patch/delete` with input/output types |
| **TanStack Query hook** | `queryOptions()` factory + `useQuery()` wrapper |
| **Zustand store** | State + actions, devtools middleware, selector hooks |
| **Route guard** | Layout-level check against cached membership/user state (Tier 2) |
| **Error handling** | `handleApiError()` for forms, `{ showToast: true }` for non-form mutations |
| **Permission check** | `useHasPermission(code, accountType, accountId)` for UI gating (Tier 1) |
| **Error boundary** | `<FeatureErrorBoundary>` wrapping feature sections |

---

## 19. Known Limitations

1. **No WebSocket/SSE** — external membership changes (admin actions) are only caught on window focus refetch or next guard miss.
2. **CSP uses `unsafe-inline`/`unsafe-eval`** — production should use nonce-based CSP via middleware.
3. **Placeholder pages** — business, platform, and admin routes have placeholder content awaiting feature implementation.
4. **No offline support** — all state is in-memory and requires network connectivity.
5. **No skeleton variations** — all loading states use the same generic `Skeleton` component.

---

## 20. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Nonce-based CSP for production | CSP currently uses unsafe-inline/eval | P1 |
| WebSocket/SSE for real-time membership invalidation | Currently relies on window focus + guard retry | P2 |
| Business CRUD pages | Placeholder routes exist, need forms + mutations | P1 |
| Platform management pages | Placeholder routes exist | P1 |
| Admin dashboard | Placeholder route exists | P2 |
| Profile editing page | Placeholder route exists, API functions ready | P1 |
| Notification preferences | Query keys defined, no implementation yet | P2 |
| Request cancellation via AbortController | TanStack Query handles query cancellation; imperative calls don't | P3 |

---

## 21. Changelog

### v1 (2026-03-01)
- 7-phase Frontend Foundation Overhaul
- Phase 1: Fixed 6 bugs (double-toast, route matching, callbackUrl, session cookie, resend email, session label)
- Phase 1: Backend serializer additions (3 user fields, membership slug/name)
- Phase 2: Membership types, Zustand store, permission hooks, event-driven invalidation
- Phase 3: Centralized `handleApiError<T>()`, refactored all 7 form components
- Phase 4: 4 route guards, complete route tree with 22 route pages, real app sidebar
- Phase 5: Typed API modules for users, business, platform domains
- Phase 6: CSP header + security hardening
- Phase 7: 29 new tests (AuthInitializer, middleware, API client, ResetPassword, ChangePassword)
- Total: 131 tests across 20 files, 0 TypeScript errors

### v1.1 (2026-03-01)
- CSP `connect-src` updated to include backend URL dynamically (`${NEXT_PUBLIC_API_URL}`)
- Removed non-functional Next.js rewrite proxy (trailing slash incompatibility with Django)
- Added configurable `REFRESH_TOKEN_COOKIE_SAMESITE` setting for cross-origin deployments
- All 3 `set_cookie` calls in `auth/views.py` now use `settings.REFRESH_TOKEN_COOKIE_SAMESITE`
- Documented deployment topology: Vercel + separate backend vs same-server nginx
