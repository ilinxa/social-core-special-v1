# 09 — Styling & Theming Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 9.1 Tailwind v4 CSS-First Config

| ID | Rule | Verdict |
|----|------|---------|
| 9.1.1 | FAIL if design tokens are not declared inside @theme { } in globals.css | PASS/FAIL |
| 9.1.2 | FAIL if a legacy tailwind.config.js or tailwind.config.ts file exists | PASS/FAIL |
| 9.1.3 | FAIL if globals.css uses @tailwind directives instead of @import "tailwindcss" | PASS/FAIL |
| 9.1.4 | FAIL if theme extensions use JavaScript objects instead of CSS custom properties | PASS/FAIL |
| 9.1.5 | FAIL if dark mode variant is not defined as @custom-variant dark (&:is(.dark *)) | PASS/FAIL |
| 9.1.6 | FAIL if postcss.config does not reference @tailwindcss/postcss plugin | PASS/FAIL |
| 9.1.7 | WARN if tw-animate-css is not imported in globals.css for animation utilities | PASS/WARN |

## 9.2 Design Token Usage

| ID | Rule | Verdict |
|----|------|---------|
| 9.2.1 | FAIL if components use raw color classes (text-gray-500, bg-blue-600) instead of semantic tokens (text-foreground, bg-background) | PASS/FAIL |
| 9.2.2 | FAIL if hardcoded color values (#fff, rgb(), hsl(), oklch()) appear in className strings | PASS/FAIL |
| 9.2.3 | WARN if destructive actions do not use text-destructive and bg-destructive tokens | PASS/WARN |
| 9.2.4 | WARN if secondary content areas do not use bg-muted and text-muted-foreground tokens | PASS/WARN |
| 9.2.5 | INFO if chart color tokens (chart-1 through chart-5) are defined but not yet used | PASS/INFO |
| 9.2.6 | WARN if highlighted/selected states do not use bg-accent and text-accent-foreground tokens | PASS/WARN |
| 9.2.7 | FAIL if any semantic token is missing either :root or .dark variant | PASS/FAIL |

## 9.3 Dark Mode

| ID | Rule | Verdict |
|----|------|---------|
| 9.3.1 | FAIL if color token values are not in oklch() format | PASS/FAIL |
| 9.3.2 | FAIL if ThemeProvider does not use attribute="class" for class-based theme switching | PASS/FAIL |
| 9.3.3 | FAIL if <html> element does not include suppressHydrationWarning | PASS/FAIL |
| 9.3.4 | WARN if any component has unreadable text or broken contrast in dark mode | PASS/WARN |
| 9.3.5 | WARN if any className contains hardcoded colors without dark: counterparts | PASS/WARN |
| 9.3.6 | WARN if dark mode toggle does not use next-themes useTheme hook | PASS/WARN |
| 9.3.7 | WARN if disableTransitionOnChange is not set on ThemeProvider | PASS/WARN |

## 9.4 Responsive Design

| ID | Rule | Verdict |
|----|------|---------|
| 9.4.1 | PASS if base styles target mobile and responsive prefixes enhance for larger screens | PASS/FAIL |
| 9.4.2 | WARN if responsive prefix usage is inconsistent across pages | PASS/WARN |
| 9.4.3 | FAIL if navigation does not adapt across breakpoints (sidebar desktop, bottom nav mobile) | PASS/FAIL |
| 9.4.4 | WARN if horizontal scrolling occurs on mobile viewports | PASS/WARN |
| 9.4.5 | WARN if touch targets are smaller than 44x44px on mobile | PASS/WARN |
| 9.4.6 | WARN if dialogs and sheets are not full-width on mobile viewports | PASS/WARN |
| 9.4.7 | WARN if tables do not scroll horizontally or stack on narrow screens | PASS/WARN |

## 9.5 Class Composition

| ID | Rule | Verdict |
|----|------|---------|
| 9.5.1 | FAIL if cn() utility is not defined using clsx + tailwind-merge | PASS/FAIL |
| 9.5.2 | WARN if conflicting Tailwind classes exist on the same element (e.g., p-4 and p-6) | PASS/WARN |
| 9.5.3 | WARN if CVA is not used for components with multiple visual variants | PASS/WARN |
| 9.5.4 | WARN if inline style attributes are used in regular components (except global-error.tsx) | PASS/WARN |
| 9.5.5 | FAIL if conditional classes use string concatenation instead of cn() | PASS/FAIL |
| 9.5.6 | WARN if Tailwind class ordering is inconsistent across components | PASS/WARN |

## 9.6 Spacing & Layout Consistency

| ID | Rule | Verdict |
|----|------|---------|
| 9.6.1 | WARN if arbitrary pixel values (p-[13px], m-[7px]) are used instead of the Tailwind spacing scale | PASS/WARN |
| 9.6.2 | PASS if flex is used for 1D layouts and grid for 2D layouts appropriately | PASS/FAIL |
| 9.6.3 | WARN if page content max-width is inconsistent across pages | PASS/WARN |
| 9.6.4 | WARN if similar UI containers (cards, dialogs, sections) have inconsistent padding | PASS/WARN |
| 9.6.5 | WARN if child spacing uses margin hacks instead of gap-* on parent containers | PASS/WARN |
| 9.6.6 | WARN if page layouts are not centered with mx-auto and constrained with max-width | PASS/WARN |

## 9.7 Typography

| ID | Rule | Verdict |
|----|------|---------|
| 9.7.1 | FAIL if fonts are not loaded via next/font (external CDN loading) | PASS/FAIL |
| 9.7.2 | FAIL if font CSS custom properties are not set on the body element | PASS/FAIL |
| 9.7.3 | WARN if text size usage skips levels in the scale without justification | PASS/WARN |
| 9.7.4 | WARN if arbitrary pixel font sizes (text-[14px]) are used without documented reason | PASS/WARN |
| 9.7.5 | WARN if heading hierarchy is not visually consistent (h1 > h2 > h3) | PASS/WARN |
| 9.7.6 | WARN if code/technical content does not use font-mono | PASS/WARN |

## 9.8 Animation & Transitions

| ID | Rule | Verdict |
|----|------|---------|
| 9.8.1 | WARN if standard animations come from custom keyframes instead of tw-animate-css | PASS/WARN |
| 9.8.2 | PASS if interactive elements (hover, focus, expand) have smooth CSS transitions | PASS/FAIL |
| 9.8.3 | WARN if disableTransitionOnChange is not set on ThemeProvider | PASS/WARN |
| 9.8.4 | WARN if animations cause layout shifts or run below 60fps | PASS/WARN |
| 9.8.5 | WARN if animations do not respect prefers-reduced-motion | PASS/WARN |

## 9.9 Icon Consistency

| ID | Rule | Verdict |
|----|------|---------|
| 9.9.1 | FAIL if icon libraries other than lucide-react are used | PASS/FAIL |
| 9.9.2 | FAIL if icons are imported via catch-all instead of individual named imports | PASS/FAIL |
| 9.9.3 | WARN if icon sizes are inconsistent with surrounding text context | PASS/WARN |
| 9.9.4 | FAIL if standalone icon buttons lack accessible labels (aria-label or sr-only text) | PASS/FAIL |
| 9.9.5 | FAIL if any icon-only button has no accessible name | PASS/FAIL |
