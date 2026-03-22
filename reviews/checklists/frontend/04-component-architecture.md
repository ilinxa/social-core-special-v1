# 04 — Component Architecture Checklist

## 4.1 Server vs Client Components

- [ ] **Server components are the default** — components without "use client" are server-rendered, leveraging zero-bundle-size rendering and direct server-side data access
- [ ] **"use client" is pushed to the narrowest boundary** — the directive is placed on the smallest leaf component that needs interactivity, not on parent containers or entire feature trees
- [ ] **No server-only code in client components** — database queries, secret environment variables, fs operations, and Node.js APIs never appear in files with "use client"
- [ ] **No unnecessary "use client" on static components** — components that only render props without hooks, event handlers, or browser APIs remain server components
- [ ] **Providers.tsx is the main client boundary** — QueryClientProvider, ThemeProvider, AuthInitializer, and Toaster are composed in a single "use client" Providers component at the root
- [ ] **Feature hooks that use browser APIs have "use client"** — hooks accessing window, localStorage, navigator, or IntersectionObserver are in client-side files
- [ ] **Server components can import client components** — server components render client components as children, but client components do not import server-only modules

## 4.2 Component Declaration Style

- [ ] **Named function declarations used consistently** — components are declared as export function UserCard() {}, not export const UserCard = () => {} or export default function()
- [ ] **Props interface declared above the component** — the props type (interface or type alias) is defined immediately before the component function, named with Props suffix (UserCardProps)
- [ ] **No arrow function component exports** — top-level component exports use function declarations for hoisting, stack trace clarity, and consistency
- [ ] **No anonymous default exports** — only Next.js conventions (page.tsx, layout.tsx, error.tsx, loading.tsx, not-found.tsx) use default exports; all other components use named exports
- [ ] **Consistent pattern across all feature components** — every feature component follows the same structure: imports, type definition, function declaration, return JSX
- [ ] **Component name matches filename** — UserCard is defined in UserCard.tsx (or user-card.tsx), ProfileHeader in ProfileHeader.tsx — no mismatches between export name and file name

## 4.3 shadcn/ui Primitive Usage

- [ ] **components/ui/ contains only auto-generated shadcn primitives** — Button, Card, Dialog, Input, Select, Sheet, Skeleton, Tabs, Toast, and other primitives are generated via npx shadcn add
- [ ] **shadcn primitives are not hand-modified** — generated component files remain unchanged; project-specific behavior is achieved through composition in components/common/
- [ ] **components/common/ wraps primitives for project-specific behavior** — FormField wraps Input + Label + error display, PasswordInput wraps Input with visibility toggle, ConfirmActionDialog wraps Dialog
- [ ] **CVA (class-variance-authority) used for variant patterns** — composed components that need multiple visual variants use cva() to define variant classes, consistent with shadcn's pattern
- [ ] **All shadcn components use the project's design tokens** — no hardcoded hex/rgb colors in shadcn component overrides; all colors reference the OKLCH tokens from the Tailwind theme
- [ ] **New shadcn components added via CLI** — new primitives are installed with npx shadcn add component-name, not manually created or copied from the shadcn/ui website
- [ ] **Existing shadcn components can be updated** — when shadcn releases updates, components can be refreshed via CLI without losing project functionality (because customizations are in common/)

## 4.4 Composition Patterns

- [ ] **Composed components use children/render props not configuration props** — complex components accept children or render callbacks instead of large config objects with nested options
- [ ] **Radix asChild pattern used correctly** — when a shadcn component needs to render as a different element (e.g. Button as Link), asChild is used to merge props without extra DOM nodes
- [ ] **No prop drilling deeper than 3 levels** — data needed by deeply nested components is passed via context or hooks, not threaded through intermediate components that don't use it
- [ ] **Context used for cross-cutting concerns within feature boundaries** — feature-scoped context (e.g. BusinessContext for bconsole) provides shared data without global state pollution
- [ ] **Compound component pattern for complex widgets** — components like Tabs, Accordion, and custom form builders use the compound pattern (Parent + Parent.Item) for flexible composition
- [ ] **Slot-based composition preferred over boolean props** — instead of <Card showHeader showFooter>, the component accepts <Card.Header> and <Card.Footer> as children
- [ ] **Render callbacks are typed correctly** — render props and children-as-function patterns have explicit TypeScript types for the callback parameters and return type

## 4.5 Permission-Aware Components

- [ ] **Can component gates UI elements** — <Can allowed={permissions.can_edit_business}> wraps edit buttons, settings panels, and danger zones to show/hide based on evaluated RBAC booleans
- [ ] **Permissions consumed from _permissions on GET detail responses** — the _permissions object is extracted from detail API responses and passed to Can components, not fetched separately
- [ ] **No permission injection on PATCH/POST/list responses** — _permissions is present only on GET detail endpoints; list views, create responses, and update responses do not include it
- [ ] **No direct role name checks in components** — components never check if role === "admin" or role === "owner"; all authorization is expressed through boolean permission flags
- [ ] **Fallback content via fallback prop** — Can components accept an optional fallback prop to render alternative content (e.g. a read-only view) when the permission is false
- [ ] **Permission-gated sections are invisible, not disabled** — unauthorized UI elements are not rendered at all (return null), not shown in a disabled/grayed-out state that reveals feature existence

## 4.6 Forms & Controlled Components

