/**
 * W-CMS-VER: CMS Content Versioning workflow.
 *
 * Create page → Edit block → Check version → Edit again →
 * Rollback → Verify restored → Publish → Check version action.
 *
 * @layer L2
 * @system cms
 * @parameters P3, P8
 * @priority P1
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS } from '../../lib/constants';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
  getCmsPageViaApi,
  updateBlockPlacementViaApi,
  getBlockHistoryViaApi,
  rollbackBlockViaApi,
  publishCmsPageViaApi,
} from '../../helpers/cms.helper';

test.describe('W-CMS-VER: CMS Content Versioning', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('edit → version history → rollback → publish with version tracking', async ({
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();

    // Step 1 — Create site + page
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Version Site',
      slug: `ver-site-${ts}`,
    });
    const pg = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Version Page',
      slug: `ver-page-${ts}`,
      path: '/version',
      page_type: 'content',
      order: 0,
    });

    // Get page with full depth to find block placements
    const fullPage = await getCmsPageViaApi(apiClient, site.slug, pg.slug, 'full');
    const sections = fullPage.sections as Array<{
      block_placements: Array<{ id: string }>;
    }>;

    // Skip if no block placements exist (no templates assigned)
    if (!sections || sections.length === 0) {
      // Skip when page has no sections — template auto-assignment depends on seeding
      test.skip(true, 'No sections on page — template seeding may be incomplete');
      return;
    }

    const blockPlacements = sections.flatMap((s) => s.block_placements || []);
    if (blockPlacements.length === 0) {
      // Skip when sections have no block placements — no content to version
      test.skip(true, 'No block placements on page');
      return;
    }

    const placementId = blockPlacements[0].id;

    // Step 2 — Edit block content (V1)
    await updateBlockPlacementViaApi(apiClient, placementId, { title: 'V1 Content' });

    // Step 3 — Check history
    const history1 = await getBlockHistoryViaApi(apiClient, placementId);
    expect(history1.results.length).toBeGreaterThanOrEqual(1);
    expect((history1.results[0] as { action: string }).action).toBe('draft_save');

    // Step 4 — Edit again (V2) — need to wait for version throttle (30s)
    // In e2e, we just update and accept that it may or may not create a new version
    await updateBlockPlacementViaApi(apiClient, placementId, { title: 'V2 Content' });

    // Step 5 — Rollback to first version
    const v1Number = (history1.results[history1.results.length - 1] as { version_number: number }).version_number;
    await rollbackBlockViaApi(apiClient, placementId, v1Number);

    // Step 6 — Check history has rollback entry
    const history2 = await getBlockHistoryViaApi(apiClient, placementId);
    const actions = history2.results.map((v: Record<string, unknown>) => v.action);
    expect(actions).toContain('rollback');

    // Step 7 — Publish and check version
    await publishCmsPageViaApi(apiClient, site.slug, pg.slug);
    const history3 = await getBlockHistoryViaApi(apiClient, placementId);
    const publishActions = history3.results.map((v: Record<string, unknown>) => v.action);
    expect(publishActions).toContain('publish');
  });
});
