/**
 * Explore system types matching backend API contracts.
 *
 * Backend source: apps.explore.serializers
 */

// =============================================================================
// EXPLORE BUSINESS
// =============================================================================

export interface ExploreBusinessProfile {
  display_name: string;
  tagline: string;
  logo: string | null;
  industry: string;
  company_size: string;
  tags: string[];
  website: string;
}

export interface ExploreBusiness {
  id: string;
  slug: string;
  legal_name: string;
  country: string;
  city: string;
  business_type: string;
  is_platform_branch: boolean;
  open_member_request: boolean;
  is_verified: boolean;
  profile: ExploreBusinessProfile | null;
  search_rank: number;
}

// =============================================================================
// EXPLORE USER
// =============================================================================

export interface ExploreUserProfile {
  first_name: string;
  last_name: string;
  bio: string;
  avatar_url: string | null;
  country: string;
  city: string;
  tags: string[];
}

export interface ExploreUser {
  id: string;
  username: string;
  email: string;
  is_verified: boolean;
  display_name: string;
  profile: ExploreUserProfile | null;
  search_rank: number;
}

// =============================================================================
// COMBINED RESPONSE
// =============================================================================

export interface ExploreCombinedResponse {
  businesses: ExploreBusiness[];
  users: ExploreUser[];
  businesses_count: number;
  users_count: number;
}

// =============================================================================
// TAG & CITY
// =============================================================================

export interface SuggestedTag {
  id: number;
  name: string;
  slug: string;
  category: "user" | "business" | "both";
  usage_count: number;
}

export interface CityListResponse {
  country: string;
  cities: string[];
}

// =============================================================================
// SEARCH PARAMS
// =============================================================================

export type BusinessSearchParams = {
  q?: string;
  country?: string;
  city?: string;
  industry?: string;
  company_size?: string;
  business_type?: string;
  verified?: string;
  is_platform_branch?: string;
  tags?: string;
  founded_year_min?: string;
  founded_year_max?: string;
  has_website?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
};

export type UserSearchParams = {
  q?: string;
  country?: string;
  city?: string;
  language?: string;
  verified?: string;
  tags?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
};
