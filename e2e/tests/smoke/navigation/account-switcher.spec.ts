/**
 * Account switcher navigation smoke tests.
 *
 * Verifies that users can switch between Personal, Business A,
 * and Business B contexts via the account switcher combobox.
 * Confirms URL changes and context label updates for each switch.
 *
 * @layer L1
 * @system navigation
 * @parameters P1, P2, P3
 * @priority P1
 */

import { test, expect } from '../../../fixtures/business.fixture';
import { BasePage } from '../../../pages/base.page';
import { createBusinessViaApi } from '../../../helpers/business.helper';
import { generateBusinessName } from '../../../lib/utils';

test.describe('Account Switcher', () => {
  test('account switcher is visible on authenticated pages', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const basePage = new BasePage(page);
    await page.goto('/home');

    await expect(basePage.accountSwitcher).toBeVisible();
  });

  test('switcher shows Personal as active on personal routes', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const basePage = new BasePage(page);
    await page.goto('/home');

    await expect(basePage.accountSwitcher).toContainText('Personal');
  });

  test('switching to business navigates to business console', async ({ businessOwnerPage, businessContext }) => {
    const page = businessOwnerPage;
    const basePage = new BasePage(page);
    await page.goto('/home');

    // Use POM method to switch to business
    await basePage.switchToBusiness(businessContext.legalName);

    // Should navigate to business console
    await page.waitForURL(new RegExp(`/bconsole/${businessContext.slug}`));
    await expect(page).toHaveURL(new RegExp(`/bconsole/${businessContext.slug}`));
  });

  test('switching back to personal navigates to home', async ({ businessOwnerPage, businessContext }) => {
    const page = businessOwnerPage;
    const basePage = new BasePage(page);

    // Start on business console
    await page.goto(`/bconsole/${businessContext.slug}/dashboard`);
    await expect(basePage.accountSwitcher).toContainText(businessContext.legalName);

    // Switch to personal
    await basePage.switchToPersonal();
    await page.waitForURL(/\/home/);
    await expect(basePage.accountSwitcher).toContainText('Personal');
  });

  test('switching between two businesses updates context', async ({ businessOwnerPage, businessContext, apiClient, dbClient }) => {
    const page = businessOwnerPage;
    const basePage = new BasePage(page);

    // Create a second business for the same owner
    const secondName = generateBusinessName();
    const secondBiz = await createBusinessViaApi(apiClient, dbClient, { legalName: secondName });

    // Start at first business
    await page.goto(`/bconsole/${businessContext.slug}/dashboard`);
    await expect(basePage.accountSwitcher).toContainText(businessContext.legalName);

    // Switch to second business
    await basePage.switchToBusiness(secondName);
    await page.waitForURL(new RegExp(`/bconsole/${secondBiz.slug}`));
    await expect(basePage.accountSwitcher).toContainText(secondName);
  });
});
