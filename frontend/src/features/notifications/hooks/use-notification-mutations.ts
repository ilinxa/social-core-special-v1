/**
 * Notification Mutation Hooks
 * ===========================
 * TanStack Query mutation hooks for notification write operations.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import {
  resetNotificationPreferenceApi,
  updateNotificationPreferenceApi,
} from "@/features/notifications/api/notifications-api";
import type { UpdatePreferenceInput } from "@/features/notifications/types";

// =============================================================================
// MUTATIONS
// =============================================================================

export function useUpdatePreference() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      notificationType,
      data,
    }: {
      notificationType: string;
      data: UpdatePreferenceInput;
    }) => updateNotificationPreferenceApi(notificationType, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.preferences(),
      });
    },
    onError: () => {
      toast.error("Failed to update notification preference");
    },
  });
}

export function useResetPreference() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationType: string) =>
      resetNotificationPreferenceApi(notificationType),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.preferences(),
      });
      toast.success("Preference reset to default");
    },
    onError: () => {
      toast.error("Failed to reset notification preference");
    },
  });
}
