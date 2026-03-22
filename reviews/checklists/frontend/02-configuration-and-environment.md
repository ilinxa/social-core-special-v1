# 02 — Configuration & Environment Checklist

## 2.1 Next.js Configuration

- [ ] **output: "standalone" configured for containerized deployment** — next.config.ts sets output to "standalone" so the build produces a self-contained server without needing node_modules at runtime
- [ ] **reactCompiler: true enabled** — the React Compiler (React 19 feature) is enabled for automatic memoization, reducing manual useMemo/useCallback overhead
- [ ] **Redirects configured for legacy paths** — /dashboard redirects to /home, /business/:slug/* redirects to /bconsole/:slug/*, /platform/:path redirects to /pconsole/:path with proper negative lookahead for exceptions
- [ ] **Rewrites configured for media proxy** — /media/* rewrites to the backend media URL so the frontend serves static media without exposing the backend origin
- [ ] **Security headers configured in headers()** — Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy set on all routes
- [ ] **No deprecated config options** — no experimental.appDir (default in Next.js 16), no deprecated webpack5 flag, no removed serverActions flag
- [ ] **No webpack customizations that break RSC** — any custom webpack config does not interfere with React Server Components bundling or tree-shaking
- [ ] **Turbopack compatibility maintained** — next dev --turbopack works without errors, no plugins or loaders that are turbopack-incompatible

## 2.2 TypeScript Configuration

- [ ] **strict: true enabled** — full strict mode including strictNullChecks, strictFunctionTypes, strictBindCallApply, strictPropertyInitialization, noImplicitAny, noImplicitThis
- [ ] **Path alias @/ maps to ./src/** — configured in compilerOptions.paths so imports use @/components/, @/features/, @/lib/ consistently
- [ ] **moduleResolution set to "bundler"** — uses the modern bundler resolution strategy compatible with Next.js and Vite/Vitest
- [ ] **jsx set to "preserve"** — Next.js handles JSX transformation, TypeScript should not compile it
- [ ] **target is ES2017 or newer** — ensures async/await and modern syntax are preserved for the bundler to handle
- [ ] **noEmit: true configured** — TypeScript is used for type-checking only; Next.js SWC handles compilation
- [ ] **incremental: true for faster builds** — TypeScript caches type-check results in .tsbuildinfo for subsequent runs

## 2.3 Environment Variables

- [ ] **NEXT_PUBLIC_API_URL is the only client-exposed variable** — verified by searching for NEXT_PUBLIC_ prefix in .env files; no secrets or internal URLs exposed to the browser
- [ ] **No secrets prefixed with NEXT_PUBLIC_** — API keys, database URLs, auth secrets never use the NEXT_PUBLIC_ prefix which would embed them in the client bundle
- [ ] **.env.example documents all variables** — every environment variable used in the codebase has a corresponding entry in .env.example with a descriptive comment
- [ ] **Fallback values are localhost not production** — default values in code (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') point to development, never to production endpoints
- [ ] **Server-side variables not leaked to client** — variables without NEXT_PUBLIC_ prefix are only accessed in server components, API routes, or middleware — never in "use client" files
- [ ] **No hardcoded API URLs in source code** — all API endpoint construction goes through the centralized api-client.ts which reads from environment variables
- [ ] **Environment-specific .env files are gitignored** — .env, .env.local, .env.development.local, .env.production.local all in .gitignore; only .env.example is committed

## 2.4 Tailwind CSS v4 Configuration

- [ ] **CSS-first config via globals.css** — Tailwind v4 configured through @import "tailwindcss" in styles/globals.css, not through a JavaScript config file
- [ ] **@theme block defines custom design tokens** — custom colors, spacing, border-radius, font families, and animation tokens declared in the @theme inline block
- [ ] **OKLCH color space used for perceptual uniformity** — all custom color tokens use oklch() format for consistent lightness across hues (e.g. --color-primary: oklch(0.65 0.25 250))
- [ ] **Dark mode uses @custom-variant** — dark mode variant configured with @custom-variant dark (&:is(.dark *)) for class-based toggling
- [ ] **PostCSS uses @tailwindcss/postcss** — postcss.config.mjs uses the Tailwind v4 PostCSS plugin, not the legacy tailwindcss package or autoprefixer (Tailwind v4 includes autoprefixing)
- [ ] **No legacy tailwind.config.js present** — the JavaScript/TypeScript config file from Tailwind v3 is removed; all configuration is CSS-first
- [ ] **tw-animate-css imported for animations** — animation utilities (fade-in, slide-in, etc.) are available via the tw-animate-css package imported in globals.css

## 2.5 shadcn/ui Configuration

- [ ] **components.json specifies new-york style** — the style property is set to "new-york" for the sharper, more structured variant of shadcn components
- [ ] **rsc: true enabled** — React Server Components support is enabled, allowing shadcn components to work in both server and client contexts
- [ ] **Color format uses OKLCH** — the cssVariables and color configuration use OKLCH color space matching the Tailwind v4 theme tokens
- [ ] **Aliases match tsconfig paths** — the aliases in components.json (@/components, @/lib/utils, @/hooks) exactly match the path aliases in tsconfig.json
- [ ] **UI components installed in components/ui/** — all shadcn primitives are in the designated components/ui/ directory as specified in components.json
- [ ] **Components are not hand-modified** — shadcn primitives remain as generated; customization is done through composition in components/common/ or via CVA variants

## 2.6 ESLint Configuration

- [ ] **Flat config in eslint.config.mjs** — uses the modern flat config format (ESLint 9+), not the legacy .eslintrc.json or .eslintrc.js
- [ ] **Extends Next.js recommended rules** — includes next/core-web-vitals and next/typescript rule sets for Next.js-specific linting
- [ ] **TypeScript rules enforced** — @typescript-eslint/no-explicit-any prevents untyped escape hatches, consistent-type-imports enforces import type {} syntax
- [ ] **No unused variables enforced** — no-unused-vars configured to catch dead code, with underscore prefix exception for intentionally unused parameters
- [ ] **Prettier integration configured** — eslint-config-prettier disables formatting rules that conflict with Prettier, no conflicting rule sets between ESLint and Prettier
- [ ] **Import ordering enforced** — import/order or equivalent rule groups imports consistently (React, Next, external, internal @/, relative, styles)
- [ ] **No conflicting rule sets** — no rules that contradict each other (e.g. indent rules from both ESLint and Prettier, or conflicting JSX rules)

## 2.7 Vitest Configuration

- [ ] **environment: happy-dom configured** — NOT jsdom, which has documented incompatibility with ESM packages (@asamuzakjp/css-color -> @csstools/css-calc breaks forks/threads pool in jsdom 27)
- [ ] **Setup file imports jest-dom matchers** — setupFiles points to test/setup.ts which imports @testing-library/jest-dom/vitest for DOM assertion matchers
- [ ] **Coverage provider is v8** — coverage.provider set to "v8" for native V8 coverage instrumentation (faster than istanbul)
- [ ] **Test include pattern is correct** — test.include matches src/**/*.test.{ts,tsx} to find all test files within the source tree
- [ ] **Path aliases match tsconfig** — resolve.alias in vitest.config.ts maps @/ to ./src/ identically to tsconfig.json paths
- [ ] **Coverage threshold is at least 80%** — coverage.thresholds.global or equivalent enforces minimum line/branch/function coverage in CI
- [ ] **globals: false (explicit imports)** — test functions (describe, it, expect, vi) are explicitly imported from vitest, not injected as globals

