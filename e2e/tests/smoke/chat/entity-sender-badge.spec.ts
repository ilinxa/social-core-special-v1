/**
 * Chat entity sender badge smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage } from '../../../pages/chat/chat.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Entity Sender Badge', () => {
  test('business chat page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const chatPage = new ChatPage(page);
    await chatPage.gotoBusinessChat(E2E_BUSINESS.slug);

    // Business chat should render the chat layout
    await expect(chatPage.sidebarHeading).toBeVisible();
  });

  test('platform chat page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const chatPage = new ChatPage(page);
    await chatPage.gotoPlatformChat();

    await expect(chatPage.sidebarHeading).toBeVisible();
  });
});
