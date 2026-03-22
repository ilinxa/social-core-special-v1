/**
 * Shared TypeScript types matching backend API contracts.
 *
 * Backend source: apps.core.exceptions, apps.core.pagination,
 * apps.users.serializers, apps.auth.serializers
 */

import type { WithPermissions } from "@/types/api";
import type { EntityRelationship } from "@/types/organization";

// =============================================================================
// API ERROR RESPONSE
// =============================================================================

export interface ApiErrorResponse {
  error: {
    message: string;
    code: string;
    details?: Record<string, unknown>;
  };
}

export type ApiErrorCode =
  | "bad_request"
  | "validation_error"
  | "business_rule_violation"
  | "domain_error"
  | "authentication_error"
  | "invalid_credentials"
  | "token_expired"
  | "token_invalid"
  | "token_already_used"
  | "account_not_verified"
  | "account_inactive"
  | "permission_denied"
  | "not_found"
  | "conflict"
  | "missing_token"
  | "oauth_error"
  | "rate_limit_exceeded"
  | "service_unavailable";

// =============================================================================
// PAGINATION
// =============================================================================

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// =============================================================================
// USER
// =============================================================================

export interface UserProfile {
  first_name: string;
  last_name: string;
  full_name: string;
  display_name: string;
  phone: string;
  avatar_url: string | null;
  has_avatar: boolean;
  cover_image_url: string | null;
  has_cover_image: boolean;
  timezone: string;
  language: string;
  bio: string;
  country: string;
  city: string;
  tags: string[];
  is_public: boolean;
}

// Public profile — subset visible to other users (no phone, timezone, language)
export type UserPublicProfile = {
  first_name: string;
  last_name: string;
  full_name: string;
  display_name: string;
  avatar_url: string | null;
  has_avatar: boolean;
  cover_image_url: string | null;
  has_cover_image: boolean;
  bio: string;
  country: string;
  city: string;
  tags: string[];
  is_public: boolean;
};

export type UserPublic = {
  id: string;
  username: string;
  is_verified: boolean;
  is_complete: boolean;
  date_joined: string;
  profile: UserPublicProfile | null;
};

export type UserPublicPermissions = {
  is_own_profile: boolean;
  can_edit_profile: boolean;
};

export type UserPublicWithPerms = UserPublic & WithPermissions<UserPublicPermissions>;

export type UserLimitedProfile = {
  display_name: string;
  avatar_url: string | null;
  has_avatar: boolean;
};

export type UserLimited = {
  id: string;
  username: string;
  is_verified: boolean;
  date_joined: string;
  profile: UserLimitedProfile;
  is_limited: true;
  _permissions?: UserPublicPermissions;
  _relationship?: EntityRelationship;
};

/** User public detail with both _permissions and _relationship. */
export type UserPublicWithRelationship = UserPublicWithPerms & {
  _relationship?: EntityRelationship;
};

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
  is_complete: boolean;
  can_create_business: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
  profile: UserProfile;
}

export interface UserMinimal {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export type ApprovedCreatorItem = {
  id: string;
  email: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  can_create_business: boolean;
  date_joined: string;
};

// =============================================================================
// AUTH
// =============================================================================

export interface AuthTokens {
  access_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
  token_type: "Bearer";
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
  is_new_user?: boolean;
}
