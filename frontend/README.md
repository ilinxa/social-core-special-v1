# Frontend — SocialMedia Adv

Web client for the SocialMedia Adv platform, built with Next.js 16 (App Router) and React 19.

> **Phase 0 — Foundation Setup**
> This document covers the production-grade base structure established during Phase 0. No features are implemented yet — this is the scaffold upon which all future development builds.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Architecture Decisions](#architecture-decisions)
- [Tooling & Configuration](#tooling--configuration)
- [Backend Integration](#backend-integration)
- [Component Library](#component-library)
- [State Management](#state-management)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Deployment](#deployment)
- [Available Scripts](#available-scripts)

---

## Tech Stack

| Category            | Technology                                | Version |
| ------------------- | ----------------------------------------- | ------- |
| Framework           | Next.js (App Router)                      | 16.1.6  |
| Runtime             | React                                     | 19.2.3  |
| Language            | TypeScript (strict)                       | 5.x     |
| Styling             | Tailwind CSS (CSS-first)                  | 4.x     |
| Component Library   | shadcn/ui (new-york, OKLCH)               | latest  |
| Client State        | Zustand                                   | 5.x     |
| Server State        | TanStack Query                            | 5.x     |
| Forms               | react-hook-form + Zod                     | latest  |
| HTTP Client         | Axios                                     | 1.x     |
| Icons               | lucide-react                              | latest  |
| Theming             | next-themes                               | latest  |
| Toast Notifications | sonner                                    | 2.x     |
| Animation           | tw-animate-css                            | latest  |
| Testing             | Vitest + React Testing Library + MSW      | latest  |
| Linting             | ESLint (flat config) + eslint-config-next | 9.x     |
| Formatting          | Prettier + prettier-plugin-tailwindcss    | 3.x     |
| Pre-commit          | Husky + lint-staged                       | latest  |
| Node                | Node.js (pinned via `.nvmrc`)             | 22      |
| Package Manager     | npm                                       | default |

---

## Prerequisites

- **Node.js 22** — pinned in `.nvmrc`, use `nvm use` to switch
- **npm** — ships with Node.js
- **Backend running** (optional for dev) — Django API at `http://localhost:8000`

---

## Getting Started

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Create local environment config
cp .env.example .env.local

# 4. Start the dev server
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000).

### Environment Variables

| Variable                 | Default                 | Description                          |
| ------------------------ | ----------------------- | ------------------------------------ |
| `NEXT_PUBLIC_API_URL`    | `http://localhost:8000` | Backend API base URL                 |
| `NEXT_PUBLIC_APP_NAME`   | `SocialMedia Adv`       | Application display name             |
| `NEXT_PUBLIC_SENTRY_DSN` | —                       | Sentry error tracking DSN (optional) |

---

## Project Structure

```
frontend/
├── public/                          # Static assets (favicon, robots.txt)
├── src/
│   ├── app/                         # Next.js App Router (routing layer only)
│   │   ├── layout.tsx               # Root layout — Providers, fonts, metadata
│   │   ├── page.tsx                 # Landing page (/)
│   │   ├── loading.tsx              # Global loading fallback
│   │   ├── error.tsx                # Global error boundary
│   │   ├── global-error.tsx         # Root error boundary (layout crashes)
│   │   ├── not-found.tsx            # Custom 404 page
│   │   ├── Providers.tsx            # Client providers (QueryClient, Theme, Toast)
│   │   ├── (auth)/                  # Auth route group — no sidebar
│   │   │   ├── layout.tsx           # Centered layout for auth pages
│   │   │   ├── login/page.tsx       # /login
│   │   │   └── register/page.tsx    # /register
│   │   └── (app)/                   # App route group — sidebar + header
│   │       ├── layout.tsx           # Dashboard shell layout
│   │       └── dashboard/page.tsx   # /dashboard
│   ├── components/
│   │   ├── ui/                      # shadcn/ui primitives (auto-generated)
│   │   └── common/                  # Composed reusable components
│   ├── features/                    # Feature modules
│   │   └── auth/                    # Auth feature (stub)
│   │       ├── components/          # Feature-specific components
│   │       ├── hooks/               # Feature-specific hooks
│   │       ├── api/                 # API call functions
│   │       ├── actions/             # Next.js Server Actions
│   │       └── types.ts             # Feature-specific types
│   ├── hooks/                       # Shared custom hooks
│   ├── lib/                         # Core utilities
│   │   ├── utils.ts                 # cn() helper (clsx + tailwind-merge)
│   │   ├── api-client.ts            # Axios instance with JWT interceptors
│   │   ├── query-client.ts          # TanStack QueryClient factory
│   │   ├── query-keys.ts            # Query key factory (all endpoints)
│   │   ├── error-reporting.ts       # Error reporting (console / Sentry)
│   │   └── validations/             # Shared Zod schemas
│   ├── stores/                      # Zustand stores (client state only)
│   ├── types/                       # Shared TypeScript types
│   │   └── index.ts                 # API contract types (User, Error, Pagination)
│   ├── styles/
│   │   └── globals.css              # Tailwind v4 CSS-first theme (OKLCH)
│   └── test/
│       ├── setup.ts                 # Vitest setup (jest-dom, cleanup)
│       └── utils.tsx                # renderWithProviders() test helper
├── .vscode/                         # VS Code workspace settings
├── .husky/                          # Git hooks (pre-commit → lint-staged)
├── .env.example                     # Environment variable template
├── .nvmrc                           # Node version pin (22)
├── .prettierrc                      # Prettier config
├── .prettierignore                  # Prettier ignore patterns
├── .lintstagedrc                    # lint-staged config
├── components.json                  # shadcn/ui configuration
├── eslint.config.mjs                # ESLint flat config
├── next.config.ts                   # Next.js config (security headers, API proxy)
├── postcss.config.mjs               # PostCSS config (Tailwind v4)
├── tsconfig.json                    # TypeScript config (strict, @/ alias)
├── vitest.config.ts                 # Vitest config
└── package.json                     # Dependencies and scripts
```

---

## Architecture Decisions

### Routing: Route Groups

Routes are organized into **route groups** using the `(name)` convention — these create logical groupings without adding URL segments:

| Group    | Layout                  | URL Prefix | Purpose                                      |
| -------- | ----------------------- | ---------- | -------------------------------------------- |
| `(auth)` | Centered, no navigation | None       | Login, Register, Verify, Reset               |
| `(app)`  | Sidebar + Header        | None       | Dashboard, Settings, all authenticated views |

### Pages as Thin Wrappers

Every `page.tsx` stays under 30 lines. It imports a feature component and renders it:

```tsx
// src/app/dashboard/page.tsx
import { DashboardPage } from "@/features/dashboard/components/DashboardPage";

export default function Page() {
  return <DashboardPage />;
}
```

All business logic, data fetching, and complex UI live in `src/features/`.

### Server vs Client Components

- **Default to Server Components.** Only add `"use client"` when the component needs hooks, event handlers, browser APIs, or context.
- **Push `"use client"` down** to the narrowest boundary — keep the interactive layer small.

### State Architecture

| State Type              | Tool           | Example                                   |
| ----------------------- | -------------- | ----------------------------------------- |
| Server state (API data) | TanStack Query | User profile, business list, transactions |
| Client state (UI)       | Zustand        | Sidebar toggle, theme, form drafts        |

These never overlap. Zustand stores never call `fetch`. TanStack Query handles all server data.

---

## Tooling & Configuration

### TypeScript

- **Strict mode** enabled (`"strict": true`)
- Path alias: `@/` maps to `src/`
- No `any` — use `unknown` and narrow
- No `enum` — use union types
- `interface` for object shapes, `type` for unions/utilities
- `import type { X }` for type-only imports (enforced by ESLint)

### Tailwind CSS v4 (CSS-First)

The theme is defined entirely in CSS using `globals.css`:

- `@import "tailwindcss"` — core framework
- `@import "tw-animate-css"` — animation utilities
- `@import "shadcn/tailwind.css"` — shadcn integration
- `@custom-variant dark (&:is(.dark *))` — dark mode variant
- `@theme inline { ... }` — color and radius mappings

Colors use **OKLCH** format (not HSL). Light and dark themes are fully defined via CSS custom properties.

### Prettier

Configuration (`.prettierrc`):

- Double quotes, semicolons, 2-space indent
- `printWidth: 100`, trailing commas
- `prettier-plugin-tailwindcss` for automatic class sorting

### ESLint

Flat config (`eslint.config.mjs`):

- `eslint-config-next/core-web-vitals` — Next.js best practices
- `eslint-config-next/typescript` — TypeScript rules
- `eslint-config-prettier/flat` — disables conflicting format rules
- Custom rules: no `any`, consistent type imports, unused vars pattern

### Pre-commit Hooks

Husky + lint-staged runs on every commit:

- `.ts/.tsx` files: ESLint fix + Prettier format
- `.json/.md/.css` files: Prettier format

---

## Backend Integration

### API Client (`src/lib/api-client.ts`)

A pre-configured Axios instance that handles the full JWT lifecycle:

- **Base URL**: `NEXT_PUBLIC_API_URL/api/v1` (default: `http://localhost:8000/api/v1`)
- **Credentials**: `withCredentials: true` — sends HttpOnly cookies automatically
- **Request interceptor**: attaches `Authorization: Bearer <access_token>` from in-memory store
- **Response interceptor**:
  - `401 / token_expired` — silently refreshes via `POST /api/v1/auth/refresh/` (cookie-based) and retries the original request
  - `401 / token_already_used` — security breach detected, clears tokens, redirects to `/login`
  - All other errors — normalized into `ApiError` class

### API Proxy

`next.config.ts` proxies `/api/:path*` to the backend, avoiding CORS issues during development.

### Token Security

- **Access token**: stored in-memory only (module-level variable). Never touches `localStorage`.
- **Refresh token**: HttpOnly cookie set by the backend (`key: refresh_token`, `path: /api/v1/auth/refresh/`, `SameSite: Strict`, `Secure` in production).
- **Token rotation**: each refresh token is single-use. Reuse triggers full session revocation.

### ApiError Class

Maps directly to the backend's error response format:

```typescript
class ApiError extends Error {
  status: number; // HTTP status code
  code: string; // Backend error code (e.g., "invalid_credentials")
  details?: Record<string, unknown>; // Field errors, retry_after, etc.

  get isNotFound(): boolean; // 404
  get isUnauthorized(): boolean; // 401
  get isForbidden(): boolean; // 403
  get isValidation(): boolean; // 400 + validation_error code
  get isConflict(): boolean; // 409
  get isRateLimited(): boolean; // 429
  get retryAfter(): number | undefined;
}
```

### Query Key Factory (`src/lib/query-keys.ts`)

Pre-defined query keys matching all backend endpoints:

```typescript
queryKeys.auth.sessions(); // ["auth", "sessions"]
queryKeys.users.me(); // ["users", "me"]
queryKeys.business.detail("acme"); // ["business", "detail", "acme"]
queryKeys.transactions.list(); // ["transactions", "list"]
queryKeys.forms.library(); // ["forms", "library"]
queryKeys.notifications.preferences(); // ["notifications", "preferences"]
```

### Shared Types (`src/types/index.ts`)

TypeScript interfaces matching backend serializers exactly:

| Interface              | Backend Source                | Fields                                           |
| ---------------------- | ----------------------------- | ------------------------------------------------ |
| `User`                 | `UserOutputSerializer`        | id (UUID), email, username, is_verified, profile |
| `UserProfile`          | `UserProfileSerializer`       | first_name, last_name, avatar_url, timezone      |
| `UserMinimal`          | `UserMinimalOutputSerializer` | id, username, display_name, avatar_url           |
| `AuthTokens`           | `AuthResponseSerializer`      | access_token, access_expires_in, token_type      |
| `AuthResponse`         | `AuthResponseSerializer`      | user, tokens, is_new_user                        |
| `ApiErrorResponse`     | `exception_handler`           | error.message, error.code, error.details         |
| `PaginatedResponse<T>` | `StandardPagination`          | count, next, previous, results                   |
| `ApiErrorCode`         | `exception_handler`           | 16 possible error codes                          |

### Backend Endpoints

The frontend connects to a Django REST API at `/api/v1/`:

| Area              | Key Endpoints                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Auth**          | `/auth/login/`, `/auth/register/`, `/auth/refresh/`, `/auth/logout/`, `/auth/verify-email/`, `/auth/oauth/google/` |
| **Users**         | `/users/me/`, `/users/me/profile/`, `/users/me/avatar/`, `/users/me/memberships/`                                  |
| **Organization**  | `/platform/account/`, `/business/`, `/business/<slug>/`                                                            |
| **RBAC**          | `/rbac/permissions/`, `/<account>/roles/`, `/<account>/members/`                                                   |
| **Transactions**  | `/transactions/`, `/transactions/<id>/accept/`, `/transactions/<id>/deny/`                                         |
| **Forms**         | `/forms/templates/library/`, `/forms/templates/<id>/`, `/forms/responses/<id>/`                                    |
| **Notifications** | `/notifications/preferences/`, `/notifications/history/`                                                           |

---

## Component Library

### shadcn/ui

shadcn/ui is used as the component primitive layer. Components are **generated into `src/components/ui/`** (not installed as a dependency).

**Configuration** (`components.json`):

- Style: `new-york`
- Colors: OKLCH format
- Base color: neutral
- Icon library: lucide
- Aliases: `@/components/ui`, `@/lib/utils`, `@/hooks`

**Installed components (Phase 0):**

| Component    | File                   | Purpose                |
| ------------ | ---------------------- | ---------------------- |
| Button       | `ui/button.tsx`        | Primary action element |
| Card         | `ui/card.tsx`          | Content container      |
| Input        | `ui/input.tsx`         | Text input field       |
| Label        | `ui/label.tsx`         | Form labels            |
| Sonner       | `ui/sonner.tsx`        | Toast notifications    |
| Dialog       | `ui/dialog.tsx`        | Modal dialogs          |
| DropdownMenu | `ui/dropdown-menu.tsx` | Context menus          |
| Sheet        | `ui/sheet.tsx`         | Slide-out panels       |
| Skeleton     | `ui/skeleton.tsx`      | Loading placeholders   |
| Avatar       | `ui/avatar.tsx`        | User avatars           |
| Separator    | `ui/separator.tsx`     | Visual dividers        |

**Adding new components:**

```bash
npx shadcn@latest add <component-name>
```

### Custom Components

Composed components go in `src/components/common/`. These build on shadcn primitives but are project-specific.

### `cn()` Helper

The `cn()` utility merges Tailwind classes with conflict resolution:

```typescript
import { cn } from "@/lib/utils";

// Conditional classes with automatic conflict resolution
<div className={cn("rounded-lg p-4", isActive && "bg-primary text-primary-foreground")} />
```

---

## State Management

### TanStack Query (Server State)

Pre-configured in `src/lib/query-client.ts`:

| Setting                   | Value            | Reason                                |
| ------------------------- | ---------------- | ------------------------------------- |
| `staleTime`               | 5 minutes        | Reduce unnecessary refetches          |
| `retry` (queries)         | 3                | Resilience against transient failures |
| `retry` (mutations)       | 0                | Fail fast on write operations         |
| `refetchOnWindowFocus`    | false            | Avoid unwanted refetches              |
| Global mutation `onError` | Toast via sonner | User-visible error feedback           |

### Zustand (Client State)

Stores go in `src/stores/`. Conventions:

- One store per domain (`useAuthStore`, `useSidebarStore`)
- Always use selector hooks to prevent unnecessary re-renders
- Middleware order: `devtools(persist(immer(store)))`
- Never mix with server state — Zustand stores never call `fetch`

---

## Error Handling

### Layered Error Boundaries

```
global-error.tsx  →  Catches root layout errors (renders raw HTML)
  └── error.tsx   →  Catches route-level render errors (uses shadcn Button)
      └── Feature ErrorBoundary  →  Per-feature (react-error-boundary)
```

### Error Reporting (`src/lib/error-reporting.ts`)

- **Development**: logs to console
- **Production**: placeholder for Sentry integration

### Not Found Page

Custom `not-found.tsx` with styled 404 page and navigation back to home.

---

## Testing

### Framework: Vitest + React Testing Library

Configuration (`vitest.config.ts`):

- Environment: jsdom
- Globals enabled (no manual imports for `describe`, `it`, `expect`)
- Path alias `@/` configured
- Coverage provider: v8
- Setup file: `src/test/setup.ts` (jest-dom matchers + cleanup)

### Test Helper

`src/test/utils.tsx` provides `renderWithProviders()` which wraps components with `QueryClientProvider` (retry disabled for deterministic tests).

### Running Tests

```bash
npm run test              # Single run
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage report
```

### Conventions

- Tests co-located with source: `Button.test.tsx` next to `Button.tsx`
- Query priority: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`
- Use `userEvent.setup()` for interactions
- Mock API calls with MSW (Mock Service Worker)

---

## Code Quality

### Verification Checklist

All of these pass as of Phase 0 completion:

```bash
npm run build         # Next.js production build
npm run lint          # ESLint (zero errors)
npm run typecheck     # TypeScript strict compilation
npm run test          # Vitest
npm run format:check  # Prettier formatting
```

### Naming Conventions

| Element         | Convention                       | Example                       |
| --------------- | -------------------------------- | ----------------------------- |
| Component files | PascalCase                       | `UserProfile.tsx`             |
| Hook files      | camelCase with `use` prefix      | `useAuth.ts`                  |
| Utility files   | camelCase                        | `formatDate.ts`               |
| Test files      | `*.test.tsx`                     | `UserProfile.test.tsx`        |
| Variables       | camelCase                        | `isLoading`, `userName`       |
| Constants       | UPPER_SNAKE                      | `MAX_RETRIES`, `API_BASE_URL` |
| Booleans        | `is`/`has`/`should`/`can` prefix | `isActive`, `hasPermission`   |
| Event handlers  | `handle` prefix                  | `handleClick`, `handleSubmit` |

### Import Order

```typescript
// 1. React / framework
import { useState } from "react";

// 2. Third-party
import { useQuery } from "@tanstack/react-query";

// 3. Internal @/ aliases
import { Button } from "@/components/ui/button";

// 4. Relative / feature-local
import { UserCard } from "./UserCard";

// 5. Type-only
import type { User } from "@/types";

// 6. Side-effects (rare)
import "./styles.css";
```

---

## Deployment

### Standalone Output

`next.config.ts` sets `output: "standalone"` for Docker deployment. This produces a self-contained build with minimal `node_modules`.

### Security Headers

Applied to all routes via `next.config.ts`:

| Header                   | Value                                      |
| ------------------------ | ------------------------------------------ |
| `X-Content-Type-Options` | `nosniff`                                  |
| `X-Frame-Options`        | `DENY`                                     |
| `X-XSS-Protection`       | `1; mode=block`                            |
| `Referrer-Policy`        | `strict-origin-when-cross-origin`          |
| `Permissions-Policy`     | `camera=(), microphone=(), geolocation=()` |

### Docker

A Dockerfile can use the standalone output:

```dockerfile
FROM node:22-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Available Scripts

| Script          | Command                 | Description                        |
| --------------- | ----------------------- | ---------------------------------- |
| `dev`           | `npm run dev`           | Start dev server at localhost:3000 |
| `build`         | `npm run build`         | Production build (standalone)      |
| `start`         | `npm run start`         | Serve production build             |
| `lint`          | `npm run lint`          | ESLint check                       |
| `lint:fix`      | `npm run lint:fix`      | ESLint auto-fix                    |
| `format`        | `npm run format`        | Prettier format all files          |
| `format:check`  | `npm run format:check`  | Check Prettier formatting          |
| `typecheck`     | `npm run typecheck`     | TypeScript strict compilation      |
| `test`          | `npm run test`          | Run tests (single run)             |
| `test:watch`    | `npm run test:watch`    | Run tests in watch mode            |
| `test:coverage` | `npm run test:coverage` | Run tests with coverage            |

---

## Phase 0 Deliverables Summary

| Deliverable                                                      | Status |
| ---------------------------------------------------------------- | ------ |
| Next.js 16 + React 19 initialized                                | Done   |
| TypeScript strict mode configured                                | Done   |
| Tailwind CSS v4 (CSS-first, OKLCH theme)                         | Done   |
| shadcn/ui (new-york style, 11 base components)                   | Done   |
| ESLint flat config + Prettier + tailwindcss plugin               | Done   |
| Husky + lint-staged pre-commit hooks                             | Done   |
| Vitest + React Testing Library + MSW setup                       | Done   |
| API client with JWT interceptors + token refresh                 | Done   |
| TanStack Query client with global error handling                 | Done   |
| Query key factory matching all backend endpoints                 | Done   |
| Shared types matching backend API contracts                      | Done   |
| Route groups: (auth) + (app) with layouts                        | Done   |
| Error boundaries (error.tsx, global-error.tsx, not-found.tsx)    | Done   |
| Security headers in next.config.ts                               | Done   |
| Standalone output for Docker deployment                          | Done   |
| VS Code workspace settings + recommended extensions              | Done   |
| Environment variable template (.env.example)                     | Done   |
| `build`, `lint`, `typecheck`, `test`, `format:check` all passing | Done   |
