# Error Handling

Every error: caught, communicated to user, logged for developers. Silent failures are bugs.

## Table of Contents
1. [Error Boundary Strategy](#error-boundary-strategy)
2. [API Error Handling](#api-error-handling)
3. [Form Validation Errors](#form-validation-errors)
4. [Next.js Error Handling](#nextjs-error-handling)
5. [Error Tracking](#error-tracking)
6. [Decision Matrix](#decision-matrix)

---

## Error Boundary Strategy

### Layered Boundaries

```
Root ErrorBoundary (app-level — "Something went wrong, reload")
└── Feature ErrorBoundary (per major section)
    └── Component ErrorBoundary (individual widgets)
```

Error boundaries catch: rendering errors, lifecycle errors, constructor errors.
They do NOT catch: event handlers, async code, server-side errors, errors in the boundary itself.

### Fallback Components

```tsx
// Generic fallback
interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

export function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return (
    <div role="alert" className="rounded-lg border border-destructive p-6">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="text-sm text-muted-foreground">{error.message}</p>
      <Button onClick={resetErrorBoundary} variant="outline">Try Again</Button>
    </div>
  );
}
```

Use `react-error-boundary` package:

```tsx
import { ErrorBoundary } from "react-error-boundary";

<ErrorBoundary FallbackComponent={ErrorFallback} onReset={() => queryClient.invalidateQueries()}>
  <UserDashboard />
</ErrorBoundary>
```

### With TanStack Query

```tsx
// Option 1: throwOnError — catches in ErrorBoundary
const { data } = useQuery({ ...userQueries.detail(id), throwOnError: true });

// Option 2: Inline handling (default)
const { data, error } = useQuery(userQueries.detail(id));
if (error) return <ErrorMessage error={error} />;
```

---

## API Error Handling

### ApiError Class

```typescript
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isNotFound() { return this.status === 404; }
  get isUnauthorized() { return this.status === 401; }
  get isForbidden() { return this.status === 403; }
  get isValidation() { return this.status === 422; }
}
```

### Global Query Error Handling

```tsx
new QueryClient({
  defaultOptions: {
    mutations: {
      onError: (error) => {
        if (error instanceof ApiError) {
          if (error.isUnauthorized) redirect("/login");
          toast.error(error.message);
        } else {
          toast.error("An unexpected error occurred");
        }
        reportError(error);
      },
    },
  },
});
```

### Mutation Error Pattern

```tsx
const mutation = useCreateUser();

<form onSubmit={(e) => {
  e.preventDefault();
  mutation.mutate(formData, {
    onSuccess: () => toast.success("User created"),
    onError: (error) => {
      if (error instanceof ApiError && error.isValidation) {
        setFieldErrors(error.data);
      } else {
        toast.error(error.message);
      }
    },
  });
}}>
  {mutation.isPending && <Spinner />}
  {mutation.error && <ErrorMessage error={mutation.error} />}
</form>
```

---

## Form Validation Errors

### Client-Side (Zod + react-hook-form)

```tsx
const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "Must be at least 8 characters"),
});

const form = useForm({ resolver: zodResolver(schema) });

// Errors auto-display via <FormMessage /> component
```

### Server-Side Validation Errors

Map API validation errors to form fields:

```typescript
// API returns: { errors: { email: ["already taken"], name: ["too short"] } }
if (error instanceof ApiError && error.isValidation) {
  const serverErrors = error.data as Record<string, string[]>;
  Object.entries(serverErrors).forEach(([field, messages]) => {
    form.setError(field as keyof FormData, { message: messages[0] });
  });
}
```

---

## Next.js Error Handling

### error.tsx (Route-Level)

```tsx
// app/dashboard/error.tsx
"use client";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => { reportError(error); }, [error]);

  return (
    <div role="alert">
      <h2>Dashboard Error</h2>
      <p>{error.message}</p>
      <Button onClick={reset}>Try Again</Button>
    </div>
  );
}
```

### global-error.tsx (Root — catches layout errors)

```tsx
// app/global-error.tsx
"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <html><body>
      <h1>Something went wrong</h1>
      <button onClick={reset}>Try Again</button>
    </body></html>
  );
}
```

### not-found.tsx

```tsx
// app/not-found.tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <div>
      <h1>404 — Page Not Found</h1>
      <Link href="/">Go Home</Link>
    </div>
  );
}
```

---

## Error Tracking

### Log Errors, Don't Expose Them

```tsx
// ✅ User sees friendly message
<p>Something went wrong. Please try again.</p>

// ✅ Developer sees full error
console.error("[Dashboard]", error);
reportError(error);

// ❌ Never expose stack traces or internal details to users
<p>{error.stack}</p>
```

### Error Reporting Function

```typescript
// src/lib/error-reporting.ts
export function reportError(error: unknown, context?: Record<string, unknown>) {
  const errorObj = error instanceof Error ? error : new Error(String(error));

  // In production: send to Sentry, DataDog, etc.
  if (process.env.NODE_ENV === "production") {
    // Sentry.captureException(errorObj, { extra: context });
  }

  console.error("[Error]", errorObj, context);
}
```

---

## Decision Matrix

| Error Type | Where to Catch | User Feedback |
|-----------|---------------|---------------|
| Render error | ErrorBoundary | Fallback component |
| API error (query) | `useQuery` error state or ErrorBoundary | Inline error or fallback |
| API error (mutation) | `onError` callback | Toast + inline |
| Form validation | react-hook-form | Inline per field |
| 404 | Next.js `not-found.tsx` | Custom 404 page |
| Unhandled | Root ErrorBoundary / `global-error.tsx` | "Something went wrong" |
