# 09 — Styling & Theming Checklist

## 9.1 Tailwind v4 CSS-First Config

- [ ] **Theme defined in globals.css via @theme inline block** — all design tokens (colors, fonts, radii, shadows) are declared inside @theme { } in the global CSS file, not in a JavaScript config
- [ ] **No legacy tailwind.config.js file** — Tailwind v4 uses CSS-first configuration exclusively; no tailwind.config.js or tailwind.config.ts exists in the project
- [ ] **@import "tailwindcss" at top of globals.css** — the Tailwind v4 entry point is a CSS import directive, not @tailwind directives from v3
- [ ] **Custom properties use CSS custom properties pattern** — all theme extensions and overrides use standard CSS custom properties (--color-primary, --radius-lg, etc.)
- [ ] **@custom-variant dark correctly defined** — the dark mode variant is defined as @custom-variant dark (&:is(.dark *)) for class-based dark mode toggling
- [ ] **PostCSS config uses @tailwindcss/postcss plugin** — postcss.config.mjs references the Tailwind v4 PostCSS plugin, not the legacy postcss-tailwindcss or v3 plugin
- [ ] **tw-animate-css imported for animation utilities** — the animation utility library is imported via @import "tw-animate-css" in globals.css for transition and keyframe support

## 9.2 Design Token Usage

- [ ] **All colors use semantic tokens** — bg-background, text-foreground, border-border, and other semantic class names are used instead of raw color values
- [ ] **No hardcoded color values in component classes** — no #fff, rgb(…), hsl(…), or oklch(…) literals appear in className strings; all colors go through design tokens
- [ ] **Destructive actions use text-destructive and bg-destructive** — delete buttons, error states, and danger zones use the destructive token pair for consistent styling
- [ ] **Muted backgrounds use bg-muted and text-muted-foreground** — secondary content areas, disabled states, and placeholder text use the muted token pair
- [ ] **Chart colors use chart-1 through chart-5 tokens** — data visualization components reference the chart color palette tokens for consistent, theme-aware coloring
- [ ] **Accent colors use bg-accent and text-accent-foreground** — highlighted items, selected states, and interactive affordances use the accent token pair
- [ ] **All tokens defined in both :root and .dark variants** — every semantic color token has both a light mode value (in :root) and a dark mode value (in .dark) using OKLCH color space

## 9.3 Dark Mode

- [ ] **Both :root and .dark themes use OKLCH color values** — all color tokens are specified in oklch() format for perceptually uniform color manipulation and consistent contrast
- [ ] **ThemeProvider from next-themes wraps app with attribute="class"** — class-based theme switching is used rather than media query or data attribute approaches
- [ ] **suppressHydrationWarning on html tag** — the <html> element includes suppressHydrationWarning to prevent React hydration mismatch warnings caused by theme class injection
- [ ] **All components render correctly in both light and dark modes** — no component has unreadable text, invisible borders, or broken contrast in either theme
- [ ] **No hardcoded light-only or dark-only colors** — no className contains colors that only work in one theme (e.g., text-gray-900 without a dark: counterpart)
- [ ] **Dark mode toggle uses next-themes useTheme hook** — theme switching UI reads and sets the theme via the useTheme() hook, not direct DOM class manipulation
- [ ] **disableTransitionOnChange prevents flash during theme switch** — the ThemeProvider prop disableTransitionOnChange avoids a jarring flash of transitioning elements when the theme changes

## 9.4 Responsive Design

- [ ] **Mobile-first approach** — base styles target mobile viewports, and responsive prefixes (sm:, md:, lg:, xl:) progressively enhance the layout for larger screens
- [ ] **Tailwind responsive prefixes used consistently** — breakpoint usage follows a consistent pattern across all pages: base for mobile, md: for tablet, lg: for desktop
- [ ] **Navigation adapts across breakpoints** — Sidebar on desktop (lg:), BottomNavbar on mobile (base), MobileMenuSheet on tablet (md:) for the authenticated app shell
- [ ] **No horizontal scrolling on mobile viewports** — all page content fits within the viewport width on mobile devices, with no unintentional horizontal overflow
- [ ] **Touch targets are minimum 44x44px on mobile** — buttons, links, and interactive elements meet the WCAG minimum touch target size on touch devices
- [ ] **Dialogs and sheets are full-width on mobile** — modal dialogs expand to fill the screen width on small viewports, switching to centered fixed-width on desktop
- [ ] **Tables scroll horizontally or stack on mobile** — data tables either wrap in a horizontal scroll container or transform to a stacked card layout on narrow screens

