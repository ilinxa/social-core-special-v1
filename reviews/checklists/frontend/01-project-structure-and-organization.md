# 01 — Project Structure & Organization Checklist

## 1.1 Directory Layout

- [ ] **src/ top-level directories are clear and purposeful** — app/, components/, features/, hooks/, stores/, lib/, types/, styles/, test/ each serve a distinct role with no overlap
- [ ] **No business logic at the root level** — src/ root contains no utility files, helper functions, or domain logic outside the established directories
- [ ] **No experimental or temporary files committed** — no temp_, draft_, old_, or .bak files anywhere in the source tree
- [ ] **public/ contains only static assets** — images, fonts, manifest.json, robots.txt — no JavaScript, no data files, no server logic
- [ ] **styles/ contains only global CSS** — globals.css with Tailwind v4 directives and design tokens, no component-specific stylesheets
- [ ] **test/ contains only test infrastructure** — setup.ts for global test configuration and utils.tsx for renderWithProviders, no actual test cases in this directory
- [ ] **.gitignore covers the full stack** — node_modules/, .next/, .env, .env.local, coverage/, dist/, .turbo/, IDE files (.idea/, .vscode/settings.json), OS files (.DS_Store, Thumbs.db)
- [ ] **No deeply nested empty directories** — every directory in the tree contains meaningful files, no placeholder or "reserved for future" empty folders

## 1.2 Feature Module Structure

- [ ] **Each feature module has a consistent internal layout** — api/, components/, hooks/ directories follow the same pattern across all 11 feature modules (auth, business, explore, forms, members, network, platform, transactions, users, settings, rbac)
- [ ] **Each module encapsulates exactly one domain** — auth handles authentication, business handles business account operations, explore handles search — no feature bleeds into another
- [ ] **No "god feature" module** — no single feature directory owns more than ~30% of the feature code; large domains are split into separate modules (e.g. members vs. business)
- [ ] **API layer is isolated in api/ subdirectory** — each feature's API calls live in a dedicated api/ folder with typed request/response functions
- [ ] **Components are feature-scoped** — feature components live in features/*/components/, not in the shared components/ directory unless reused by 2+ features
- [ ] **Hooks are feature-scoped** — feature-specific query hooks, mutation hooks, and behavioral hooks live in features/*/hooks/
- [ ] **Optional subdirectories are used when needed** — constants/, utils/, __tests__/, types.ts present only when the feature requires them, not as empty boilerplate
- [ ] **Index barrel exports are consistent** — each feature has an index.ts that re-exports public API (components, hooks, types) for clean imports from other parts of the app

## 1.3 App Router Organization

- [ ] **(public) route group contains unauthenticated pages** — home, about, explore, business/[slug], platform/[slug], user/[username] are accessible without login
- [ ] **(auth) route group contains authentication flows** — login, register, forgot-password, reset-password, verify-email are scoped to auth layout
- [ ] **(app) route group contains authenticated routes** — personal dashboard, bconsole/[slug], pconsole, admin, settings require authentication
- [ ] **Nested route groups are correctly scoped** — (user) for personal pages, bconsole/[slug] for business console, pconsole for platform console, admin for admin panel
- [ ] **No parallel route conflicts** — no two route groups resolve to the same URL path (e.g. app/page.tsx and app/(public)/page.tsx both mapping to /)
- [ ] **Route groups do not create URL segments** — parenthesized group names ((public), (auth), (app)) are organizational only and do not appear in the URL
- [ ] **Each route group has an appropriate layout** — (auth) has a clean centered shell, (app) has sidebar + topbar, bconsole has business-scoped navigation
- [ ] **API route handler is isolated** — /api/[...path]/route.ts lives outside route groups and handles only proxy forwarding, no business logic

## 1.4 Component Organization

- [ ] **ui/ contains only shadcn primitives** — the 24 shadcn components (Button, Card, Dialog, etc.) are auto-generated and unmodified, no custom components mixed in
- [ ] **common/ contains composed shared components** — Can, FormField, PasswordInput, ConfirmActionDialog, and other project-specific reusable components that wrap shadcn primitives
- [ ] **guards/ contains only route protection components** — AuthGuard, BusinessGuard, PlatformGuard, AdminGuard — no other logic in this directory
- [ ] **navigation/ contains all navigation components** — Sidebar, TopNavbar, BottomNavbar, MobileMenuSheet, AccountSwitcher, navigation-config.ts — no nav logic scattered elsewhere
- [ ] **No stray components in app/ or lib/** — page files in app/ are thin wrappers (<30 lines) that import from features/, lib/ contains only utilities and configuration
- [ ] **Components do not import directly from features/** — shared components in components/ never import from features/*/; data flows down via props
- [ ] **Component directory hierarchy is flat** — components/ui/ and components/common/ are at most 1 level deep, no deeply nested component subdirectories

## 1.5 Naming Conventions

