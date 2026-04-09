/**
 * Notification helper — common notification operations for tests.
 *
 * Provides API-based notification preference, history, scope, and type operations.
 * All endpoints are at `/notifications/` and require authentication.
 */

import type { ApiClient } from '../lib/api-client';
import type {
  NotificationHistoryResponse,
  NotificationLogItem,
  NotificationPreference,
  NotificationScopesResponse,
  NotificationTypesResponse,
} from '../lib/types';
import { retry } from '../lib/utils';

// ---------------------------------------------------------------------------
// Preferences
// ---------------------------------------------------------------------------

/** Get all notification preferences grouped by category. */
export async function getNotificationPreferencesViaApi(
  api: ApiClient,
): Promise<Record<string, NotificationPreference[]>> {
  const res = await api.get('notifications/preferences/');
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getNotificationPreferencesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, NotificationPreference[]>;
}

/** Get a single notification preference by type. */
export async function getNotificationPreferenceViaApi(
  api: ApiClient,
  notificationType: string,
): Promise<NotificationPreference> {
  const res = await api.get(`notifications/preferences/${notificationType}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getNotificationPreferenceViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as NotificationPreference;
}

/** Update channel preferences for a notification type. */
export async function updateNotificationPreferenceViaApi(
  api: ApiClient,
  notificationType: string,
  channels: {
    email_enabled?: boolean;
    push_enabled?: boolean;
    sms_enabled?: boolean;
  },
): Promise<NotificationPreference> {
  const res = await api.patch(
    `notifications/preferences/${notificationType}/`,
    channels,
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(
      `updateNotificationPreferenceViaApi failed (${res.status}): ${body}`,
    );
  }
  return (await res.json()) as NotificationPreference;
}

/** Reset a notification preference to type defaults. */
export async function resetNotificationPreferenceViaApi(
  api: ApiClient,
  notificationType: string,
): Promise<void> {
  const res = await api.delete(`notifications/preferences/${notificationType}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(
      `resetNotificationPreferenceViaApi failed (${res.status}): ${body}`,
    );
  }
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

/** Get notification history with optional filters. */
export async function getNotificationHistoryViaApi(
  api: ApiClient,
  params?: {
    notification_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
    scope_type?: string;
    scope_id?: string;
  },
): Promise<NotificationHistoryResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
  }
  const qs = searchParams.toString();
  const path = qs ? `notifications/history/?${qs}` : 'notifications/history/';
  const res = await api.get(path);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getNotificationHistoryViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as NotificationHistoryResponse;
}

// ---------------------------------------------------------------------------
// Scopes
// ---------------------------------------------------------------------------

/** Get distinct notification scopes with counts. */
export async function getNotificationScopesViaApi(
  api: ApiClient,
): Promise<NotificationScopesResponse> {
  const res = await api.get('notifications/scopes/');
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getNotificationScopesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as NotificationScopesResponse;
}

// ---------------------------------------------------------------------------
// Configurable Types
// ---------------------------------------------------------------------------

/** Get all user-configurable notification types. */
export async function getConfigurableTypesViaApi(
  api: ApiClient,
): Promise<NotificationTypesResponse> {
  const res = await api.get('notifications/types/');
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getConfigurableTypesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as NotificationTypesResponse;
}

// ---------------------------------------------------------------------------
// Polling Utilities
// ---------------------------------------------------------------------------

/**
 * Wait for a notification of a given type to appear in the user's history.
 * Polls the history API until the type is found or retries are exhausted.
 */
export async function waitForNotificationInHistory(
  api: ApiClient,
  notificationType: string,
  options?: {
    retries?: number;
    delay?: number;
    scope_type?: string;
    scope_id?: string;
  },
): Promise<NotificationLogItem> {
  const { retries = 15, delay = 1000, scope_type, scope_id } = options ?? {};
  let found: NotificationLogItem | undefined;

  await retry(
    async () => {
      const history = await getNotificationHistoryViaApi(api, {
        notification_type: notificationType,
        scope_type,
        scope_id,
      });
      found = history.notifications.find(
        (n) => n.notification_type === notificationType,
      );
      if (!found) {
        throw new Error(
          `Notification type "${notificationType}" not found in history`,
        );
      }
    },
    { retries, delay, description: `Wait for ${notificationType} notification` },
  );

  return found!;
}