## 2.8 Pre-commit & Formatting

- [ ] **Husky 9 installed and configured** — .husky/ directory exists with prepare script, Husky initializes on npm install via prepare lifecycle hook
- [ ] **.husky/pre-commit runs lint-staged** — the pre-commit hook file contains npx lint-staged (or equivalent) to check only staged files
- [ ] **lint-staged runs ESLint and Prettier on staged files** — .lintstagedrc or lint-staged config in package.json runs eslint --fix and prettier --write on *.{ts,tsx,js,jsx}
- [ ] **Prettier uses tailwindcss plugin** — prettier-plugin-tailwindcss is configured for automatic Tailwind class sorting in all formatted files
- [ ] **.prettierrc and .prettierignore committed** — Prettier config specifies consistent formatting rules (semi, singleQuote, tabWidth, printWidth), ignore file excludes generated files
- [ ] **format:check script available for CI** — package.json includes a format:check script (prettier --check .) that CI runs to verify formatting without modifying files

## 2.9 Security Headers

- [ ] **Content-Security-Policy configured with appropriate directives** — script-src, style-src, img-src, connect-src, font-src, frame-ancestors set to restrict resource loading to trusted origins
- [ ] **X-Content-Type-Options: nosniff** — prevents browsers from MIME-sniffing responses away from the declared content-type
- [ ] **X-Frame-Options: DENY** — prevents the application from being embedded in iframes, protecting against clickjacking attacks
- [ ] **X-XSS-Protection: 0** — explicitly disabled because CSP replaces it; the legacy XSS filter can introduce vulnerabilities in modern browsers
- [ ] **Referrer-Policy: strict-origin-when-cross-origin** — sends the origin for cross-origin requests but full URL for same-origin, balancing privacy and debugging
- [ ] **Permissions-Policy restricts sensitive APIs** — camera=(), microphone=(), geolocation=(), payment=() disable browser APIs the app does not use
- [ ] **Headers applied via next.config.ts headers()** — all security headers are configured in the async headers() function of next.config.ts, applying to all routes via source: "/(.*)"

## 2.10 Build & Output Configuration

- [ ] **Standalone output produces self-contained build** — next build with output: "standalone" creates a .next/standalone/ directory that runs with node server.js without node_modules
- [ ] **next/font used for font loading** — fonts loaded via next/font/google or next/font/local, no external font CSS links in <head> that block rendering
- [ ] **No experimental features without documented justification** — any experimental Next.js flags in next.config.ts have a comment explaining why they are needed and when they can be removed
- [ ] **Build succeeds without warnings** — next build completes with zero warnings; any existing warnings have tracking issues for resolution
- [ ] **TypeScript errors fail the build** — TypeScript type-checking runs during build and any type errors prevent the build from completing (default Next.js behavior with strict tsconfig)
- [ ] **Source maps configured for production debugging** — productionBrowserSourceMaps set appropriately (true for debugging, false for production security — documented decision)
