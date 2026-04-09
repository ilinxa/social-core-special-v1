/**
 * Governance console types — matches backend governance serializers.
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// BUSINESS GOVERNANCE
// =============================================================================

export interface GovernanceBusinessProfile {
  display_name: string;
  tagline: string;
  logo: string | null;
  cover_image: string | null;
  website: string;
  industry: string;
  is_public: boolean;
}

export interface GovernanceBusiness {
  id: string;
  slug: string;
  legal_name: string;
  country: string;
  city: string;
  business_type: string;
  business_type_display: string;
  status: string;
  status_display: string;
  verification_status: string;
  verification_status_display: string;
  is_platform_branch: boolean;
  member_count: number;
  created_by_email: string | null;
  profile: GovernanceBusinessProfile;
  created_at: string;
  updated_at: string;
}

export interface GovernanceBusinessDetail extends GovernanceBusiness {
  registration_number: string;
  tax_id: string;
  legal_address: string;
  verified_at: string | null;
  max_members: number;
  open_member_request: boolean;
  settings: Record<string, unknown>;
  owner_email: string | null;
  owner_name: string | null;
}

export type GovernanceBusinessPermissions = {
  can_suspend: boolean;
  can_view_businesses: boolean;
  can_edit: boolean;
  can_verify: boolean;
  can_remove_owner: boolean;
  can_transfer_ownership: boolean;
  can_view_legal_info: boolean;
  can_archive: boolean;
  can_approve_creation: boolean;
};

export type GovernanceBusinessDetailWithPerms = GovernanceBusinessDetail &
  WithPermissions<GovernanceBusinessPermissions>;

// =============================================================================
// FILTER PARAMS
// =============================================================================

export interface GovernanceBusinessListParams {
  status?: string;
  verification_status?: string;
  business_type?: string;
  country?: string;
  search?: string;
  include_deleted?: boolean;
  page?: number;
  page_size?: number;
}

// =============================================================================
// AUDIT LOG
// =============================================================================

export interface GovernanceAuditLog {
  id: string;
  timestamp: string;
  actor_id: string;
  actor_email: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id: string;
  resource_repr: string;
  outcome: string;
  details: Record<string, unknown> | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  request_id: string | null;
}

export interface GovernanceAuditListParams {
  action?: string;
  outcome?: string;
  actor_id?: string;
  since?: string;
  until?: string;
  resource_type?: string;
  page?: number;
  page_size?: number;
}

// =============================================================================
// MEMBER GOVERNANCE
// =============================================================================

export interface GovernanceMemberUser {
  id: string;
  email: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface GovernanceMember {
  id: string;
  user: GovernanceMemberUser;
  account_type: string;
  account_id: string;
  account_name: string;
  account_slug: string | null;
  role_name: string;
  role_level: number;
  is_owner: boolean;
  status: string;
  status_reason: string;
  status_changed_at: string | null;
  joined_at: string;
}

export interface GovernanceMemberDetail extends GovernanceMember {
  created_at: string;
  updated_at: string;
}

export type GovernanceMemberPermissions = {
  can_suspend: boolean;
  can_ban: boolean;
  can_remove: boolean;
  can_reactivate: boolean;
  can_change_role: boolean;
};

export type GovernanceMemberDetailWithPerms = GovernanceMemberDetail &
  WithPermissions<GovernanceMemberPermissions>;

export interface GovernanceMemberListParams {
  account_type?: string;
  status?: string;
  search?: string;
  include_deleted?: boolean;
  page?: number;
  page_size?: number;
}

// =============================================================================
// TRANSACTION GOVERNANCE
// =============================================================================

export interface GovernanceTransactionListParams {
  status?: string;
  mode?: string;
  transaction_type?: string;
  context_type?: string;
  page?: number;
  page_size?: number;
}
