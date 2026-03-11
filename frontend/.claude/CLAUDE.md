# Frontend — Next.js Web Client

## Tech Stack

- **Framework:** Next.js 16 (App Router) + React 19
- **Language:** TypeScript 5 (strict mode)
- **Styling:** Tailwind CSS v4 (CSS-first) + shadcn/ui (new-york, OKLCH)
- **Client State:** Zustand 5 (devtools, persist, immer middleware)
- **Server State:** TanStack Query v5
- **Forms:** react-hook-form + Zod
- **HTTP Client:** Axios (with JWT interceptors)
- **Icons:** lucide-react
- **Theming:** next-themes (dark/light/system)
- **Toast:** sonner
- **Testing:** Vitest + React Testing Library + MSW
- **Linting:** ESLint flat config + Prettier + tailwindcss plugin
- **Pre-commit:** Husky + lint-staged

## Commands

- `npm run dev` — Development server (localhost:3000)
- `npm run build` — Production build
- `npm run lint` — ESLint check
- `npm run typecheck` — TypeScript strict check
- `npm run test` — Run tests (Vitest)
- `npm run format` — Format code (Prettier)
- `npm run format:check` — Check formatting

## Skills Mandates

- IMPORTANT: Use `ilinxa-frontend-standards` skill for all frontend code.

## Architecture

- `src/app/` — Routes only. Pages are thin wrappers (<30 lines), import from `features/`.
- `src/features/` — Feature modules (components, hooks, api, actions, types).
- `src/components/ui/` — shadcn/ui primitives (auto-generated). `src/components/common/` — composed shared components.
- `src/lib/` — Utilities: `api-client.ts` (Axios + JWT), `query-client.ts`, `query-keys.ts`, `utils.ts` (cn helper).
- `src/stores/` — Zustand stores (client state only, never fetch).
- `src/types/` — Shared types matching backend API contracts.
- `src/styles/globals.css` — Tailwind v4 CSS-first theme (OKLCH colors).
- `src/test/` — Test setup and utilities.

## Key Conventions

- Named exports only (except Next.js page/layout/error files).
- Named function declarations for components: `export function UserCard() {}`.
- `interface` for object shapes, `type` for unions. No `enum`, no `any`.
- Import order: React → third-party → @/ aliases → relative → type-only → side-effects.
- Server components by default. Push `"use client"` down to narrowest boundary.
- Access tokens in memory only (never localStorage). Refresh tokens in HttpOnly cookies.

## Backend API

- Base URL: `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)
- API proxy configured in `next.config.ts`: `/api/:path*` → backend
- Auth: JWT (15min access, 7day refresh), `Authorization: Bearer <token>`
- Error format: `{ error: { message, code, details } }`
- Pagination: `{ count, next, previous, results }`
