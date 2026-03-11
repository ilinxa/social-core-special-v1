# Tailwind & shadcn Version Guide

## Table of Contents
1. [Compatibility Matrix](#compatibility-matrix)
2. [Key Differences](#key-differences)
3. [Migration v3 → v4](#migration-v3--v4)
4. [New Project Setup](#new-project-setup)
5. [Troubleshooting](#troubleshooting)

---

## Compatibility Matrix

| Component | v3 Stack | v4 Stack |
|-----------|----------|----------|
| **Tailwind CSS** | 3.4.x | 4.x |
| **React** | 18.x | 19.x |
| **shadcn/ui style** | `default` or `new-york` | `new-york` only |
| **Color format** | HSL (raw channels) | OKLCH (with wrapper) |
| **CSS vars location** | Inside `@layer base {}` | Outside `@layer`, via `@theme inline` |
| **Radix UI** | Individual `@radix-ui/react-*` | Unified `radix-ui` |
| **Ref handling** | `React.forwardRef` | `ref` as prop (React 19) |
| **Animation** | `tailwindcss-animate` | `tw-animate-css` |
| **Config** | `tailwind.config.ts` (JS) | CSS-first (`@theme`, `@import`) |
| **Content** | Manual `content` array | Automatic detection |
| **Build** | PostCSS plugin + autoprefixer | `@tailwindcss/vite` or `@tailwindcss/postcss` |
| **Container queries** | Plugin required | Built-in |
| **Dark mode** | `darkMode: "class"` in config | `@custom-variant dark (&:is(.dark *))` |

**Rule:** Never mix v3 and v4 in the same project.

---

## Key Differences

### Color Format (HSL → OKLCH) — #1 migration issue

```css
/* v3: raw HSL channels, Tailwind wraps with hsl() */
--primary: 222.2 47.4% 11.2%;

/* v4: complete oklch() value, used directly */
--primary: oklch(0.205 0 0);
```

Using v3 values in v4 or vice versa breaks colors silently.

### Config Approach

```typescript
// v3: tailwind.config.ts
export default { content: ["./src/**/*.{ts,tsx}"], darkMode: "class", theme: { extend: {} }, plugins: [require("tailwindcss-animate")] };
```
```css
/* v4: globals.css */
@import "tailwindcss";
@import "tw-animate-css";
@custom-variant dark (&:is(.dark *));
@theme { --color-brand: #3b82f6; }
```

### Radix UI: `@radix-ui/react-dialog` (v3) → `import { Dialog } from "radix-ui"` (v4)
### Refs: `React.forwardRef` (v3) → `ref` as prop (v4/React 19)
### Renamed utilities: `tailwindcss-animate` → `tw-animate-css`, `ring-offset-*` → `ring-offset:*`

---

## Migration v3 → v4

### Pre-checks
- [ ] All deps updated to latest v3 (Tailwind 3.4.x)
- [ ] No custom PostCSS plugins that conflict
- [ ] Git clean state with passing tests

### Tailwind Migration Steps
1. `npm install tailwindcss@latest @tailwindcss/vite` (Vite) or `@tailwindcss/postcss` (Next.js)
2. Remove `autoprefixer` from PostCSS
3. Replace `@tailwind base/components/utilities` with `@import "tailwindcss";`
4. Move `tailwind.config.ts` → `@theme` block in CSS. Use `@theme inline` for CSS variable-backed values
5. Move `darkMode: "class"` → `@custom-variant dark (&:is(.dark *));`
6. Replace `tailwindcss-animate` → `tw-animate-css`
7. Convert HSL variables → OKLCH: change raw channels to `oklch()` wrapper values
8. Remove `hsl(var(--...))` from color config — use `var(--...)` directly
9. Update Vite config to use `@tailwindcss/vite` plugin (or PostCSS for Next.js)
10. Remove `content` array (v4 auto-detects)

### shadcn Migration Steps
1. `npx shadcn@latest init` — select new-york style
2. Regenerate all components: `npx shadcn@latest add --all --overwrite`
3. Re-apply custom variants/modifications (check git diff)
4. Replace individual `@radix-ui/react-*` → unified `radix-ui`
5. Replace `React.forwardRef` → direct `ref` prop (React 19)
6. Update `components.json` to v4 settings
7. Test every component visually

---

## New Project Setup

### v4 Stack (Recommended)
```bash
npx create-next-app@latest --ts --tailwind --eslint --app --src-dir
npx shadcn@latest init  # choose new-york, oklch
```

### v3 Stack (Legacy Only)
```bash
npx create-next-app@latest --ts --tailwind --eslint --app --src-dir
npx shadcn@latest init  # choose new-york, hsl
```

---

## Troubleshooting

- **Colors invisible/wrong:** Version mismatch between HSL and OKLCH variables. Check CSS variable format.
- **`@apply` not working (v4):** Must come after `@import "tailwindcss"`. Can't use in files not processed by Tailwind.
- **Radix import errors:** Mismatch between individual (`@radix-ui/react-*`) and unified (`radix-ui`). Pick one for the whole project.
- **Animation not working:** Wrong library (`tailwindcss-animate` vs `tw-animate-css`).
- **Border default color changed (v4):** v4 borders default to `currentColor` instead of `border-gray-200`. Fix: add `--color-border` to theme or override `border` base.
