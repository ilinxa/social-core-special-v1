# 12 — Performance & Optimization Checklist

## 12.1 Server Components

- [ ] **Data-fetching pages use Server Components by default** — pages that only display data from the backend are Server Components, not marked "use client"
- [ ] **"use client" pushed to leaf and interactive components** — only components that use useState, useEffect, event handlers, or browser APIs are client components
- [ ] **No unnecessary "use client" on container or wrapper components** — layout wrappers, page containers, and structural components remain server components unless they contain interactivity
- [ ] **Server components do not import client-side libraries** — no useState, useEffect, useRef, useRouter, or Zustand imports in server component files
- [ ] **Server component data fetching avoids waterfalls** — parallel Promise.all used when multiple independent data fetches are needed, not sequential await chains
- [ ] **No client component wrapping server component children unnecessarily** — server component children passed through client component slots (children prop) retain their server rendering
- [ ] **Server actions used where appropriate for mutations** — form submissions and simple mutations use server actions when they benefit from server-side execution without API roundtrips

## 12.2 React Compiler

- [ ] **reactCompiler enabled in next.config.ts** — the experimental React Compiler is active for automatic memoization across the codebase
- [ ] **No manual useMemo/useCallback/React.memo where compiler handles it** — redundant manual memoization removed in favor of compiler-generated optimizations
- [ ] **Components follow React rules for compiler compatibility** — no side effects in render body, no mutations of props or state during render, no conditional hook calls
- [ ] **Compiler compatibility verified** — no unsupported patterns (dynamic hook calls, non-standard React patterns) that cause compiler bailouts
- [ ] **Existing manual memoization removed where redundant** — previously added useMemo and useCallback calls reviewed and removed when the compiler handles the same optimization
- [ ] **Compiler does not cause regressions** — behavior verified through tests after enabling the compiler, no unexpected stale closures or missing updates

## 12.3 Bundle Size

- [ ] **Tree-shaking works correctly** — named imports used (import { Search } from "lucide-react", not import * as icons), barrel imports do not pull in entire libraries
- [ ] **No large libraries imported in client components unnecessarily** — heavy dependencies (date-fns, chart libraries) are imported only where needed, not in shared layout components
- [ ] **Dynamic imports used for heavy components loaded on interaction** — next/dynamic with ssr: false defers loading of modals, rich text editors, and other interaction-triggered components
- [ ] **Bundle analyzer run periodically** — @next/bundle-analyzer or equivalent used to audit bundle composition and identify unexpectedly large dependencies
- [ ] **No duplicate dependencies** — package-lock.json does not contain multiple versions of the same library (React, Zod, Axios) causing bundle bloat
- [ ] **Client bundle does not include server-only code** — server utilities, database clients, and backend-only modules are not accidentally imported in client components
- [ ] **Polyfills minimized for modern browsers** — browserslist targets modern browsers, no unnecessary polyfills for features natively supported by target browsers

## 12.4 Image Optimization

