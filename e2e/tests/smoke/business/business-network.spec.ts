/**
 * Business network management smoke tests (followers + connections).
 *
 * @layer L1
 * @system network
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import {
  BusinessFollowersPage,
  BusinessConnectionsPage,
} from '../../../pages/business/business-network.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Network', () => {
  test('followers page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const followersPage = new BusinessFollowersPage(page);
    await followersPage.goto(E2E_BUSINESS.slug);

    await expect(followersPage.heading).toBeVisible();
  });

  test('connections page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const connectionsPage = new BusinessConnectionsPage(page);
    await connectionsPage.goto(E2E_BUSINESS.slug);

    await expect(connectionsPage.heading).toBeVisible();
  });
});
