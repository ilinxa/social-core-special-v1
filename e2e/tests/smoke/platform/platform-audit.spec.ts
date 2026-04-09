/**
 * Platform audit log smoke tests.
 *
 * @layer L1
 * @system platform
 * @parameters P1, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformAuditPage } from '../../../pages/platform/platform-console.page';

test.describe('Platform Audit Log', () => {
  test('audit page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const auditPage = new PlatformAuditPage(page);
    await auditPage.goto();

    await expect(auditPage.heading).toBeVisible();
  });
});
