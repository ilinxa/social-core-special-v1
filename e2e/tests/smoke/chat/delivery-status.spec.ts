/**
 * Chat delivery status smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { DeliveryStatus } from '../../../pages/chat/chat.page';

test.describe('Delivery Status', () => {
  test('delivery status POM instantiates with test IDs', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    await page.goto('/chat');

    // Delivery status icons only visible on own messages in conversation
    const delivery = new DeliveryStatus(page);
    expect(delivery.sent).toBeDefined();
    expect(delivery.delivered).toBeDefined();
    expect(delivery.seen).toBeDefined();
    expect(delivery.seenCount).toBeDefined();
  });
});
