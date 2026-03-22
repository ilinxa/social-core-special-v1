# 12 — Performance & Optimization Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 12.1 Server Components

| ID | Rule | Verdict |
|----|------|---------|
| 12.1.1 | WARN if data-fetching pages are marked "use client" when they could be Server Components | PASS/WARN |
| 12.1.2 | WARN if "use client" is not pushed to leaf/interactive components | PASS/WARN |
| 12.1.3 | WARN if container or wrapper components are unnecessarily marked "use client" | PASS/WARN |
| 12.1.4 | FAIL if server components import client-side libraries (useState, useEffect, useRouter, Zustand) | PASS/FAIL |
| 12.1.5 | WARN if server component data fetching uses sequential awaits instead of Promise.all | PASS/WARN |
| 12.1.6 | PASS if server component children passed through client component slots retain server rendering | PASS/FAIL |
| 12.1.7 | INFO if server actions are not used for mutations (acceptable if using API client pattern) | PASS/INFO |

## 12.2 React Compiler

| ID | Rule | Verdict |
|----|------|---------|
| 12.2.1 | FAIL if reactCompiler is not enabled in next.config.ts | PASS/FAIL |
| 12.2.2 | WARN if manual useMemo/useCallback/React.memo exist where compiler handles memoization | PASS/WARN |
| 12.2.3 | FAIL if components have side effects in render body or conditional hook calls | PASS/FAIL |
| 12.2.4 | WARN if unsupported patterns cause compiler bailouts | PASS/WARN |
| 12.2.5 | INFO if previously manual memoization has not been reviewed for removal | PASS/INFO |
| 12.2.6 | PASS if compiler does not cause regressions (verified via tests) | PASS/FAIL |

## 12.3 Bundle Size

| ID | Rule | Verdict |
|----|------|---------|
| 12.3.1 | FAIL if wildcard imports or barrel imports pull in entire libraries | PASS/FAIL |
| 12.3.2 | WARN if large libraries are imported in shared layout or frequently-rendered components | PASS/WARN |
| 12.3.3 | INFO if next/dynamic is not used for heavy interaction-triggered components | PASS/INFO |
| 12.3.4 | INFO if bundle analyzer is not configured or run periodically | PASS/INFO |
| 12.3.5 | WARN if package-lock.json contains duplicate versions of core dependencies | PASS/WARN |
| 12.3.6 | FAIL if client bundle includes server-only code (database clients, backend modules) | PASS/FAIL |
| 12.3.7 | INFO if polyfill strategy is not documented or browserslist not configured | PASS/INFO |

## 12.4 Image Optimization

