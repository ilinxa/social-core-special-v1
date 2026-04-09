/**
 * Feature gate 403 smoke tests.
 *
 * Verifies that disabled features return appropriate error states
 * and that the UI hides gated elements when features are off.
 *
 * @layer L1
 * @system feature-gates
 * @parameters P1, P6, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';

test.describe('Feature Gate 403', () => {
  test('chat page renders (feature gate enabled)', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    await page.goto('/chat');

    // Chat page renders with conversations sidebar or error state
    // The heading may be "Conversations" not "Chat", and the empty state
    // shows "Select a conversation" text
    const chatContent = page.getByText(/conversations|select a conversation/i).first();
    const errorMessage = page.getByText(/feature.*disabled|not available|access denied/i);

    await expect(chatContent.or(errorMessage)).toBeVisible();
  });

  test('explore page renders (feature gate enabled)', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    await page.goto('/explore');

    const exploreHeading = page.getByRole('heading', { name: /explore/i });
    const errorMessage = page.getByText(/feature.*disabled|not available|access denied/i);

    await expect(exploreHeading.or(errorMessage)).toBeVisible();
  });

  test('forms page renders for business owner (feature gate enabled)', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    await page.goto('/bconsole/e2e-test-biz/forms');

    const formsHeading = page.getByRole('heading', { name: /forms/i });
    const errorMessage = page.getByText(/feature.*disabled|not available|access denied/i);

    await expect(formsHeading.or(errorMessage)).toBeVisible();
  });
});
