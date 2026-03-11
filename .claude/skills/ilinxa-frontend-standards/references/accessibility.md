# Accessibility Baseline

Target: **WCAG 2.2 Level AA**. Not optional.

## Table of Contents
1. [Semantic HTML](#semantic-html)
2. [ARIA](#aria)
3. [Keyboard Navigation](#keyboard-navigation)
4. [Focus Management](#focus-management)
5. [Color and Contrast](#color-and-contrast)
6. [Forms](#forms)
7. [Dynamic Content](#dynamic-content)
8. [Testing](#testing)

---

## Semantic HTML

Use the right element. Native HTML carries built-in a11y, keyboard, and screen reader support.

```tsx
// ✅
<button onClick={handleSubmit}>Submit</button>
<nav><ul><li><a href="/home">Home</a></li></ul></nav>
<main><article><h1>Title</h1></article></main>

// ❌
<div onClick={handleSubmit}>Submit</div>
<div className="nav"><div className="link">Home</div></div>
```

Common mappings: `<button>` not `<div onClick>`, `<a>` for navigation, `<nav>` for navigation blocks, `<main>` for primary content, `<section>` with heading for thematic groups, `<dialog>` for modals, `<details>/<summary>` for disclosure.

Heading hierarchy: one `<h1>` per page, no skipped levels (`h1` → `h2` → `h3`, never `h1` → `h3`).

---

## ARIA

**First rule: don't use ARIA if a native HTML element provides the semantics.**

Essential patterns:

```tsx
// Toggle button
<button aria-pressed={isActive} onClick={toggle}>Mute</button>

// Loading state
<div aria-busy={isLoading} aria-live="polite">{content}</div>

// Current navigation
<a href="/dashboard" aria-current={isActive ? "page" : undefined}>Dashboard</a>

// Expandable section
<button aria-expanded={isOpen} aria-controls="panel-1">Details</button>
<div id="panel-1" role="region">{isOpen && <p>Content</p>}</div>
```

Images: meaningful → descriptive `alt`. Decorative → `alt=""` or `aria-hidden="true"`. Complex → describe the conclusion, not the data (`alt="Revenue grew 15% in Q3 compared to Q2"`).

---

## Keyboard Navigation

All interactive elements must be keyboard accessible. Tab for navigation, Enter/Space for activation, Escape for dismissal, Arrow keys within composite widgets.

```tsx
// ✅ Keyboard accessible — native button
<button onClick={handleAction}>Action</button>

// ❌ Not keyboard accessible
<div onClick={handleAction}>Action</div>

// If you must use a non-interactive element (rare):
<div role="button" tabIndex={0} onClick={handleAction}
  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleAction(); }}>
  Action
</div>
```

Tab order: use natural DOM order. `tabIndex={0}` to add to tab order. `tabIndex={-1}` for programmatic focus only. Never use `tabIndex` > 0.

Skip navigation link:
```tsx
<a href="#main-content" className="sr-only focus:not-sr-only focus:absolute ...">
  Skip to main content
</a>
```

---

## Focus Management

Visible focus indicators on every focusable element:

```css
/* Tailwind */
.focus-ring {
  @apply focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary;
}
```

Never `outline: none` without a replacement.

Focus trapping in modals — use Radix Dialog or equivalent. Focus returns to trigger element on close.

After dynamic content changes (route navigation, accordion expand, toast): move focus to the new content or announce it with `aria-live`.

---

## Color and Contrast

| Element | Minimum Ratio |
|---------|--------------|
| Normal text (<18px) | 4.5:1 |
| Large text (≥18px bold or ≥24px) | 3:1 |
| UI components, icons | 3:1 |

Never rely on color alone. Pair with: icons, text labels, patterns, underlines.

```tsx
// ❌ Color-only status
<span className={isOnline ? "text-green-500" : "text-red-500"}>●</span>

// ✅ Color + text
<span className={isOnline ? "text-green-500" : "text-red-500"}>
  {isOnline ? "● Online" : "● Offline"}
</span>
```

---

## Forms

Every input needs a visible `<label>`:

```tsx
// ✅ Explicit association
<label htmlFor="email">Email</label>
<input id="email" type="email" aria-describedby="email-error" />
{error && <p id="email-error" role="alert">{error}</p>}

// ❌ Placeholder as label
<input placeholder="Email" />
```

Error messages: linked via `aria-describedby`, announced with `role="alert"`. Required fields: `aria-required="true"` + visible indicator.

Group related fields with `<fieldset>` + `<legend>`.

---

## Dynamic Content

- `aria-live="polite"` for non-urgent updates (search results, form feedback)
- `aria-live="assertive"` for urgent updates (errors, time-sensitive)
- Route changes: announce new page title, move focus to heading or main content

---

## Testing

- Manual: keyboard-only navigation through every flow
- Browser: axe DevTools extension
- Automated: `jest-axe` or `vitest-axe` for component tests
- Screen reader: VoiceOver (Mac) or NVDA (Windows) for critical flows

```tsx
import { axe } from "jest-axe";

it("has no a11y violations", async () => {
  const { container } = render(<Component />);
  expect(await axe(container)).toHaveNoViolations();
});
```
