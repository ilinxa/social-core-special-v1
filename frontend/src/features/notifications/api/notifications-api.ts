/**
 * Notification API Functions
 * ==========================
 * Typed async functions for all notification REST endpoints.
 *
 * Backend: apps.notifications.views (5 endpoints)
 */

import { apiClient } from "@/lib/api-client";
import type {
  NotificationHistoryParams,
  NotificationHistoryResponse,
  NotificationPreferencesResponse,
  NotificationScopesResponse,
  NotificationTypesResponse,
  PreferenceItem,
  UpdatePreferenceInput,
} from "@/features/notifications/types";

// =============================================================================
// HISTORY
// =============================================================================

export async function fetchNotificationHistoryApi(
  params?: NotificationHistoryParams,
): Promise<NotificationHistoryResponse> {
  const response = await apiClient.get<NotificationHistoryResponse>(
    "/notifications/history/",
    { params },
  );
  return response.data;
}

// =============================================================================
// SCOPES
// =============================================================================

export async function fetchNotificationScopesApi(): Promise<NotificationScopesResponse> {
  const response = await apiClient.get<NotificationScopesResponse>(
    "/notifications/scopes/",
  );
  return response.data;
}

// =============================================================================
// PREFERENCES
// =============================================================================

export async function fetchNotificationPreferencesApi(): Promise<NotificationPreferencesResponse> {
  const response = await apiClient.get<NotificationPreferencesResponse>(
    "/notifications/preferences/",
  );
  return response.data;
}

export async function updateNotificationPreferenceApi(
  notificationType: string,
  data: UpdatePreferenceInput,
): Promise<PreferenceItem> {
  const response = await apiClient.patch<PreferenceItem>(
    `/notifications/preferences/${notificationType}/`,
    data,
  );
  return response.data;
}

export async function resetNotificationPreferenceApi(
  notificationType: string,
): Promise<void> {
  await apiClient.delete(`/notifications/preferences/${notificationType}/`);
}

// =============================================================================
// CONFIGURABLE TYPES
// =============================================================================

export async function fetchNotificationTypesApi(): Promise<NotificationTypesResponse> {
  const response = await apiClient.get<NotificationTypesResponse>(
    "/notifications/types/",
  );
  return response.data;
}
