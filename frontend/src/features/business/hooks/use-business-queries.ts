import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { fetchBusinessApi, fetchMyBusinessesApi } from "@/features/business/api/business-api";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function myBusinessesQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.business.my(),
    queryFn: fetchMyBusinessesApi,
    staleTime: 5 * 60 * 1000,
  });
}

export function businessDetailQueryOptions(slug: string) {
  return queryOptions({
    queryKey: queryKeys.business.detail(slug),
    queryFn: () => fetchBusinessApi(slug),
    staleTime: 5 * 60 * 1000,
    enabled: !!slug,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useMyBusinesses() {
  return useQuery(myBusinessesQueryOptions());
}

export function useBusiness(slug: string, overrides?: { staleTime?: number }) {
  return useQuery({
    ...businessDetailQueryOptions(slug),
    ...overrides,
  });
}
