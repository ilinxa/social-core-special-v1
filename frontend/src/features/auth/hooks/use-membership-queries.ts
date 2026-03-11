import { queryOptions, useQuery, type QueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { fetchMyMembershipsApi } from "@/features/auth/api/membership-api";

/**
 * Event-driven invalidation strategy for memberships:
 * - staleTime: Infinity — never auto-refetch on a timer
 * - refetchOnWindowFocus: "always" — catch external changes when user returns
 * - gcTime: 30 min — keep cached data longer since we control invalidation
 *
 * Memberships change through discrete events (join, leave, role change),
 * not on a clock. Invalidation is triggered by:
 * 1. User login (initial fetch in AuthInitializer)
 * 2. User's own mutation (onSuccess → invalidateMemberships)
 * 3. Route guard cache miss (guard triggers single refetch)
 * 4. Window/tab focus (refetchOnWindowFocus: "always")
 */
export function membershipsQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.users.memberships(),
    queryFn: fetchMyMembershipsApi,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: "always",
  });
}

export function useMembershipsQuery() {
  return useQuery(membershipsQueryOptions());
}

/**
 * Invalidate cached memberships. Call this in mutation onSuccess callbacks
 * for any action that changes the user's memberships (join, leave, create business, etc).
 */
export function invalidateMemberships(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.users.memberships() });
}
