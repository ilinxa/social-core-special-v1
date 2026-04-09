/**
 * Persona: Carol — The Platform Admin
 *
 * A platform administrator who manages the platform, businesses,
 * CMS content, and forms from the platform console.
 *
 * 17 progressive steps.
 *
 * @layer L3
 * @system auth, platform, business, cms, forms
 * @parameters P1 (Auth), P2 (Navigation), P5 (CRUD), P6 (RBAC)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { BasePage } from '../../pages/base.page';
import { isSystemEnabled, getOrgMode } from '../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD } from '../../lib/constants';
import { generateEmail } from '../../lib/utils';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { createBusinessViaApi } from '../../helpers/business.helper';
import { createCmsSiteViaApi, createCmsPageViaApi, publishCmsPageViaApi } from '../../helpers/cms.helper';
import { createTemplateViaApi, addFieldViaApi, publishTemplateViaApi } from '../../helpers/form.helper';
import { getPlatformViaApi, getPlatformMembersViaApi } from '../../helpers/platform.helper';

test.describe.serial('Carol: The Platform Admin', () => {
  const carolEmail = TEST_USERS.platformAdmin.email;
  const carolPassword = TEST_USERS.platformAdmin.password;
  let cmsSiteSlug: string;
  let cmsSiteId: string;
  let cmsPageSlug: string;

  // -----------------------------------------------------------------------
  // Phase 1: Login & Dashboard
  // -----------------------------------------------------------------------

  test('Step 1: Carol logs into the platform', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(carolEmail, carolPassword);
    await expect(page).toHaveURL(/\/(home|dashboard)/);
  });

  test('Step 2: Carol navigates to platform console dashboard', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/pconsole/dashboard');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 3: Carol views the platform account via API', async ({ apiClient }) => {
    await apiClient.login(carolEmail, carolPassword);
    const platform = await getPlatformViaApi(apiClient);
    expect(platform).toBeTruthy();
  });

  test('Step 4: Carol views platform members', async ({ apiClient }) => {
    await apiClient.login(carolEmail, carolPassword);
    const members = await getPlatformMembersViaApi(apiClient);
    expect(members.count).toBeGreaterThanOrEqual(1); // At least Carol
  });

  // -----------------------------------------------------------------------
  // Phase 2: Business Management
  // -----------------------------------------------------------------------

  test('Step 5: Carol views the business list page', async ({ browser }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/pconsole/businesses');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 6: Carol creates a test business for admin management', async ({
    apiClient,
    dbClient,
  }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const owner = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('carol-biz-owner'),
    });
    await dbClient.grantBusinessCreation(owner.email);
    await apiClient.login(owner.email, DEFAULT_PASSWORD);
    const biz = await createBusinessViaApi(apiClient, dbClient, {
      legalName: 'Carol Admin Managed Biz',
    });
    expect(biz.slug).toBeTruthy();
  });

  // -----------------------------------------------------------------------
  // Phase 3: CMS Management
  // -----------------------------------------------------------------------

  test('Step 7: Carol creates a CMS site via API', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('cms'), 'CMS disabled');

    await apiClient.login(carolEmail, carolPassword);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Carol Test Site',
      slug: 'carol-test-site',
      description: 'A CMS site managed by Carol',
    });
    cmsSiteSlug = site.slug;
    cmsSiteId = site.id;
    expect(site.id).toBeTruthy();
  });

  test('Step 8: Carol creates a CMS page', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('cms'), 'CMS disabled');

    await apiClient.login(carolEmail, carolPassword);
    const page = await createCmsPageViaApi(apiClient, {
      site_id: cmsSiteId,
      title: 'Welcome to Our Platform',
      slug: 'welcome',
      path: '/welcome',
      page_type: 'content',
      order: 0,
    });
    cmsPageSlug = page.slug;
    expect(page.status).toBe('draft');
  });

  test('Step 9: Carol publishes the CMS page', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('cms'), 'CMS disabled');

    await apiClient.login(carolEmail, carolPassword);
    await publishCmsPageViaApi(apiClient, cmsSiteSlug, cmsPageSlug);
  });

  test('Step 10: Carol views the CMS section in platform console', async ({ browser }) => {
    test.skip(!isSystemEnabled('cms'), 'CMS disabled');

    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/cconsole/sites');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 4: Forms Management
  // -----------------------------------------------------------------------

  test('Step 11: Carol creates a platform-scoped form template', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    await apiClient.login(carolEmail, carolPassword);

    // Get platform ID
    const platform = await getPlatformViaApi(apiClient);
    const platformId = (platform as { id: string }).id;

    const template = await createTemplateViaApi(apiClient, 'platform', platformId, {
      name: 'Platform Feedback Form',
      description: 'Collect feedback from platform users',
    });
    expect(template.id).toBeTruthy();

    await addFieldViaApi(apiClient, template.id, {
      field_key: 'feedback',
      field_type: 'textarea',
      label: 'Your Feedback',
      is_required: true,
      order: 1,
    });

    await publishTemplateViaApi(apiClient, template.id);
  });

  test('Step 12: Carol views forms section in platform console', async ({ browser }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/pconsole/forms');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 5: Audit & Verification
  // -----------------------------------------------------------------------

  test('Step 13: Carol views platform transactions page', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/pconsole/transactions');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 14: Carol views platform audit page', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/pconsole/audit');
    // May be stub but should render
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 15: Carol navigates back to dashboard', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/pconsole/dashboard');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 16: Carol returns to personal home', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/home');
    const basePage = new BasePage(page);
    await expect(basePage.main).toBeVisible();
    await context.close();
  });

  test("Step 17: Carol's admin journey is complete", async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, carolEmail, carolPassword);

    await page.goto('/profile');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });
});
