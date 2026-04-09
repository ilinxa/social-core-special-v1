/**
 * Business lifecycle smoke tests (suspend/reactivate/archive).
 *
 * @layer L1
 * @system business
 * @parameters P2, P4, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/business.fixture';
import { BusinessDashboardPage } from '../../../pages/business/business-console.page';

test.describe('Business Lifecycle', () => {
  test('newly created business is active', async ({
    businessOwnerPage,
    businessContext,
  }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(businessContext.slug);

    // Dashboard should render (business is active)
    await expect(dashboard.heading).toBeVisible();
  });
});
