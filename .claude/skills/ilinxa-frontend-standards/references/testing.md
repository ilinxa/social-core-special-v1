# Testing Conventions

Vitest + React Testing Library. **Test behavior, not implementation.**

## Table of Contents
1. [Setup](#setup)
2. [File Organization](#file-organization)
3. [Component Testing](#component-testing)
4. [Mocking](#mocking)
5. [Hook Testing](#hook-testing)
6. [Store Testing](#store-testing)
7. [What to Test / Skip](#what-to-test--skip)

---

## Setup

### Dependencies
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

### Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import { resolve } from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.*", "src/test/**", "src/types/**"],
    },
  },
  resolve: {
    alias: { "@": resolve(__dirname, "./src") },
  },
});
```

### Setup File

```typescript
// src/test/setup.ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

---

## File Organization

Tests co-located with source:

```
components/
  ui/
    Button.tsx
    Button.test.tsx         # ✅ next to source

features/
  auth/
    components/
      LoginForm.tsx
      LoginForm.test.tsx    # ✅ next to source
    hooks/
      useAuth.ts
      useAuth.test.ts
```

Naming: `ComponentName.test.tsx`, `useHook.test.ts`, `utilName.test.ts`.

---

## Component Testing

### Query Priority (prefer user-visible queries)

1. `getByRole` — buttons, links, headings (best)
2. `getByLabelText` — form inputs
3. `getByPlaceholderText` — when no label
4. `getByText` — visible text content
5. `getByTestId` — last resort

```tsx
// ✅ User-centric queries
screen.getByRole("button", { name: "Submit" });
screen.getByLabelText("Email");
screen.getByText("Welcome back");

// ❌ Implementation details
screen.getByTestId("submit-btn");
document.querySelector(".submit-button");
```

### User Events

```tsx
import userEvent from "@testing-library/user-event";

it("submits the form", async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  render(<LoginForm onSubmit={onSubmit} />);

  await user.type(screen.getByLabelText("Email"), "test@example.com");
  await user.type(screen.getByLabelText("Password"), "password123");
  await user.click(screen.getByRole("button", { name: "Sign In" }));

  expect(onSubmit).toHaveBeenCalledWith({
    email: "test@example.com",
    password: "password123",
  });
});
```

### Async Queries

```tsx
// Wait for element to appear
const heading = await screen.findByRole("heading", { name: "Dashboard" });

// Wait for element to disappear
await waitFor(() => {
  expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
});
```

### Rendering with Providers

```tsx
// src/test/utils.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

export function renderWithProviders(ui: React.ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: createWrapper(), ...options });
}
```

---

## Mocking

### Module Mocks

```typescript
vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));
```

### Function Mocks

```typescript
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual("react-router-dom")),
  useNavigate: () => mockNavigate,
}));
```

### Timer Mocks

```typescript
beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it("debounces search", async () => {
  render(<SearchInput />);
  await userEvent.type(screen.getByRole("textbox"), "query");
  vi.advanceTimersByTime(300);
  expect(onSearch).toHaveBeenCalledWith("query");
});
```

### API Mocking with MSW (optional, for integration tests)

```typescript
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.get("/api/users", () => HttpResponse.json([{ id: "1", name: "Alice" }])),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## Hook Testing

```typescript
import { renderHook, act } from "@testing-library/react";

it("toggles value", () => {
  const { result } = renderHook(() => useToggle(false));

  expect(result.current[0]).toBe(false);

  act(() => result.current[1]()); // toggle
  expect(result.current[0]).toBe(true);
});
```

---

## Store Testing

Reset Zustand stores between tests:

```typescript
import { useCartStore } from "@/stores/cartStore";

beforeEach(() => {
  useCartStore.setState({ items: [], total: 0 }); // reset
});

it("adds item to cart", () => {
  const { addItem } = useCartStore.getState();
  addItem({ id: "1", name: "Widget", price: 10, quantity: 1 });
  expect(useCartStore.getState().items).toHaveLength(1);
});
```

---

## What to Test / Skip

### Test
- User interactions (click, type, submit)
- Conditional rendering (loading, error, empty states)
- Form validation and submission
- Custom hook logic
- Zustand store actions and derived state
- Edge cases (empty arrays, null values, error states)

### Skip
- Implementation details (internal state, method calls)
- Third-party library internals (shadcn, Radix)
- Pure CSS / styling (visual regression tools instead)
- 1:1 component snapshots (brittle, low value)
- Simple pass-through components with no logic

### Mock Cleanup
- Always `vi.clearAllMocks()` or `vi.restoreAllMocks()` in `afterEach`
- Reset stores in `beforeEach`
- Never share mock state across tests
