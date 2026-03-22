# 11 — Testing Checklist

## 11.1 Test Architecture & Organization

- [ ] **Tests co-located with source files** — test files (.test.ts, .test.tsx) live next to the source file they test or in __tests__/ directories within the same feature module
- [ ] **Test structure mirrors feature structure** — features/auth/__tests__/ tests auth, features/business/__tests__/ tests business — no cross-feature test files
- [ ] **Test files focused on one concern per file** — each test file covers a single component, hook, utility, or store — not multiple unrelated modules
- [ ] **Dead or skipped tests tracked and cleaned up periodically** — it.skip and describe.skip are temporary, tracked in issues, and removed once resolved or the feature is dropped
- [ ] **Test file naming matches source file naming** — auth-store.test.ts tests auth-store.ts, LoginForm.test.tsx tests LoginForm.tsx — names are predictable and grep-friendly
- [ ] **No test files outside src/ directory** — all test code lives within src/, no rogue test files at the project root, in public/, or in config directories
- [ ] **Test imports use @/ alias matching source** — tests import from @/features/auth/api/auth-api, not ../../../features/auth/api/auth-api — consistent with source import style

## 11.2 Test Types & Coverage Balance

- [ ] **Component rendering tests for all user-facing components** — every component in features/*/components/ and components/common/ has at least one render test verifying its output
- [ ] **Hook tests for query and mutation hooks** — useBusinessQuery, useCreateBusinessMutation, and other TanStack Query wrappers are tested via renderHook
- [ ] **API function tests for all API calls** — every function in features/*/api/ is tested to verify correct URL, method, headers, and request body construction
- [ ] **Zod validation schema tests for all schemas** — every Zod schema (login, register, business creation, form builder) is tested with valid and invalid inputs
- [ ] **Zustand store tests for all stores** — auth-store, business-store, membership-store, and other Zustand stores have tests verifying actions and state transitions
- [ ] **Integration-style tests for critical user flows** — login flow, business creation, form submission, and other multi-step flows have end-to-end component tests
- [ ] **No over-reliance on any single test type** — the test suite is not 90% snapshot tests or 90% unit tests — a balanced mix of component, hook, API, and integration tests

## 11.3 Test Utilities

- [ ] **renderWithProviders wraps components in required context** — QueryClientProvider, ThemeProvider, and router context are composed in a single test render function
- [ ] **createTestQueryClient disables retries and sets staleTime to 0** — test QueryClient prevents flaky retry behavior and ensures fresh data on every test
- [ ] **createWrapper available for renderHook** — a wrapper function compatible with renderHook from @testing-library/react provides QueryClientProvider context for hook tests
- [ ] **Test utilities centralized in src/test/utils.tsx** — all shared test helpers (render wrappers, mock factories, custom matchers) live in one location, not duplicated
- [ ] **setup.ts imports @testing-library/jest-dom/vitest** — global test setup imports vitest-compatible DOM matchers (toBeInTheDocument, toHaveTextContent, etc.)
- [ ] **Cleanup runs automatically via afterEach** — @testing-library/react cleanup is automatic, no manual cleanup calls needed — verified by no stale DOM between tests

## 11.4 Component Testing Patterns

- [ ] **Tests use accessible queries as primary selectors** — screen.getByRole, getByText, getByLabelText are the default — not implementation-coupled selectors
- [ ] **User interactions via @testing-library/user-event** — user.click, user.type, user.tab are used instead of fireEvent for realistic event simulation
- [ ] **Assertions use @testing-library/jest-dom matchers** — toBeInTheDocument, toHaveTextContent, toBeDisabled, toHaveAttribute — not raw DOM property checks
- [ ] **No querySelector or getByTestId as primary queries** — data-testid is a last resort for elements with no accessible role, label, or text — not the default strategy
- [ ] **Tests verify what users see and interact with** — assertions check visible text, enabled/disabled state, and navigation outcomes — not internal state or implementation details
- [ ] **Conditional rendering tested for all states** — loading, error, empty, and populated states each have dedicated assertions verifying the correct UI is shown
- [ ] **Children and slot rendering verified** — components accepting children or render props are tested to confirm they correctly render provided content

## 11.5 Hook Testing

- [ ] **Custom hooks tested via renderHook** — renderHook from @testing-library/react is used to test hooks in isolation without a component wrapper
- [ ] **Query hooks mock API client responses** — API functions are mocked to return controlled data, verifying the hook processes and exposes the data correctly
- [ ] **Mutation hooks verify mutationFn receives correct arguments** — the mock function is asserted against the exact payload shape passed to the mutation
- [ ] **TQ v5 mutationFn context arg handled correctly** — assertions use mock.calls[0][0] to check the first argument only, ignoring the extra context object TanStack Query v5 passes as the second argument
- [ ] **Hook return values verified after state changes** — result.current is re-checked after act() calls to confirm the hook updates its return values correctly
- [ ] **Async hooks use waitFor for assertions** — hooks that fetch data or perform async operations are asserted inside waitFor blocks to avoid timing-dependent failures

## 11.6 Mocking Patterns

