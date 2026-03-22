# 10 — TypeScript & Type Safety Checklist

## 10.1 Strict Mode Compliance

- [ ] **strict: true enabled in tsconfig.json** — the TypeScript compiler runs with all strict checks enabled, including strictNullChecks, strictFunctionTypes, and strictPropertyInitialization
- [ ] **No @ts-ignore without documented justification** — every @ts-ignore comment includes an adjacent explanation of why the suppression is necessary and what would be needed to remove it
- [ ] **No @ts-expect-error without documented justification** — every @ts-expect-error includes a comment explaining the type system limitation or third-party issue that necessitates it
- [ ] **No as any type assertions anywhere in source code** — type assertions use specific types (as User, as HTMLInputElement), never as any which defeats the purpose of type checking
- [ ] **noEmit: true set** — the TypeScript compiler is used only for type checking; the bundler (Next.js / SWC) handles the actual JavaScript output
- [ ] **strictNullChecks active via strict** — null and undefined are not assignable to other types without explicit handling, catching potential null reference errors at compile time
- [ ] **No // eslint-disable for type-related rules** — TypeScript-related ESLint rules (@typescript-eslint/*) are not suppressed without documented justification

## 10.2 Type vs Interface Conventions

- [ ] **interface used for object shapes** — component props, API response objects, and data models are defined with the interface keyword for consistency and readability
- [ ] **type used for unions, intersections, and generic constraints** — string literal unions, intersection types, and types that need to satisfy Record<string, T> constraints use the type keyword
- [ ] **No enum keyword** — instead of TypeScript enums, the codebase uses string literal unions ("pending" | "active" | "removed") or as const objects for similar functionality
- [ ] **Consistent pattern across the entire codebase** — the interface-vs-type decision follows the same rule everywhere, not varying by developer preference or feature module
- [ ] **type used when extending Record<string, T> constraint** — since interface doesn't satisfy Record<string, boolean> in generic constraints (like WithPermissions), type alias is used instead
- [ ] **Discriminated unions use type with literal members** — union types that switch on a discriminant field (status: "loading" | "error" | "success") are defined with type, not interface

## 10.3 API Contract Types

- [ ] **Types in types/ match backend serializer output exactly** — every field name, nesting level, and optionality in the TypeScript type mirrors the corresponding Django REST Framework serializer
- [ ] **Field names use snake_case matching backend convention** — the frontend does not transform snake_case to camelCase; API types use snake_case throughout for a direct 1:1 mapping
- [ ] **PaginatedResponse<T> type matches backend pagination shape** — {count: number, next: string | null, previous: string | null, results: T[]} matches DRF's standard pagination output
- [ ] **ApiErrorResponse type matches backend error format** — the error response type includes status, message, code, and details fields matching the backend's exception handler output
- [ ] **AuthTokens type matches JWT response shape** — the type includes access, refresh (when applicable), and user fields matching the backend's token endpoint response
- [ ] **No any or unknown in API response types** — every field in every API response type has a specific type; no any or unknown is used as a placeholder for fields not yet typed
- [ ] **Types updated when backend API changes** — when a backend serializer adds, removes, or renames a field, the corresponding frontend type is updated in the same development cycle

## 10.4 Component Prop Types

- [ ] **Every component has an explicit props interface** — props are defined as a named interface (interface UserCardProps) rather than inline object types in the function signature
- [ ] **Props use children: React.ReactNode for slot components** — components that accept children content type the children prop as React.ReactNode, not React.ReactElement or JSX.Element
- [ ] **Event handlers typed correctly** — onChange uses React.ChangeEvent<HTMLInputElement>, onClick uses React.MouseEvent<HTMLButtonElement>, and other handlers match their element types
- [ ] **Optional props use ? syntax** — optional props are marked with ? (name?: string) rather than name: string | undefined, for cleaner call sites
- [ ] **Required props have no default values in destructuring** — props that are required in the interface do not have fallback defaults in the destructuring pattern, which would mask missing-prop errors
- [ ] **Callback props use descriptive names** — event callback props are named with the on prefix and describe the action (onSubmit, onChange, onDelete, onMemberRemoved)
- [ ] **Spread props typed with ComponentProps or HTMLAttributes** — components that forward props to HTML elements type the rest props with React.ComponentProps<"div"> or React.HTMLAttributes<HTMLDivElement>

## 10.5 Generic Types

