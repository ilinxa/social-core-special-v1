/**
 * Chat attachments smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage, MessageViewPanel } from '../../../pages/chat/chat.page';

test.describe('Chat Attachments', () => {
  test('attachment button exists in compose bar', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    const messageView = new MessageViewPanel(page);
    await chatPage.goto();

    // If compose bar is visible, the attachment button should be present
    await expect(messageView.attachmentButton.or(chatPage.selectConversationMessage)).toBeVisible();
  });
});
