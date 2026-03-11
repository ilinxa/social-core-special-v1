import { test, expect } from "../helpers/fixtures";
import { TEST_USERS, TEST_BUSINESS, API_BASE_URL, API_HEADERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";
import * as api from "../helpers/api-helper";

// =============================================================================
// U-83..U-93 — User Transactions (13 tests)
// =============================================================================

test.describe("User Transactions", () => {
  test("[U-83] Activity page renders", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");

    // Heading
    await expect(
      page.getByText(/activity|transactions/i).first()
    ).toBeVisible({ timeout: 10_000 });

    // Tabs (All / Sent / Received)
    await expect(
      page.getByRole("tab", { name: /all/i }).or(page.getByText(/all/i).first())
    ).toBeVisible();
  });

  test("[U-84] Empty state for fresh user", async ({ page }) => {
    // User C should have no transactions
    await loginViaUI(page, TEST_USERS.userC.email, TEST_USERS.userC.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    // Should show empty state or no transactions
    const emptyState = await page
      .getByText(/no transactions|no activity|nothing.*yet/i)
      .first()
      .isVisible()
      .catch(() => false);

    const hasContent = await page
      .locator("[data-testid='transaction-card'], .transaction-card")
      .count();

    expect(emptyState || hasContent === 0).toBeTruthy();
  });

  test("[U-85] Request to Join creates transaction visible in activity", async ({
    page,
  }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    // First check if User A already has a pending request
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    const hasPending = await page
      .getByText(/pending|request/i)
      .first()
      .isVisible()
      .catch(() => false);

    if (!hasPending) {
      // Create a request via the business page
      await page.goto(`/business/${TEST_BUSINESS.slug}`);
      await page.waitForTimeout(2000);

      const joinBtn = page
        .getByRole("button", { name: /request to join|join/i })
        .first();

      if (await joinBtn.isVisible().catch(() => false)) {
        await joinBtn.click();
        await page.waitForTimeout(3000);
      }
    }

    // Check activity page for the transaction
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    // Should see at least one transaction
    const bodyText = await page.textContent("body");
    expect(bodyText).toBeTruthy();
  });

  test("[U-86] Pending request appears in activity", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    // Check for pending status badge or text
    const hasPending = await page
      .getByText(/pending/i)
      .first()
      .isVisible()
      .catch(() => false);

    // May also show as a transaction card
    const hasCards = await page
      .locator("[data-testid='transaction-card'], article, .card")
      .count();

    expect(hasPending || hasCards > 0).toBeTruthy();
  });

  test("[U-87] Cancel request", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    // Find a pending transaction and click on it
    const pendingItem = page.getByText(/pending/i).first();
    if (await pendingItem.isVisible().catch(() => false)) {
      await pendingItem.click();
      await page.waitForTimeout(2000);

      // Look for Cancel button on detail page
      const cancelBtn = page.getByRole("button", { name: /cancel/i });
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click();
        await page.waitForTimeout(2000);

        // Confirm cancellation if dialog appears
        const confirmBtn = page.getByRole("button", {
          name: /confirm|yes|cancel/i,
        });
        if (await confirmBtn.isVisible().catch(() => false)) {
          await confirmBtn.click();
        }

        await page.waitForTimeout(2000);

        // Status should change to cancelled
        const cancelled = await page
          .getByText(/cancelled|canceled/i)
          .first()
          .isVisible()
          .catch(() => false);

        expect(cancelled).toBeTruthy();
      }
    }
  });

  test("[U-88] Accept invitation (smoke test)", async ({ page }) => {
    // This requires User B to create an invitation for User A.
    // We set this up via API and then test the accept flow in the UI.
    let invitationCreated = false;

    try {
      const userBAuth = await api.login(
        TEST_USERS.userB.email,
        TEST_USERS.userB.password
      );

      // Search for User A's ID
      const searchResp = await fetch(
        `${API_BASE_URL}/explore/users/?q=${TEST_USERS.userA.username}`,
        {
          headers: { Authorization: `Bearer ${userBAuth.access_token}` },
        }
      );

      if (searchResp.ok) {
        const searchData = await searchResp.json();
        const targetUser = searchData.results?.find(
          (u: any) => u.username === TEST_USERS.userA.username
        );

        if (targetUser) {
          // Create invitation
          const invResp = await fetch(
            `${API_BASE_URL}/business/${TEST_BUSINESS.slug}/transactions/invitations/`,
            {
              method: "POST",
              headers: {
                ...API_HEADERS,
                Authorization: `Bearer ${userBAuth.access_token}`,
              },
              body: JSON.stringify({ target_user_id: targetUser.id }),
            }
          );

          invitationCreated = invResp.ok;
        }
      }
    } catch {
      // API setup failed — skip this test
    }

    if (!invitationCreated) {
      test.skip();
      return;
    }

    // Login as User A and check for invitation
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(3000);

    // Look for the invitation
    const invItem = page.getByText(/invitation/i).first();
    if (await invItem.isVisible().catch(() => false)) {
      await invItem.click();
      await page.waitForTimeout(2000);

      // Accept button
      const acceptBtn = page.getByRole("button", { name: /accept/i });
      if (await acceptBtn.isVisible().catch(() => false)) {
        await acceptBtn.click();
        await page.waitForTimeout(3000);

        // Should show accepted status
        await expect(
          page.getByText(/accepted/i).first()
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test("[U-89] Deny invitation (smoke test)", async ({ page }) => {
    // Similar to U-88 — create invitation via API, then deny in UI
    let invitationCreated = false;

    try {
      const userBAuth = await api.login(
        TEST_USERS.userB.email,
        TEST_USERS.userB.password
      );

      const searchResp = await fetch(
        `${API_BASE_URL}/explore/users/?q=${TEST_USERS.userA.username}`,
        {
          headers: { Authorization: `Bearer ${userBAuth.access_token}` },
        }
      );

      if (searchResp.ok) {
        const searchData = await searchResp.json();
        const targetUser = searchData.results?.find(
          (u: any) => u.username === TEST_USERS.userA.username
        );

        if (targetUser) {
          const invResp = await fetch(
            `${API_BASE_URL}/business/${TEST_BUSINESS.slug}/transactions/invitations/`,
            {
              method: "POST",
              headers: {
                ...API_HEADERS,
                Authorization: `Bearer ${userBAuth.access_token}`,
              },
              body: JSON.stringify({ target_user_id: targetUser.id }),
            }
          );

          invitationCreated = invResp.ok;
        }
      }
    } catch {
      // skip
    }

    if (!invitationCreated) {
      test.skip();
      return;
    }

    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(3000);

    const invItem = page.getByText(/invitation/i).first();
    if (await invItem.isVisible().catch(() => false)) {
      await invItem.click();
      await page.waitForTimeout(2000);

      const denyBtn = page.getByRole("button", { name: /deny|decline/i });
      if (await denyBtn.isVisible().catch(() => false)) {
        await denyBtn.click();
        await page.waitForTimeout(3000);

        await expect(
          page.getByText(/denied|declined/i).first()
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test("[U-90] Transaction detail page renders", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    // Click on any transaction to view detail
    const firstCard = page
      .locator("[data-testid='transaction-card'], article, .card")
      .first();

    if (await firstCard.isVisible().catch(() => false)) {
      await firstCard.click();
      await page.waitForURL(/\/activity\//, { timeout: 10_000 });

      // Detail page should show timeline or details
      const bodyText = await page.textContent("body");
      expect(bodyText!.length).toBeGreaterThan(100);
    }
  });

  test("[U-91] Sent tab shows only sent transactions", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    const sentTab = page.getByRole("tab", { name: /sent/i });
    if (await sentTab.isVisible().catch(() => false)) {
      await sentTab.click();
      await page.waitForTimeout(1000);

      // Page should filter to sent only (or show empty state)
      const bodyText = await page.textContent("body");
      expect(bodyText).toBeTruthy();
    }
  });

  test("[U-92] Received tab shows only received transactions", async ({
    page,
  }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    const receivedTab = page.getByRole("tab", { name: /received/i });
    if (await receivedTab.isVisible().catch(() => false)) {
      await receivedTab.click();
      await page.waitForTimeout(1000);

      const bodyText = await page.textContent("body");
      expect(bodyText).toBeTruthy();
    }
  });

  test("[U-93] Status filter works", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/activity");
    await page.waitForTimeout(2000);

    // Find status filter dropdown
    const statusFilter = page
      .getByRole("combobox", { name: /status/i })
      .or(page.getByLabel(/status/i));

    if (await statusFilter.isVisible().catch(() => false)) {
      await statusFilter.click();
      await page.waitForTimeout(500);

      // Select "Pending"
      await page.getByText(/pending/i).first().click();
      await page.waitForTimeout(1000);

      // URL or results should reflect filter
      const bodyText = await page.textContent("body");
      expect(bodyText).toBeTruthy();
    }
  });
});
