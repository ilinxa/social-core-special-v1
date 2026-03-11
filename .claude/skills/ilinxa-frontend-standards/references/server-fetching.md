# Server Data Fetching (Next.js)

Next.js App Router: Server Components fetch on server, Server Actions handle mutations, client picks up where server left off.

## Table of Contents
1. [Decision Tree](#decision-tree)
2. [Server Component Fetching](#server-component-fetching)
3. [Parallel vs Sequential](#parallel-vs-sequential)
4. [Server Actions](#server-actions)
5. [Hydrating TanStack Query](#hydrating-tanstack-query)
6. [Caching and Revalidation](#caching-and-revalidation)
7. [Common Patterns](#common-patterns)

---

## Decision Tree

```
Does this data exist on initial page load?
├── YES → Fetch in Server Component
│   ├── Needs client interactivity after load?
│   │   ├── YES → Prefetch on server, hydrate to TanStack Query (§5)
│   │   └── NO → Server Component only — no client JS
│   └── Changes based on user actions (filter, paginate)?
│       └── YES → TanStack Query on client (see tanstack-query.md)
├── NO (triggered by user action) → TanStack Query mutation
└── Form submission → Server Action (§4)
```

---

## Server Component Fetching

### Direct Data Access (no fetch needed for DB)

```tsx
// Server Component — runs on server only
import { db } from "@/lib/server/db";

export default async function UsersPage() {
  const users = await db.user.findMany({ where: { active: true } });
  return <UserList users={users} />;
}
```

### Fetch from API

```tsx
async function getUsers(): Promise<User[]> {
  const res = await fetch(`${process.env.API_URL}/users`, {
    next: { revalidate: 60 }, // ISR: revalidate every 60s
  });
  if (!res.ok) throw new Error("Failed to fetch users");
  return res.json();
}

export default async function UsersPage() {
  const users = await getUsers();
  return <UserList users={users} />;
}
```

### Request Deduplication with React.cache

```typescript
import { cache } from "react";
import { db } from "@/lib/server/db";

// Multiple components calling getUser(id) in the same request → single DB query
export const getUser = cache(async (id: string) => {
  return db.user.findUnique({ where: { id } });
});
```

### Server-Only Guard

```typescript
import "server-only"; // throws if imported in client bundle

export async function getSecretData() {
  return db.secrets.findMany();
}
```

### Streaming with Suspense

```tsx
import { Suspense } from "react";

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<StatsSkeleton />}>
        <DashboardStats />  {/* async server component — streams when ready */}
      </Suspense>
      <Suspense fallback={<ChartSkeleton />}>
        <RevenueChart />
      </Suspense>
    </div>
  );
}
```

---

## Parallel vs Sequential

### Waterfall Problem (bad)

```tsx
// ❌ Sequential — second waits for first
export default async function Page() {
  const user = await getUser(id);        // 200ms
  const projects = await getProjects(id); // 200ms — starts AFTER user finishes
  // Total: 400ms
}
```

### Parallel with Promise.all

```tsx
// ✅ Parallel — both fire simultaneously
export default async function Page() {
  const [user, projects] = await Promise.all([
    getUser(id),
    getProjects(id),
  ]);
  // Total: 200ms (max of both)
}
```

### Parallel with Suspense (Best)

```tsx
// ✅ Each component fetches independently, streams when ready
export default function Page() {
  return (
    <>
      <Suspense fallback={<UserSkeleton />}>
        <UserProfile id={id} />
      </Suspense>
      <Suspense fallback={<ProjectsSkeleton />}>
        <ProjectList userId={id} />
      </Suspense>
    </>
  );
}
```

---

## Server Actions

### Defining

```typescript
// src/features/users/actions/createUser.ts
"use server";

import { z } from "zod";
import { db } from "@/lib/server/db";
import { revalidatePath } from "next/cache";

const schema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

export async function createUser(formData: FormData) {
  const parsed = schema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { error: parsed.error.flatten().fieldErrors };

  await db.user.create({ data: parsed.data });
  revalidatePath("/users");
  return { success: true };
}
```

### Using in Client Components

```tsx
"use client";
import { useActionState } from "react";
import { createUser } from "@/features/users/actions/createUser";

export function CreateUserForm() {
  const [state, action, isPending] = useActionState(createUser, null);

  return (
    <form action={action}>
      <input name="name" required />
      <input name="email" type="email" required />
      {state?.error && <p className="text-destructive">{JSON.stringify(state.error)}</p>}
      <button type="submit" disabled={isPending}>
        {isPending ? "Creating..." : "Create User"}
      </button>
    </form>
  );
}
```

### Server Action Rules
- Always validate input with Zod.
- Always call `revalidatePath` or `revalidateTag` after mutations.
- Return structured responses `{ success, error }` — don't throw.
- Keep actions in `features/*/actions/` files.
- Mark every action file with `"use server"` at the top.

---

## Hydrating TanStack Query

When data is fetched on the server but needs client-side interactivity (polling, refetching, optimistic updates):

```tsx
// Server Component (page.tsx)
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { userQueries } from "@/features/users/api/userQueries";

export default async function UsersPage() {
  const queryClient = new QueryClient();
  await queryClient.prefetchQuery(userQueries.list({}));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <UserListClient />  {/* client component uses useQuery — gets prefetched data */}
    </HydrationBoundary>
  );
}
```

**Use when:** Data needs polling, user can filter/paginate, optimistic updates needed.
**Don't use when:** Static display only, no client interactivity, data doesn't change.

---

## Caching and Revalidation

Next.js cache layers: Request Memoization (React.cache) → Data Cache (fetch) → Full Route Cache.

### After Mutations

```typescript
"use server";
import { revalidatePath, revalidateTag } from "next/cache";

// Revalidate specific path
revalidatePath("/users");

// Revalidate by tag (more granular)
revalidateTag("users");

// In fetch calls, tag for targeted revalidation:
fetch(url, { next: { tags: ["users"] } });
```

---

## Common Patterns

### Protected Data Fetching

```typescript
import { auth } from "@/lib/server/auth";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/login");

  const data = await getDashboardData(session.userId);
  return <Dashboard data={data} />;
}
```

### Data Fetching Location Summary

| Scenario | Where to Fetch |
|----------|---------------|
| Initial page data, no interactivity | Server Component |
| Initial data + client interactivity | Server prefetch → hydrate to TanStack Query |
| User-triggered (search, filter, paginate) | TanStack Query (client) |
| Form submission | Server Action |
| Real-time updates | TanStack Query polling or WebSocket |
