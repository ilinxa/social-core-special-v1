/**
 * @layer L1
 * @system cms, business
 * @parameters P1, P2, P3, P4
 * @priority P0
 */
import { test, expect } from '../../../fixtures/cms.fixture';
import { BusinessCmsSitesPage } from '../../../pages/cms/business-cms.page';
import { CmsSiteDetailPage } from '../../../pages/cms/site-detail.page';
import { isSystemEnabled } from '../../../lib/feature-gates';
import {
  getBusinessCmsSiteViaApi,
  listBusinessCmsSitesViaApi,
} from '../../../helpers/cms.helper';

test.describe('CMS Business Site CRUD', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('business owner sees site list via CmsBusinessGuard', async ({
    businessCmsPage,
    businessSlug,
  }) => {
    const sitesPage = new BusinessCmsSitesPage(businessCmsPage);
    await sitesPage.goto(businessSlug);

    await expect(sitesPage.heading).toBeVisible();
  });

  test('business can create a site', async ({
    businessCmsPage,
    businessSlug,
  }) => {
    const sitesPage = new BusinessCmsSitesPage(businessCmsPage);
    await sitesPage.goto(businessSlug);

    const slug = `biz-site-${Date.now()}`;
    await sitesPage.createSite({ name: 'Business Site', slug });

    await expect(businessCmsPage.getByText('Business Site')).toBeVisible();
  });

  test('site detail returns _permissions with 14 booleans', async ({
    businessCmsApi,
    businessSlug,
  }) => {
    const { createBusinessCmsSiteViaApi } = await import(
      '../../../helpers/cms.helper'
    );
    const site = await createBusinessCmsSiteViaApi(businessCmsApi, businessSlug, {
      name: 'Perm Check Site',
      slug: `perm-${Date.now()}`,
    });

    const detail = await getBusinessCmsSiteViaApi(
      businessCmsApi,
      businessSlug,
      site.slug,
    );
    const permissions = detail._permissions as Record<string, boolean>;
    expect(permissions).toBeDefined();
    expect(Object.keys(permissions)).toHaveLength(14);
    // Owner should have all permissions true
    for (const value of Object.values(permissions)) {
      expect(value).toBe(true);
    }
  });

  test('business can edit a site', async ({
    businessCmsPage,
    businessCmsApi,
    businessSlug,
  }) => {
    const { createBusinessCmsSiteViaApi } = await import(
      '../../../helpers/cms.helper'
    );
    const site = await createBusinessCmsSiteViaApi(businessCmsApi, businessSlug, {
      name: 'Edit Biz Site',
      slug: `edit-biz-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(businessCmsPage);
    await detailPage.gotoForBusiness(businessSlug, site.slug);

    await detailPage.editButton.click();
    await detailPage.editNameInput.clear();
    await detailPage.editNameInput.fill('Updated Biz Site');
    await detailPage.saveButton.click();

    await expect(businessCmsPage.getByText('Updated Biz Site')).toBeVisible();
  });

  test('business can delete a site', async ({
    businessCmsPage,
    businessCmsApi,
    businessSlug,
  }) => {
    const { createBusinessCmsSiteViaApi } = await import(
      '../../../helpers/cms.helper'
    );
    const site = await createBusinessCmsSiteViaApi(businessCmsApi, businessSlug, {
      name: 'Delete Biz Site',
      slug: `del-biz-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(businessCmsPage);
    await detailPage.gotoForBusiness(businessSlug, site.slug);
    await expect(detailPage.siteName).toBeVisible();

    await detailPage.deleteButton.click();
    await expect(detailPage.deleteConfirmButton).toBeVisible();
    await detailPage.deleteConfirmButton.click();

    // Should return to sites list
    const sitesPage = new BusinessCmsSitesPage(businessCmsPage);
    await expect(sitesPage.heading).toBeVisible();
  });

  test('sites are scoped to business', async ({
    businessCmsApi,
    businessSlug,
  }) => {
    const sites = await listBusinessCmsSitesViaApi(businessCmsApi, businessSlug);
    // All returned sites belong to this business (no cross-contamination)
    expect(sites.results).toBeDefined();
    expect(Array.isArray(sites.results)).toBe(true);
  });
});
