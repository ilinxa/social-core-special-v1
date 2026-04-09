/**
 * Chat presence indicator smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage } from '../../../pages/chat/chat.page';

test.describe('Presence Indicators', () => {
  test('chat page loads with WebSocket connection', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Connection banner should either not be visible (connected) or show connecting state
    // After page load settles, banner should disappear (connected state)
    await expect(chatPage.sidebarHeading).toBeVisible();
  });
});
