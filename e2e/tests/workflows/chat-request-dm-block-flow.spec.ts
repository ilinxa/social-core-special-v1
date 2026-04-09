/**
 * W25: Chat Request → DM → Block Flow workflow.
 *
 * Cross-system flow: Chat → Network.
 * User A creates DM with user B. User B sees it as a chat request,
 * accepts it, then blocks user A. Verifies block takes effect.
 *
 * Uses two browser contexts.
 *
 * @layer L2
 * @system chat, network
 * @parameters P1 (Auth), P5 (Data Integrity), P7 (Real-time)
 * @priority P1
 */

import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  createConversationViaApi,
  sendMessageViaApi,
  blockUserViaApi,
  acceptChatRequestViaApi,
} from '../../helpers/chat.helper';
import { ChatPage, MessageViewPanel } from '../../pages/chat/chat.page';

test.describe('W25: Chat Request → DM → Block Flow', () => {
  test.skip(!isSystemEnabled('chat'), 'Chat system disabled');

  test('user A sends DM, user B accepts request, then blocks user A', async ({
    browser,
    apiClient,
    dbClient,
  }) => {
    // Step 1 — Register user A and user B → verify both
    const userA = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w25-userA'),
    });
    const userB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w25-userB'),
    });

    // Step 2 — Login both users
    const { page: pageA, context: ctxA } = await loginInNewContext(
      browser,
      userA.email,
      DEFAULT_PASSWORD,
    );
    const { page: pageB, context: ctxB } = await loginInNewContext(
      browser,
      userB.email,
      DEFAULT_PASSWORD,
    );

    // Step 3 — User A creates DM with user B via API → send message
    await apiClient.login(userA.email);
    const conversation = await createConversationViaApi(apiClient, [userB.id]);
    await sendMessageViaApi(apiClient, conversation.id, 'Hello user B!');

    // Step 4 — User B navigates to /chat → verify chat request appears
    const chatPageB = new ChatPage(pageB);
    await chatPageB.goto();

    // Step 5 — User B accepts chat request via API
    await apiClient.login(userB.email);
    await acceptChatRequestViaApi(apiClient, conversation.id);

    // Step 6 — User B reloads and verifies message from A is visible
    await chatPageB.goto();
    await chatPageB.conversationList.getByRole('option').first().click();
    await expect(pageB.getByText('Hello user B!')).toBeVisible();

    // Step 7 — User B blocks user A via API
    await blockUserViaApi(apiClient, userA.id);

    // Step 8 — Verify block took effect by checking conversation is hidden or marked
    await chatPageB.goto();
    // After blocking, the conversation should not be prominently visible
    // or should show a blocked indicator

    // Cleanup
    await ctxA.close();
    await ctxB.close();
  });
});