- [ ] **react-hook-form with zodResolver for all forms** — every form uses useForm() with zodResolver(schema) for declarative validation, no manual validation in submit handlers
- [ ] **Form fields use common components** — FormField, FormTextarea, PasswordInput, and other common/ components provide consistent label, input, error display, and description text
- [ ] **Validation schemas in lib/validations/ or feature files** — shared schemas (email, password strength, slug) live in lib/validations/, feature-specific schemas co-locate with their form
- [ ] **No uncontrolled form state mixed with controlled** — forms are fully controlled via react-hook-form or fully uncontrolled; no hybrid approach where some fields are ref-based and others are state-based
- [ ] **Controller used for non-native inputs** — Select, Combobox, DatePicker, TagInput, and other complex inputs are wrapped with Controller from react-hook-form for proper value/onChange binding
- [ ] **register used for native inputs** — standard text, email, password, number inputs use the register() function directly for optimal performance without Controller overhead

## 4.7 Dialog & Sheet Patterns

- [ ] **Dialogs use shadcn Dialog component consistently** — all modal dialogs use the Dialog/DialogContent/DialogHeader/DialogFooter components from components/ui/, not custom modal implementations
- [ ] **Complex dialogs manage their own internal state** — multi-step dialogs (e.g. AcceptWithFormDialog) maintain step progression, form state, and validation internally without leaking to the parent
- [ ] **Dialog open/close state controlled by parent** — the open boolean and onOpenChange callback are passed as props from the parent component that triggers the dialog
- [ ] **No body scroll lock issues on mobile** — dialogs and sheets properly lock background scrolling on mobile devices and release it on close, no residual scroll-lock after unmount
- [ ] **Confirmation dialogs use ConfirmActionDialog** — destructive actions (delete, remove, cancel) use the standardized confirmation dialog with title, description, and confirm/cancel buttons
- [ ] **Sheet used for mobile navigation** — MobileMenuSheet provides a slide-out panel for navigation on mobile viewports, using the shadcn Sheet component with proper touch handling

## 4.8 Loading States

- [ ] **Skeleton components used for loading states** — loading UIs use Skeleton components (animated placeholder blocks), not spinner icons or text-only "Loading..." messages
- [ ] **Each page/section has appropriate loading skeletons** — every data-dependent section has a corresponding skeleton that matches the eventual content's structure and dimensions
- [ ] **Loading states match eventual content layout** — skeletons have the same height, width, and spacing as the real content, preventing Cumulative Layout Shift (CLS) when data arrives
- [ ] **No layout shift when content loads** — the transition from skeleton to content is seamless with no visible jump, resize, or reflow of surrounding elements
- [ ] **Loading skeletons are accessible** — skeleton containers have role="status" and aria-label="Loading" (or equivalent) so screen readers announce the loading state
- [ ] **Progressive loading for large data sets** — infinite scroll lists show skeleton cards at the bottom while fetching the next page, not a full-page skeleton replacement

## 4.9 Error Display

- [ ] **Error boundaries wrap feature-level sections** — each major feature area has an error boundary that catches rendering errors without crashing the entire application
- [ ] **Error states use Card with destructive variant styling** — error displays use consistent visual treatment with red/destructive colors, an error icon, and clear messaging
- [ ] **Error messages are user-friendly** — displayed errors show human-readable messages ("Something went wrong" or "Could not load members"), never raw error codes, stack traces, or JSON
- [ ] **Reset/retry functionality provided** — error states include a "Try again" button that either calls error boundary reset() or re-triggers the failed query/mutation
- [ ] **Empty states distinguished from error states** — "No members found" (empty) uses a neutral illustration/icon, while "Failed to load members" (error) uses destructive styling — they are visually distinct
- [ ] **Error components are tested** — error display components have test cases verifying the error message, retry button functionality, and correct rendering of different error types

## 4.10 Component File Size & Complexity

- [ ] **Components are under 200 lines** — no single component file exceeds ~200 lines of code; larger components are split into sub-components or extract logic into hooks
- [ ] **Complex components split into sub-components** — multi-section UIs (form builders, dashboards, profile pages) use a directory structure with index.tsx composing smaller pieces
- [ ] **No single component file with multiple unrelated exports** — each file exports one primary component; helper sub-components are either in the same file (if small) or in separate files
- [ ] **Logic-heavy components extract custom hooks** — components with significant state management, data transformation, or side effect logic extract that logic into a co-located custom hook
- [ ] **JSX nesting depth is manageable** — component JSX does not exceed 5 levels of nesting; deeply nested structures are extracted into named sub-components for readability
- [ ] **Helper functions extracted from component body** — pure utility functions (formatDate, calculateTotal, transformData) are defined outside the component function or in a utils file, not re-created on each render

## 4.11 Component Testing

- [ ] **Every common/ component has a co-located test file** — each shared component in components/common/ (Can, FormField, PasswordInput, ConfirmActionDialog, etc.) has a corresponding .test.tsx
- [ ] **Feature components with user interaction have tests** — buttons, forms, dialogs, and interactive elements in features/ have test coverage for click handlers, form submission, and state changes
- [ ] **Tests use renderWithProviders from test/utils.tsx** — all component tests render through the shared utility that provides QueryClientProvider, router context, and any required wrappers
- [ ] **Tests assert rendering, user interaction, and edge cases** — each test file covers initial render state, user actions (click, type, submit), loading states, error states, and boundary conditions
- [ ] **No snapshot-only tests without behavioral assertions** — snapshot tests, if used, are supplemented by behavioral assertions (getByRole, fireEvent, waitFor) that verify functionality
- [ ] **Tests mock external dependencies** — API calls, router navigation, Zustand stores, and other external dependencies are mocked to isolate the component under test
- [ ] **Component tests use accessible queries** — tests prefer getByRole, getByLabelText, getByText, and getByPlaceholderText over getByTestId, following Testing Library best practices
