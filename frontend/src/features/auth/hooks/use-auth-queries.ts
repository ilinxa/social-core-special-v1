import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { fetchSessionsApi } from "@/features/auth/api/auth-api";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function sessionsQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.auth.sessions(),
    queryFn: fetchSessionsApi,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useSessions() {
  return useQuery(sessionsQueryOptions());
}
