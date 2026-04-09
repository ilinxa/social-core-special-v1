/**
 * Notification Query Hooks
 * ========================
 * TanStack Query hooks for all notification read operations.
 *
 * Feature gate: useNotificationScopes() catches 404 from the scopes endpoint
 * and sets isSystemEnabled=false in the Zustand store. All other queries
 * check isSystemEnabled via the `enabled` option.
 */

import { useEffect } from "react";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { ApiError } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import {
  fetchNotificationHistoryApi,
  fetchNotificationPreferencesApi,
  fetchNotificationScopesApi,
  fetchNotificationTypesApi,
} from "@/features/notifications/api/notifications-api";
import { NOTIFICATION_SCOPES_POLL_INTERVAL_MS } from "@/features/notifications/constants/notification-constants";
import type {
  NotificationHistoryParams,
  NotificationScopeItem,
} from "@/features/notifications/types";
import {
  getNotificationStore,
  useNotificationSystemEnabled,
} from "@/stores/notification-store";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function notificationScopesQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.notifications.scopes(),
    queryFn: async () => {
      try {
        const data = await fetchNotificationScopesApi();
        getNotificationStore().setSystemEnabled(true);
        return data;
      } catch (error) {
        if (error instanceof ApiError && error.isNotFound) {
          getNotificationStore().setSystemEnabled(false);
          return null;
        }
        throw error;
      }
    },
    staleTime: 30 * 1000,
    refetchInterval: NOTIFICATION_SCOPES_POLL_INTERVAL_MS,
    retry: (failureCount, error) => {
      // Don't retry 404 (system disabled) — it's an expected state
      if (error instanceof ApiError && error.isNotFound) return false;
      return failureCount < 3;
    },
  });
}

export function notificationHistoryQueryOptions(
  params?: NotificationHistoryParams,
) {
  return queryOptions({
    queryKey: queryKeys.notifications.history(params as Record<string, unknown>),
    queryFn: () => fetchNotificationHistoryApi(params),
    staleTime: 30 * 1000,
  });
}

export function notificationPreferencesQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.notifications.preferences(),
    queryFn: fetchNotificationPreferencesApi,
    staleTime: 5 * 60 * 1000,
  });
}

export function notificationTypesQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.notifications.types(),
    queryFn: fetchNotificationTypesApi,
    staleTime: 10 * 60 * 1000,
  });
}

// =============================================================================
// HELPERS
// =============================================================================

function scopeKey(scope: NotificationScopeItem): string {
  if (scope.scope_type === "user") return "user";
  return `${scope.scope_type}:${scope.scope_id}`;
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

/**
 * Scopes with notification counts. Also serves as feature gate probe.
 * Syncs scope counts to Zustand store for cross-tree badge reactivity.
 */
export function useNotificationScopes() {
  const query = useQuery(notificationScopesQueryOptions());

  // Sync scope counts to store
  useEffect(() => {
    if (query.data?.scopes) {
      const counts: Record<string, number> = {};
      for (const scope of query.data.scopes) {
        counts[scopeKey(scope)] = scope.count;
      }
      getNotificationStore().setScopeCounts(counts);
    }
  }, [query.data]);

  return query;
}

/** Paginated notification history, optionally filtered by scope. */
export function useNotificationHistory(params?: NotificationHistoryParams) {
  const isEnabled = useNotificationSystemEnabled();
  return useQuery({
    ...notificationHistoryQueryOptions(params),
    enabled: isEnabled,
  });
}

/** Preferences grouped by category. */
export function useNotificationPreferences() {
  const isEnabled = useNotificationSystemEnabled();
  return useQuery({
    ...notificationPreferencesQueryOptions(),
    enabled: isEnabled,
  });
}

/** All configurable notification types. */
export function useNotificationTypes() {
  const isEnabled = useNotificationSystemEnabled();
  return useQuery({
    ...notificationTypesQueryOptions(),
    enabled: isEnabled,
  });
}
