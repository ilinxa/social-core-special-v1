/**
 * Business audit log smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessAuditPage } from '../../../pages/business/business-audit.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Audit Log', () => {
  test('audit page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const auditPage = new BusinessAuditPage(page);
    await auditPage.goto(E2E_BUSINESS.slug);

    await expect(auditPage.heading).toBeVisible();
  });
});
