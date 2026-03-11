import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchFollowingApi,
  fetchConnectionsApi,
  fetchNetworkStatsApi,
  fetchBusinessFollowersApi,
  fetchBusinessConnectionsApi,
  fetchBusinessNetworkStatsApi,
} from "@/features/network/api/network-api";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function followingQueryOptions(type?: string) {
  return queryOptions({
    queryKey: queryKeys.network.following(type),
    queryFn: () => fetchFollowingApi(type ? { type: type as "business" | "platform" } : undefined),
    staleTime: 5 * 60 * 1000,
  });
}

export function connectionsQueryOptions(status?: string) {
  return queryOptions({
    queryKey: queryKeys.network.connections(status),
    queryFn: () => fetchConnectionsApi(status ? { status } : undefined),
    staleTime: 5 * 60 * 1000,
  });
}

export function networkStatsQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.network.stats(),
    queryFn: fetchNetworkStatsApi,
    staleTime: 5 * 60 * 1000,
  });
}

export function businessFollowersQueryOptions(slug: string) {
  return queryOptions({
    queryKey: queryKeys.network.businessFollowers(slug),
    queryFn: () => fetchBusinessFollowersApi(slug),
    staleTime: 5 * 60 * 1000,
    enabled: !!slug,
  });
}

export function businessConnectionsQueryOptions(slug: string) {
  return queryOptions({
    queryKey: queryKeys.network.businessConnections(slug),
    queryFn: () => fetchBusinessConnectionsApi(slug),
    staleTime: 5 * 60 * 1000,
    enabled: !!slug,
  });
}

export function businessNetworkStatsQueryOptions(slug: string) {
  return queryOptions({
    queryKey: queryKeys.network.businessStats(slug),
    queryFn: () => fetchBusinessNetworkStatsApi(slug),
    staleTime: 5 * 60 * 1000,
    enabled: !!slug,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useFollowing(type?: string) {
  return useQuery(followingQueryOptions(type));
}

export function useConnections(status?: string) {
  return useQuery(connectionsQueryOptions(status));
}

export function useNetworkStats() {
  return useQuery(networkStatsQueryOptions());
}

export function useBusinessFollowers(slug: string) {
  return useQuery(businessFollowersQueryOptions(slug));
}

export function useBusinessConnections(slug: string) {
  return useQuery(businessConnectionsQueryOptions(slug));
}

export function useBusinessNetworkStats(slug: string) {
  return useQuery(businessNetworkStatsQueryOptions(slug));
}
