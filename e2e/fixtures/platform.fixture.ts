/**
 * Platform context fixture — provides platform admin access.
 *
 * Extends auth fixtures with platform context for platform console tests.
 *
 * Usage:
 * ```typescript
 * import { test, expect } from '../../fixtures/platform.fixture';
 *
 * test('platform dashboard renders', async ({ platformAdminPage, platformContext }) => {
 *   await platformAdminPage.goto('/pconsole');
 * });
 * ```
 */

import { test as authTest } from './auth.fixture';

type PlatformContext = {
  id: string;
  configured: boolean;
};

type PlatformFixtures = {
  /** Platform singleton context (configured by global-setup) */
  platformContext: PlatformContext;
};

export const test = authTest.extend<PlatformFixtures>({
  platformContext: async ({ apiClient }, use) => {
    // Platform is a singleton — just fetch its state
    const res = await apiClient.get('platform/account/');

    if (!res.ok) {
      // Platform may not be configured yet — provide defaults
      await use({ id: '', configured: false });
      return;
    }

    const data = (await res.json()) as { id: string };
    await use({
      id: data.id,
      configured: true,
    });
  },
});

export { expect } from '@playwright/test';
