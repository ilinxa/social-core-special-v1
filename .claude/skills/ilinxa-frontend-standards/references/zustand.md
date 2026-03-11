# Zustand State Management

Zustand = **client state only** (UI toggles, form drafts, preferences, filters). Server state → TanStack Query. Never mix.

## Table of Contents
1. [When to Use](#when-to-use)
2. [Store Organization](#store-organization)
3. [Selectors](#selectors)
4. [State Updates](#state-updates)
5. [Middleware](#middleware)
6. [TypeScript Patterns](#typescript-patterns)
7. [Next.js SSR](#nextjs-ssr)

---

## When to Use

**Use Zustand when:** Multiple unrelated components need the same client state, state needs to survive unmounts, you need state outside React, `useState` lifted 3+ levels through props.

**Don't use when:** State is only for one component (`useState`), data comes from an API (TanStack Query), state is a form (react-hook-form).

---

## Store Organization

One store per domain. Files in `src/stores/`:

```
stores/
├── authStore.ts        # auth state
├── uiStore.ts          # sidebar, theme, modals
└── filterStore.ts      # search/filter state
```

### Store File Anatomy

```typescript
// src/stores/authStore.ts
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

interface AuthActions {
  login: (user: User, token: string) => void;
  logout: () => void;
}

const useAuthStoreBase = create<AuthState & AuthActions>()(
  devtools(
    persist(
      (set) => ({
        // State
        user: null,
        token: null,
        isAuthenticated: false,

        // Actions
        login: (user, token) => set({ user, token, isAuthenticated: true }),
        logout: () => set({ user: null, token: null, isAuthenticated: false }),
      }),
      { name: "auth-storage" },
    ),
  ),
);

// ✅ Export selector hooks, NOT the raw store
export const useUser = () => useAuthStoreBase((s) => s.user);
export const useIsAuthenticated = () => useAuthStoreBase((s) => s.isAuthenticated);
export const useAuthActions = () => useAuthStoreBase((s) => ({ login: s.login, logout: s.logout }));
```

---

## Selectors

**Always use selectors.** Without them, every subscriber re-renders on any state change.

```typescript
// ✅ Atomic selector — re-renders only when `user` changes
const user = useAuthStoreBase((s) => s.user);

// ❌ Full store subscription — re-renders on ANY change
const store = useAuthStoreBase();
```

### `useShallow` for Multi-Value Selectors

```typescript
import { useShallow } from "zustand/react/shallow";

// ✅ Re-renders only when user OR token change (shallow compare)
const { user, token } = useAuthStoreBase(
  useShallow((s) => ({ user: s.user, token: s.token })),
);
```

### Derived State

```typescript
// ✅ Compute in selector — no extra store field needed
export const useCartTotal = () => useCartStore((s) =>
  s.items.reduce((sum, item) => sum + item.price * item.quantity, 0)
);
```

---

## State Updates

**Immutable by default:**
```typescript
// ✅ Spread for shallow objects
set((state) => ({ items: [...state.items, newItem] }));

// ✅ Filter for removal
set((state) => ({ items: state.items.filter((i) => i.id !== id) }));
```

**Immer for deeply nested state:**
```typescript
import { immer } from "zustand/middleware/immer";

const useStore = create<State>()(
  immer((set) => ({
    nested: { deep: { value: 0 } },
    updateDeep: () => set((state) => { state.nested.deep.value += 1; }),
  })),
);
```

**Actions live in the store.** No external functions that call `set`:

```typescript
// ✅ Actions inside store
create((set) => ({
  count: 0,
  increment: () => set((s) => ({ count: s.count + 1 })),
}));

// ❌ External function
function increment() { useStore.setState((s) => ({ count: s.count + 1 })); }
```

---

## Middleware

Order: `devtools(persist(immer(store)))` — outer to inner.

### persist
```typescript
persist(storeCreator, {
  name: "store-key",           // localStorage key
  partialize: (state) => ({    // persist only specific fields
    token: state.token,
    user: state.user,
  }),
});
```

### devtools
```typescript
devtools(storeCreator, { name: "AuthStore" }); // visible in Redux DevTools
```

---

## TypeScript Patterns

### Separate State and Actions interfaces
```typescript
interface CountState { count: number; }
interface CountActions { increment: () => void; reset: () => void; }

const useStore = create<CountState & CountActions>()((set) => ({ ... }));
```

### Access state inside actions
```typescript
create((set, get) => ({
  items: [],
  addItem: (item: Item) => {
    const current = get().items;
    if (current.some((i) => i.id === item.id)) return; // guard
    set({ items: [...current, item] });
  },
}));
```

---

## Next.js SSR

Zustand stores are client-side only. Prevent hydration mismatch:

```tsx
"use client";
import { useEffect, useState } from "react";

export function HydrationGuard({ children }: { children: React.ReactNode }) {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  if (!hydrated) return null; // or skeleton
  return <>{children}</>;
}
```

Or use Zustand's `onRehydrateStorage` callback for persisted stores. Never read persisted state during SSR.