- [ ] **vi.mock for module-level mocking** — entire modules (next/navigation, @/lib/api-client) are mocked at the top of the test file with vi.mock()
- [ ] **vi.fn() for individual function mocks** — standalone mock functions use vi.fn() with optional mockImplementation or mockResolvedValue
- [ ] **next/navigation mocked consistently** — useRouter, usePathname, useSearchParams are mocked with sensible defaults (push: vi.fn(), pathname: "/") across all test files
- [ ] **Zustand stores mocked or reset between tests** — stores are either mocked via vi.mock or reset to initial state in beforeEach to prevent state leakage
- [ ] **Axios mocked at the instance level** — vi.mock("@/lib/api-client") mocks the shared Axios instance, not the axios package itself
- [ ] **MSW or manual mocks used for API responses** — API response shapes match backend contracts, with realistic data including edge cases (empty arrays, null fields)
- [ ] **Mock implementations reset in beforeEach/afterEach** — vi.clearAllMocks() or vi.resetAllMocks() called to prevent mock state from leaking between tests
- [ ] **Partial mocks preserve original module exports** — vi.mock with factory functions spread the original module (vi.importActual) when only some exports need mocking

## 11.7 Async Testing

- [ ] **waitFor used for async assertions** — assertions on async state changes are wrapped in waitFor, not preceded by arbitrary setTimeout delays
- [ ] **act() used for state updates triggered outside React flow** — Zustand store actions, manual promise resolutions, and timer advances are wrapped in act()
- [ ] **Fake timers and waitFor conflict resolved correctly** — timers advanced in act(), then vi.useRealTimers() called before waitFor to avoid frozen intervals
- [ ] **No setTimeout or setInterval in tests for timing** — tests never use real delays to wait for async operations — waitFor and act() handle all timing
- [ ] **findBy* queries used for elements that appear asynchronously** — findByText, findByRole are used instead of getBy* when the element is not immediately present
- [ ] **Promise-based assertions use await** — all assertions on async operations (API calls, state updates, navigation) properly await the result

## 11.8 Test Isolation

- [ ] **Each test is independent** — no test relies on the side effects or state mutations of a previous test — every test starts from a clean baseline
- [ ] **Zustand store state reset between tests** — store state is reset to initial values in beforeEach or via a dedicated reset function to prevent cross-test contamination
- [ ] **TanStack Query cache cleared between tests** — queryClient.clear() or a fresh createTestQueryClient() in beforeEach ensures no stale query data leaks
- [ ] **Mock functions reset via vi.clearAllMocks()** — mock call counts, arguments, and implementations are cleared in afterEach to prevent assertion pollution
- [ ] **No test order dependencies** — tests pass when run in isolation (vitest --run path/to/test.test.ts) and when run as part of the full suite
- [ ] **Tests can run in parallel** — no tests depend on shared global state (window.location, document.cookie) that would conflict when run concurrently

## 11.9 Accessibility Testing

- [ ] **Accessible queries used as default** — getByRole, getByLabelText are the primary query methods, establishing a baseline of semantic HTML verification
- [ ] **Role attributes verified on custom widgets** — dialogs, menus, tabs, and other custom widgets are asserted to have correct ARIA roles
- [ ] **aria-label and aria-describedby verified on interactive elements** — icon-only buttons, inputs with descriptions, and error-linked fields have correct ARIA attributes
- [ ] **Tab order tested for forms and navigation** — user.tab() verifies focus moves through form fields and navigation items in the expected logical order
- [ ] **Screen reader text verified for dynamic content** — visually hidden labels, aria-live regions, and status messages are asserted to contain meaningful text
- [ ] **Error messages linked to inputs via aria attributes** — form validation errors are associated with their fields through aria-describedby, verified in tests

## 11.10 Test Performance

- [ ] **Full test suite runs under 60 seconds locally** — the complete vitest run completes within a reasonable time, not degrading developer feedback loops
- [ ] **No real delays in tests** — no setTimeout, no arbitrary sleep functions — all timing handled via fake timers, waitFor, or act()
- [ ] **Tests avoid unnecessary re-renders** — test setup does not trigger multiple redundant renders by updating state outside act() or re-rendering without purpose
- [ ] **happy-dom used for speed** — vitest.config.ts specifies happy-dom as the test environment, not jsdom (which has ESM compatibility issues and slower performance)
- [ ] **Large test files split into focused smaller files** — test files exceeding ~300 lines are split by concern (rendering, interactions, error states) into separate files

## 11.11 CI Test Execution

- [ ] **npm run test runs in CI pipeline** — vitest run (non-watch mode) executes as part of the CI build, not vitest (watch mode)
- [ ] **Tests fail the build on failure** — any test failure causes the CI pipeline to report failure, blocking merge or deployment
- [ ] **Coverage reports generated via vitest run --coverage** — code coverage is collected and reported in CI, with results visible in the pipeline output
- [ ] **No flaky tests in CI** — tests produce deterministic results across runs — no tests that pass locally but fail intermittently in CI
- [ ] **Test results are visible in CI output** — test names, pass/fail counts, and failure details are clearly displayed in the CI log for debugging

## 11.12 Test Quality

- [ ] **Tests assert behavior not implementation details** — tests check what the component does (renders text, navigates, shows error) not how it does it (internal state shape, effect count)
- [ ] **Test names are descriptive** — describe/it blocks read like specifications ("renders error message when API returns 422", not "test error")
- [ ] **No snapshot-only tests without behavioral assertions** — snapshot tests, if used, are supplemented by explicit assertions on key behaviors and content
- [ ] **Parameterized tests for data-driven variations** — it.each used to test multiple input/output combinations (valid emails, invalid passwords, role permissions) without duplication
- [ ] **Complex test scenarios have comments explaining business context** — non-obvious test setups include comments explaining why the arrangement matters and what business rule is being verified
- [ ] **Edge cases covered** — empty data arrays, null values, undefined optional fields, boundary conditions (max length, zero count), and error responses are all tested
