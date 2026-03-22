# 14 — Accessibility & UX Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 14.1 Semantic HTML

| ID | Rule | Verdict |
|----|------|---------|
| 14.1.1 | FAIL if heading levels are skipped (h1 → h3) or multiple h1 elements exist on a single page | PASS/FAIL |
| 14.1.2 | WARN if groups of related items use styled divs instead of ul/ol elements | PASS/WARN |
| 14.1.3 | FAIL if div or span elements have onClick handlers without button/link semantics (role, tabIndex, keyboard events) | PASS/FAIL |
| 14.1.4 | WARN if form inputs are not wrapped in a form element with onSubmit handler | PASS/WARN |
| 14.1.5 | WARN if primary navigation is not wrapped in nav landmark with aria-label | PASS/WARN |
| 14.1.6 | WARN if the primary content area does not use a main element | PASS/WARN |
| 14.1.7 | WARN if tabular data is displayed using CSS grid/flex divs instead of table elements | PASS/WARN |

## 14.2 ARIA Attributes

| ID | Rule | Verdict |
|----|------|---------|
| 14.2.1 | WARN if custom widgets (dialogs, menus, tabs) lack appropriate ARIA roles | PASS/WARN |
| 14.2.2 | FAIL if icon-only buttons lack aria-label or accessible text | PASS/FAIL |
| 14.2.3 | WARN if form field error messages are not linked via aria-describedby | PASS/WARN |
| 14.2.4 | WARN if dynamic content updates (toasts, status changes) lack aria-live regions | PASS/WARN |
| 14.2.5 | WARN if collapsible elements (accordions, dropdowns) lack aria-expanded | PASS/WARN |
| 14.2.6 | INFO if decorative icons do not use aria-hidden="true" | PASS/INFO |
| 14.2.7 | INFO if active navigation items lack aria-current="page" | PASS/INFO |

## 14.3 Keyboard Navigation

| ID | Rule | Verdict |
|----|------|---------|
| 14.3.1 | FAIL if interactive elements are not reachable via Tab key | PASS/FAIL |
| 14.3.2 | WARN if tab order does not follow visual/logical layout order | PASS/WARN |
| 14.3.3 | FAIL if Escape does not close dialogs, sheets, and dropdown menus | PASS/FAIL |
| 14.3.4 | PASS if Enter and Space activate buttons and checkboxes (native browser behavior) | PASS/FAIL |
| 14.3.5 | INFO if arrow key navigation is not implemented within composite widgets (menus, tabs, radio groups) | PASS/INFO |
| 14.3.6 | FAIL if any element creates a keyboard trap (focus cannot leave) | PASS/FAIL |
| 14.3.7 | WARN if no skip-to-content link is provided for keyboard users | PASS/WARN |

## 14.4 Focus Management

| ID | Rule | Verdict |
|----|------|---------|
| 14.4.1 | WARN if focus does not move to dialog/sheet content on open | PASS/WARN |
| 14.4.2 | WARN if focus does not return to trigger element on dialog/sheet close | PASS/WARN |
| 14.4.3 | INFO if focus does not move to error summary on form validation failure | PASS/INFO |
| 14.4.4 | FAIL if no focus-visible indicator exists on interactive elements | PASS/FAIL |
| 14.4.5 | FAIL if outline: none or focus:outline-none is applied without a replacement focus indicator | PASS/FAIL |
| 14.4.6 | INFO if dynamically rendered content does not receive programmatic focus | PASS/INFO |
| 14.4.7 | WARN if focus ring has insufficient contrast against backgrounds | PASS/WARN |

## 14.5 Color & Contrast

