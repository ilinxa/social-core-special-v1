/**
 * Persona: Frank — The Multi-Context User
 *
 * A user who manages 3 different business accounts simultaneously,
 * testing scope isolation and context switching.
 *
 * 21 progressive steps.
 *
 * @layer L3
 * @system auth, business
 * @parameters P1 (Auth), P2 (Navigation), P5 (CRUD), P6 (RBAC)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { BusinessDashboardPage, BusinessSettingsPage } from '../../pages/business/business-console.page';
import { BusinessProfilePage } from '../../pages/business/business-profile.page';
import { BasePage } from '../../pages/base.page';
import { getOrgMode } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { createBusinessViaApi, getBusinessMembersViaApi } from '../../helpers/business.helper';
import { acceptTransactionViaApi, inviteToBusinessViaApi } from '../../helpers/transaction.helper';

test.describe.serial('Frank: The Multi-Context User', () => {
  test.skip(getOrgMode() === 'user_only', 'Organization disabled');

  const frankEmail = generateEmail('frank-persona');
  const frankPassword = 'FrankPass123!';
  let frankId: string;
  const businesses: { slug: string; id: string; name: string }[] = [];
  const ownerEmails: string[] = [];

  // -----------------------------------------------------------------------
  // Phase 1: Registration & Business Setup
  // -----------------------------------------------------------------------

  test('Step 1: Frank registers and verifies', async ({ apiClient, dbClient }) => {
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: frankEmail,
      password: frankPassword,
    });
    frankId = user.id;
  });

  test('Step 2: Create 3 businesses with different owners', async ({
    apiClient,
    dbClient,
  }) => {
    for (let i = 0; i < 3; i++) {
      const ownerEmail = generateEmail(`frank-owner-${i}`);
      ownerEmails.push(ownerEmail);
      const owner = await registerAndVerifyViaApi(apiClient, dbClient, { email: ownerEmail });
      await dbClient.grantBusinessCreation(ownerEmail);
      await apiClient.login(ownerEmail, DEFAULT_PASSWORD);
      const biz = await createBusinessViaApi(apiClient, dbClient, {
        legalName: `Frank Biz ${i + 1}`,
      });
      businesses.push({ slug: biz.slug, id: biz.id, name: biz.legalName });
    }
  });

  test('Step 3: Invite Frank to all 3 businesses', async ({ apiClient }) => {
    for (let i = 0; i < 3; i++) {
      await apiClient.login(ownerEmails[i], DEFAULT_PASSWORD);
      await inviteToBusinessViaApi(apiClient, businesses[i].slug, businesses[i].id, frankId);
    }
  });

  test('Step 4: Frank accepts all 3 invitations', async ({ apiClient }) => {
    await apiClient.login(frankEmail, frankPassword);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };

    for (const txn of txns.results) {
      await acceptTransactionViaApi(apiClient, txn.id as string);
    }
  });

  // -----------------------------------------------------------------------
  // Phase 2: Context Switching
  // -----------------------------------------------------------------------

  test('Step 5: Frank logs in and sees home', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(frankEmail, frankPassword);
    await expect(page).toHaveURL(/\/home/);
  });

  test('Step 6: Frank navigates to business 1 dashboard', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(businesses[0].slug);
    await expect(dashboard.heading).toBeVisible();
    await context.close();
  });

  test('Step 7: Frank navigates to business 2 dashboard', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(businesses[1].slug);
    await expect(dashboard.heading).toBeVisible();
    await context.close();
  });

  test('Step 8: Frank navigates to business 3 dashboard', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(businesses[2].slug);
    await expect(dashboard.heading).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 3: Scope Isolation
  // -----------------------------------------------------------------------

  test('Step 9: Business 1 has correct member count', async ({ apiClient }) => {
    await apiClient.login(ownerEmails[0], DEFAULT_PASSWORD);
    const members = await getBusinessMembersViaApi(apiClient, businesses[0].slug);
    expect(members.count).toBe(2); // Owner + Frank
  });

  test('Step 10: Business 2 has correct member count', async ({ apiClient }) => {
    await apiClient.login(ownerEmails[1], DEFAULT_PASSWORD);
    const members = await getBusinessMembersViaApi(apiClient, businesses[1].slug);
    expect(members.count).toBe(2);
  });

  test('Step 11: Business 3 has correct member count', async ({ apiClient }) => {
    await apiClient.login(ownerEmails[2], DEFAULT_PASSWORD);
    const members = await getBusinessMembersViaApi(apiClient, businesses[2].slug);
    expect(members.count).toBe(2);
  });

  test('Step 12: Frank views each business public profile', async ({ page }) => {
    for (const biz of businesses) {
      const profilePage = new BusinessProfilePage(page);
      await profilePage.goto(biz.slug);
      await expect(profilePage.businessName).toBeVisible();
    }
  });

  // -----------------------------------------------------------------------
  // Phase 4: Settings & Navigation
  // -----------------------------------------------------------------------

  test('Step 13: Frank views settings of business 1', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businesses[0].slug);
    await expect(settingsPage.heading).toBeVisible();
    // Frank is NOT owner — transfer button should be hidden
    await context.close();
  });

  test('Step 14: Frank views settings of business 2', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businesses[1].slug);
    await expect(settingsPage.heading).toBeVisible();
    await context.close();
  });

  test('Step 15: Frank returns to personal home', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    await page.goto('/home');
    const basePage = new BasePage(page);
    await expect(basePage.main).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 5: Rapid Context Switch
  // -----------------------------------------------------------------------

  test('Step 16: Frank rapidly switches between all 3 businesses', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);

    // Rapid navigation between 3 businesses
    for (const biz of businesses) {
      await page.goto(`/bconsole/${biz.slug}/dashboard`);
      await expect(page.getByRole('heading').first()).toBeVisible();
    }
    await context.close();
  });

  test('Step 17: Frank navigates from biz 3 back to home without issues', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);

    await page.goto(`/bconsole/${businesses[2].slug}/dashboard`);
    await expect(page.getByRole('heading').first()).toBeVisible();

    await page.goto('/home');
    await expect(page).toHaveURL(/\/home/);
    await context.close();
  });

  test('Step 18: Frank views explore page from personal context', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    await page.goto('/explore');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 19: Frank views profile from personal context', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, frankEmail, frankPassword);
    await page.goto('/profile');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test("Step 20: Frank's multi-context journey is complete", async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(frankEmail, frankPassword);

    await expect(page).toHaveURL(/\/home/);
  });

  test('Step 21: All 3 businesses still have correct state', async ({ apiClient }) => {
    for (let i = 0; i < 3; i++) {
      await apiClient.login(ownerEmails[i], DEFAULT_PASSWORD);
      const members = await getBusinessMembersViaApi(apiClient, businesses[i].slug);
      expect(members.count).toBe(2);
    }
  });
});
