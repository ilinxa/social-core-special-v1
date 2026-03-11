import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  createFollowApi,
  unfollowApi,
  createConnectionRequestApi,
  disconnectUserApi,
  removeBusinessFollowerApi,
  createBusinessConnectionApi,
  disconnectBusinessConnectionApi,
  type CreateFollowData,
  type CreateConnectionData,
  type CreateBusinessConnectionData,
} from "@/features/network/api/network-api";

// =============================================================================
// FOLLOW MUTATIONS
// =============================================================================

export function useFollow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateFollowData) => createFollowApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.network.all });
    },
  });
}

export function useUnfollow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (followId: string) => unfollowApi(followId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.network.all });
    },
  });
}

// =============================================================================
// USER CONNECTION MUTATIONS
// =============================================================================

export function useConnectUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateConnectionData) => createConnectionRequestApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.network.all });
    },
  });
}

export function useDisconnectUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (connectionId: string) => disconnectUserApi(connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.network.all });
    },
  });
}

// =============================================================================
// BUSINESS NETWORK MUTATIONS
// =============================================================================

export function useRemoveBusinessFollower(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (followId: string) => removeBusinessFollowerApi(slug, followId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.businessFollowers(slug),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.businessStats(slug),
      });
    },
  });
}

export function useBusinessConnect(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateBusinessConnectionData) =>
      createBusinessConnectionApi(slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.businessConnections(slug),
      });
    },
  });
}

export function useBusinessDisconnect(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (connectionId: string) =>
      disconnectBusinessConnectionApi(slug, connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.network.businessConnections(slug),
      });
    },
  });
}
