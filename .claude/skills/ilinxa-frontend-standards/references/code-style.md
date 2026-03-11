# Code Style & Formatting

## Table of Contents
1. [Prettier Configuration](#prettier-configuration)
2. [ESLint Configuration](#eslint-configuration)
3. [Import Organization](#import-organization)
4. [Function & Component Style](#function--component-style)
5. [Commenting Conventions](#commenting-conventions)
6. [General Patterns](#general-patterns)
7. [Package Scripts](#package-scripts)

---

## Prettier Configuration

`.prettierrc`:
```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "jsxSingleQuote": false,
  "bracketSameLine": false,
  "singleAttributePerLine": false
}
```

`.prettierignore`:
```
node_modules/
dist/
build/
.next/
coverage/
pnpm-lock.yaml
package-lock.json
```

`.vscode/settings.json`:
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[typescriptreact]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[json]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[css]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[markdown]": { "editor.defaultFormatter": "esbenp.prettier-vscode" }
}
```

---

## ESLint Configuration

All projects use flat config (`eslint.config.mjs`). No legacy `.eslintrc`.

### React SPA (Vite)

```javascript
import { defineConfig } from "eslint/config";
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import prettier from "eslint-config-prettier/flat";

export default defineConfig(
  { ignores: ["dist/", "node_modules/", "coverage/", "**/*.d.ts"] },
  eslint.configs.recommended,
  {
    files: ["**/*.ts", "**/*.tsx"],
    extends: [tseslint.configs.recommended],
    plugins: { "@typescript-eslint": tseslint.plugin },
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: { ecmaVersion: "latest", sourceType: "module", ecmaFeatures: { jsx: true } },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", {
        argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_",
      }],
      "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports", fixStyle: "inline-type-imports" }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-empty-interface": "off",
      "@typescript-eslint/no-empty-object-type": "off",
    },
  },
  {
    files: ["**/*.tsx", "**/*.jsx"],
    plugins: { react: reactPlugin, "react-hooks": reactHooksPlugin },
    settings: { react: { version: "detect" } },
    rules: {
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "react/jsx-no-target-blank": "error",
      "react/jsx-curly-brace-presence": ["error", { props: "never", children: "never" }],
      "react/self-closing-comp": "error",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  { files: ["**/*.js", "**/*.mjs", "**/*.cjs"], extends: [tseslint.configs.disableTypeChecked] },
  prettier,
);
```

### Next.js

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";

export default defineConfig(
  ...nextVitals,
  ...nextTs,
  {
    files: ["**/*.ts", "**/*.tsx"],
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", {
        argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_",
      }],
      "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports", fixStyle: "inline-type-imports" }],
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  prettier,
);
```

### Dependencies

React SPA: `npm install -D eslint @eslint/js typescript-eslint eslint-plugin-react eslint-plugin-react-hooks eslint-config-prettier prettier`

Next.js: `npm install -D eslint eslint-config-next eslint-config-prettier prettier`

---

## Import Organization

Six groups, separated by blank lines:

```typescript
// 1. React / framework
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// 2. Third-party libraries
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

// 3. Internal @/ aliases
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

// 4. Feature-local / relative
import { UserCard } from "./UserCard";

// 5. Type-only
import type { User } from "@/types/user";

// 6. Side-effects (rare)
import "./styles.css";
```

No ESLint import sorting plugin by default. Manual convention, verified in code review. Add `eslint-plugin-simple-import-sort` if team grows and manual enforcement becomes impractical.

No barrel `index.ts` re-exports. Import directly from source files.

---

## Function & Component Style

| Context | Style |
|---------|-------|
| Components | `export function UserCard() {}` — named function declaration |
| Hooks | `export function useAuth() {}` — named function declaration |
| Inline callbacks | Arrow: `onClick={() => handleClick()}` |
| Utilities | Either named function or arrow, both fine |

**Named exports only.** Exceptions: Next.js `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `next.config.ts`.

Early returns over nested if/else:

```tsx
// ✅
export function UserCard({ user }: UserCardProps) {
  if (!user) return null;
  if (user.isDeactivated) return <DeactivatedBanner />;
  return <Card><h2>{user.name}</h2></Card>;
}
```

---

## Commenting Conventions

- Comments explain **why**, not what.
- Every TODO/FIXME references a ticket: `// TODO(ILX-1234): description`
- JSDoc for public utilities and hooks.
- No commented-out code — git has history.

---

## General Patterns

- `const` by default, `let` only for reassignment, never `var`.
- Template literals over concatenation: `` `Hello, ${name}` ``
- `??` over `||` for defaults (preserves `0` and `""`).
- Ternaries for simple single-expression decisions. Maps/objects for complex lookups.
- No nested ternaries.

---

## Package Scripts

### React SPA (Vite)
```json
{
  "dev": "vite",
  "build": "tsc --noEmit && vite build",
  "lint": "eslint .",
  "lint:fix": "eslint . --fix",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "typecheck": "tsc --noEmit"
}
```

### Next.js
```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint .",
  "lint:fix": "eslint . --fix",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "typecheck": "tsc --noEmit"
}
```

### Pre-commit (Husky + lint-staged)

```bash
npm install -D husky lint-staged && npx husky init
```

`.lintstagedrc`:
```json
{
  "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
  "*.{json,md,css}": ["prettier --write"]
}
```
