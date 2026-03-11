import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  BusinessSearchParams,
  CityListResponse,
  ExploreBusiness,
  ExploreCombinedResponse,
  ExploreUser,
  SuggestedTag,
  UserSearchParams,
} from "@/types/explore";

// =============================================================================
// HELPERS
// =============================================================================

function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function fetchExploreCombinedApi(params: {
  q?: string;
}): Promise<ExploreCombinedResponse> {
  const qs = buildQueryString(params);
  const response = await apiClient.get<ExploreCombinedResponse>(`/explore/${qs}`);
  return response.data;
}

export async function searchBusinessesApi(
  params: BusinessSearchParams,
): Promise<PaginatedResponse<ExploreBusiness>> {
  const qs = buildQueryString(params);
  const response = await apiClient.get<PaginatedResponse<ExploreBusiness>>(
    `/explore/businesses/${qs}`,
  );
  return response.data;
}

export async function searchUsersApi(
  params: UserSearchParams,
): Promise<PaginatedResponse<ExploreUser>> {
  const qs = buildQueryString(params);
  const response = await apiClient.get<PaginatedResponse<ExploreUser>>(
    `/explore/users/${qs}`,
  );
  return response.data;
}

export async function fetchTagSuggestionsApi(
  q?: string,
  category?: string,
  limit?: number,
): Promise<SuggestedTag[]> {
  const qs = buildQueryString({ q, category, limit });
  const response = await apiClient.get<SuggestedTag[]>(`/explore/tags/${qs}`);
  return response.data;
}

export async function fetchCitiesApi(country: string): Promise<CityListResponse> {
  const qs = buildQueryString({ country });
  const response = await apiClient.get<CityListResponse>(`/explore/cities/${qs}`);
  return response.data;
}