- [ ] **WithPermissions<TPerms extends Record<string, boolean>> is generic over permission shapes** — each resource defines its own permission type, composed with WithPermissions for type-safe permission access
- [ ] **PaginatedResponse<T> generic over result type** — the paginated response wrapper is parameterized so PaginatedResponse<User> and PaginatedResponse<Business> are distinct types
- [ ] **Query key factories use as const for tuple type inference** — query key arrays are typed as const tuples, enabling TanStack Query to infer exact key shapes for cache operations
- [ ] **Hook factories are generic where reuse is needed** — shared hooks that operate on different data types accept generic parameters rather than using any or duplicating hook logic
- [ ] **No unnecessary generic constraints** — generic types do not over-constrain their parameters; constraints are only added when the generic body actually requires specific properties
- [ ] **Generic type parameters have descriptive names** — TData, TError, TPerms, TFormValues are used instead of single-letter T, U, V when the meaning is not obvious from context

## 10.6 Import Typing

- [ ] **type keyword used for type-only imports** — imports that bring in only types use import type { User } from "@/types" to ensure they are erased at compile time
- [ ] **Enforced by @typescript-eslint/consistent-type-imports ESLint rule** — the linter flags any type-only import that is missing the type keyword, preventing accidental runtime imports
- [ ] **No runtime imports of type-only symbols** — interfaces, type aliases, and other compile-time-only constructs are never imported without the type keyword
- [ ] **Type re-exports use export type** — barrel files that re-export types from other modules use export type { X } from "./module" to keep them as type-only
- [ ] **Barrel exports in types/index.ts use export type where appropriate** — the types directory's index file distinguishes between runtime exports (enums, const objects) and type-only exports

## 10.7 Discriminated Unions

- [ ] **ApiErrorCode uses string literal union** — error codes like "validation_error" | "not_found" | "permission_denied" are typed as a union of string literals, not plain string
- [ ] **Status types use discriminated unions** — transaction status, membership status, and other state fields are typed as literal unions ("pending" | "active" | "removed") enabling type narrowing
- [ ] **is_limited: true literal type enables type narrowing** — UserLimited has is_limited: true as a literal type, allowing TypeScript to narrow between full User and UserLimited in conditionals
- [ ] **Error types distinguish validation vs auth vs network errors** — the error type hierarchy uses discriminants to enable pattern matching on error kind without runtime type checking
- [ ] **State machine states use discriminated unions** — component states like { status: "loading" } | { status: "error"; error: ApiError } | { status: "success"; data: T } enable exhaustive handling
- [ ] **Switch/if exhaustiveness checking via never** — default cases in switch statements on discriminated unions assign to a never variable, catching unhandled union members at compile time

## 10.8 Null Safety

- [ ] **strictNullChecks enabled via strict: true** — null and undefined are distinct types that must be explicitly handled, not silently assignable to any variable
- [ ] **Optional chaining used for potentially null/undefined values** — user?.name, data?.results, and similar patterns safely access nested properties without throwing on null
- [ ] **Nullish coalescing preferred over logical OR for defaults** — value ?? "default" is used instead of value || "default" to avoid treating empty string, 0, or false as missing
- [ ] **No non-null assertions without documented justification** — the ! postfix operator (user!.name) is not used unless accompanied by a comment explaining why the value is guaranteed non-null
- [ ] **API responses with nullable fields typed correctly** — fields that can be null in the backend response are typed as string | null, not string or string | undefined
- [ ] **undefined vs null used consistently** — undefined represents optional/missing values (optional props, unset fields), null represents explicit absence (nullable API fields, cleared values)

## 10.9 Third-Party Type Coverage

- [ ] **@types/react, @types/react-dom, and @types/node are installed** — the core React and Node.js type packages are present in devDependencies for full type coverage
- [ ] **All dependencies have types** — every npm package used in the project either ships built-in types or has a corresponding @types/ package installed
- [ ] **No untyped third-party API usage** — no library is used in a way that produces implicit any due to missing type definitions
- [ ] **Type declarations (.d.ts) for any untyped modules** — if a rare dependency lacks types, a local .d.ts file provides at minimum a module declaration with basic type stubs
- [ ] **No ambient module declarations that bypass type checking** — declare module "*" or similar blanket declarations that suppress all type errors for entire modules are not used

## 10.10 Type Testing & CI

- [ ] **npm run typecheck (tsc --noEmit) available and runs in CI** — a dedicated script runs the TypeScript compiler in check-only mode as part of the continuous integration pipeline
- [ ] **Type errors fail the build** — type errors from tsc --noEmit cause the CI pipeline to fail, not just warn, preventing type-unsafe code from being merged
- [ ] **No suppression of type errors to pass CI** — type errors are fixed rather than suppressed with @ts-ignore, @ts-expect-error, or by loosening tsconfig strictness
- [ ] **Generic types tested implicitly through usage** — generic types like WithPermissions<T> and PaginatedResponse<T> are exercised across multiple concrete types in the codebase, ensuring they compose correctly
- [ ] **Typecheck runs independently from build** — tsc --noEmit can be run separately from next build, allowing fast type checking during development without a full production build