| ID | Rule | Verdict |
|----|------|---------|
| 12.4.1 | WARN if raw <img> tags are used instead of next/image | PASS/WARN |
| 12.4.2 | WARN if next/image components lack explicit width and height | PASS/WARN |
| 12.4.3 | PASS if lazy loading is the default (not overridden with loading="eager") | PASS/FAIL |
| 12.4.4 | WARN if above-the-fold images lack priority={true} | PASS/WARN |
| 12.4.5 | PASS if Next.js serves optimized formats (WebP/AVIF) automatically | PASS/FAIL |
| 12.4.6 | PASS if /media/* routes proxied via next.config.ts rewrites | PASS/FAIL |

## 12.5 Font Optimization

| ID | Rule | Verdict |
|----|------|---------|
| 12.5.1 | FAIL if fonts are not loaded via next/font/google | PASS/FAIL |
| 12.5.2 | FAIL if font CSS variables are not set on the body element | PASS/FAIL |
| 12.5.3 | PASS if font-display: swap is configured | PASS/FAIL |
| 12.5.4 | PASS if no FOUT/FOIT is visible | PASS/FAIL |
| 12.5.5 | FAIL if external font CDN links exist in the document head | PASS/FAIL |

## 12.6 Data Loading Patterns

| ID | Rule | Verdict |
|----|------|---------|
| 12.6.1 | PASS if TanStack Query staleTime is configured appropriately | PASS/FAIL |
| 12.6.2 | PASS if stale data is reused on component remount within staleTime | PASS/FAIL |
| 12.6.3 | PASS if infinite scroll uses useInfiniteQuery + useInView | PASS/FAIL |
| 12.6.4 | INFO if prefetching is not implemented for anticipated navigation | PASS/INFO |
| 12.6.5 | PASS if multiple independent queries fire in parallel | PASS/FAIL |
| 12.6.6 | INFO if pagination state is not restored on back navigation | PASS/INFO |
| 12.6.7 | WARN if background refetching causes visible UI flicker | PASS/WARN |

## 12.7 Render Performance

| ID | Rule | Verdict |
|----|------|---------|
| 12.7.1 | PASS if Zustand selectors subscribe to specific state slices | PASS/FAIL |
| 12.7.2 | FAIL if useShallow is not used for selectors returning arrays/objects | PASS/FAIL |
| 12.7.3 | FAIL if array index is used as React key on dynamic lists | PASS/FAIL |
| 12.7.4 | FAIL if key={index} is used on lists that can be reordered/filtered | PASS/FAIL |
| 12.7.5 | PASS if expensive computations are memoized (or handled by React Compiler) | PASS/FAIL |
| 12.7.6 | WARN if inline function/object creation in render causes child re-renders | PASS/WARN |
| 12.7.7 | INFO if React DevTools Profiler has not been used to audit key pages | PASS/INFO |

## 12.8 Lazy Loading & Code Splitting

| ID | Rule | Verdict |
|----|------|---------|
| 12.8.1 | PASS if route-based code splitting is automatic via App Router page.tsx | PASS/FAIL |
| 12.8.2 | INFO if heavy modals/dialogs do not use next/dynamic with ssr: false | PASS/INFO |
| 12.8.3 | INFO if below-the-fold content is not lazily loaded | PASS/INFO |
| 12.8.4 | INFO if large feature components (>50KB) do not use dynamic imports | PASS/INFO |
| 12.8.5 | WARN if dynamically imported components lack a loading fallback | PASS/WARN |
| 12.8.6 | INFO if rarely-used features (admin, settings) are not code-split | PASS/INFO |

## 12.9 Caching Strategy

| ID | Rule | Verdict |
|----|------|---------|
| 12.9.1 | FAIL if TQ cache keys are not centralized in query-keys.ts | PASS/FAIL |
| 12.9.2 | PASS if staleTime prevents refetch on mount for recently fetched data | PASS/FAIL |
| 12.9.3 | PASS if static assets use hashed filenames for long-term caching | PASS/FAIL |
| 12.9.4 | INFO if CDN caching is not configured for production | PASS/INFO |
| 12.9.5 | PASS if API proxy does not add cache headers to dynamic responses | PASS/FAIL |
| 12.9.6 | FAIL if cache invalidation is not targeted (invalidates entire cache instead of specific keys) | PASS/FAIL |

## 12.10 Network Performance

| ID | Rule | Verdict |
|----|------|---------|
| 12.10.1 | PASS if Axios instance uses connection reuse (keep-alive) | PASS/FAIL |
| 12.10.2 | PASS if TanStack Query deduplicates simultaneous identical requests | PASS/FAIL |
| 12.10.3 | WARN if a single page load makes 10+ sequential API requests | PASS/WARN |
| 12.10.4 | PASS if proactive token refresh prevents 401 roundtrips | PASS/FAIL |
| 12.10.5 | INFO if batch endpoints are not used where available | PASS/INFO |
| 12.10.6 | INFO if response compression is not verified | PASS/INFO |

## 12.11 Performance Measurement

| ID | Rule | Verdict |
|----|------|---------|
| 12.11.1 | INFO if Core Web Vitals are not monitored in production | PASS/INFO |
| 12.11.2 | INFO if Lighthouse audits are not run periodically | PASS/INFO |
| 12.11.3 | INFO if performance budgets are not defined | PASS/INFO |
| 12.11.4 | INFO if React DevTools Profiler has not been used | PASS/INFO |
| 12.11.5 | INFO if web-vitals or Sentry performance monitoring is not configured | PASS/INFO |
| 12.11.6 | INFO if slow pages have not been identified and optimized | PASS/INFO |
