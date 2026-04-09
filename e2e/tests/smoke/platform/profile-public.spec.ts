/**
 * Platform public profile smoke tests.
 *
 * @layer L1
 * @system platform
 * @parameters P1, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { PlatformPublicProfilePage } from '../../../pages/platform/platform-profile.page';

test.describe('Platform Public Profile', () => {
  test('platform profile page renders', async ({ page }) => {
    const profilePage = new PlatformPublicProfilePage(page);
    await profilePage.goto();

    // Should show platform name or not-available message
    await expect(
      profilePage.platformName.or(profilePage.notAvailableMessage),
    ).toBeVisible();
  });
});
