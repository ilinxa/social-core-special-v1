# React SPA Project Structure (Vite)

## Table of Contents
1. [Top-Level Structure](#top-level-structure)
2. [Folder Breakdown](#folder-breakdown)
3. [File Naming](#file-naming)
4. [Routing](#routing)
5. [Co-location Principle](#co-location-principle)

---

## Top-Level Structure

```
project-root/
├── public/                   # Static assets (favicon, robots.txt)
├── src/
│   ├── app/                  # App shell — providers, router, global layout
│   ├── components/           # Shared, reusable UI components
│   ├── features/             # Feature modules (domain-driven)
│   ├── hooks/                # Shared custom hooks
│   ├── lib/                  # Utilities, helpers, third-party wrappers
│   ├── stores/               # Zustand stores
│   ├── types/                # Shared TypeScript type definitions
│   ├── styles/               # Global styles, Tailwind config extensions
│   └── main.tsx              # Vite entry point
├── .vscode/
├── .prettierrc
├── eslint.config.mjs
├── tsconfig.json
├── vite.config.ts
└── package.json
```

---

## Folder Breakdown

### `src/app/` — App Shell
```
app/
├── App.tsx                   # Root component (renders router)
├── Providers.tsx             # All context providers (QueryClient, theme, etc.)
├── Router.tsx                # Route definitions
└── layouts/
    └── MainLayout.tsx        # Header, sidebar, footer shell
```

### `src/features/` — Feature Modules
Each feature is a self-contained domain:
```
features/
├── auth/
│   ├── components/           # Feature-specific components
│   │   ├── LoginForm.tsx
│   │   └── AuthGuard.tsx
│   ├── hooks/
│   │   └── useAuth.ts
│   ├── api/
│   │   └── authApi.ts        # TanStack Query hooks for auth
│   ├── stores/
│   │   └── authStore.ts      # Feature-specific Zustand store (if needed)
│   └── types.ts              # Feature-specific types
├── dashboard/
│   └── ...
└── users/
    └── ...
```

Rules:
- Features never import from other features directly. Shared code goes to `components/`, `hooks/`, `lib/`, or `types/`.
- Each feature owns its components, hooks, API layer, and types.
- Feature folders can have their own `stores/` when state is feature-specific.

### `src/components/` — Shared UI
```
components/
├── ui/                       # shadcn/ui + custom primitives
│   ├── Button.tsx
│   ├── Input.tsx
│   └── Dialog.tsx
├── layout/                   # Shared layout components
│   ├── PageHeader.tsx
│   └── Container.tsx
└── common/                   # Shared business components
    ├── DataTable.tsx
    └── EmptyState.tsx
```

### Other folders
- `hooks/` — shared hooks used across features (`useDebounce`, `useMediaQuery`)
- `lib/` — utilities, third-party wrappers, `cn()` helper, API client config
- `stores/` — global Zustand stores (auth, theme, sidebar)
- `types/` — shared types organized by domain (`user.ts`, `api.ts`, `common.ts`)
- `styles/` — global CSS, Tailwind extensions

---

## File Naming

| What | Convention | Example |
|------|-----------|---------|
| Component | PascalCase | `UserProfile.tsx` |
| Hook | camelCase, `use` prefix | `useAuth.ts` |
| Utility | camelCase | `formatDate.ts` |
| Store | camelCase, `Store` suffix | `authStore.ts` |
| Types (dedicated) | camelCase or PascalCase | `types.ts` or `UserTypes.ts` |
| Test | Same name + `.test` | `UserProfile.test.tsx` |
| One component per file | Component name = file name | |

---

## Routing

Single router file: `src/app/Router.tsx` with React Router:

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { lazy, Suspense } from "react";

const Dashboard = lazy(() => import("@/features/dashboard/pages/DashboardPage"));
const Users = lazy(() => import("@/features/users/pages/UsersPage"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <Suspense fallback={<Spinner />}><Dashboard /></Suspense> },
      { path: "users", element: <Suspense fallback={<Spinner />}><Users /></Suspense> },
    ],
  },
]);

export function Router() {
  return <RouterProvider router={router} />;
}
```

Route constants in `src/lib/routes.ts`:
```typescript
export const ROUTES = {
  HOME: "/",
  DASHBOARD: "/dashboard",
  USERS: "/users",
  USER_DETAIL: (id: string) => `/users/${id}`,
} as const;
```

---

## Co-location Principle

Keep related code together. A feature's components, hooks, types, and API layer live in the same folder. Only promote to shared folders (`components/`, `hooks/`, `lib/`) when genuinely reused across multiple features.
