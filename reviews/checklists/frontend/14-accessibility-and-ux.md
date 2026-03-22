# 14 — Accessibility & UX Checklist

## 14.1 Semantic HTML

- [ ] **Headings follow hierarchy** — h1, h2, h3 are used in order with no skipped levels (no h1 followed directly by h3), each page has exactly one h1
- [ ] **Lists use ul/ol elements** — groups of related items use <ul> or <ol>, not styled <div> elements that visually resemble lists
- [ ] **Buttons are button, links are a** — interactive elements that trigger actions use <button>, elements that navigate use <a> — no <div onClick> or <span onClick>
- [ ] **Forms use form with onSubmit** — form elements are wrapped in <form> with an onSubmit handler, not <div> wrappers that bypass native form behavior
- [ ] **Navigation uses nav landmark** — primary and secondary navigation sections are wrapped in <nav> with aria-label distinguishing multiple nav regions
- [ ] **Main content uses main element** — the primary content area of each page is wrapped in <main> for landmark navigation
- [ ] **Tables use table for tabular data** — data grids and comparison layouts use <table>, <thead>, <tbody>, <th>, and <td> — not CSS grid divs

## 14.2 ARIA Attributes

- [ ] **Role attributes on custom widgets** — custom-built dialogs, menus, tabs, and alert dialogs have appropriate ARIA roles (role="dialog", role="menu", role="tablist")
- [ ] **aria-label on icon-only buttons and non-text interactive elements** — buttons containing only icons have descriptive aria-label text explaining the action
- [ ] **aria-describedby links error messages and descriptions to form fields** — input fields reference their error messages and help text via aria-describedby IDs
- [ ] **aria-live regions for dynamic content updates** — toast notifications, status changes, and real-time updates use aria-live="polite" or aria-live="assertive" for screen reader announcement
- [ ] **aria-expanded on collapsible elements** — accordions, dropdowns, and expandable panels use aria-expanded="true"/"false" to communicate their state
- [ ] **aria-hidden on decorative elements** — icons, dividers, and other purely decorative elements use aria-hidden="true" to be ignored by screen readers
- [ ] **aria-current on active navigation items** — the currently active page in navigation uses aria-current="page" to indicate the user's location

## 14.3 Keyboard Navigation

- [ ] **All interactive elements are focusable via Tab** — buttons, links, inputs, selects, and custom widgets can all be reached using the Tab key
- [ ] **Tab order follows visual and logical order** — focus moves through the page in a sequence that matches the visual layout, with no unexpected jumps
- [ ] **Escape closes dialogs, sheets, and dropdown menus** — all overlay components respond to Escape key by closing and returning focus to the trigger
- [ ] **Enter and Space activate buttons and checkboxes** — standard keyboard interaction patterns are supported on all interactive elements
- [ ] **Arrow keys navigate within menus, tabs, and radio groups** — composite widgets use arrow key navigation per WAI-ARIA authoring practices
- [ ] **No keyboard traps** — focus can always move away from any element using Tab or Shift+Tab — no element captures focus permanently
- [ ] **Skip-to-content link available for long navigation** — a visually hidden but focusable skip link appears at the top of the page for keyboard users to bypass repetitive navigation

## 14.4 Focus Management

- [ ] **Focus moves to dialog and sheet content on open** — when a dialog or sheet opens, focus is programmatically moved to the first focusable element or the dialog title
- [ ] **Focus returns to trigger element on close** — when a dialog, sheet, or dropdown closes, focus returns to the element that triggered it
- [ ] **Focus moves to error summary on form submission failure** — when a form submission fails validation, focus is moved to the first error or an error summary
- [ ] **Focus-visible indicator present** — :focus-visible styles are applied via Tailwind's ring utilities, providing a visible focus indicator only on keyboard navigation
- [ ] **Focus is not removed from interactive elements** — no outline: none, outline: 0, or focus:outline-none applied without a replacement focus indicator
- [ ] **Programmatic focus set with ref.focus() for dynamic content** — dynamically rendered content (new form sections, loaded results, inserted elements) receives focus when appropriate
- [ ] **Focus ring has sufficient contrast** — the focus indicator ring is visible against both light and dark backgrounds, meeting contrast requirements

## 14.5 Color & Contrast

