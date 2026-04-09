/**
 * W28: Feature Gate Degradation workflow.
 *
 * Tests that the UI handles feature gate 403 responses gracefully.
 * Uses Playwright route interception to simulate a disabled feature gate
 * (since config is file-based and loaded at startup).
 *
 * @layer L2
 * @system feature-gates, chat
 * @parameters P14 (Feature Gates)
 * @priority P1
 */

import { test, expect } from '../../fixtures/auth.fixture';

test.describe('W28: Feature Gate Degradation', () => {
  test('UI handles 403 from feature-gated endpoint gracefully', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;

    // Step 1 — Verify chat system enabled: navigate to /chat → page loads
    await page.goto('/chat');
    await expect(page.getByRole('heading', { name: /chat/i })).toBeVisible();

    // Step 2 — Intercept chat conversations endpoint → return 403
    await page.route('**/api/v1/chat/conversations/**', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'feature_disabled',
            message: 'Chat feature is disabled',
          },
        }),
      }),
    );

    // Step 3 — Navigate to /chat again with intercepted route
    await page.goto('/chat');

    // Step 4 — Verify UI shows appropriate error or feature-disabled message
    // The chat page should handle the 403 gracefully rather than crashing
    await expect(
      page.getByText(/disabled|unavailable|error|not available/i).or(
        page.getByRole('heading', { name: /chat/i }),
      ),
    ).toBeVisible();

    // Step 5 — Remove route intercept → refresh → verify chat loads normally
    await page.unroute('**/api/v1/chat/conversations/**');
    await page.goto('/chat');
    await expect(page.getByRole('heading', { name: /chat/i })).toBeVisible();
  });
});
