# 11 — Testing Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 11.1 Test Architecture & Organization

| ID | Rule | Verdict |
|----|------|---------|
| 11.1.1 | FAIL if test files are not co-located with source files or in __tests__/ directories within the same feature module | PASS/FAIL |
| 11.1.2 | FAIL if test file structure does not mirror feature module structure (features/auth/__tests__/ for auth, etc.) | PASS/FAIL |
| 11.1.3 | WARN if a single test file covers multiple unrelated modules or components | PASS/WARN |
| 11.1.4 | WARN if it.skip or describe.skip exists without a tracking comment or issue reference | PASS/WARN |
| 11.1.5 | WARN if test file naming does not match source file naming (LoginForm.test.tsx for LoginForm.tsx) | PASS/WARN |
| 11.1.6 | FAIL if test files exist outside src/ directory (at project root, in public/, or config dirs) | PASS/FAIL |
| 11.1.7 | WARN if tests use relative imports instead of @/ alias matching source import style | PASS/WARN |

## 11.2 Test Types & Coverage Balance

| ID | Rule | Verdict |
|----|------|---------|
| 11.2.1 | WARN if user-facing components in features/*/components/ lack at least one render test | PASS/WARN |
| 11.2.2 | WARN if TanStack Query hooks lack renderHook tests | PASS/WARN |
| 11.2.3 | WARN if API functions in features/*/api/ lack tests verifying URL, method, and payload | PASS/WARN |
| 11.2.4 | WARN if Zod validation schemas lack tests with valid and invalid inputs | PASS/WARN |
| 11.2.5 | WARN if Zustand stores lack tests for actions and state transitions | PASS/WARN |
| 11.2.6 | INFO if no integration-style tests exist for multi-step user flows | PASS/INFO |
| 11.2.7 | WARN if test suite is dominated by a single test type (>80% snapshots or >80% unit-only) | PASS/WARN |

## 11.3 Test Utilities

| ID | Rule | Verdict |
|----|------|---------|
| 11.3.1 | FAIL if renderWithProviders does not wrap with QueryClientProvider + ThemeProvider + router context | PASS/FAIL |
| 11.3.2 | FAIL if test QueryClient does not disable retries | PASS/FAIL |
| 11.3.3 | WARN if no createWrapper function exists for renderHook tests | PASS/WARN |
| 11.3.4 | FAIL if shared test utilities are not centralized in src/test/utils.tsx | PASS/FAIL |
| 11.3.5 | FAIL if setup.ts does not import @testing-library/jest-dom/vitest matchers | PASS/FAIL |
| 11.3.6 | PASS if @testing-library/react cleanup runs automatically | PASS/FAIL |

## 11.4 Component Testing Patterns

| ID | Rule | Verdict |
|----|------|---------|
| 11.4.1 | FAIL if getByRole, getByText, getByLabelText are not the primary query methods | PASS/FAIL |
| 11.4.2 | FAIL if fireEvent is used instead of @testing-library/user-event for user interactions | PASS/FAIL |
| 11.4.3 | WARN if assertions do not use @testing-library/jest-dom matchers (toBeInTheDocument, etc.) | PASS/WARN |
| 11.4.4 | WARN if querySelector or getByTestId is the primary query strategy | PASS/WARN |
| 11.4.5 | PASS if tests verify visible text, enabled/disabled state, and navigation outcomes | PASS/FAIL |
| 11.4.6 | WARN if loading, error, empty, and populated states are not all tested | PASS/WARN |
| 11.4.7 | WARN if components accepting children or render props lack slot rendering tests | PASS/WARN |

## 11.5 Hook Testing

| ID | Rule | Verdict |
|----|------|---------|
| 11.5.1 | FAIL if custom hooks are not tested via renderHook | PASS/FAIL |
| 11.5.2 | PASS if query hooks mock API responses via mocked API client functions | PASS/FAIL |
| 11.5.3 | PASS if mutation hook tests verify mutationFn receives correct arguments | PASS/FAIL |
| 11.5.4 | FAIL if mutation tests do not handle TQ v5 extra context arg (use mock.calls[0][0]) | PASS/FAIL |
| 11.5.5 | PASS if result.current is re-checked after act() to verify state updates | PASS/FAIL |
| 11.5.6 | PASS if async hooks use waitFor for assertions | PASS/FAIL |

## 11.6 Mocking Patterns