- [ ] **Text meets WCAG AA contrast ratio** — normal text has at least 4.5:1 contrast ratio, large text (18px+ or 14px bold) has at least 3:1
- [ ] **Semantic colors have sufficient contrast in both themes** — destructive (red), success (green), warning (amber) colors meet contrast requirements in both light and dark mode
- [ ] **Information not conveyed by color alone** — icons, text labels, or patterns supplement color to convey meaning (error states use icon + text + color, not just red)
- [ ] **Dark mode maintains the same contrast ratios** — switching to dark theme does not degrade text contrast below WCAG AA thresholds
- [ ] **Links are distinguishable from body text** — links have underline, distinct color contrast, or another visual indicator beyond color to distinguish them from plain text
- [ ] **Disabled states have sufficient contrast** — disabled buttons and inputs are readable (not invisible), even though they are not interactive

## 14.6 Loading & Status Communication

- [ ] **Loading states have role="status" or aria-label="Loading"** — spinner and skeleton components communicate loading state to screen readers
- [ ] **Error alerts have role="alert"** — error messages that appear dynamically use role="alert" for immediate screen reader announcement
- [ ] **Toast notifications from sonner are accessible** — toast messages are announced to assistive technology via aria-live regions
- [ ] **Progress indicators have labels** — progress bars and loading indicators have aria-label or visible text describing what is loading
- [ ] **Status changes announced dynamically** — state transitions (form submitted, item deleted, member invited) are not just visual — screen readers are notified
- [ ] **Skeleton loaders have aria-label="Loading content"** — skeleton UI placeholders communicate their purpose to screen readers rather than appearing as empty elements

## 14.7 Responsive Accessibility

- [ ] **Touch targets are minimum 44x44px on mobile** — buttons, links, and interactive elements meet the minimum touch target size for comfortable mobile interaction
- [ ] **No hover-only interactions** — tooltips, menus, and information revealed on hover have touch and keyboard alternatives
- [ ] **Pinch-to-zoom is not disabled** — no maximum-scale=1 in the viewport meta tag, allowing users to zoom for readability
- [ ] **Text is resizable up to 200% without breaking layout** — content reflows and remains usable when the browser zoom is set to 200%, with no overflow or hidden text
- [ ] **Content reflows on zoom** — zooming does not introduce horizontal scrolling on the main content area, maintaining a single-column readable layout
- [ ] **Mobile menu is keyboard-accessible** — the mobile hamburger menu can be opened, navigated, and closed using only the keyboard

## 14.8 Image Accessibility

- [ ] **All content images have descriptive alt text** — images that convey information have alt text describing their content or purpose
- [ ] **Decorative images have empty alt** — images that are purely decorative use alt="" to be ignored by screen readers
- [ ] **Avatar images use user's name as alt text** — user and business avatars include the entity's name in alt text for identification
- [ ] **Icon buttons have accessible labels** — buttons containing only an icon have aria-label describing the action the button performs
- [ ] **next/image width and height prevent CLS** — explicit dimensions on all images prevent Cumulative Layout Shift during page load

## 14.9 Error Messaging

- [ ] **Form errors are descriptive and suggest correction** — error messages explain what went wrong and how to fix it ("Email must be a valid address", not just "Invalid")
- [ ] **Error messages associated with fields via aria-describedby** — each form field's error message is linked to the input via aria-describedby for screen reader users
- [ ] **Global errors announced to screen readers** — page-level error messages use role="alert" to be announced immediately by assistive technology
- [ ] **404 page provides clear next actions** — the not-found page includes navigation links (back, home) so users are not stranded
- [ ] **Error recovery options are keyboard-accessible** — retry buttons, "go back" links, and error recovery actions can be activated via keyboard
- [ ] **Error states maintain page context** — errors display inline within the page, not navigating the user away from their current context unexpectedly

## 14.10 Accessibility Testing

- [ ] **Component tests use accessible queries as default** — getByRole and getByLabelText are the primary query methods in testing-library tests, establishing semantic HTML as a requirement
- [ ] **Manual keyboard testing performed for critical flows** — login, registration, form submission, navigation, and dialog interactions have been manually tested with keyboard-only navigation
- [ ] **Automated accessibility checks considered** — axe-core, @testing-library/jest-dom accessibility matchers, or eslint-plugin-jsx-a11y used to catch common accessibility issues
- [ ] **Screen reader testing for authentication and key user flows** — critical flows have been tested with NVDA, VoiceOver, or another screen reader to verify usability
- [ ] **Color contrast checked with browser DevTools or tools** — Colour Contrast Analyser, Chrome DevTools contrast checker, or similar tools used to verify WCAG AA compliance
- [ ] **WCAG compliance level documented** — the target WCAG level (AA) is documented, and known deviations are tracked with remediation plans