- [ ] **PascalCase for component files** — all .tsx component files use PascalCase or kebab-case matching the exported component name (UserCard.tsx or user-card.tsx, applied consistently)
- [ ] **kebab-case for utility and config files** — .ts files for hooks, utilities, configs, and types use kebab-case (api-client.ts, query-keys.ts, auth-store.ts)
- [ ] **Named exports everywhere except Next.js conventions** — all components and utilities use named exports; only pages, layouts, error, loading, and not-found use default exports
- [ ] **Test files are co-located and consistently named** — test files use .test.ts or .test.tsx suffix, matching the source file name (auth-store.test.ts tests auth-store.ts)
- [ ] **Index barrel files use index.ts** — barrel exports are always named index.ts, not index.tsx (unless the barrel itself renders JSX, which it should not)
- [ ] **No default exports for non-Next.js files** — hooks, stores, utilities, types, and shared components use named exports exclusively for better refactoring and tree-shaking
- [ ] **Hook files prefixed with "use"** — all custom hook files follow the use- prefix convention (use-auth-queries.ts, use-business-queries.ts)
- [ ] **Type files match backend contract names** — type files in types/ correspond to backend API shapes (auth.ts, business.ts, transaction.ts, etc.)

## 1.6 Shared vs Feature-Scoped Code

- [ ] **Shared hooks live in hooks/** — hooks used by 2+ features (useDebounce, useMediaQuery, useInView) are in the top-level hooks/ directory, not duplicated across features
- [ ] **Shared types live in types/** — API contract types, common utility types (WithPermissions<T>, PaginatedResponse<T>) are in types/, not scattered in feature modules
- [ ] **Shared utilities live in lib/** — api-client.ts, query-keys.ts, utils.ts, and validation schemas used across features live in lib/
- [ ] **Feature-specific code stays in features/** — code only used by one feature never gets promoted to shared directories prematurely
- [ ] **No cross-feature sibling imports** — features/auth/ does not import from features/business/, features/explore/ does not import from features/members/ — shared needs go through hooks/, lib/, or types/
- [ ] **Static data files live in lib/ or hooks/** — country-data, city-data (cities.json), and other static datasets live in shared directories, features re-export for internal use
- [ ] **Validation schemas are shared when appropriate** — schemas used in multiple forms (email, password requirements) live in lib/validations/, feature-only schemas stay in their feature

## 1.7 Configuration Files

- [ ] **All configuration files at project root** — next.config.ts, tsconfig.json, vitest.config.ts, eslint.config.mjs, postcss.config.mjs, components.json, package.json all at frontend root
- [ ] **Path aliases are consistent across configs** — @/ maps to ./src/ in tsconfig.json, vitest.config.ts, and ESLint config without any discrepancies
- [ ] **No duplicate or conflicting configs** — no tailwind.config.js alongside CSS-first Tailwind v4 config, no .eslintrc alongside flat config, no jest.config alongside vitest.config
- [ ] **components.json configured for shadcn** — style: new-york, rsc: true, color format: oklch, aliases match tsconfig paths
- [ ] **.env.example is committed and documented** — lists all required NEXT_PUBLIC_* variables with comments explaining each, no actual secret values
- [ ] **PostCSS config uses @tailwindcss/postcss** — postcss.config.mjs uses the Tailwind v4 PostCSS plugin, not the legacy @tailwindcss/postcss7-compat

## 1.8 Entry Points & Root Files

- [ ] **Root layout.tsx wraps the entire application** — imports Providers component, sets metadata (title, description), configures fonts via next/font, applies global className
- [ ] **Providers.tsx composes all context providers** — QueryClientProvider, ThemeProvider, AuthInitializer, Toaster — in correct nesting order with stable QueryClient instance
- [ ] **middleware.ts is at src/ root** — handles auth routing (redirect unauthenticated users, redirect authenticated users away from login), uses Edge Runtime
- [ ] **error.tsx exists at root app/ level** — catches unhandled errors with a user-friendly message and reset button
- [ ] **global-error.tsx exists at root app/ level** — catches root layout errors using inline styles (Tailwind may not be loaded), includes html and body tags
- [ ] **not-found.tsx exists at root app/ level** — provides a useful 404 page with navigation back to home
- [ ] **loading.tsx exists at appropriate route segments** — root loading.tsx and per-section loading files provide skeleton UIs during navigation

## 1.9 Test Structure

- [ ] **test/setup.ts imports vitest-compatible matchers** — imports @testing-library/jest-dom/vitest for toBeInTheDocument(), toHaveTextContent(), etc.
- [ ] **test/utils.tsx exports renderWithProviders** — wraps components in QueryClientProvider, MemoryRouter (or equivalent), and any required context providers for testing
- [ ] **Tests mirror source structure** — test files live alongside or in __tests__/ subdirectories matching the source file they test
- [ ] **No test files outside src/** — all test code is within the src/ tree, no rogue test files at the project root or in public/
- [ ] **Feature tests use __tests__/ directories** — each feature module has an __tests__/ directory for component, hook, and integration tests
- [ ] **Test utilities are not duplicated** — shared mocks (mock router, mock query client, mock stores) defined once in test/ and imported, not copy-pasted across test files

## 1.10 Stale & Dead Code

- [ ] **No unused feature modules** — every directory in features/ is actively imported by at least one route or component
- [ ] **No empty component files** — every .tsx file exports a meaningful component, no placeholder files with TODO comments
- [ ] **No orphaned routes without feature code** — every page.tsx in app/ imports a corresponding component from features/ or components/
- [ ] **No dead imports** — no imported modules or components that are never used (enforced by ESLint no-unused-vars)
- [ ] **No commented-out code blocks** — no multi-line commented-out JSX, function bodies, or import statements left as "just in case" references
- [ ] **No .bak, .old, or temporary files** — no backup copies of components, no draft files, no experimental branches merged with leftover artifacts
