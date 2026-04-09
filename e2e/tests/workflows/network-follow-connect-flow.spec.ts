/**
 * W9: Network Follow + Connect Flow workflow.
 *
 * Cross-system flow: Network → Transaction → Auth.
 * User B follows the pre-built business, then sends the business owner a
 * connection request. Owner accepts. Both verify the connection.
 *
 * Uses two browser contexts.
 *
 * @layer L2
 * @system network, transactions, auth
 * @parameters P1 (Auth), P4 (Transaction), P5 (Data Integrity)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  followBusinessViaApi,
  sendConnectionRequestViaApi,
  getConnectionsViaApi,
} from '../../helpers/network.helper';
import { acceptTransactionViaApi } from '../../helpers/transaction.helper';

test.describe('W9: Network Follow + Connect Flow', () => {
  test.skip(!isSystemEnabled('network'), 'Network system disabled');

  test('user follows business, connects with owner, both see connection', async ({
    browser,
    apiClient,
    dbClient,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;
    const ownerEmail = TEST_USERS.businessOwner.email;
    const ownerPassword = TEST_USERS.businessOwner.password;

    // Step 1 — Register user B
    const userB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w9-userB'),
    });

    // Step 2 — User B follows the pre-built business via API
    await apiClient.login(userB.email);
    await followBusinessViaApi(apiClient, bizId);

    // Step 3 — Get owner's user ID for connection request
    const ownerLoginData = await apiClient.login(ownerEmail, ownerPassword);
    const ownerUserId = (ownerLoginData as { user?: { id?: string } }).user?.id;

    // Step 4 — Login both users in browser contexts
    const { page: pageA, context: ctxA } = await loginInNewContext(
      browser,
      ownerEmail,
      ownerPassword,
    );
    const { page: pageB, context: ctxB } = await loginInNewContext(
      browser,
      userB.email,
      DEFAULT_PASSWORD,
    );

    // Step 5 — User B navigates to owner's profile (verify page loads)
    const ownerUsername = TEST_USERS.businessOwner.username;
    await pageB.goto(`/users/${ownerUsername}`);
    await expect(pageB.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 10000 });

    // Step 6 — Send connection request via API (button opens modal; API is more reliable)
    await apiClient.login(userB.email);
    if (ownerUserId) {
      await sendConnectionRequestViaApi(apiClient, ownerUserId);
    } else {
      // Fallback: look for the Connect button + modal in the UI
      const connectButton = pageB.getByRole('button', { name: /connect/i });
      await expect(connectButton).toBeVisible();
      await connectButton.click();
      // Wait for modal and click "Send Request"
      const sendRequestBtn = pageB.getByRole('button', { name: /send request/i });
      await expect(sendRequestBtn).toBeVisible({ timeout: 5000 });
      await Promise.all([
        pageB.waitForResponse(
          (resp) =>
            resp.url().includes('/transactions') &&
            resp.request().method() === 'POST' &&
            resp.ok(),
        ),
        sendRequestBtn.click(),
      ]);
    }

    // Step 7 — Accept connection request via API (as owner)
    await apiClient.login(ownerEmail, ownerPassword);
    const txRes = await apiClient.get(
      'transactions/?role=target&status=pending&transaction_type=user_connection_request',
    );
    const txBody = (await txRes.json()) as { results: { id: string }[] };
    expect(txBody.results.length).toBeGreaterThanOrEqual(1);
    await acceptTransactionViaApi(apiClient, txBody.results[0].id);

    // Step 8 — Verify connection exists via API
    await apiClient.login(userB.email);
    const bConns = await getConnectionsViaApi(apiClient);
    expect(bConns.results.length).toBeGreaterThanOrEqual(1);

    await apiClient.login(ownerEmail, ownerPassword);
    const aConns = await getConnectionsViaApi(apiClient);
    expect(aConns.results.length).toBeGreaterThanOrEqual(1);

    // Step 9 — User B navigates to /network → page loads
    await pageB.goto('/network');
    await expect(pageB.getByRole('heading', { level: 1 })).toBeVisible();

    // Cleanup
    await ctxA.close();
    await ctxB.close();
  });
});
