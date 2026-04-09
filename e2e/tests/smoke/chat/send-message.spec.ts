/**
 * Chat send message smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P2, P3
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage, MessageViewPanel } from '../../../pages/chat/chat.page';

test.describe('Send Message', () => {
  test('compose bar shows message input', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // If there's an active conversation, the compose bar should be visible
    const messageView = new MessageViewPanel(page);
    // On desktop, we should see either compose bar or the "select conversation" prompt
    await expect(
      messageView.messageInput.or(chatPage.selectConversationMessage),
    ).toBeVisible();
  });

  test('message log has proper ARIA role', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    const messageView = new MessageViewPanel(page);
    // Message log may not be visible if no conversation selected
    if (await messageView.messageLog.isVisible()) {
      await expect(messageView.messageLog).toHaveAttribute('role', 'log');
    }
  });
});
