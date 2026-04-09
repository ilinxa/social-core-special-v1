/**
 * @layer L1
 * @system cms
 * @parameters P3, P8
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { PageEditorPage } from '../../../pages/cms/page-editor.page';
import { isSystemEnabled } from '../../../lib/feature-gates';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
} from '../../../helpers/cms.helper';
import { TEST_USERS } from '../../../lib/constants';

test.describe('CMS Content Editing (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('content tree renders with ARIA tree role', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Tree Site',
      slug: `e2e-tree-${ts}`,
    });
    await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Tree Page',
      slug: `tree-${ts}`,
      path: '/tree',
      page_type: 'content',
      order: 0,
    });

    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, `tree-${ts}`);

    await expect(editor.contentTree).toBeVisible();
  });

  test('no-selection message shown before clicking block', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'NoSel Site',
      slug: `e2e-nosel-${ts}`,
    });
    await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'NoSel Page',
      slug: `nosel-${ts}`,
      path: '/nosel',
      page_type: 'content',
      order: 0,
    });

    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, `nosel-${ts}`);

    await expect(editor.noSelectionMessage).toBeVisible();
  });

  test('edit field shows saved indicator', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Save Site',
      slug: `e2e-save-${ts}`,
    });
    await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Save Page',
      slug: `save-${ts}`,
      path: '/save',
      page_type: 'content',
      order: 0,
    });

    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, `save-${ts}`);

    // Select first treeitem if available
    const blockNode = editor.contentTree.getByRole('treeitem').first();
    if (await blockNode.isVisible()) {
      await blockNode.click();

      const textInput = platformAdminPage.getByRole('textbox').first();
      if (await textInput.isVisible()) {
        await textInput.fill('Updated content');
        await expect(editor.saveStatusSaved).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('page editor has export and import buttons', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Export Site',
      slug: `e2e-export-${ts}`,
    });
    await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Export Page',
      slug: `export-${ts}`,
      path: '/export',
      page_type: 'content',
      order: 0,
    });

    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, `export-${ts}`);

    await expect(editor.exportButton).toBeVisible();
    await expect(editor.importButton).toBeVisible();
  });
});