- [ ] **next/image used for all raster images** — all img tags replaced with next/image for automatic optimization, responsive sizing, and lazy loading
- [ ] **Width and height specified on images** — explicit dimensions prevent layout shift (CLS) during image loading
- [ ] **Lazy loading is the default** — images below the fold use the default lazy loading behavior, not overridden with loading="eager"
- [ ] **Priority prop set for above-the-fold hero and banner images** — critical images use priority={true} to preload and avoid LCP delays
- [ ] **Image formats optimized** — Next.js serves WebP or AVIF automatically based on browser support, no unoptimized PNG/JPEG served
- [ ] **Media files served via backend proxy rewrite** — /media/* routes are proxied to the backend via next.config.ts rewrites, not fetched from a separate origin

## 12.5 Font Optimization

- [ ] **next/font/google used for Geist Sans and Geist Mono** — fonts loaded via next/font to enable automatic self-hosting and preloading
- [ ] **Font variables set on body element** — --font-geist-sans and --font-geist-mono CSS custom properties applied to the body for Tailwind font-family usage
- [ ] **display: "swap" prevents invisible text during load** — font-display: swap ensures text is visible immediately with a fallback font, replaced when the custom font loads
- [ ] **No FOUT or FOIT visible** — flash of unstyled text and flash of invisible text are eliminated through proper font preloading and swap strategy
- [ ] **No external font CSS imports** — no Google Fonts CDN link tags in the document head — all fonts are self-hosted via next/font

## 12.6 Data Loading Patterns

- [ ] **TanStack Query handles caching with appropriate staleTime** — default staleTime of 5 minutes prevents unnecessary refetches while keeping data reasonably fresh
- [ ] **No unnecessary refetches on component mount** — stale data is reused when navigating back to a page, not refetched unless explicitly invalidated
- [ ] **Infinite scroll uses useInfiniteQuery with useInView** — paginated lists use TanStack Query's infinite query with react-intersection-observer to trigger fetchNextPage on scroll
- [ ] **Prefetching used for anticipated navigation** — queryClient.prefetchQuery preloads data for routes the user is likely to visit next (hover on links, tab navigation)
- [ ] **Parallel data fetching where possible** — multiple independent queries on a page fire simultaneously, not in sequential waterfall pattern
- [ ] **Pagination state persisted on back navigation** — returning to a paginated list restores the previous scroll position and loaded pages from TanStack Query cache
- [ ] **Background refetching does not cause UI flicker** — refetchOnWindowFocus and background updates show fresh data without visible loading states or content jumps

## 12.7 Render Performance

- [ ] **Zustand selectors prevent unnecessary re-renders** — granular selectors subscribe components to only the specific state slices they need, not the entire store
- [ ] **useShallow used when selectors return arrays or objects** — selectors that return new array/object references on every call use useShallow from zustand/react/shallow to prevent infinite re-render loops
- [ ] **Lists use stable keys** — UUIDs or other stable identifiers used as React keys, not array indices that cause unnecessary remounts on reorder
- [ ] **No key={index} on dynamic lists** — array index keys are not used on lists that can be reordered, filtered, or have items added/removed
- [ ] **Expensive computations memoized** — heavy calculations are memoized where the React Compiler does not handle them (or verified that the compiler does)
- [ ] **No inline function or object creation in render causing child re-renders** — callback functions and config objects passed as props are stable references, not recreated on every render
- [ ] **React DevTools Profiler used to identify re-render issues** — the Profiler has been used to audit key pages for unnecessary re-renders and the findings have been addressed

## 12.8 Lazy Loading & Code Splitting

- [ ] **Route-based code splitting automatic via App Router** — each page.tsx is a natural code split boundary, no manual configuration needed
- [ ] **Heavy modals and dialogs use next/dynamic with ssr: false** — large dialog components loaded only when triggered, not included in the initial page bundle
- [ ] **Below-the-fold content loaded lazily** — components not visible in the initial viewport are deferred until the user scrolls near them
- [ ] **Component-level code splitting for large feature components** — feature components exceeding ~50KB use dynamic imports to keep the initial bundle small
- [ ] **Loading fallback provided for dynamically imported components** — next/dynamic calls include a loading prop that renders a skeleton or spinner during chunk download
- [ ] **No eager loading of rarely-used features** — admin panels, settings dialogs, and other infrequently accessed features are code-split away from the main bundle

## 12.9 Caching Strategy

- [ ] **TanStack Query cache keyed by centralized queryKeys** — all cache keys defined in lib/query-keys.ts using a structured factory pattern for consistency and easy invalidation
- [ ] **staleTime prevents refetch on mount for recently fetched data** — components remounting within the staleTime window reuse cached data without a network request
- [ ] **Browser cache used for static assets** — hashed filenames in .next/static/ enable long-term browser caching without stale content
- [ ] **CDN caching for production static files** — static assets served with appropriate Cache-Control headers for CDN edge caching
- [ ] **API proxy does not cache dynamic responses** — the Next.js API proxy route forwards backend responses without adding client-side cache headers to dynamic data
- [ ] **Cache invalidation on mutations is targeted** — mutations invalidate only the affected query keys (queryClient.invalidateQueries), not the entire cache

## 12.10 Network Performance

- [ ] **API client uses connection reuse** — the shared Axios instance maintains keep-alive connections, not creating new TCP connections per request
- [ ] **Request deduplication via TanStack Query** — multiple components requesting the same data simultaneously result in a single network request, not duplicated calls
- [ ] **No chatty API patterns** — a single page load does not make 10+ sequential API requests when the data could be fetched in fewer calls or batched
- [ ] **Proactive token refresh prevents 401 roundtrips** — the token refresh interceptor refreshes tokens before expiry, saving the cost of a failed request followed by retry
- [ ] **Batch requests where backend supports it** — related data fetches use batch endpoints or Promise.all for parallel execution when available
- [ ] **Response compression enabled** — gzip or brotli compression active on the API proxy and static asset serving, verified via Content-Encoding headers

## 12.11 Performance Measurement

- [ ] **Core Web Vitals monitored** — LCP, INP, and CLS are tracked in production via web-vitals library, Sentry performance monitoring, or equivalent tooling
- [ ] **Lighthouse audits run periodically on key pages** — landing page, dashboard, and high-traffic pages audited for performance, accessibility, and best practices
- [ ] **Performance budgets defined** — maximum bundle size, LCP threshold, and CLS limit are documented and enforced, with alerts when budgets are exceeded
- [ ] **React DevTools Profiler used for render analysis** — the Profiler has been used to identify slow renders, unnecessary re-renders, and component bottlenecks
- [ ] **Web-vitals library or Sentry performance monitoring configured** — real user metrics collected in production for data-driven performance optimization
- [ ] **Slow pages identified and optimized** — pages with LCP > 2.5s, INP > 200ms, or CLS > 0.1 are identified and have optimization plans