## 9.5 Class Composition

- [ ] **cn() utility from lib/utils.ts merges classes** — clsx for conditional class joining and tailwind-merge for deduplication are combined in the cn() utility function
- [ ] **No conflicting Tailwind classes** — no element has both p-4 and p-6, both text-sm and text-lg, or other conflicting utility classes that would produce unpredictable results
- [ ] **CVA used for component variants** — class-variance-authority defines variant maps for components with multiple visual states (button sizes, card styles, badge colors)
- [ ] **No inline style attributes except where justified** — inline styles are used only in global-error.tsx (where Tailwind may not be loaded) and never in regular components
- [ ] **Conditional classes use cn() not string concatenation** — dynamic class application uses cn("base", condition && "conditional") rather than template literals or string addition
- [ ] **Tailwind classes ordered consistently** — utility classes follow a consistent order: layout/display, positioning, sizing, spacing, typography, colors, borders, effects

## 9.6 Spacing & Layout Consistency

- [ ] **Consistent spacing scale used throughout** — spacing values follow the Tailwind default scale (1=4px, 2=8px, 3=12px, 4=16px, etc.) without arbitrary pixel values
- [ ] **Layout patterns use flex and grid appropriately** — flex for one-dimensional layouts (navbars, toolbars, card rows), grid for two-dimensional layouts (page grids, form layouts)
- [ ] **Container widths consistent across pages** — page content uses a consistent max-width pattern (max-w-4xl, max-w-6xl, etc.) for readable line lengths
- [ ] **Cards, dialogs, and sections use consistent padding** — similar UI containers apply the same internal padding (p-4, p-6) throughout the application
- [ ] **Gap utilities used for flex/grid spacing** — child element spacing uses gap-* on the parent container, not margin hacks on individual children
- [ ] **Page layouts use consistent max-width and centering** — top-level page containers are centered with mx-auto and constrained with a consistent max-width value

## 9.7 Typography

- [ ] **Geist Sans and Geist Mono loaded via next/font/google** — font files are self-hosted through Next.js font optimization, not loaded from external CDNs
- [ ] **Font variables set on body** — --font-geist-sans and --font-geist-mono CSS custom properties are applied to the <body> element for global availability
- [ ] **Text sizes follow consistent scale** — text-xs, text-sm, text-base, text-lg, text-xl, and text-2xl are used according to content hierarchy without skipping sizes
- [ ] **No arbitrary pixel font sizes without justification** — text-[14px] and similar arbitrary values are not used unless there is a documented design reason
- [ ] **Headings follow visual hierarchy** — h1 elements are larger than h2, h2 larger than h3, with consistent size and weight differences throughout the app
- [ ] **Monospace font used for code and technical content** — code snippets, API keys, IDs, and technical strings use font-mono (Geist Mono) to distinguish them from prose

## 9.8 Animation & Transitions

- [ ] **tw-animate-css provides base animation utilities** — standard animation classes (fade-in, slide-in, etc.) come from the tw-animate-css import, not custom keyframe definitions
- [ ] **Transitions used for interactive elements** — hover states, focus rings, expand/collapse, and toggle animations use CSS transitions for smooth visual feedback
- [ ] **disableTransitionOnChange on ThemeProvider** — theme switches skip CSS transitions to prevent every element on the page from visually transitioning between color values
- [ ] **No janky or excessive animations** — animations run at 60fps, do not cause layout shifts, and are subtle enough to enhance rather than distract from the user experience
- [ ] **Animations respect prefers-reduced-motion** — users who have set prefers-reduced-motion: reduce in their OS see minimal or no animations throughout the app

## 9.9 Icon Consistency

- [ ] **lucide-react is the sole icon library** — no mixing of icon sets from FontAwesome, Heroicons, Material Icons, or other libraries alongside lucide-react
- [ ] **Icons imported individually for tree-shaking** — each icon is imported by name (import { Search } from "lucide-react") rather than a catch-all import that bundles unused icons
- [ ] **Icon sizes consistent with surrounding text** — size={16} for small text contexts, size={20} for base text contexts, scaled proportionally to avoid visual imbalance
- [ ] **Icons have accessible labels when standalone** — icon-only buttons include aria-label or sr-only text so screen readers can announce the action
- [ ] **No icon-only buttons without accessible names** — every button that renders only an icon provides an accessible name via aria-label, title, or visually hidden text
