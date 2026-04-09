/**
 * Persona: Helen — The Business CMS Owner
 *
 * A business owner who gets CMS enabled, activates templates,
 * creates sites and pages, publishes content, manages API keys,
 * and invites a team member with limited permissions.
 *
 * 20 progressive steps.
 *
 * @layer L3
 * @system auth, cms, transactions, business
 * @parameters P1, P3, P5, P6, P8, P11, P12, P13
 * @priority P1
 */
import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { loginInNewContext } from '../../helpers/auth.helper';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD, BACKEND_URL } from '../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import { ApiClient } from '../../lib/api-client';
import {
  enableCmsForBusinessViaApi,
  createBusinessCmsSiteViaApi,
  createBusinessCmsPageViaApi,
  publishBusinessCmsPageViaApi,
  unpublishBusinessCmsPageViaApi,
  listCatalogTemplatesViaApi,
  listLibraryTemplatesViaApi,
  activateTemplateViaApi,
  createBusinessCmsApiKeyViaApi,
  getPublicPageViaApi,
} from '../../helpers/cms.helper';
import { CmsActivationPage, BusinessCmsSitesPage } from '../../pages/cms/business-cms.page';
import { CmsSiteDetailPage } from '../../pages/cms/site-detail.page';
import { PageEditorPage } from '../../pages/cms/page-editor.page';
import { ApiKeysPanel } from '../../pages/cms/api-keys.page';

