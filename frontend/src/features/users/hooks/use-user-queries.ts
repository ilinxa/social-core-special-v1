import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchApprovedCreatorsApi,
  fetchCurrentUserApi,
  fetchProfileApi,
  fetchUserByUsernameApi,
} from "@/features/users/api/users-api";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function currentUserQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.users.me(),
    queryFn: fetchCurrentUserApi,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function profileQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.users.profile(),
    queryFn: fetchProfileApi,
    staleTime: 5 * 60 * 1000,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useCurrentUser() {
  return useQuery(currentUserQueryOptions());
}

export function useProfile() {
  return useQuery(profileQueryOptions());
}

export function useUserByUsername(username: string) {
  return useQuery({
    queryKey: queryKeys.users.byUsername(username),
    queryFn: () => fetchUserByUsernameApi(username),
    staleTime: 5 * 60 * 1000,
    enabled: !!username,
    retry: (failureCount, error) => {
      // Don't retry 404s
      if ("status" in error && (error as { status: number }).status === 404) return false;
      return failureCount < 2;
    },
  });
}

export function useApprovedCreators(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: queryKeys.users.withBusinessPermission(params),
    queryFn: () => fetchApprovedCreatorsApi(params),
    staleTime: 2 * 60 * 1000,
  });
}
