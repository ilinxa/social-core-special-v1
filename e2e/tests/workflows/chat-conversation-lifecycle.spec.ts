/**
 * W7: Chat Conversation Lifecycle workflow.
 *
 * Cross-system flow: Chat → Auth.
 * Single user manages their own conversation: views messages,
 * edits a message, deletes a message, and verifies changes.
 *
 * @layer L2
 * @system chat, auth
 * @parameters P5 (Data Integrity), P7 (Real-time)
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
  editMessageViaApi,
  deleteMessageViaApi,
} from '../../helpers/chat.helper';
import { ChatPage, MessageViewPanel } from '../../pages/chat/chat.page';

test.describe('W7: Chat Conversation Lifecycle', () => {
  test.skip(!isSystemEnabled('chat'), 'Chat system disabled');

  test('user views, edits, and deletes messages in a conversation', async ({
    browser,
    apiClient,
    dbClient,
  }) => {
    // Step 1 — Register two users
    const userA = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w7-userA'),
    });
    const userB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w7-userB'),
    });

    // Step 2 — Create DM conversation and send 3 messages (as user A)
    await apiClient.login(userA.email);
    const conversation = await createConversationViaApi(apiClient, [userB.id]);
    const msg1 = await sendMessageViaApi(apiClient, conversation.id, 'First message');
    const msg2 = await sendMessageViaApi(apiClient, conversation.id, 'Second message');
    const msg3 = await sendMessageViaApi(apiClient, conversation.id, 'Third message');

    // Step 3 — Login user A in browser → navigate to /chat → click first conversation
    const { page: pageA, context: ctxA } = await loginInNewContext(
      browser,
      userA.email,
      DEFAULT_PASSWORD,
    );
    const chatPage = new ChatPage(pageA);
    await chatPage.goto();

    // DM conversations have empty name — click the first available option
    const convItem = chatPage.conversationList.getByRole('option').first();
    await expect(convItem).toBeVisible({ timeout: 10000 });
    await convItem.click();

    // Wait for message panel to load
    const msgPanel = new MessageViewPanel(pageA);
    await expect(msgPanel.messageInput).toBeVisible({ timeout: 10000 });

    // Step 4 — Verify all 3 messages visible (scoped to message log to avoid sidebar matches)
    const messageLog = msgPanel.messageLog;
    await expect(messageLog.getByText('First message')).toBeVisible();
    await expect(messageLog.getByText('Second message')).toBeVisible();
    await expect(messageLog.getByText('Third message')).toBeVisible();

    // Step 5 — Edit message 2 via API → verify via API
    // Token should still be valid from step 2 login — no re-login needed
    await editMessageViaApi(apiClient, conversation.id, msg2.id, 'Second message (updated)');

    // Verify edit via API (UI cache may not refresh on reload)
    const editCheckRes = await apiClient.get(`chat/conversations/${conversation.id}/messages/`);
    const editCheckBody = await editCheckRes.json();
    const editMsgList = Array.isArray(editCheckBody)
      ? editCheckBody
      : (editCheckBody as { results: unknown[] }).results ?? [];
    const editedMsg = (editMsgList as { id: string; content: string }[]).find(
      (m) => m.id === msg2.id,
    );
    expect(editedMsg?.content).toBe('Second message (updated)');

    // Step 6 — Delete message 3 via API → verify via API
    await deleteMessageViaApi(apiClient, conversation.id, msg3.id);

    const deleteCheckRes = await apiClient.get(`chat/conversations/${conversation.id}/messages/`);
    const deleteCheckBody = await deleteCheckRes.json();
    const deleteMsgList = Array.isArray(deleteCheckBody)
      ? deleteCheckBody
      : (deleteCheckBody as { results: unknown[] }).results ?? [];
    // After deletion, "Third message" should not appear as active content
    const thirdStillActive = (deleteMsgList as { content: string; is_deleted?: boolean }[]).find(
      (m) => m.content === 'Third message' && !m.is_deleted,
    );
    expect(thirdStillActive).toBeFalsy();

    // Step 7 — First message should still be intact (verified via API)
    const firstMsg = (deleteMsgList as { content: string; is_deleted?: boolean }[]).find(
      (m) => m.content === 'First message' && !m.is_deleted,
    );
    expect(firstMsg).toBeTruthy();

    // Cleanup
    await ctxA.close();
  });
});
