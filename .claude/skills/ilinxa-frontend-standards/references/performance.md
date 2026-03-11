# Performance

Measure first, optimize second. Use React DevTools Profiler and browser performance tools before applying any optimization.

## Table of Contents
1. [Re-Render Optimization](#re-render-optimization)
2. [Code Splitting and Lazy Loading](#code-splitting-and-lazy-loading)
3. [List Virtualization](#list-virtualization)
4. [Image Optimization](#image-optimization)
5. [Bundle Size](#bundle-size)
6. [Concurrent Features](#concurrent-features)
7. [Web Vitals](#web-vitals)

---

## Re-Render Optimization

### React.memo

```tsx
// ✅ Use when: component re-renders with same props due to parent re-rendering
const UserCard = memo(function UserCard({ user }: UserCardProps) {
  return <div>{user.name}</div>;
});

// Use when: renders expensive UI, parent re-renders frequently, props rarely change
// Skip when: component is cheap to render, props change on every render
```

### useMemo

```tsx
// ✅ Expensive computation
const sortedItems = useMemo(
  () => items.sort((a, b) => a.name.localeCompare(b.name)),
  [items],
);

// ❌ Don't memoize cheap operations
const fullName = useMemo(() => `${first} ${last}`, [first, last]); // just compute it
```

### useCallback

```tsx
// ✅ Stabilize function reference passed to memoized child
const handleDelete = useCallback((id: string) => {
  setItems((prev) => prev.filter((item) => item.id !== id));
}, []);

<MemoizedList onDelete={handleDelete} />
```

### React Compiler

React 19+ includes an experimental compiler that auto-memoizes. When enabled, skip manual `memo`, `useMemo`, `useCallback` — the compiler handles it. Check project's React version before deciding.

---

## Code Splitting and Lazy Loading

### Route-Level (React SPA)

```tsx
import { lazy, Suspense } from "react";

const Dashboard = lazy(() => import("@/features/dashboard/pages/DashboardPage"));
const Settings = lazy(() => import("@/features/settings/pages/SettingsPage"));

// In router
{ path: "dashboard", element: <Suspense fallback={<PageSkeleton />}><Dashboard /></Suspense> }
```

### Route-Level (Next.js)

Automatic — each `page.tsx` is its own bundle. Use `loading.tsx` for the fallback.

### Component-Level

```tsx
const HeavyChart = lazy(() => import("@/components/HeavyChart"));

function Dashboard() {
  return (
    <div>
      <Stats />
      <Suspense fallback={<ChartSkeleton />}>
        <HeavyChart data={chartData} />
      </Suspense>
    </div>
  );
}
```

### Dynamic Library Imports

```tsx
async function exportToPdf() {
  const { jsPDF } = await import("jspdf"); // only loaded when user clicks
  const doc = new jsPDF();
  // ...
}
```

---

## List Virtualization

For lists with 100+ items, use `@tanstack/react-virtual`:

```tsx
import { useVirtualizer } from "@tanstack/react-virtual";

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50, // estimated row height in px
  });

  return (
    <div ref={parentRef} style={{ height: 400, overflow: "auto" }}>
      <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.key}
            style={{
              position: "absolute",
              top: 0,
              transform: `translateY(${virtualRow.start}px)`,
              height: virtualRow.size,
            }}
          >
            <ListItem item={items[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Image Optimization

### Next.js

```tsx
import Image from "next/image";

<Image src="/hero.jpg" alt="Hero" width={1200} height={600} priority />  {/* above fold */}
<Image src="/card.jpg" alt="Card" width={400} height={300} loading="lazy" /> {/* below fold */}
```

### React SPA

```tsx
<img src="/hero.jpg" alt="Hero" loading="eager" fetchPriority="high" />
<img src="/card.jpg" alt="Card" loading="lazy" />
```

### Rules
- Always set `width` and `height` (prevents layout shift)
- Use WebP/AVIF formats
- `priority` / `fetchPriority="high"` for above-the-fold images only
- `loading="lazy"` for everything below the fold
- Serve responsive sizes with `srcSet` or Next.js `sizes` prop

---

## Bundle Size

### Monitoring

```bash
# Vite
npx vite-bundle-visualizer

# Next.js
ANALYZE=true next build  # with @next/bundle-analyzer
```

### Common Bloat Sources
- Full `lodash` import (use `lodash/pick` or `lodash-es`)
- Moment.js (use `date-fns` or `dayjs`)
- Full icon libraries (import individual icons: `import { Search } from "lucide-react"`)
- Unused dependencies

### Budget

| Metric | Target |
|--------|--------|
| Initial JS (gzipped) | < 150KB |
| Per-route chunk | < 50KB |
| Total CSS | < 50KB |
| Any single dependency | < 30KB |

Fail CI if budget exceeded (configure in `vite.config.ts` or webpack).

---

## Concurrent Features

### useTransition — Keep UI Responsive

```tsx
const [isPending, startTransition] = useTransition();

function handleFilterChange(value: string) {
  startTransition(() => {
    setFilter(value); // low-priority update — doesn't block input
  });
}

<Input onChange={(e) => handleFilterChange(e.target.value)} />
{isPending && <Spinner />}
<FilteredResults filter={filter} />
```

### useDeferredValue — Defer Expensive Renders

```tsx
const deferredQuery = useDeferredValue(searchQuery);
const isStale = deferredQuery !== searchQuery;

<div style={{ opacity: isStale ? 0.5 : 1 }}>
  <SearchResults query={deferredQuery} />
</div>
```

---

## Web Vitals

| Metric | Target | What It Measures |
|--------|--------|-----------------|
| LCP (Largest Contentful Paint) | < 2.5s | Loading performance |
| INP (Interaction to Next Paint) | < 200ms | Responsiveness |
| CLS (Cumulative Layout Shift) | < 0.1 | Visual stability |

### Measuring

```tsx
// Next.js: built-in via next/web-vitals
// SPA: web-vitals library
import { onLCP, onINP, onCLS } from "web-vitals";

onLCP(console.log);
onINP(console.log);
onCLS(console.log);
```

Monitor in production with: Vercel Analytics, Google PageSpeed Insights, or custom reporting.
