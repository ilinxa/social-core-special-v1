---
name: ilinxa-frontend-standards
description: >
  ilinxa frontend coding standards for React SPA (Vite) and Next.js (App Router) projects.
  Covers TypeScript conventions, code style, component architecture, Tailwind/shadcn styling,
  Zustand state, TanStack Query data fetching, server-side fetching, testing, error handling,
  performance, git workflow, CI/CD, and deployment. Use when writing any frontend code, creating
  components, setting up a project, configuring tooling, writing tests, or reviewing code for
  an ilinxa project. Triggers: React, Next.js, Vite, Tailwind, shadcn, Zustand, TanStack Query,
  Vitest, component, hook, store, fetch, deploy, CI/CD, ESLint, Prettier, TypeScript, ilinxa.
---

# ilinxa Frontend Standards

All ilinxa frontend code follows these standards. This file contains the universal rules that apply to every task. Domain-specific details are in `references/` — load only what you need.

## Project Detection

Before writing any code, determine the project type:

| Signal | Project Type |
|--------|-------------|
| `next.config.ts`, `app/` dir with `page.tsx`, `"next"` in package.json | **Next.js (App Router)** |
| `vite.config.ts`, `main.tsx` entry, `"vite"` in package.json | **React SPA (Vite)** |

This affects: tsconfig (`jsx: "preserve"` vs `"react-jsx"`), ESLint config, routing, data fetching, and deployment.

## Task Router — Which References to Load

Read only the references your current task needs:

**Building components / writing JSX:**
→ [references/components.md](references/components.md) + [references/tailwind.md](references/tailwind.md)
→ If using shadcn: also [references/shadcn.md](references/shadcn.md)

**Setting up state management:**
→ [references/zustand.md](references/zustand.md)

**Building data fetching (client-side):**
→ [references/tanstack-query.md](references/tanstack-query.md)

**Building data fetching (Next.js server-side):**
→ [references/server-fetching.md](references/server-fetching.md)

**Writing TypeScript (typing, generics, patterns):**
→ [references/typescript.md](references/typescript.md)

**Configuring tooling (ESLint, Prettier, tsconfig):**
→ [references/code-style.md](references/code-style.md)

**Writing tests:**
→ [references/testing.md](references/testing.md)

**Implementing error handling:**
→ [references/error-handling.md](references/error-handling.md)

**Optimizing performance:**
→ [references/performance.md](references/performance.md)

**Setting up project structure:**
→ React SPA: [references/react-project.md](references/react-project.md)
→ Next.js: [references/nextjs-project.md](references/nextjs-project.md)

**Accessibility:**
→ [references/accessibility.md](references/accessibility.md)

**Git, CI/CD, deployment:**
→ [references/git.md](references/git.md)
→ [references/tooling.md](references/tooling.md)

**Tailwind/shadcn version issues or migration:**
→ [references/version-guide.md](references/version-guide.md)

---

## Universal Rules

These apply to ALL tasks. Never violate these regardless of which domain you're working in.

### TypeScript

- `strict: true` always. No exceptions.
- `interface` for object shapes, `type` for unions/utilities.
- **No `enum`** — use union types: `type Status = "idle" | "loading" | "success" | "error";`
- **No `any`** — use `unknown` and narrow.
- `import type { X }` for type-only imports.
- Path alias: `@/` maps to `src/`. Single alias, no multiples.
- No `I` prefix on interfaces, no `T` prefix on types.
- Props interface: `ComponentNameProps`.

### Code Style

- **Prettier** handles formatting, **ESLint** handles logic. They never overlap.
- Double quotes (`""`), semicolons, 2-space indent, `printWidth: 100`, trailing commas.
- **Named exports only.** No default exports (except Next.js `page.tsx`, `layout.tsx`, `error.tsx`).
- **Named function declarations** for components and hooks: `export function UserCard() {}` not `const UserCard = () => {}`.
- `const` by default. `let` only when reassignment is needed. Never `var`.
- Early returns over nested if/else.
- No barrel `index.ts` re-exports (hurts tree-shaking, IDE perf).

### Import Order

```typescript
// 1. React / framework
import { useState } from "react";

// 2. Third-party
import { useQuery } from "@tanstack/react-query";

// 3. Internal @/ aliases
import { Button } from "@/components/ui/Button";

// 4. Relative / feature-local
import { UserCard } from "./UserCard";

// 5. Type-only
import type { User } from "@/types/user";

// 6. Side-effects (rare)
import "./styles.css";
```

