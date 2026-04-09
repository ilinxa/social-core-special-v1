/**
 * Base Playwright fixture — extends `test` with custom fixtures.
 *
 * All test files import `{ test, expect }` from this file instead of `@playwright/test`.
 * This provides:
 *   - `apiClient`: HTTP client for data setup (direct to backend:8001)
 *   - `dbClient`: PostgreSQL client for verification codes, tokens, etc.
 */

import { test as base, expect } from '@playwright/test';
import { ApiClient } from '../lib/api-client';
import { DbClient } from '../lib/db-client';

/**
 * Custom fixture types available in all tests.
 */
type CustomFixtures = {
  /** HTTP API client for test data setup (connects to backend:8001) */
  apiClient: ApiClient;
  /** Direct PostgreSQL client (connects to PG:5433) */
  dbClient: DbClient;
};

/**
 * Extended test with custom fixtures.
 *
 * Usage:
 * ```typescript
 * import { test, expect } from '../../fixtures/base.fixture';
 *
 * test('example', async ({ page, apiClient, dbClient }) => {
 *   const user = await apiClient.register('test@e2e.com');
 *   const code = await dbClient.getVerificationCode('test@e2e.com');
 *   // ...
 * });
 * ```
 */
export const test = base.extend<CustomFixtures>({
  apiClient: async ({}, use) => {
    const client = new ApiClient();
    await use(client);
    // No cleanup needed — ApiClient is stateless (just a token)
  },

  dbClient: async ({}, use) => {
    const client = new DbClient();
    await use(client);
    await client.close();
  },
});

export { expect };
