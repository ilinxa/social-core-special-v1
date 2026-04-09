/**
 * Chat group admin smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage } from '../../../pages/chat/chat.page';

test.describe('Group Admin', () => {
  test('chat page loads for group management', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Group admin features available through conversation settings
    await expect(chatPage.sidebarHeading).toBeVisible();
  });
});