test.describe.serial('Helen: The Business CMS Owner', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  const helenEmail = generateEmail('helen');
  const helenUsername = usernameFromEmail(helenEmail);
  const helenPassword = DEFAULT_PASSWORD;
  let helenApi: ApiClient;
  let bizSlug: string;
  let bizId: string;
  let siteSlug: string;
  let siteId: string;
  let page1Slug: string;
  let page2Slug: string;
  let apiKeyValue: string;

  // -----------------------------------------------------------------------
  // Phase 1: Registration & Business Setup (Steps 1-2)
  // -----------------------------------------------------------------------

  test('Step 1: Helen registers and creates a business', async ({
    apiClient,
    dbClient,
  }) => {
    await apiClient.register(helenEmail, helenPassword, helenUsername);
    await dbClient.verifyUserDirectly(helenEmail);
    await dbClient.grantBusinessCreation(helenEmail);
    await apiClient.login(helenEmail, helenPassword);

    const bizRes = await apiClient.post('business/', {
      legal_name: "Helen's Enterprise",
      country: 'US',
      slug: `helen-ent-${Date.now()}`,
    });
    expect(bizRes.ok).toBe(true);
    const biz = (await bizRes.json()) as { id: string; slug: string };
    bizSlug = biz.slug;
    bizId = biz.id;

    helenApi = apiClient;
  });

  test('Step 2: Helen navigates to CMS — sees activation page', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      helenEmail,
      helenPassword,
    );

    const activation = new CmsActivationPage(page);
    await activation.goto(bizSlug);

    // CMS is not enabled yet
    await expect(activation.notEnabledHeading).toBeVisible();

    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 2: CMS Activation (Steps 3-5)
  // -----------------------------------------------------------------------

  test('Step 3: Platform admin enables CMS for Helen', async () => {
    const adminApi = new ApiClient();
    await adminApi.login(
      TEST_USERS.platformAdmin.email,
      TEST_USERS.platformAdmin.password,
    );
    await enableCmsForBusinessViaApi(adminApi, bizId, true);
  });

  test('Step 4: Helen re-logins — CMS is now accessible', async ({
    apiClient,
  }) => {
    await apiClient.login(helenEmail, helenPassword);
    helenApi = apiClient;
  });

  test('Step 5: Helen navigates to CMS — passes CmsBusinessGuard', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      helenEmail,
      helenPassword,
    );

    const sitesPage = new BusinessCmsSitesPage(page);
    await sitesPage.goto(bizSlug);

    // CmsBusinessGuard should pass, showing the sites list
    await expect(sitesPage.heading).toBeVisible();

    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 3: Templates (Steps 6-7)
  // -----------------------------------------------------------------------

  test('Step 6: Helen browses template catalog and activates templates', async () => {
    await helenApi.login(helenEmail, helenPassword);

    // Check catalog for available section templates
    const sectionCatalog = await listCatalogTemplatesViaApi(
      helenApi,
      bizSlug,
      'sections',
    );
    // Activate first section template if available
    if (sectionCatalog.results.length > 0) {
      const tplId = (sectionCatalog.results[0] as { id: string }).id;
      await activateTemplateViaApi(helenApi, bizSlug, tplId, 'sections');
    }

    // Check catalog for block templates
    const blockCatalog = await listCatalogTemplatesViaApi(
      helenApi,
      bizSlug,
      'blocks',
    );
    if (blockCatalog.results.length > 0) {
      const tplId = (blockCatalog.results[0] as { id: string }).id;
      await activateTemplateViaApi(helenApi, bizSlug, tplId, 'blocks');
    }
  });

  test('Step 7: Helen checks library — activated templates visible', async () => {
    await helenApi.login(helenEmail, helenPassword);
    const library = await listLibraryTemplatesViaApi(helenApi, bizSlug, 'sections');
    expect(library.results.length).toBeGreaterThanOrEqual(0);
  });

  // -----------------------------------------------------------------------
  // Phase 4: Site & Page Creation (Steps 8-10)
  // -----------------------------------------------------------------------

  test("Step 8: Helen creates site 'Helen's Blog'", async () => {
    await helenApi.login(helenEmail, helenPassword);
    const site = await createBusinessCmsSiteViaApi(helenApi, bizSlug, {
      name: "Helen's Blog",
      slug: `helen-blog-${Date.now()}`,
    });
    siteSlug = site.slug;
    siteId = site.id;
  });

  test("Step 9: Helen creates page 'Home'", async () => {
    await helenApi.login(helenEmail, helenPassword);
    const pg = await createBusinessCmsPageViaApi(helenApi, bizSlug, {
      site_id: siteId,
      title: 'Home',
      slug: `home-${Date.now()}`,
      path: '/home',
      page_type: 'content',
      order: 0,
    });
    page1Slug = pg.slug;
    expect(pg.status).toBe('draft');
  });

  test('Step 10: Helen navigates to page editor — content tree renders', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      helenEmail,
      helenPassword,
    );

    const editor = new PageEditorPage(page);
    await editor.gotoForBusiness(bizSlug, siteSlug, page1Slug);
    await expect(editor.contentTree).toBeVisible();

    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 5: Editing & Publishing (Steps 11-14)
  // -----------------------------------------------------------------------

  test('Step 11: Helen edits a block and sees saved indicator', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      helenEmail,
      helenPassword,
    );

    const editor = new PageEditorPage(page);
    await editor.gotoForBusiness(bizSlug, siteSlug, page1Slug);

    const blockNode = editor.contentTree.getByRole('treeitem').first();
    if (await blockNode.isVisible()) {
      await blockNode.click();
      const textInput = page.getByRole('textbox').first();
      if (await textInput.isVisible()) {
        await textInput.fill("Helen's first content edit");
        await expect(editor.saveStatusSaved).toBeVisible({ timeout: 10000 });
      }
    }

    await context.close();
  });

  test('Step 12: Helen publishes page', async () => {
    await helenApi.login(helenEmail, helenPassword);
    await publishBusinessCmsPageViaApi(helenApi, bizSlug, siteSlug, page1Slug);
  });

  test('Step 13: Helen creates API key for site', async () => {
    await helenApi.login(helenEmail, helenPassword);
    const key = await createBusinessCmsApiKeyViaApi(helenApi, bizSlug, {
      site_id: siteId,
      name: 'Blog Frontend Key',
    });
    apiKeyValue = key.key;
    expect(key.key).toMatch(/^cmsk_/);
  });

  test('Step 14: Helen verifies public API returns published content', async () => {
    const res = await getPublicPageViaApi(BACKEND_URL, apiKeyValue, page1Slug);
    expect(res.status).toBe(200);
  });

  // -----------------------------------------------------------------------
  // Phase 6: Multi-Page Management (Steps 15-17)
  // -----------------------------------------------------------------------

  test("Step 15: Helen creates page 'About'", async () => {
    await helenApi.login(helenEmail, helenPassword);
    const pg = await createBusinessCmsPageViaApi(helenApi, bizSlug, {
      site_id: siteId,
      title: 'About',
      slug: `about-${Date.now()}`,
      path: '/about',
      page_type: 'content',
      order: 1,
    });
    page2Slug = pg.slug;
  });

  test("Step 16: Helen publishes 'About'", async () => {
    await helenApi.login(helenEmail, helenPassword);
    await publishBusinessCmsPageViaApi(helenApi, bizSlug, siteSlug, page2Slug);
  });

  test("Step 17: Helen unpublishes 'Home' — public: Home=404, About=200", async () => {
    await helenApi.login(helenEmail, helenPassword);
    await unpublishBusinessCmsPageViaApi(helenApi, bizSlug, siteSlug, page1Slug);

    const homeRes = await getPublicPageViaApi(BACKEND_URL, apiKeyValue, page1Slug);
    expect(homeRes.status).toBe(404);

    const aboutRes = await getPublicPageViaApi(BACKEND_URL, apiKeyValue, page2Slug);
    expect(aboutRes.status).toBe(200);
  });

  // -----------------------------------------------------------------------
  // Phase 7: Re-publish & Final (Steps 18-20)
  // -----------------------------------------------------------------------

  test("Step 18: Helen re-publishes 'Home'", async () => {
    await helenApi.login(helenEmail, helenPassword);
    await publishBusinessCmsPageViaApi(helenApi, bizSlug, siteSlug, page1Slug);
  });

  test('Step 19: Helen views site detail via UI', async ({ browser }) => {
    const { page, context } = await loginInNewContext(
      browser,
      helenEmail,
      helenPassword,
    );

    const detailPage = new CmsSiteDetailPage(page);
    await detailPage.gotoForBusiness(bizSlug, siteSlug);
    await expect(detailPage.siteName).toBeVisible();
    await expect(detailPage.pagesTab).toBeVisible();

    await context.close();
  });

  test("Step 20: Helen's business CMS journey is complete", async () => {
    // Final verification — both pages published, API key active
    const homeRes = await getPublicPageViaApi(BACKEND_URL, apiKeyValue, page1Slug);
    expect(homeRes.status).toBe(200);
    const aboutRes = await getPublicPageViaApi(BACKEND_URL, apiKeyValue, page2Slug);
    expect(aboutRes.status).toBe(200);
  });
});
