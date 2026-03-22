# 01 — Project Structure & Organization Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 1.1 Directory Layout

| ID | Rule | Verdict |
|----|------|---------|
| 1.1.1 | FAIL if a new developer cannot understand the purpose of each top-level `src/` directory within 10 seconds | PASS/FAIL |
| 1.1.2 | FAIL if any `.ts` or `.tsx` file at `src/` root contains utility functions, helper logic, or domain-specific code outside established directories | PASS/FAIL |
| 1.1.3 | FAIL if `temp_*`, `draft_*`, `old_*`, `.bak`, or experimental files are tracked in version control under `src/` | PASS/FAIL |
| 1.1.4 | FAIL if `public/` contains JavaScript, TypeScript, data files, or server logic — only static assets allowed | PASS/FAIL |
| 1.1.5 | FAIL if `styles/` contains component-specific stylesheets — only `globals.css` with Tailwind v4 directives allowed | PASS/FAIL |
| 1.1.6 | FAIL if `test/` contains actual test cases — only `setup.ts` and `utils.tsx` infrastructure files allowed | PASS/FAIL |
| 1.1.7 | FAIL if `.gitignore` is missing entries for: `node_modules/`, `.next/`, `.env`, `.env.local`, `coverage/`, `dist/` | PASS/FAIL |
| 1.1.8 | WARN if empty directories exist in the source tree with no meaningful files | PASS/WARN |

## 1.2 Feature Module Structure

| ID | Rule | Verdict |
|----|------|---------|
| 1.2.1 | FAIL if any feature module is missing an `api/` subdirectory for API calls | PASS/FAIL |
| 1.2.2 | FAIL if any feature module is missing a `components/` subdirectory | PASS/FAIL |
| 1.2.3 | FAIL if any feature module is missing a `hooks/` subdirectory | PASS/FAIL |
| 1.2.4 | FAIL if a single feature module owns more than ~30% of all feature code | PASS/FAIL |
| 1.2.5 | FAIL if a feature module handles more than one domain concept (e.g. auth + business in same feature) | PASS/FAIL |
| 1.2.6 | WARN if optional subdirectories (`constants/`, `utils/`, `__tests__/`, `types.ts`) exist as empty boilerplate | PASS/WARN |
| 1.2.7 | WARN if feature modules lack an `index.ts` barrel file re-exporting public API | PASS/WARN |
| 1.2.8 | FAIL if feature count does not match expected 11 modules (auth, business, explore, forms, members, network, platform, transactions, users, settings, rbac) | PASS/FAIL |

## 1.3 App Router Organization

| ID | Rule | Verdict |
|----|------|---------|
| 1.3.1 | FAIL if unauthenticated pages (home, about, explore, business/[slug]) are not under `(public)` route group | PASS/FAIL |
| 1.3.2 | FAIL if authentication flows (login, register, forgot-password) are not under `(auth)` route group | PASS/FAIL |
| 1.3.3 | FAIL if authenticated routes (dashboard, bconsole, pconsole, admin, settings) are not under `(app)` route group | PASS/FAIL |
| 1.3.4 | FAIL if two route groups resolve to the same URL path (parallel route conflict) | PASS/FAIL |
| 1.3.5 | FAIL if parenthesized group names appear in the URL as path segments | PASS/FAIL |
| 1.3.6 | WARN if a route group is missing an appropriate layout file | PASS/WARN |
| 1.3.7 | FAIL if API route handler (`/api/[...path]/route.ts`) contains business logic instead of just proxy forwarding | PASS/FAIL |
| 1.3.8 | WARN if nested route groups within `(app)` are not correctly scoped (user, bconsole, pconsole, admin) | PASS/WARN |

## 1.4 Component Organization

| ID | Rule | Verdict |
|----|------|---------|
| 1.4.1 | FAIL if `ui/` directory contains custom components mixed with shadcn primitives | PASS/FAIL |
| 1.4.2 | FAIL if shared composed components (Can, FormField, PasswordInput, ConfirmActionDialog) are in `ui/` instead of `common/` | PASS/FAIL |
| 1.4.3 | FAIL if `guards/` contains anything other than route protection components (AuthGuard, BusinessGuard, PlatformGuard, AdminGuard) | PASS/FAIL |
| 1.4.4 | WARN if navigation components (Sidebar, TopNavbar, etc.) are scattered across directories instead of consolidated in `navigation/` | PASS/WARN |
| 1.4.5 | FAIL if page files in `app/` exceed 30 lines — they should be thin wrappers importing from `features/` | PASS/FAIL |
| 1.4.6 | FAIL if shared components in `components/` import directly from `features/*/` — data must flow via props | PASS/FAIL |
| 1.4.7 | WARN if component directory hierarchy exceeds 2 levels deep | PASS/WARN |

## 1.5 Naming Conventions