| ID | Rule | Verdict |
|----|------|---------|
| 14.5.1 | WARN if text contrast ratios appear below WCAG AA (4.5:1 normal, 3:1 large text) | PASS/WARN |
| 14.5.2 | WARN if semantic colors (destructive, success, warning) lack sufficient contrast in either theme | PASS/WARN |
| 14.5.3 | FAIL if information is conveyed by color alone without supporting icon, text, or pattern | PASS/FAIL |
| 14.5.4 | WARN if dark mode degrades text contrast below WCAG AA thresholds | PASS/WARN |
| 14.5.5 | WARN if links are indistinguishable from body text (no underline, no distinct color) | PASS/WARN |
| 14.5.6 | WARN if disabled states are unreadable (insufficient contrast for state communication) | PASS/WARN |

## 14.6 Loading & Status Communication

| ID | Rule | Verdict |
|----|------|---------|
| 14.6.1 | WARN if loading spinners/skeletons lack role="status" or aria-label="Loading" | PASS/WARN |
| 14.6.2 | WARN if dynamically appearing error messages lack role="alert" | PASS/WARN |
| 14.6.3 | PASS if toast notifications (sonner) use aria-live regions | PASS/FAIL |
| 14.6.4 | INFO if progress bars lack aria-label or visible text | PASS/INFO |
| 14.6.5 | INFO if state transitions are not announced to screen readers | PASS/INFO |
| 14.6.6 | WARN if skeleton loaders lack aria-label="Loading content" or equivalent | PASS/WARN |

## 14.7 Responsive Accessibility

| ID | Rule | Verdict |
|----|------|---------|
| 14.7.1 | WARN if touch targets are smaller than 44x44px on mobile | PASS/WARN |
| 14.7.2 | WARN if interactions are hover-only without touch/keyboard alternatives | PASS/WARN |
| 14.7.3 | FAIL if maximum-scale=1 is set in viewport meta tag, preventing zoom | PASS/FAIL |
| 14.7.4 | INFO if layout breaks at 200% browser zoom | PASS/INFO |
| 14.7.5 | INFO if zooming introduces unnecessary horizontal scrolling | PASS/INFO |
| 14.7.6 | WARN if mobile menu cannot be operated via keyboard | PASS/WARN |

## 14.8 Image Accessibility

| ID | Rule | Verdict |
|----|------|---------|
| 14.8.1 | WARN if content images lack descriptive alt text | PASS/WARN |
| 14.8.2 | WARN if decorative images do not have alt="" | PASS/WARN |
| 14.8.3 | WARN if avatar images do not include the entity's name in alt text | PASS/WARN |
| 14.8.4 | FAIL if icon-only buttons lack accessible labels (aria-label or sr-only text) | PASS/FAIL |
| 14.8.5 | WARN if next/image components lack explicit width and height causing CLS | PASS/WARN |

## 14.9 Error Messaging

| ID | Rule | Verdict |
|----|------|---------|
| 14.9.1 | PASS if form errors are descriptive and suggest correction (not just "Invalid") | PASS/FAIL |
| 14.9.2 | WARN if error messages are not linked to fields via aria-describedby | PASS/WARN |
| 14.9.3 | WARN if page-level error messages lack role="alert" for screen reader announcement | PASS/WARN |
| 14.9.4 | PASS if 404 page provides navigation links (back, home) for recovery | PASS/FAIL |
| 14.9.5 | PASS if error recovery options (retry, go back) are keyboard-accessible | PASS/FAIL |
| 14.9.6 | PASS if errors display inline without navigating the user away from their context | PASS/FAIL |

## 14.10 Accessibility Testing

| ID | Rule | Verdict |
|----|------|---------|
| 14.10.1 | PASS if component tests primarily use getByRole and getByLabelText queries | PASS/FAIL |
| 14.10.2 | INFO if manual keyboard testing has not been performed for critical flows | PASS/INFO |
| 14.10.3 | INFO if automated accessibility checks (axe-core, eslint-plugin-jsx-a11y) are not configured | PASS/INFO |
| 14.10.4 | INFO if screen reader testing has not been performed for key flows | PASS/INFO |
| 14.10.5 | INFO if color contrast has not been verified with tools | PASS/INFO |
| 14.10.6 | INFO if WCAG compliance level is not documented | PASS/INFO |