### Components

- Single responsibility. >150 lines or >3 `useState` = split it.
- Three roles: **UI** (presentational), **Container** (data + logic), **Layout** (structure).
- **No `React.FC`** — type props directly in function signature.
- Destructure props in the signature: `function Card({ title, children }: CardProps)`.
- `children: React.ReactNode` for slot content.
- Minimize `useEffect`. If you're syncing state to props, you probably don't need it.
- Derived state: compute, don't store. `const fullName = first + " " + last;` not `useState`.

### Naming

| Thing | Convention | Example |
|-------|-----------|---------|
| Component files | PascalCase | `UserProfile.tsx` |
| Hook files | camelCase, `use` prefix | `useAuth.ts` |
| Utility files | camelCase | `formatDate.ts` |
| Test files | `*.test.tsx` | `UserProfile.test.tsx` |
| Variables | camelCase | `isLoading`, `userName` |
| Constants | UPPER_SNAKE | `MAX_RETRIES`, `API_BASE_URL` |
| Booleans | `is`/`has`/`should`/`can` prefix | `isActive`, `hasPermission` |
| Event handlers | `handle` prefix | `handleClick`, `handleSubmit` |
| Branch names | `type/TICKET-description` | `feat/ILX-1234-user-avatar` |
| Commits | Conventional Commits | `feat(auth): add social login` |

### State Architecture

- **Client state** (UI toggles, filters, form drafts) → **Zustand**
- **Server state** (API data) → **TanStack Query**
- Never mix these. A Zustand store should never call `fetch`.

### Tailwind

- Utility-first. Extract to React components, not CSS classes.
- Use the `cn()` helper for conditional classes: `cn("base", condition && "extra")`.
- Prettier plugin `prettier-plugin-tailwindcss` sorts classes automatically.
- Mobile-first responsive: `base → md: → lg:`.

### Git

- Conventional Commits: `type(scope): subject` — present tense, imperative, ≤72 chars.
- Squash-merge feature branches into `develop`.
- PR = one ticket. Keep PRs under 400 lines.
- Every TODO/FIXME references a ticket: `TODO(ILX-1234)`.

### Accessibility

- WCAG 2.2 Level AA target.
- Semantic HTML first, ARIA second.
- All interactive elements keyboard accessible.
- Visible focus indicators on every focusable element.
- Every input needs a visible `<label>`.
- 4.5:1 contrast ratio for normal text, 3:1 for large text.

---

## Anti-Patterns — NEVER Do This

```tsx
// ❌ enum
enum Status { Active = "active" }
// ✅ union
type Status = "active" | "inactive";

// ❌ any
function parse(data: any) { return data.name; }
// ✅ unknown + narrow
function parse(data: unknown) {
  if (typeof data === "object" && data !== null && "name" in data) {
    return (data as { name: string }).name;
  }
}

// ❌ default export
export default function UserCard() {}
// ✅ named export
export function UserCard() {}

// ❌ const arrow for components
const UserCard = ({ user }: Props) => { ... };
// ✅ named function declaration
export function UserCard({ user }: Props) { ... }

// ❌ React.FC
const Card: React.FC<Props> = ({ title }) => { ... };
// ✅ direct typing
export function Card({ title }: Props) { ... }

// ❌ barrel re-exports
export { Button } from "./Button"; // in index.ts
// ✅ direct imports
import { Button } from "@/components/ui/Button";

// ❌ server state in Zustand
const useStore = create(() => ({
  users: [],
  fetchUsers: async () => { ... } // NO — use TanStack Query
}));

// ❌ useEffect for derived state
const [fullName, setFullName] = useState("");
useEffect(() => { setFullName(first + " " + last); }, [first, last]);
// ✅ just compute it
const fullName = `${first} ${last}`;

// ❌ || for defaults (treats 0 and "" as falsy)
const count = data.total || 10;
// ✅ ?? (only null/undefined)
const count = data.total ?? 10;

// ❌ non-null assertion
const name = user!.name;
// ✅ guard
const name = user?.name ?? "Anonymous";

// ❌ div as button
<div onClick={handleClick}>Click me</div>
// ✅ semantic HTML
<button onClick={handleClick}>Click me</button>
```