| ID | Rule | Verdict |
|----|------|---------|
| 1.5.1 | FAIL if component files use inconsistent casing (mix of PascalCase and kebab-case without project-wide convention) | PASS/FAIL |
| 1.5.2 | FAIL if utility/config `.ts` files use PascalCase instead of kebab-case | PASS/FAIL |
| 1.5.3 | FAIL if non-Next.js files use default exports (hooks, stores, utilities, types, shared components must use named exports) | PASS/FAIL |
| 1.5.4 | WARN if test files don't match source file names (e.g. `auth-store.test.ts` should test `auth-store.ts`) | PASS/WARN |
| 1.5.5 | WARN if barrel exports use `index.tsx` instead of `index.ts` (unless barrel renders JSX) | PASS/WARN |
| 1.5.6 | WARN if custom hook files don't follow `use-` prefix convention | PASS/WARN |
| 1.5.7 | WARN if type files don't correspond to backend API contract names | PASS/WARN |
| 1.5.8 | FAIL if Next.js pages/layouts/error/loading/not-found use named exports instead of required default exports | PASS/FAIL |

## 1.6 Shared vs Feature-Scoped Code

| ID | Rule | Verdict |
|----|------|---------|
| 1.6.1 | FAIL if hooks used by 2+ features are duplicated in feature directories instead of living in top-level `hooks/` | PASS/FAIL |
| 1.6.2 | FAIL if API contract types used across features are scattered in feature modules instead of top-level `types/` | PASS/FAIL |
| 1.6.3 | FAIL if shared utilities (api-client, query-keys, utils) are in feature directories instead of `lib/` | PASS/FAIL |
| 1.6.4 | FAIL if feature-specific code (used only by one feature) is prematurely promoted to shared directories | PASS/FAIL |
| 1.6.5 | FAIL if cross-feature sibling imports exist (e.g. `features/auth/` importing from `features/business/`) | PASS/FAIL |
| 1.6.6 | WARN if static data files (country-data, cities.json) are inside feature directories instead of `lib/` or `hooks/` | PASS/WARN |
| 1.6.7 | WARN if validation schemas used in multiple forms live in a single feature instead of `lib/validations/` | PASS/WARN |

## 1.7 Configuration Files

| ID | Rule | Verdict |
|----|------|---------|
| 1.7.1 | FAIL if configuration files are not all at the `frontend/` project root | PASS/FAIL |
| 1.7.2 | FAIL if `@/` path alias is inconsistent between `tsconfig.json`, `vitest.config.ts`, and ESLint config | PASS/FAIL |
| 1.7.3 | FAIL if conflicting configs exist (e.g. `tailwind.config.js` alongside CSS-first Tailwind v4, or `.eslintrc` alongside flat config) | PASS/FAIL |
| 1.7.4 | WARN if `components.json` is missing or misconfigured for shadcn/ui (style, rsc, aliases) | PASS/WARN |
| 1.7.5 | FAIL if `.env.example` is missing or doesn't document all required `NEXT_PUBLIC_*` variables | PASS/FAIL |
| 1.7.6 | FAIL if PostCSS config uses legacy `@tailwindcss/postcss7-compat` instead of Tailwind v4 `@tailwindcss/postcss` | PASS/FAIL |

## 1.8 Entry Points & Root Files

| ID | Rule | Verdict |
|----|------|---------|
| 1.8.1 | FAIL if root `layout.tsx` is missing or doesn't wrap the application with Providers, metadata, and fonts | PASS/FAIL |
| 1.8.2 | FAIL if `Providers.tsx` is missing or doesn't compose QueryClientProvider, ThemeProvider, AuthInitializer, Toaster | PASS/FAIL |
| 1.8.3 | FAIL if `middleware.ts` is not at `src/` root | PASS/FAIL |
| 1.8.4 | WARN if `error.tsx` is missing at root `app/` level | PASS/WARN |
| 1.8.5 | WARN if `global-error.tsx` is missing at root `app/` level | PASS/WARN |
| 1.8.6 | WARN if `not-found.tsx` is missing at root `app/` level | PASS/WARN |
| 1.8.7 | WARN if `loading.tsx` is missing at root `app/` level or key route segments | PASS/WARN |

## 1.9 Test Structure

| ID | Rule | Verdict |
|----|------|---------|
| 1.9.1 | FAIL if `test/setup.ts` doesn't import `@testing-library/jest-dom/vitest` for matcher support | PASS/FAIL |
| 1.9.2 | FAIL if `test/utils.tsx` doesn't export `renderWithProviders` wrapping QueryClientProvider and required contexts | PASS/FAIL |
| 1.9.3 | WARN if test files don't mirror source structure (co-located or in `__tests__/` subdirectories) | PASS/WARN |
| 1.9.4 | FAIL if test files exist outside `src/` tree | PASS/FAIL |
| 1.9.5 | WARN if feature modules are missing `__tests__/` directories for component, hook, and integration tests | PASS/WARN |
| 1.9.6 | FAIL if test utilities (mock router, mock query client, mock stores) are duplicated across test files instead of shared in `test/` | PASS/FAIL |

## 1.10 Stale & Dead Code

| ID | Rule | Verdict |
|----|------|---------|
| 1.10.1 | FAIL if any directory in `features/` is not imported by at least one route or component | PASS/FAIL |
| 1.10.2 | WARN if `.tsx` files export empty components with only TODO comments | PASS/WARN |
| 1.10.3 | FAIL if `page.tsx` files in `app/` don't import from `features/` or `components/` | PASS/FAIL |
| 1.10.4 | WARN if multi-line commented-out code blocks exist (>5 lines) | PASS/WARN |
| 1.10.5 | FAIL if `.bak`, `.old`, or temporary files exist in the source tree | PASS/FAIL |
| 1.10.6 | WARN if dead imports exist that are never used (should be caught by ESLint) | PASS/WARN |
