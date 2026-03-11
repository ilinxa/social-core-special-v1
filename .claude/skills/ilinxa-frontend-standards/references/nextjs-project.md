# Next.js Project Structure (App Router)

## Table of Contents
1. [Top-Level Structure](#top-level-structure)
2. [The app/ Directory](#the-app-directory)
3. [Features Directory](#features-directory)
4. [Server vs Client Components](#server-vs-client-components)
5. [Root Layout and Providers](#root-layout-and-providers)
6. [The lib/ Directory](#the-lib-directory)
7. [File Naming](#file-naming)

---

## Top-Level Structure

```
project-root/
├── public/                   # Static assets
├── src/
│   ├── app/                  # Next.js App Router — routes, layouts, pages
│   ├── components/           # Shared UI components
│   ├── features/             # Feature modules (same as React SPA)
│   ├── hooks/                # Shared hooks (client-side)
│   ├── lib/                  # Utilities, server functions
│   ├── stores/               # Zustand stores (client-side)
│   ├── types/                # Shared types
│   └── styles/               # Global styles
├── .vscode/
├── eslint.config.mjs
├── next.config.ts
├── tsconfig.json
└── package.json
```

Key difference from SPA: `app/` is the routing layer (file-based), no `Router.tsx`.

---

## The app/ Directory

```
app/
├── layout.tsx                # Root layout — wraps ALL pages
├── page.tsx                  # Home page (/)
├── loading.tsx               # Global loading fallback
├── error.tsx                 # Global error boundary
├── not-found.tsx             # 404 page
├── (auth)/                   # Route group (no URL segment)
│   ├── login/page.tsx
│   └── register/page.tsx
├── dashboard/
│   ├── layout.tsx            # Dashboard-specific layout
│   ├── page.tsx              # /dashboard
│   └── settings/page.tsx     # /dashboard/settings
└── api/                      # API routes (if needed)
    └── webhooks/route.ts
```

### Rules for app/

- `app/` is ONLY for routing. No business logic, no complex components.
- Pages are thin wrappers: import from `features/`, render layout + feature component.
- Keep `page.tsx` under 30 lines. Extract complex logic to feature components.
- Default export required for `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`.

```tsx
// ✅ Thin page — imports from feature
// src/app/dashboard/page.tsx
import { DashboardPage } from "@/features/dashboard/components/DashboardPage";

export default function Page() {
  return <DashboardPage />;
}
```

### Special Files

| File | Purpose |
|------|---------|
| `page.tsx` | Route component (default export) |
| `layout.tsx` | Persistent layout wrapping children |
| `loading.tsx` | Suspense fallback for the route |
| `error.tsx` | Error boundary (`"use client"` required) |
| `not-found.tsx` | 404 page |
| `route.ts` | API route handler |
| `template.tsx` | Like layout but re-mounts on navigation |

### Route Groups

Prefix folder name with `()` for logical grouping without URL segments:

```
app/
├── (marketing)/              # No /marketing in URL
│   ├── page.tsx              # /
│   └── about/page.tsx        # /about
└── (app)/                    # No /app in URL
    ├── layout.tsx            # App-specific layout
    └── dashboard/page.tsx    # /dashboard
```

---

## Features Directory

Same structure as React SPA features, plus Next.js-specific folders:

```
features/
├── auth/
│   ├── components/
│   ├── hooks/
│   ├── api/
│   ├── actions/              # Server Actions
│   │   └── loginAction.ts
│   └── types.ts
```

---

## Server vs Client Components

**Default to Server.** Only add `"use client"` when the component needs: `useState`, `useEffect`, hooks, event handlers, browser APIs, or context.

**Push `"use client"` down.** Keep the boundary as narrow as possible:

```tsx
// ✅ Server component fetches, passes to client
// app/dashboard/page.tsx (SERVER)
import { DashboardStats } from "@/features/dashboard/components/DashboardStats";

export default async function Page() {
  const stats = await getStats(); // server-side fetch
  return <DashboardStats initialData={stats} />; // client component
}

// features/dashboard/components/DashboardStats.tsx
"use client";
export function DashboardStats({ initialData }: Props) {
  // interactive client behavior here
}
```

**Identify client components by presence of:** `"use client"` directive, `useState`, `useEffect`, `useContext`, `onClick`/`onChange`, Zustand stores, TanStack Query hooks.

---

## Root Layout and Providers

```tsx
// src/app/layout.tsx
import type { Metadata } from "next";
import { Providers } from "@/app/Providers";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: { default: "App Name", template: "%s | App Name" },
  description: "App description",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

```tsx
// src/app/Providers.tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

---

## The lib/ Directory

Next.js-specific additions:

```
lib/
├── utils.ts                  # cn() helper, general utilities
├── api-client.ts             # Fetch wrapper for client-side
├── server/                   # Server-only code
│   ├── db.ts                 # Database client
│   ├── auth.ts               # Auth helpers
│   └── fetchers.ts           # Server Component data fetchers
└── validations/              # Zod schemas (shared client + server)
    └── user.ts
```

Mark server-only code with `import "server-only"` to prevent accidental client imports.

---

## File Naming

Same as React SPA conventions. Additional Next.js files use lowercase: `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`, `route.ts`.
