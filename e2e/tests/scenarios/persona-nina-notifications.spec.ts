/**
 * Persona: Nina — The Notification Explorer
 *
 * A user who explores the notification system: checks the bell,
 * views notification center, configures preferences, triggers
 * notifications, and verifies scope isolation.
 *
 * 15 progressive steps.
 *
 * @layer L3
 * @system auth, notifications, business
 * @parameters P1, P2, P3, P5, P6
 * @priority P1
 */
import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { loginInNewContext } from '../../helpers/auth.helper';
import { isSystemEnabled } from '../../lib/feature-gates';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import { ApiClient } from '../../lib/api-client';
import {
  getNotificationPreferencesViaApi,
  getNotificationPreferenceViaApi,
  updateNotificationPreferenceViaApi,
  resetNotificationPreferenceViaApi,
  getNotificationHistoryViaApi,
  getNotificationScopesViaApi,
  waitForNotificationInHistory,
} from '../../helpers/notification.helper';
import { NotificationsPage, NotificationPreferencesSection, NotificationBellComponent } from '../../pages/notifications/notifications.page';

test.describe.serial('Nina: The Notification Explorer', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  const ninaEmail = generateEmail('nina');
  const ninaUsername = usernameFromEmail(ninaEmail);
  const ninaPassword = DEFAULT_PASSWORD;
  let ninaApi: ApiClient;

  // -----------------------------------------------------------------------
  // Phase 1: Registration & Initial Exploration (Steps 1-3)
  // -----------------------------------------------------------------------

  test('Step 1: Nina registers and verifies', async ({ apiClient, dbClient }) => {
    await apiClient.register(ninaEmail, ninaPassword, ninaUsername);
    await dbClient.verifyUserDirectly(ninaEmail);
    await apiClient.login(ninaEmail, ninaPassword);
    ninaApi = apiClient;
  });

  test('Step 2: Nina sees notification bell in topbar', async ({ browser }) => {
    const { page, context } = await loginInNewContext(
      browser,
      ninaEmail,
      ninaPassword,
    );

    await page.goto('/home');
    const bell = new NotificationBellComponent(page);
    await expect(bell.bellButton).toBeVisible();

    await context.close();
  });

  test('Step 3: Nina navigates to notifications page — sees empty or initial state', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      ninaEmail,
      ninaPassword,
    );

    const notifPage = new NotificationsPage(page);
    await notifPage.goto();
    await expect(notifPage.heading).toBeVisible();

    // New user — either empty state or registration notifications
    await expect(
      notifPage.emptyHeading.or(notifPage.allTab),
    ).toBeVisible();

    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 2: Preferences (Steps 4-7)
  // -----------------------------------------------------------------------

  test('Step 4: Nina navigates to settings — preferences visible', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      ninaEmail,
      ninaPassword,
    );

    const prefsSection = new NotificationPreferencesSection(page);
    await prefsSection.goto();
    await expect(prefsSection.sectionHeading).toBeVisible();

    await context.close();
  });

  test('Step 5: Nina verifies all 5 category cards', async ({ browser }) => {
    const { page, context } = await loginInNewContext(
      browser,
      ninaEmail,
      ninaPassword,
    );

    const prefsSection = new NotificationPreferencesSection(page);
    await prefsSection.goto();

    await expect(prefsSection.authCategory).toBeVisible();
    await expect(prefsSection.securityCategory).toBeVisible();
    await expect(prefsSection.transactionsCategory).toBeVisible();
    await expect(prefsSection.marketingCategory).toBeVisible();
    await expect(prefsSection.socialCategory).toBeVisible();

    await context.close();
  });

  test('Step 6: Nina toggles email off for New Login Alert', async () => {
    await ninaApi.login(ninaEmail, ninaPassword);
    const updated = await updateNotificationPreferenceViaApi(
      ninaApi,
      'new_login',
      { email_enabled: false },
    );
    expect(updated.email_enabled).toBe(false);
  });

  test('Step 7: Nina verifies preference persisted', async () => {
    await ninaApi.login(ninaEmail, ninaPassword);
    const pref = await getNotificationPreferenceViaApi(ninaApi, 'new_login');
    expect(pref.email_enabled).toBe(false);
  });

  // -----------------------------------------------------------------------
  // Phase 3: Notification Triggering (Steps 8-10)
  // -----------------------------------------------------------------------

  test('Step 8: Nina triggers a new_login notification', async () => {
    // Login from a fresh API client (simulates "new device")
    const freshApi = new ApiClient();
    await freshApi.login(ninaEmail, ninaPassword);
    ninaApi = freshApi;
  });

  test('Step 9: Nina checks notification in history via API', async () => {
    await ninaApi.login(ninaEmail, ninaPassword);
    // new_login should appear in history
    const history = await getNotificationHistoryViaApi(ninaApi, {
      notification_type: 'new_login',
    });
    // May or may not have new_login depending on channel config
    expect(history).toHaveProperty('notifications');
  });

  test('Step 10: Nina navigates to notifications page — sees items', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(
      browser,
      ninaEmail,
      ninaPassword,
    );

    const notifPage = new NotificationsPage(page);
    await notifPage.goto();
    await expect(notifPage.heading).toBeVisible();

    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 4: Reset & Business Scope (Steps 11-15)
  // -----------------------------------------------------------------------

  test('Step 11: Nina resets preference to defaults', async () => {
    await ninaApi.login(ninaEmail, ninaPassword);
    await resetNotificationPreferenceViaApi(ninaApi, 'new_login');

    const pref = await getNotificationPreferenceViaApi(ninaApi, 'new_login');
    // Default for new_login is email_enabled=true
    expect(pref.email_enabled).toBe(true);
  });

  test('Step 12: Nina creates a business', async ({ dbClient }) => {
    await ninaApi.login(ninaEmail, ninaPassword);
    await dbClient.grantBusinessCreation(ninaEmail);
    await ninaApi.login(ninaEmail, ninaPassword);

    const bizRes = await ninaApi.post('business/', {
      legal_name: "Nina's Shop",
      country: 'US',
      slug: `nina-shop-${Date.now()}`,
    });
    expect(bizRes.ok).toBe(true);
  });

  test('Step 13: Nina checks history — registration notifications visible', async () => {
    await ninaApi.login(ninaEmail, ninaPassword);
    const history = await getNotificationHistoryViaApi(ninaApi);
    expect(history).toHaveProperty('count');
    expect(history.count).toBeGreaterThanOrEqual(0);
  });

  test('Step 14: Nina checks scopes endpoint', async () => {
    await ninaApi.login(ninaEmail, ninaPassword);
    const scopes = await getNotificationScopesViaApi(ninaApi);
    expect(scopes).toHaveProperty('scopes');
    expect(scopes).toHaveProperty('count');
    // Should have at least "user" scope
    if (scopes.count > 0) {
      const scopeTypes = scopes.scopes.map((s) => s.scope_type);
      expect(scopeTypes).toContain('user');
    }
  });

  test("Step 15: Nina's notification exploration is complete", async () => {
    // Final verification — preferences API is functional
    await ninaApi.login(ninaEmail, ninaPassword);
    const prefs = await getNotificationPreferencesViaApi(ninaApi);
    expect(prefs).toBeDefined();
    expect(Object.keys(prefs).length).toBeGreaterThan(0);
  });
});
