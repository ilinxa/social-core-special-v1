# 02 — Configuration & Environment Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 2.1 Next.js Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.1.1 | FAIL if `output: "standalone"` is not configured in next.config.ts | PASS/FAIL |
| 2.1.2 | WARN if `reactCompiler: true` is not enabled (React 19 auto-memoization) | PASS/WARN |
| 2.1.3 | WARN if legacy path redirects are missing or have incorrect patterns | PASS/WARN |
| 2.1.4 | WARN if media proxy rewrite is missing or exposes backend origin to client | PASS/WARN |
| 2.1.5 | FAIL if no security headers configured in headers() function | PASS/FAIL |
| 2.1.6 | FAIL if deprecated config options present (experimental.appDir, webpack5, serverActions) | PASS/FAIL |
| 2.1.7 | FAIL if custom webpack config interferes with RSC bundling or tree-shaking | PASS/FAIL |
| 2.1.8 | WARN if turbopack-incompatible plugins or loaders are configured | PASS/WARN |

## 2.2 TypeScript Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.2.1 | FAIL if `strict: true` is not enabled in tsconfig.json | PASS/FAIL |
| 2.2.2 | FAIL if `@/` path alias does not map to `./src/*` in compilerOptions.paths | PASS/FAIL |
| 2.2.3 | WARN if moduleResolution is not "bundler" (modern strategy for Next.js) | PASS/WARN |
| 2.2.4 | WARN if jsx is not "preserve" (Next.js handles JSX transformation) | PASS/WARN |
| 2.2.5 | WARN if target is older than ES2017 | PASS/WARN |
| 2.2.6 | FAIL if noEmit is not true (TypeScript should type-check only, SWC compiles) | PASS/FAIL |
| 2.2.7 | INFO if incremental is not enabled for faster type-checking | PASS/INFO |

## 2.3 Environment Variables

| ID | Rule | Verdict |
|----|------|---------|
| 2.3.1 | WARN if more than 2 NEXT_PUBLIC_ variables are exposed to the client bundle | PASS/WARN |
| 2.3.2 | FAIL if any secret (API key, DB URL, auth secret) uses NEXT_PUBLIC_ prefix | PASS/FAIL |
| 2.3.3 | FAIL if .env.example is missing or doesn't document all used environment variables | PASS/FAIL |
| 2.3.4 | FAIL if fallback values in code point to production endpoints instead of localhost | PASS/FAIL |
| 2.3.5 | FAIL if server-only env vars are accessed in "use client" files | PASS/FAIL |
| 2.3.6 | FAIL if hardcoded API URLs exist outside api-client.ts configuration | PASS/FAIL |
| 2.3.7 | FAIL if .env or .env.local files are committed to version control | PASS/FAIL |

## 2.4 Tailwind CSS v4 Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.4.1 | FAIL if Tailwind is configured via JavaScript/TypeScript config file instead of CSS-first @import | PASS/FAIL |
| 2.4.2 | FAIL if no @theme block defines custom design tokens in globals.css | PASS/FAIL |
| 2.4.3 | WARN if colors do not use OKLCH format for perceptual uniformity | PASS/WARN |
| 2.4.4 | WARN if dark mode is not configured with @custom-variant for class-based toggling | PASS/WARN |
| 2.4.5 | FAIL if PostCSS uses legacy tailwindcss package instead of @tailwindcss/postcss | PASS/FAIL |
| 2.4.6 | FAIL if legacy tailwind.config.js exists alongside CSS-first configuration | PASS/FAIL |
| 2.4.7 | WARN if tw-animate-css or animation utilities are not available | PASS/WARN |

## 2.5 shadcn/ui Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.5.1 | WARN if components.json style is not "new-york" | PASS/WARN |
| 2.5.2 | WARN if rsc is not set to true in components.json | PASS/WARN |
| 2.5.3 | WARN if color format in components.json does not use OKLCH | PASS/WARN |
| 2.5.4 | FAIL if aliases in components.json do not match tsconfig.json path aliases | PASS/FAIL |
| 2.5.5 | FAIL if shadcn components are installed outside components/ui/ directory | PASS/FAIL |
| 2.5.6 | WARN if shadcn primitives in ui/ have been hand-modified instead of composed in common/ | PASS/WARN |