| ID | Rule | Verdict |
|----|------|---------|
| 11.6.1 | PASS if vi.mock is used for module-level mocking | PASS/FAIL |
| 11.6.2 | PASS if vi.fn() is used for individual function mocks | PASS/FAIL |
| 11.6.3 | FAIL if next/navigation is not mocked consistently with sensible defaults across tests | PASS/FAIL |
| 11.6.4 | FAIL if Zustand stores are not mocked or reset between tests | PASS/FAIL |
| 11.6.5 | PASS if Axios is mocked at the shared instance level (@/lib/api-client), not the axios package | PASS/FAIL |
| 11.6.6 | WARN if mock API responses do not match backend contract shapes | PASS/WARN |
| 11.6.7 | FAIL if vi.clearAllMocks() or vi.resetAllMocks() is not called between tests | PASS/FAIL |
| 11.6.8 | WARN if partial mocks do not preserve original module exports via vi.importActual | PASS/WARN |

## 11.7 Async Testing

| ID | Rule | Verdict |
|----|------|---------|
| 11.7.1 | FAIL if async assertions are not wrapped in waitFor | PASS/FAIL |
| 11.7.2 | PASS if act() is used for state updates triggered outside React flow | PASS/FAIL |
| 11.7.3 | WARN if fake timers and waitFor conflict is not resolved (advance in act, useRealTimers before waitFor) | PASS/WARN |
| 11.7.4 | FAIL if setTimeout or setInterval is used in tests for timing | PASS/FAIL |
| 11.7.5 | PASS if findBy* queries are used for elements appearing asynchronously | PASS/FAIL |
| 11.7.6 | FAIL if promise-based assertions do not use await | PASS/FAIL |

## 11.8 Test Isolation

| ID | Rule | Verdict |
|----|------|---------|
| 11.8.1 | FAIL if any test relies on side effects from a previous test | PASS/FAIL |
| 11.8.2 | FAIL if Zustand store state is not reset between tests | PASS/FAIL |
| 11.8.3 | FAIL if TanStack Query cache is not cleared between tests (queryClient.clear() or fresh client) | PASS/FAIL |
| 11.8.4 | FAIL if mock functions are not reset via vi.clearAllMocks() or equivalent | PASS/FAIL |
| 11.8.5 | PASS if tests pass when run individually and as part of the full suite | PASS/FAIL |
| 11.8.6 | WARN if tests depend on shared global state (window.location, document.cookie) | PASS/WARN |

## 11.9 Accessibility Testing

| ID | Rule | Verdict |
|----|------|---------|
| 11.9.1 | PASS if getByRole and getByLabelText are the primary query methods (same as 11.4.1) | PASS/FAIL |
| 11.9.2 | WARN if custom widget tests do not verify correct ARIA roles | PASS/WARN |
| 11.9.3 | WARN if icon-only buttons and error-linked fields lack ARIA attribute assertions | PASS/WARN |
| 11.9.4 | INFO if tab order is not tested via user.tab() | PASS/INFO |
| 11.9.5 | WARN if screen reader text (sr-only, aria-live) is not asserted | PASS/WARN |
| 11.9.6 | WARN if form validation errors are not verified to link to inputs via aria-describedby | PASS/WARN |

## 11.10 Test Performance

| ID | Rule | Verdict |
|----|------|---------|
| 11.10.1 | WARN if full test suite exceeds 60 seconds locally | PASS/WARN |
| 11.10.2 | FAIL if real setTimeout or sleep delays are used in tests | PASS/FAIL |
| 11.10.3 | WARN if test setup triggers unnecessary re-renders | PASS/WARN |
| 11.10.4 | FAIL if vitest.config.ts does not specify happy-dom as the test environment | PASS/FAIL |
| 11.10.5 | WARN if test files exceed ~300 lines without being split by concern | PASS/WARN |

## 11.11 CI Test Execution

| ID | Rule | Verdict |
|----|------|---------|
| 11.11.1 | FAIL if npm run test does not execute vitest run (non-watch mode) | PASS/FAIL |
| 11.11.2 | FAIL if test failures do not fail the CI pipeline | PASS/FAIL |
| 11.11.3 | WARN if coverage reports are not generated via vitest run --coverage | PASS/WARN |
| 11.11.4 | WARN if flaky tests exist that pass locally but fail intermittently in CI | PASS/WARN |
| 11.11.5 | WARN if test results are not clearly visible in CI output | PASS/WARN |

## 11.12 Test Quality

| ID | Rule | Verdict |
|----|------|---------|
| 11.12.1 | FAIL if tests assert implementation details (internal state, effect count) instead of behavior | PASS/FAIL |
| 11.12.2 | WARN if describe/it blocks have non-descriptive names ("test error", "works correctly") | PASS/WARN |
| 11.12.3 | WARN if snapshot-only tests exist without supplemental behavioral assertions | PASS/WARN |
| 11.12.4 | INFO if it.each is not used for data-driven test variations | PASS/INFO |
| 11.12.5 | WARN if complex test scenarios lack comments explaining business context | PASS/WARN |
| 11.12.6 | WARN if edge cases (empty arrays, null values, boundary conditions) are not tested | PASS/WARN |
