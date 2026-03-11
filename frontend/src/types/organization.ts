/**
 * Organization types matching backend API contracts.
 *
 * Backend source: apps.organization.business.serializers,
 *                 apps.organization.platform.serializers
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// BUSINESS
// =============================================================================

export interface BusinessProfile {
  display_name: string;
  tagline: string;
  description: string;
  logo: string | null;
  cover_image: string | null;
  website: string;
  contact_email: string;
  contact_phone: string;
  industry: string;
  company_size: string;
  founded_year: number | null;
  social_links: Record<string, string>;
  tags: string[];
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface BusinessAccount {
  id: string;
  slug: string;
  legal_name: string;
  registration_number: string;
  tax_id: string;
  country: string;
  city: string;
  legal_address: string;
  business_type: string;
  is_platform_branch: boolean;
  max_members: number;
  open_member_request: boolean;
  business_type_display: string;
  status: string;
  status_display: string;
  verification_status: string;
  verification_status_display: string;
  verified_at: string | null;
  settings: Record<string, unknown>;
  profile: BusinessProfile;
  created_at: string;
  updated_at: string;
}

export interface BusinessAccountList {
  id: string;
  slug: string;
  legal_name: string;
  country: string;
  city: string;
  business_type: string;
  is_platform_branch: boolean;
  max_members: number;
  open_member_request: boolean;
  status: string;
  verification_status: string;
  profile: BusinessProfile;
  created_at: string;
}

// =============================================================================
// PLATFORM
// =============================================================================

export interface PlatformProfile {
  name: string;
  tagline: string;
  description: string;
  logo: string | null;
  favicon: string | null;
  primary_color: string;
  secondary_color: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  social_links: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface PlatformAccount {
  id: string;
  is_configured: boolean;
  max_members: number;
  open_member_request: boolean;
  settings: Record<string, unknown>;
  profile: PlatformProfile;
  created_at: string;
  updated_at: string;
}

// =============================================================================
// PERMISSION INTERFACES (from backend Policy.get_viewer_permissions)
// =============================================================================

export type BusinessPermissions = {
  can_view: boolean;
  can_edit: boolean;
  can_edit_profile: boolean;
  can_delete: boolean;
  can_change_slug: boolean;
  can_archive: boolean;
};

export type PlatformPermissions = {
  can_view: boolean;
  can_edit_profile: boolean;
  can_edit_settings: boolean;
};

// Composed types for detail responses with evaluated permissions
export type BusinessAccountWithPerms = BusinessAccount &
  WithPermissions<BusinessPermissions>;
export type PlatformAccountWithPerms = PlatformAccount &
  WithPermissions<PlatformPermissions>;

// =============================================================================
// RELATIONSHIP (from backend RelationshipInjectMixin)
// =============================================================================

/** Summary of an active transaction in a conflict group. */
export type ActiveTransactionSummary = {
  id: string;
  type: string;
  status: string;
  mode: "invitation" | "request";
  viewer_role: "initiator" | "target";
};

/** Relationship data injected into entity detail responses for auth'd users. */
export type EntityRelationship = {
  // Membership (all account types)
  membership_status: string | null;
  active_transaction: ActiveTransactionSummary | null;
  // Follow (business/platform)
  follow_status?: string | null;
  follow_id?: string | null;
  active_follow_transaction?: ActiveTransactionSummary | null;
  // Connection (user profiles)
  connection_status?: string | null;
  connection_id?: string | null;
  active_connection_transaction?: ActiveTransactionSummary | null;
};

/** Business detail with both _permissions and _relationship. */
export type BusinessAccountWithRelationship = BusinessAccountWithPerms & {
  _relationship?: EntityRelationship;
};

/** Platform detail with both _permissions and _relationship. */
export type PlatformAccountWithRelationship = PlatformAccountWithPerms & {
  _relationship?: EntityRelationship;
};