## 2.6 ESLint Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.6.1 | FAIL if using legacy .eslintrc format instead of flat config (eslint.config.mjs) | PASS/FAIL |
| 2.6.2 | FAIL if Next.js recommended rules (core-web-vitals, typescript) are not extended | PASS/FAIL |
| 2.6.3 | FAIL if @typescript-eslint/no-explicit-any is not set to error | PASS/FAIL |
| 2.6.4 | FAIL if no-unused-vars rule is not configured | PASS/FAIL |
| 2.6.5 | WARN if eslint-config-prettier is not configured to avoid formatting conflicts | PASS/WARN |
| 2.6.6 | WARN if no import ordering rule enforces consistent import grouping | PASS/WARN |
| 2.6.7 | FAIL if conflicting rules exist between ESLint plugins | PASS/FAIL |

## 2.7 Vitest Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.7.1 | FAIL if test environment is jsdom instead of happy-dom (documented ESM incompatibility) | PASS/FAIL |
| 2.7.2 | FAIL if setup file does not import @testing-library/jest-dom/vitest | PASS/FAIL |
| 2.7.3 | WARN if coverage provider is not v8 (fastest option) | PASS/WARN |
| 2.7.4 | FAIL if test include pattern does not match src/**/*.test.{ts,tsx} | PASS/FAIL |
| 2.7.5 | FAIL if path aliases in vitest.config.ts do not match tsconfig.json | PASS/FAIL |
| 2.7.6 | WARN if no coverage threshold is configured (should be >=80%) | PASS/WARN |
| 2.7.7 | INFO if globals: true is used — explicit imports are preferred but globals work | PASS/INFO |

## 2.8 Pre-commit & Formatting

| ID | Rule | Verdict |
|----|------|---------|
| 2.8.1 | WARN if Husky is not installed or .husky/ directory is missing | PASS/WARN |
| 2.8.2 | WARN if pre-commit hook does not run lint-staged | PASS/WARN |
| 2.8.3 | WARN if lint-staged does not run both ESLint and Prettier on staged files | PASS/WARN |
| 2.8.4 | WARN if prettier-plugin-tailwindcss is not configured for automatic class sorting | PASS/WARN |
| 2.8.5 | WARN if .prettierrc is not committed with consistent formatting rules | PASS/WARN |
| 2.8.6 | INFO if no format:check script exists for CI | PASS/INFO |

## 2.9 Security Headers

| ID | Rule | Verdict |
|----|------|---------|
| 2.9.1 | FAIL if Content-Security-Policy is not configured or is set to a wildcard | PASS/FAIL |
| 2.9.2 | FAIL if X-Content-Type-Options: nosniff is missing | PASS/FAIL |
| 2.9.3 | FAIL if X-Frame-Options is missing (should be DENY or SAMEORIGIN) | PASS/FAIL |
| 2.9.4 | WARN if X-XSS-Protection is not set to 0 (legacy filter can introduce vulnerabilities) | PASS/WARN |
| 2.9.5 | WARN if Referrer-Policy is missing or set to unsafe value | PASS/WARN |
| 2.9.6 | WARN if Permissions-Policy does not restrict unused browser APIs | PASS/WARN |
| 2.9.7 | FAIL if security headers are not applied via next.config.ts headers() on all routes | PASS/FAIL |

## 2.10 Build & Output Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.10.1 | FAIL if standalone output does not produce self-contained build | PASS/FAIL |
| 2.10.2 | FAIL if fonts are loaded via external CSS links instead of next/font | PASS/FAIL |
| 2.10.3 | WARN if experimental flags are used without documented justification | PASS/WARN |
| 2.10.4 | WARN if next build produces warnings without tracking issues | PASS/WARN |
| 2.10.5 | FAIL if TypeScript errors do not fail the build | PASS/FAIL |
| 2.10.6 | INFO if source maps configuration is not documented | PASS/INFO |
