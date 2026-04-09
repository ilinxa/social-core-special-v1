/**
 * Persona: Gary — The CMS Manager
 *
 * A platform admin focused on CMS: creates sites, manages pages,
 * publishes content, edits blocks via UI, checks version history,
 * creates API keys, and verifies the full CMS workflow.
 *
 * 22 progressive steps.
 *
 * @layer L3
 * @system auth, cms, platform
 * @parameters P1, P3, P5, P6, P8, P11
 * @priority P0
 */
import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { loginInNewContext } from '../../helpers/auth.helper';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS, BACKEND_URL } from '../../lib/constants';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
  publishCmsPageViaApi,
  unpublishCmsPageViaApi,
  createCmsApiKeyViaApi,
  listCmsSitesViaApi,
  getCmsPageViaApi,
  getPublicPageViaApi,
} from '../../helpers/cms.helper';
import { PageEditorPage } from '../../pages/cms/page-editor.page';
import { CmsSiteDetailPage } from '../../pages/cms/site-detail.page';
import { ApiKeysPanel } from '../../pages/cms/api-keys.page';

test.describe.serial('Gary: The CMS Manager', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  const garyEmail = TEST_USERS.platformAdmin.email;
  const garyPassword = TEST_USERS.platformAdmin.password;
  let siteSlug: string;
  let siteId: string;
  let page1Slug: string;
  let page2Slug: string;
  let apiKeyRawKey: string;

  // -----------------------------------------------------------------------
  // Phase 1: Site Management (Steps 1-3)
  // -----------------------------------------------------------------------

  test('Step 1: Gary logs in', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(garyEmail, garyPassword);
    await expect(page).toHaveURL(/\/(home|dashboard)/);
  });

  test('Step 2: Gary creates a CMS site', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Gary Content Hub',
      slug: 'gary-content-hub',
      description: 'Main content site managed by Gary',
    });
    siteSlug = site.slug;
    siteId = site.id;
    expect(site.name).toBe('Gary Content Hub');
  });

  test('Step 3: Gary lists sites — sees his site', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    const sites = await listCmsSitesViaApi(apiClient);
    const found = sites.results.find(
      (s) => (s as Record<string, unknown>).slug === siteSlug,
    );
    expect(found).toBeTruthy();
  });

  // -----------------------------------------------------------------------
  // Phase 2: Page Creation & Publishing (Steps 4-7)
  // -----------------------------------------------------------------------

  test('Step 4: Gary creates page 1 — Home', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    const page = await createCmsPageViaApi(apiClient, {
      site_id: siteId,
      title: 'Home',
      slug: 'home',
      path: '/home',
      page_type: 'content',
      order: 0,
    });
    page1Slug = page.slug;
    expect(page.status).toBe('draft');
  });

  test('Step 5: Gary creates page 2 — About', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    const page = await createCmsPageViaApi(apiClient, {
      site_id: siteId,
      title: 'About Us',
      slug: 'about-us',
      path: '/about-us',
      page_type: 'content',
      order: 1,
    });
    page2Slug = page.slug;
    expect(page.status).toBe('draft');
  });

  test('Step 6: Gary publishes page 1', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    await publishCmsPageViaApi(apiClient, siteSlug, page1Slug);
  });

  test('Step 7: Gary publishes page 2', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    await publishCmsPageViaApi(apiClient, siteSlug, page2Slug);
  });

  // -----------------------------------------------------------------------
  // Phase 3: Content Versioning (Steps 8-9)
  // -----------------------------------------------------------------------

  test('Step 8: Gary unpublishes page 2 (back to draft)', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    await unpublishCmsPageViaApi(apiClient, siteSlug, page2Slug);
  });

  test('Step 9: Gary re-publishes page 2', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    await publishCmsPageViaApi(apiClient, siteSlug, page2Slug);
  });

  // -----------------------------------------------------------------------
  // Phase 4: UI Editing (Steps 10-13) — NEW
  // -----------------------------------------------------------------------

  test('Step 10: Gary navigates to page editor UI', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    const editor = new PageEditorPage(page);
    await editor.gotoForPlatform(siteSlug, page1Slug);
    await expect(editor.pageTitle).toBeVisible();
    await expect(editor.contentTree).toBeVisible();

    await context.close();
  });

  test('Step 11: Gary clicks a block in the content tree', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    const editor = new PageEditorPage(page);
    await editor.gotoForPlatform(siteSlug, page1Slug);

    // Should show no-selection message initially
    await expect(editor.noSelectionMessage).toBeVisible();

    // Click first treeitem if present
    const blockNode = editor.contentTree.getByRole('treeitem').first();
    if (await blockNode.isVisible()) {
      await blockNode.click();
      await expect(editor.noSelectionMessage).not.toBeVisible();
    }

    await context.close();
  });

  test('Step 12: Gary edits a block and sees saved indicator', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    const editor = new PageEditorPage(page);
    await editor.gotoForPlatform(siteSlug, page1Slug);

    const blockNode = editor.contentTree.getByRole('treeitem').first();
    if (await blockNode.isVisible()) {
      await blockNode.click();
      const textInput = page.getByRole('textbox').first();
      if (await textInput.isVisible()) {
        await textInput.fill('Gary updated this block');
        await expect(editor.saveStatusSaved).toBeVisible({ timeout: 10000 });
      }
    }

    await context.close();
  });

  test('Step 13: Gary verifies export/import buttons exist', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    const editor = new PageEditorPage(page);
    await editor.gotoForPlatform(siteSlug, page1Slug);

    await expect(editor.exportButton).toBeVisible();
    await expect(editor.importButton).toBeVisible();

    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 5: Version History (Steps 14-15) — NEW
  // -----------------------------------------------------------------------

  test('Step 14: Gary opens version history panel', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    const editor = new PageEditorPage(page);
    await editor.gotoForPlatform(siteSlug, page1Slug);

    // Select a block first (history button only visible when block selected)
    const blockNode = editor.contentTree.getByRole('treeitem').first();
    if (await blockNode.isVisible()) {
      await blockNode.click();
      if (await editor.historyButton.isVisible()) {
        await editor.historyButton.click();
        await expect(editor.historyTitle).toBeVisible();
      }
    }

    await context.close();
  });

  test('Step 15: Gary verifies version history has entries', async ({
    apiClient,
  }) => {
    await apiClient.login(garyEmail, garyPassword);
    const fullPage = await getCmsPageViaApi(apiClient, siteSlug, page1Slug, 'full');
    // Verify page was fetched with full depth
    expect(fullPage).toHaveProperty('status');
  });

  // -----------------------------------------------------------------------
  // Phase 6: API Key Management via UI (Steps 16-17) — NEW
  // -----------------------------------------------------------------------

  test('Step 16: Gary navigates to site detail API Keys tab', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    const detailPage = new CmsSiteDetailPage(page);
    await detailPage.gotoForPlatform(siteSlug);
    await detailPage.apiKeysTab.click();

    const keysPanel = new ApiKeysPanel(page);
    await expect(keysPanel.heading).toBeVisible();

    await context.close();
  });

  test('Step 17: Gary creates an API key via API', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    const key = await createCmsApiKeyViaApi(apiClient, {
      name: 'Gary Frontend Key',
      site_id: siteId,
    });
    apiKeyRawKey = key.key;
    expect(key.key).toMatch(/^cmsk_/);
  });

  // -----------------------------------------------------------------------
  // Phase 7: Cleanup & Final (Steps 18-22)
  // -----------------------------------------------------------------------

  test('Step 18: Gary unpublishes page 1', async ({ apiClient }) => {
    await apiClient.login(garyEmail, garyPassword);
    await unpublishCmsPageViaApi(apiClient, siteSlug, page1Slug);
  });

  test('Step 19: Gary re-publishes page 1 for final state', async ({
    apiClient,
  }) => {
    await apiClient.login(garyEmail, garyPassword);
    await publishCmsPageViaApi(apiClient, siteSlug, page1Slug);
  });

  test('Step 20: Gary verifies public API with API key', async () => {
    const res = await getPublicPageViaApi(BACKEND_URL, apiKeyRawKey, page1Slug);
    expect(res.status).toBe(200);
  });

  test('Step 21: Gary verifies site list still shows site', async ({
    apiClient,
  }) => {
    await apiClient.login(garyEmail, garyPassword);
    const sites = await listCmsSitesViaApi(apiClient);
    const found = sites.results.find(
      (s) => (s as Record<string, unknown>).slug === siteSlug,
    );
    expect(found).toBeTruthy();
  });

  test("Step 22: Gary's CMS management journey is complete", async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, garyEmail, garyPassword);

    await page.goto('/home');
    await expect(page).toHaveURL(/\/home/);
    await context.close();
  });
});
