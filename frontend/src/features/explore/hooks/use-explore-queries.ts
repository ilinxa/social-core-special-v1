import {
  queryOptions,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchCitiesApi,
  fetchExploreCombinedApi,
  fetchTagSuggestionsApi,
  searchBusinessesApi,
  searchUsersApi,
} from "@/features/explore/api/explore-api";
import type { BusinessSearchParams, UserSearchParams } from "@/types/explore";

// =============================================================================
// HELPERS
// =============================================================================

/** Extract page number from a DRF pagination `next` URL, or undefined. */
function getNextPage(nextUrl: string | null): number | undefined {
  if (!nextUrl) return undefined;
  try {
    const url = new URL(nextUrl);
    const page = url.searchParams.get("page");
    return page ? Number(page) : undefined;
  } catch {
    return undefined;
  }
}

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function exploreCombinedQueryOptions(
  params: { q?: string },
  isAuthenticated: boolean,
) {
  return queryOptions({
    queryKey: [...queryKeys.explore.combined(params), isAuthenticated],
    queryFn: () => fetchExploreCombinedApi(params),
    staleTime: 30 * 1000,
    placeholderData: (prev) => prev,
  });
}

export function tagSuggestionsQueryOptions(q?: string, category?: string) {
  return queryOptions({
    queryKey: queryKeys.explore.tags(q, category),
    queryFn: () => fetchTagSuggestionsApi(q, category),
    staleTime: 5 * 60 * 1000,
    enabled: (q?.length ?? 0) >= 1,
  });
}

export function citiesQueryOptions(country: string) {
  return queryOptions({
    queryKey: queryKeys.explore.cities(country),
    queryFn: () => fetchCitiesApi(country),
    staleTime: 30 * 60 * 1000,
    enabled: !!country,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useExploreCombined(
  params: { q?: string },
  isAuthenticated: boolean,
) {
  return useQuery(exploreCombinedQueryOptions(params, isAuthenticated));
}

/** Infinite-scroll business search. Omit `page` from params — managed internally. */
export function useInfiniteBusinessSearch(
  params: Omit<BusinessSearchParams, "page">,
) {
  return useInfiniteQuery({
    queryKey: queryKeys.explore.businesses(params),
    queryFn: ({ pageParam }) =>
      searchBusinessesApi({ ...params, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 30 * 1000,
  });
}

/** Infinite-scroll user search. Omit `page` from params — managed internally. */
export function useInfiniteUserSearch(
  params: Omit<UserSearchParams, "page">,
  enabled = true,
) {
  return useInfiniteQuery({
    queryKey: queryKeys.explore.users(params),
    queryFn: ({ pageParam }) =>
      searchUsersApi({ ...params, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 30 * 1000,
    enabled,
  });
}

export function useTagSuggestions(q?: string, category?: string) {
  return useQuery(tagSuggestionsQueryOptions(q, category));
}

export function useCities(country: string) {
  return useQuery(citiesQueryOptions(country));
}
