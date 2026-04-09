/**
 * @layer L1
 * @system cms
 * @parameters P13
 * @priority P0
 */
import { test, expect } from '../../../fixtures/cms.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import {
  listCatalogTemplatesViaApi,
  listLibraryTemplatesViaApi,
  activateTemplateViaApi,
  deactivateTemplateViaApi,
} from '../../../helpers/cms.helper';

test.describe('CMS Business Template Catalog', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('catalog shows eligible templates', async ({
    businessCmsApi,
    businessSlug,
  }) => {
    const catalog = await listCatalogTemplatesViaApi(
      businessCmsApi,
      businessSlug,
      'sections',
    );
    expect(catalog).toHaveProperty('results');
    expect(Array.isArray(catalog.results)).toBe(true);

    // All templates should have org_type "all" or "business" (not "platform")
    for (const tpl of catalog.results) {
      const orgType = (tpl as { org_type: string }).org_type;
      expect(['all', 'business']).toContain(orgType);
    }
  });

  test('platform-only templates NOT shown in catalog', async ({
    businessCmsApi,
    businessSlug,
  }) => {
    const sectionCatalog = await listCatalogTemplatesViaApi(
      businessCmsApi,
      businessSlug,
      'sections',
    );
    const blockCatalog = await listCatalogTemplatesViaApi(
      businessCmsApi,
      businessSlug,
      'blocks',
    );

    const allTemplates = [...sectionCatalog.results, ...blockCatalog.results];
    for (const tpl of allTemplates) {
      const orgType = (tpl as { org_type: string }).org_type;
      expect(orgType).not.toBe('platform');
    }
  });

  test('activate and deactivate template round-trip', async ({
    businessCmsApi,
    businessSlug,
  }) => {
    // Get catalog block templates
    const catalog = await listCatalogTemplatesViaApi(
      businessCmsApi,
      businessSlug,
      'blocks',
    );

    if (catalog.results.length === 0) {
      // Skip when catalog is empty — template seeding may not have created business-eligible templates
      test.skip(true, 'No block templates available in catalog');
      return;
    }

    const templateId = (catalog.results[0] as { id: string }).id;

    // Activate
    const activation = await activateTemplateViaApi(
      businessCmsApi,
      businessSlug,
      templateId,
      'blocks',
    );
    const activationId = (activation as { id: string }).id;

    // Verify in library
    const library = await listLibraryTemplatesViaApi(
      businessCmsApi,
      businessSlug,
      'blocks',
    );
    expect(library.results.length).toBeGreaterThan(0);

    // Deactivate
    await deactivateTemplateViaApi(
      businessCmsApi,
      businessSlug,
      activationId,
      'blocks',
    );

    // Verify removed from library
    const libraryAfter = await listLibraryTemplatesViaApi(
      businessCmsApi,
      businessSlug,
      'blocks',
    );
    const stillPresent = libraryAfter.results.find(
      (a: Record<string, unknown>) => (a as { id: string }).id === activationId,
    );
    expect(stillPresent).toBeUndefined();
  });
});
