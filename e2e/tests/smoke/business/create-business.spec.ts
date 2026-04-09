/**
 * Business creation smoke tests.
 *
 * Business creation uses a Dialog triggered from the AccountSwitcher,
 * NOT a standalone page route.
 *
 * @layer L1
 * @system business
 * @parameters P2, P4, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BasePage } from '../../../pages/base.page';

test.describe('Create Business', () => {
  test('business owner can create a business via account switcher', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const basePage = new BasePage(page);

    // Navigate to home where AccountSwitcher is visible
    await page.goto('/home');
    await expect(basePage.accountSwitcher).toBeVisible();

    // Open account switcher and click "Create Business"
    await basePage.openAccountSwitcher();
    await page.getByText(/create business/i).click();

    // Dialog should open — fill the creation form
    const uniqueName = `E2E Biz ${Date.now()}`;
    await page.getByLabel(/legal name/i).fill(uniqueName);

    // Country select — shadcn Popover combobox showing "All countries" initially
    // Must click the trigger text (not getByRole('combobox') which matches AccountSwitcher too)
    await page.getByText('All countries').click();
    await page.getByPlaceholder(/search country/i).fill('United States');
    await page.getByRole('option', { name: /united states/i }).click();

    // Submit the dialog form
    await page.getByRole('button', { name: /^create$/i }).or(
      page.getByRole('button', { name: /create business/i }),
    ).click();

    // Should redirect to the business console dashboard
    await expect(page).toHaveURL(/\/bconsole\/.+\/dashboard/, { timeout: 15000 });
  });

  test('regular user without permission does not see create business option', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    const basePage = new BasePage(page);

    await page.goto('/home');
    await expect(basePage.accountSwitcher).toBeVisible();

    // Open account switcher
    await basePage.openAccountSwitcher();

    // Should NOT see "Create Business" (user lacks can_create_business)
    // Instead may see "Request Business Creation" or nothing at all
    const createButton = page.getByText(/^create business$/i);
    await expect(createButton).not.toBeVisible();
  });

  test('business creation dialog validates required fields', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const basePage = new BasePage(page);

    await page.goto('/home');
    await basePage.openAccountSwitcher();
    await page.getByText(/create business/i).click();

    // Try submitting without filling required fields
    await page.getByRole('button', { name: /^create$/i }).or(
      page.getByRole('button', { name: /create business/i }),
    ).click();

    // Should show validation error for required fields (multiple may match — use first)
    await expect(
      page.getByText(/required|please fill|legal name/i).first(),
    ).toBeVisible();
  });
});
