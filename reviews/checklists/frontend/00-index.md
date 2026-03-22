# Frontend Review Checklist Index

Comprehensive review system for the Next.js 16 + React 19 + TypeScript frontend.

**Tech Stack**: Next.js 16.1.6, React 19.2.3, TypeScript 5 (strict), Tailwind CSS v4, shadcn/ui, Zustand 5, TanStack Query v5, react-hook-form + Zod, Vitest + RTL

**Codebase**: 433 TS/TSX files, 116 test files, 11 feature modules, 100+ routes, 1078 tests

---

## Review Steps

| # | Checklist | Sections | Description | Status |
|---|-----------|----------|-------------|--------|
| 01 | [Project Structure & Organization](01-project-structure-and-organization.md) | 10 | Directory layout, feature modules, App Router, naming conventions | Pending |
| 02 | [Configuration & Environment](02-configuration-and-environment.md) | 10 | Next.js, TypeScript, Tailwind v4, ESLint, Vitest, env vars | Pending |
| 03 | [Routing & Navigation](03-routing-and-navigation.md) | 10 | Route groups, middleware, guards, layouts, dynamic routes | Pending |
| 04 | [Component Architecture](04-component-architecture.md) | 11 | Server/client split, shadcn/ui, composition, permissions, dialogs | Pending |
| 05 | [State Management](05-state-management.md) | 10 | Zustand stores, TanStack Query, selectors, cache invalidation | Pending |
| 06 | [Data Fetching & API Integration](06-data-fetching-and-api-integration.md) | 11 | Axios client, JWT, token refresh, API functions, error chain | Pending |
| 07 | [Authentication & Authorization](07-authentication-and-authorization.md) | 11 | Auth flows, guards, multi-tier permissions, session management | Pending |
| 08 | [Forms & Validation](08-forms-and-validation.md) | 10 | react-hook-form, Zod schemas, field components, form builder | Pending |
| 09 | [Styling & Theming](09-styling-and-theming.md) | 9 | Tailwind v4 CSS-first, OKLCH, dark mode, responsive, cn() | Pending |
| 10 | [TypeScript & Type Safety](10-typescript-and-type-safety.md) | 10 | Strict mode, type vs interface, API contracts, generics | Pending |
| 11 | [Testing](11-testing.md) | 12 | Vitest + RTL, component/hook/API tests, mocking, async, CI | Pending |
| 12 | [Performance & Optimization](12-performance-and-optimization.md) | 11 | Server components, React Compiler, bundle size, caching | Pending |
| 13 | [Security](13-security.md) | 10 | XSS, CSP, token security, CSRF, dependency scanning | Pending |
| 14 | [Accessibility & UX](14-accessibility-and-ux.md) | 10 | Semantic HTML, ARIA, keyboard nav, focus, contrast, a11y testing | Pending |
| 15 | [Error Handling & Observability](15-error-handling-and-observability.md) | 10 | Error boundaries, ApiError, reporting, rate limiting, Sentry | Pending |

**Total: 155 checklist items across 15 steps**

---

## How to Use

1. Open the checklist for the step being audited
2. Apply corresponding rules from `rules/frontend/` (created during audit)
3. Record findings in `reports/frontend/v1/` (created during audit)
4. Re-audit as `v2/`, `v3/` to track improvement

## Backend-to-Frontend Mapping

| Backend Step | Frontend Equivalent | Notes |
|---|---|---|
| 01 Project Structure | 01 Project Structure | Feature modules replace Django apps |
| 02 Configuration | 02 Configuration | Next.js/TS/Tailwind replace Django settings |
| 03 Database & Models | 03 Routing & Navigation | Routes are the structural backbone |
| 04 API Design (DRF) | 04 Component Architecture | Components are the UI "API surface" |
| 05 Auth | 07 Auth & Authorization | In-memory JWT, guards, permissions |
| 06 Validation | 08 Forms & Validation | react-hook-form + Zod |
| 07 Testing | 11 Testing | Vitest + RTL patterns |
| 08 Performance | 12 Performance | Bundles, RSC, React Compiler |
| 09 Security | 13 Security | XSS, CSP, token storage |
| 10 Code Quality | 10 TypeScript & Type Safety | Strict mode, no-any |
| — | 05 State Management | **New** — Zustand + TanStack Query |
| — | 06 Data Fetching & API | **New** — Axios, JWT interceptors |
| — | 09 Styling & Theming | **New** — Tailwind v4, dark mode |
| — | 14 Accessibility & UX | **New** — WCAG, keyboard, ARIA |
