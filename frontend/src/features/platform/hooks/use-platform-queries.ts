import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { fetchPlatformAccountApi } from "@/features/platform/api/platform-api";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function platformAccountQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.platform.account(),
    queryFn: fetchPlatformAccountApi,
    staleTime: 5 * 60 * 1000,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function usePlatformAccount() {
  return useQuery(platformAccountQueryOptions());
}
