# Tailwind Conventions

## Table of Contents
1. [Core Principles](#core-principles)
2. [Class Ordering](#class-ordering)
3. [cn() Utility](#cn-utility)
4. [Theme Configuration](#theme-configuration)
5. [shadcn CSS Variables](#shadcn-css-variables)
6. [Responsive Design](#responsive-design)
7. [Dark Mode](#dark-mode)
8. [Common Patterns](#common-patterns)
9. [What to Avoid](#what-to-avoid)

---

## Core Principles

**Utility-first, component-extracted.** Write utilities inline in JSX. When a set of utilities repeats across multiple files, extract a React component — not a CSS class.

```tsx
// ✅ Reuse via component
function Badge({ children, variant = "default" }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }))}>{children}</span>;
}

// ❌ @apply CSS class
.badge { @apply px-2 py-1 rounded-full text-sm; }
```

`@apply` only for: base element resets, animation keyframes, third-party library overrides.

---

## Class Ordering

Automated with Prettier plugin `prettier-plugin-tailwindcss`. Add to `.prettierrc`:

```json
{ "plugins": ["prettier-plugin-tailwindcss"], "tailwindFunctions": ["cn", "cva"] }
```

Sort order: layout → box model → typography → visual → interactive → modifiers.

VS Code IntelliSense — add to `.vscode/settings.json`:
```json
{
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"],
    ["cn\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ]
}
```

---

## cn() Utility

Always use `cn()` for conditional/merged classes:

```typescript
// src/lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

```tsx
<div className={cn(
  "rounded-lg border p-4",
  isActive && "border-primary bg-primary/10",
  isDisabled && "opacity-50 pointer-events-none",
  className, // allow override from props
)} />
```

---

## Theme Configuration

### Tailwind v4 (CSS-First)

```css
/* src/styles/globals.css */
@import "tailwindcss";

@theme inline {
  --color-brand: oklch(0.65 0.15 250);
  --color-surface: oklch(0.98 0 0);
  --radius-DEFAULT: 0.5rem;
  --font-sans: "Inter", sans-serif;
}
```

### Tailwind v3 (JavaScript Config)

```typescript
// tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { brand: "hsl(var(--brand))" },
      fontFamily: { sans: ["Inter", "sans-serif"] },
      borderRadius: { DEFAULT: "0.5rem" },
    },
  },
  plugins: [],
} satisfies Config;
```

### Theme Rules
- All custom values go through the theme — never hardcode hex/oklch in JSX.
- Use CSS variables for values that change between themes (light/dark).
- Prefix custom colors: `brand-*`, `surface-*`.
- Keep custom theme small. Use default Tailwind scale where possible.

---

## shadcn CSS Variables

### v3 + shadcn (HSL Format)

```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    /* ... */
  }
  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    /* ... */
  }
}
```

Used in config: `colors: { background: "hsl(var(--background))" }`

### v4 + shadcn (OKLCH Format)

```css
@import "tailwindcss";
@plugin "tw-animate-css";

@custom-variant dark (&:is(.dark *));

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0.02 250);
  --primary: oklch(0.205 0.03 265);
  --primary-foreground: oklch(0.93 0 0);
  /* ... */
}

.dark {
  --background: oklch(0.145 0.02 250);
  --foreground: oklch(0.93 0 0);
  /* ... */
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  /* ... */
}
```

---

## Responsive Design

**Mobile-first.** Base styles are mobile, scale up:

```tsx
<div className="p-4 md:p-6 lg:p-8">
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
```

Breakpoints: `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`, `2xl: 1536px`.

Container queries (v4): `@container` for component-level responsiveness.

---

## Dark Mode

```tsx
// next-themes for Next.js, or manual class-based
<html className="dark">
```

Use semantic colors (`bg-background`, `text-foreground`) not hardcoded (`bg-white`, `text-black`). shadcn CSS variables handle light/dark automatically.

---

## Common Patterns

```tsx
// Conditional classes
<button className={cn("base", variant === "primary" && "bg-primary text-primary-foreground")} />

// Long class strings — break into multiple lines, one concern per line
<div className={cn(
  "flex items-center gap-2",          // layout
  "rounded-lg border px-4 py-2",      // box model
  "text-sm font-medium",              // typography
  "bg-card text-card-foreground",     // colors
  "hover:bg-accent transition-colors", // interactive
)} />
```

---

## What to Avoid

- ❌ `@apply` for component styles (extract React component instead)
- ❌ Hardcoded colors: `text-[#1a1a2e]` (use theme tokens)
- ❌ Inline arbitrary values when a theme token exists: `p-[17px]` vs `p-4`
- ❌ Complex conditional logic in className (extract to a function or CVA variant)
- ❌ Custom CSS files for what Tailwind can handle

### Build Setup

**Tailwind v4:** `@tailwindcss/vite` plugin (Vite) or `@tailwindcss/postcss` (Next.js). No `autoprefixer` needed.

**Tailwind v3:** `tailwindcss` PostCSS plugin + `autoprefixer`.
