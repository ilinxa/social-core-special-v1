# TypeScript Conventions

## Table of Contents
1. [Compiler Configuration](#compiler-configuration)
2. [Type Declarations](#type-declarations)
3. [Naming](#naming)
4. [Path Aliases](#path-aliases)
5. [Type Organization](#type-organization)
6. [Generics](#generics)
7. [Null Handling](#null-handling)
8. [React-Specific Patterns](#react-specific-patterns)

---

## Compiler Configuration

### Base tsconfig.json (React SPA / Vite)

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "esModuleInterop": true,
    "isolatedModules": true,
    "noEmit": true,
    "sourceMap": true,
    "resolveJsonModule": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "lib": ["DOM", "DOM.Iterable", "ESNext"]
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist", "build", ".next", "coverage"]
}
```

### Next.js Overrides

Key differences from base:
- `"jsx": "preserve"` — Next.js/SWC handles JSX transformation
- `"allowJs": true` — for config files
- `"incremental": true` — faster rebuilds
- `"plugins": [{ "name": "next" }]` — route type-checking
- `"include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"]`

---

## Type Declarations

**Interface-first.** Use `interface` for object shapes. Use `type` for unions, intersections, utilities, function signatures, tuples, mapped/conditional types.

```typescript
// ✅ interface for objects
interface User {
  id: string;
  name: string;
  role: UserRole;
}

// ✅ type for unions and utilities
type UserRole = "admin" | "editor" | "viewer";
type ApiResponse<T> = { data: T; error: string | null; status: number };
type Nullable<T> = T | null;

// ✅ extending
interface AdminUser extends User {
  permissions: string[];
}
```

**No enums.** Union types are simpler, lighter, tree-shake better:

```typescript
// ✅
type Status = "idle" | "loading" | "success" | "error";

// ✅ If you need runtime iteration
const STATUSES = ["idle", "loading", "success", "error"] as const;
type Status = (typeof STATUSES)[number];
```

**No `any`.** Use `unknown` and narrow:

```typescript
function processInput(input: unknown): string {
  if (typeof input === "string") return input.toUpperCase();
  if (typeof input === "number") return String(input);
  throw new Error("Unexpected input type");
}

// Catch blocks
try { await fetchData(); }
catch (error: unknown) {
  const message = error instanceof Error ? error.message : "Unknown error";
}
```

---

## Naming

| What | Convention | Example |
|------|-----------|---------|
| Interface | PascalCase noun | `UserProfile`, `ButtonProps` |
| Type alias | PascalCase | `UserRole`, `ApiResponse<T>` |
| Props | ComponentName + `Props` | `ButtonProps`, `UserCardProps` |
| Store state | StoreName + `State` | `AuthState`, `CartState` |
| Store actions | StoreName + `Actions` | `AuthActions` |
| API response | Entity + `Response` | `UserResponse` |
| API request | Entity + `Request` | `CreateUserRequest` |
| Generic params | Single uppercase or `T` prefix | `T`, `TData`, `TError` |

No `I` prefix (`IUser`), no `T` prefix on type aliases (`TUserRole`).

---

## Path Aliases

Single `@/` alias → `src/`. No multiple aliases.

```typescript
// ✅
import { Button } from "@/components/ui/Button";
// ❌
import { Button } from "../../../../components/ui/Button";
// ❌ multiple aliases
import { Button } from "@components/ui/Button";
```

Vite config:
```typescript
export default defineConfig({
  resolve: { alias: { "@": resolve(__dirname, "./src") } },
});
```

Next.js: reads `tsconfig.json` paths automatically.

---

## Type Organization

**Level 1 — Same file:** Types used only in that file, at top before component.
**Level 2 — Feature `types.ts`:** Types shared within a feature folder.
**Level 3 — `src/types/`:** Types shared across features, organized by domain.

```typescript
// ✅ import directly from source
import type { User } from "@/types/user";
import type { AuthState } from "@/features/auth/types";

// ❌ barrel re-export
import type { User } from "@/types"; // from index.ts
```

Always use `import type` for type-only imports. For mixed: `import { formatDate, type DateFormat } from "@/utils/date";`

---

## Generics

```typescript
// Simple
function identity<T>(value: T): T { return value; }

// Multiple — prefixed
interface ApiResponse<TData, TError = Error> {
  data: TData | null;
  error: TError | null;
}

// Constrained
function findById<T extends { id: string }>(items: T[], id: string): T | undefined {
  return items.find((item) => item.id === id);
}
```

---

## Null Handling

- Explicit `null` for intentional absence. `undefined` = "not set" naturally.
- Optional (`?`) for genuinely optional params.
- Always narrow before use. Never use non-null assertion (`!`) without documented reason.

```typescript
interface UserProfile {
  name: string;
  bio: string | null;     // intentionally empty
  avatar: string | null;  // no upload
}

interface SearchParams {
  query: string;
  page?: number;  // defaults to 1
}

// ✅ guard + optional chaining + nullish coalescing
const city = user?.address?.city ?? "Unknown";

// ❌ non-null assertion
const name = user!.name;
```

---

## React-Specific Patterns

```typescript
// ✅ Component typing — direct, no React.FC
interface GreetingProps {
  name: string;
  greeting?: string;
}
export function Greeting({ name, greeting = "Hello" }: GreetingProps) {
  return <p>{greeting}, {name}!</p>;
}

// ✅ Children
interface LayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
}

// ✅ Extending HTML attributes
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

// ✅ Event handlers
function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
  setValue(event.target.value);
}

// ✅ Hook return — let TS infer unless complex
function useToggle(initial = false) {
  const [value, setValue] = useState(initial);
  const toggle = useCallback(() => setValue((v) => !v), []);
  return [value, toggle] as const;
}

// ✅ Complex hook — explicit return type
interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}
function useAuth(): UseAuthReturn { ... }
```

### Utility Types

```typescript
type Nullable<T> = T | null;
type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;
type StrictOmit<T, K extends keyof T> = Omit<T, K>;
```
