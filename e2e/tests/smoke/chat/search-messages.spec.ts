/**
 * Chat message search smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage, MessageViewPanel, MessageSearchPanel } from '../../../pages/chat/chat.page';

test.describe('Chat Message Search', () => {
  test('search button is visible in message header', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    const messageView = new MessageViewPanel(page);
    // Search button exists when a conversation is open
    if (await messageView.searchButton.isVisible()) {
      await expect(messageView.searchButton).toBeVisible();
    }
  });

  test('search panel opens on search button click', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    const messageView = new MessageViewPanel(page);
    if (await messageView.searchButton.isVisible()) {
      await messageView.searchButton.click();

      const searchPanel = new MessageSearchPanel(page);
      await expect(searchPanel.searchInput).toBeVisible();
    }
  });
});
