# 10 — TypeScript & Type Safety Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 10.1 Strict Mode Compliance

| ID | Rule | Verdict |
|----|------|---------|
| 10.1.1 | FAIL if strict: true is not set in tsconfig.json | PASS/FAIL |
| 10.1.2 | FAIL if @ts-ignore is used without a documented justification comment | PASS/FAIL |
| 10.1.3 | WARN if @ts-expect-error is used without a documented justification comment | PASS/WARN |
| 10.1.4 | FAIL if as any type assertions exist in source code (tests excluded) | PASS/FAIL |
| 10.1.5 | FAIL if noEmit: true is not set in tsconfig.json | PASS/FAIL |
| 10.1.6 | PASS if strictNullChecks is active via strict: true | PASS/FAIL |
| 10.1.7 | WARN if @typescript-eslint/* rules are disabled without documented justification | PASS/WARN |

## 10.2 Type vs Interface Conventions

| ID | Rule | Verdict |
|----|------|---------|
| 10.2.1 | PASS if interface is used for component props and object shapes | PASS/FAIL |
| 10.2.2 | PASS if type is used for unions, intersections, and generic constraints | PASS/FAIL |
| 10.2.3 | FAIL if TypeScript enum keyword is used instead of string literal unions or as const objects | PASS/FAIL |
| 10.2.4 | WARN if interface vs type usage is inconsistent across the codebase | PASS/WARN |
| 10.2.5 | FAIL if interface is used where Record<string, T> constraint is needed (e.g., WithPermissions) | PASS/FAIL |
| 10.2.6 | PASS if discriminated unions use type with literal members | PASS/FAIL |

## 10.3 API Contract Types

| ID | Rule | Verdict |
|----|------|---------|
| 10.3.1 | FAIL if types in types/ do not match backend serializer field names and structure | PASS/FAIL |
| 10.3.2 | FAIL if API types use camelCase instead of snake_case matching backend convention | PASS/FAIL |
| 10.3.3 | FAIL if PaginatedResponse<T> does not match DRF pagination shape (count, next, previous, results) | PASS/FAIL |
| 10.3.4 | WARN if ApiErrorResponse type does not match backend error format (status, message, code, details) | PASS/WARN |
| 10.3.5 | WARN if AuthTokens type does not match JWT endpoint response shape | PASS/WARN |
| 10.3.6 | FAIL if any or unknown types exist in API response type definitions | PASS/FAIL |
| 10.3.7 | WARN if frontend types are known to be out of sync with backend serializers | PASS/WARN |

## 10.4 Component Prop Types

| ID | Rule | Verdict |
|----|------|---------|
| 10.4.1 | WARN if any component uses inline object types instead of named props interface | PASS/WARN |
| 10.4.2 | PASS if children props are typed as React.ReactNode | PASS/FAIL |
| 10.4.3 | WARN if event handler types do not match their element types (e.g., ChangeEvent<HTMLInputElement>) | PASS/WARN |
| 10.4.4 | PASS if optional props use ? syntax instead of T | undefined | PASS/FAIL |
| 10.4.5 | WARN if required props have default values in destructuring that mask missing-prop errors | PASS/WARN |
| 10.4.6 | PASS if callback props follow onAction naming convention | PASS/FAIL |
| 10.4.7 | WARN if spread props are not typed with ComponentProps or HTMLAttributes | PASS/WARN |

## 10.5 Generic Types

| ID | Rule | Verdict |
|----|------|---------|
| 10.5.1 | PASS if WithPermissions<T> is generic over permission shapes | PASS/FAIL |
| 10.5.2 | PASS if PaginatedResponse<T> is generic over result type | PASS/FAIL |
| 10.5.3 | PASS if query key factories use as const for tuple inference | PASS/FAIL |
| 10.5.4 | WARN if shared hooks duplicate logic instead of using generics | PASS/WARN |
| 10.5.5 | WARN if generic constraints are unnecessarily restrictive | PASS/WARN |
| 10.5.6 | WARN if generic type parameters use single letters (T, U) where descriptive names would be clearer | PASS/WARN |

## 10.6 Import Typing

| ID | Rule | Verdict |
|----|------|---------|
| 10.6.1 | WARN if type-only imports do not use import type { } syntax | PASS/WARN |
| 10.6.2 | WARN if @typescript-eslint/consistent-type-imports rule is not enforced | PASS/WARN |
| 10.6.3 | FAIL if type-only symbols are imported without the type keyword causing runtime imports | PASS/FAIL |
| 10.6.4 | WARN if barrel files do not use export type for type-only re-exports | PASS/WARN |
| 10.6.5 | WARN if types/index.ts does not distinguish runtime vs type-only exports | PASS/WARN |

## 10.7 Discriminated Unions

| ID | Rule | Verdict |
|----|------|---------|
| 10.7.1 | WARN if error codes are typed as plain string instead of string literal union | PASS/WARN |
| 10.7.2 | PASS if status fields use literal union types enabling type narrowing | PASS/FAIL |
| 10.7.3 | PASS if is_limited: true literal type enables narrowing between User and UserLimited | PASS/FAIL |
| 10.7.4 | WARN if error types do not distinguish validation vs auth vs network errors via discriminants | PASS/WARN |
| 10.7.5 | INFO if component states do not use discriminated unions (acceptable if using TQ states) | PASS/INFO |
| 10.7.6 | INFO if switch exhaustiveness checking via never is not implemented | PASS/INFO |

## 10.8 Null Safety

| ID | Rule | Verdict |
|----|------|---------|
| 10.8.1 | PASS if strictNullChecks is active via strict: true (same as 10.1.6) | PASS/FAIL |
| 10.8.2 | PASS if optional chaining (?.) is used for potentially null/undefined values | PASS/FAIL |
| 10.8.3 | WARN if logical OR (||) is used instead of nullish coalescing (??) for defaults | PASS/WARN |
| 10.8.4 | FAIL if non-null assertions (!) are used without documented justification | PASS/FAIL |
| 10.8.5 | FAIL if nullable API fields are typed as non-nullable (string instead of string | null) | PASS/FAIL |
| 10.8.6 | WARN if undefined and null usage is inconsistent (mixing optional props vs nullable fields) | PASS/WARN |

## 10.9 Third-Party Type Coverage

| ID | Rule | Verdict |
|----|------|---------|
| 10.9.1 | FAIL if @types/react, @types/react-dom, or @types/node are not installed | PASS/FAIL |
| 10.9.2 | WARN if any dependency lacks type definitions (no built-in types or @types/ package) | PASS/WARN |
| 10.9.3 | FAIL if untyped third-party usage produces implicit any | PASS/FAIL |
| 10.9.4 | WARN if .d.ts declarations are missing for untyped modules | PASS/WARN |
| 10.9.5 | FAIL if ambient module declarations (declare module "*") bypass type checking globally | PASS/FAIL |

## 10.10 Type Testing & CI

| ID | Rule | Verdict |
|----|------|---------|
| 10.10.1 | FAIL if npm run typecheck (tsc --noEmit) is not available | PASS/FAIL |
| 10.10.2 | FAIL if type errors do not fail the CI build | PASS/FAIL |
| 10.10.3 | WARN if type errors are suppressed to pass CI rather than fixed | PASS/WARN |
| 10.10.4 | PASS if generic types are exercised across multiple concrete types in the codebase | PASS/FAIL |
| 10.10.5 | PASS if tsc --noEmit can run independently from next build | PASS/FAIL |
