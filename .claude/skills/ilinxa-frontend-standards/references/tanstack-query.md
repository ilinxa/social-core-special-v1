# Client Data Fetching (TanStack Query)

TanStack Query = **server state** (API data). Client state → Zustand. Never mix.

## Table of Contents
1. [Setup](#setup)
2. [Query Key Architecture](#query-key-architecture)
3. [Query Options Pattern](#query-options-pattern)
4. [Queries](#queries)
5. [Mutations](#mutations)
6. [API Client Integration](#api-client-integration)
7. [Error Handling](#error-handling)
8. [File Organization](#file-organization)
9. [Zustand + TanStack Query](#zustand--tanstack-query)

---

## Setup

```tsx
// src/app/Providers.tsx (SPA) or src/app/providers.tsx (Next.js)
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,        // 1 min before refetch
        gcTime: 5 * 60 * 1000,       // 5 min cache retention
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

---

## Query Key Architecture

Hierarchical, array-based keys:

```typescript
// src/lib/query-keys.ts — Query Key Factory
export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

export const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  list: (filters: ProjectFilters) => [...projectKeys.lists(), filters] as const,
  detail: (id: string) => [...projectKeys.all, "detail", id] as const,
};
```

Rules:
- Always use the factory — never hand-write keys in components.
- Invalidation cascades: `queryClient.invalidateQueries({ queryKey: userKeys.all })` invalidates ALL user queries.
- Keys must be serializable (no functions, no class instances).

---

## Query Options Pattern

Centralize query configuration per entity:

```typescript
// src/features/users/api/userQueries.ts
import { queryOptions } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { userKeys } from "@/lib/query-keys";

export const userQueries = {
  list: (filters: UserFilters) =>
    queryOptions({
      queryKey: userKeys.list(filters),
      queryFn: () => apiClient.get<User[]>("/users", { params: filters }),
    }),

  detail: (id: string) =>
    queryOptions({
      queryKey: userKeys.detail(id),
      queryFn: () => apiClient.get<User>(`/users/${id}`),
      enabled: !!id,
    }),
};
```

Usage in components:
```tsx
function UserList({ filters }: { filters: UserFilters }) {
  const { data, isLoading, error } = useQuery(userQueries.list(filters));
  // ...
}
```

---

## Queries

### Basic Query
```tsx
const { data: users, isLoading, error } = useQuery(userQueries.list(filters));

if (isLoading) return <Spinner />;
if (error) return <ErrorMessage error={error} />;
return <UserTable users={users} />;
```

### Conditional
```tsx
const { data } = useQuery({
  ...userQueries.detail(userId),
  enabled: !!userId, // only fetch when userId exists
});
```

### Parallel
```tsx
const usersQuery = useQuery(userQueries.list(filters));
const projectsQuery = useQuery(projectQueries.list(filters));
// Both fire simultaneously
```

### select for Transformation
```tsx
const { data: userNames } = useQuery({
  ...userQueries.list(filters),
  select: (users) => users.map((u) => u.name), // transform cached data
});
```

---

## Mutations

```typescript
// src/features/users/api/userMutations.ts
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateUserRequest) => apiClient.post<User>("/users", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
}
```

### Optimistic Updates
```typescript
export function useToggleFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiClient.post(`/favorites/${id}`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: userKeys.detail(id) });
      const previous = queryClient.getQueryData(userKeys.detail(id));
      queryClient.setQueryData(userKeys.detail(id), (old: User) => ({
        ...old,
        isFavorite: !old.isFavorite,
      }));
      return { previous };
    },
    onError: (_err, id, context) => {
      queryClient.setQueryData(userKeys.detail(id), context?.previous);
    },
    onSettled: (_data, _err, id) => {
      queryClient.invalidateQueries({ queryKey: userKeys.detail(id) });
    },
  });
}
```

### Mutation Rules
- Always invalidate related queries on success.
- Show loading state during mutation (`isPending`).
- Handle errors with user-facing feedback (toast/inline).
- Use optimistic updates only for low-risk, easily reversible actions.

---

## API Client Integration

```typescript
// src/lib/api-client.ts
const BASE_URL = import.meta.env.VITE_API_URL; // or process.env.NEXT_PUBLIC_API_URL

class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers: HeadersInit = { "Content-Type": "application/json", ...options.headers };

  // Add auth token if available
  const token = localStorage.getItem("token");
  if (token) (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(response.status, errorData?.message || response.statusText, errorData);
  }

  return response.json();
}

export const apiClient = {
  get: <T>(endpoint: string, config?: { params?: Record<string, string> }) => {
    const url = config?.params ? `${endpoint}?${new URLSearchParams(config.params)}` : endpoint;
    return request<T>(url);
  },
  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, { method: "POST", body: data ? JSON.stringify(data) : undefined }),
  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, { method: "PUT", body: JSON.stringify(data) }),
  patch: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, { method: "PATCH", body: JSON.stringify(data) }),
  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: "DELETE" }),
};
```

---

## Error Handling

### Per-Query
```tsx
const { data, error } = useQuery({
  ...userQueries.list(filters),
  throwOnError: false, // handle inline (default)
});
if (error) return <ErrorMessage error={error} />;
```

### Global (in QueryClient config)
```tsx
new QueryClient({
  defaultOptions: {
    mutations: {
      onError: (error) => {
        if (error instanceof ApiError && error.status === 401) {
          // redirect to login
        }
      },
    },
  },
});
```

### With Error Boundaries
```tsx
const { data } = useQuery({
  ...userQueries.detail(id),
  throwOnError: true, // throws to nearest ErrorBoundary
});
```

---

## File Organization

```
features/
  users/
    api/
      userQueries.ts      # queryOptions factories
      userMutations.ts     # useMutation hooks
    components/
      UserList.tsx          # uses useQuery(userQueries.list(...))
```

One query file + one mutation file per feature. Components import from these.

---

## Zustand + TanStack Query

They complement, never overlap:
- Zustand store holds filter state → TanStack Query uses it in query keys
- TanStack Query fetches data → component reads both

```tsx
// Zustand holds UI state
const filters = useUserFilters(); // from Zustand store

// TanStack Query fetches based on that state
const { data } = useQuery(userQueries.list(filters));
```

Never put `queryClient.invalidateQueries()` in a Zustand action. Keep query lifecycle in TanStack Query hooks.
