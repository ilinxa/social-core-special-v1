/**
 * Member and Role management types matching backend API contracts.
 *
 * Backend source: apps.rbac.serializers, apps.rbac.policies
 */

import type { WithPermissions } from "@/types/api";
import type { AccountType, MembershipStatus, Role } from "@/types/rbac";

// =============================================================================
// OUTPUT TYPES
// =============================================================================

/** Minimal user info for membership lists (MemberUserOutputSerializer). */
export type MemberUser = {
  id: string;
  email: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
};

/** Lightweight membership for list views (MembershipListOutputSerializer). */
export type MemberListItem = {
  id: string;
  user: MemberUser;
  role_name: string;
  role_level: number;
  is_owner: boolean;
  status: MembershipStatus;
  joined_at: string;
};

/** Full membership for detail views (MembershipOutputSerializer). */
export type MemberDetail = {
  id: string;
  user: MemberUser;
  account_type: AccountType;
  account_id: string;
  role: Role;
  is_owner: boolean;
  status: MembershipStatus;
  joined_at: string;
  status_changed_at: string | null;
  status_reason: string;
  created_at: string;
  updated_at: string;
};

// =============================================================================
// ROLE TYPES
// =============================================================================

/** Role with member count for list views (RoleOutputSerializer + annotation). */
export type RoleListItem = Role & {
  member_count: number;
};

/** Permission attached to a role (RolePermissionOutputSerializer). */
export type RolePermission = {
  id: string;
  permission: Permission;
  scope: string;
};

/** Full role for detail views (RoleDetailOutputSerializer). */
export type RoleDetail = {
  id: string;
  name: string;
  account_type: AccountType;
  account_id: string;
  level: number;
  is_system_role: boolean;
  description: string;
  role_permissions: RolePermission[];
  permission_count: number;
  created_at: string;
  updated_at: string;
};

/** RBAC permission (PermissionOutputSerializer). */
export type Permission = {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  applicable_scopes: string[];
};

// =============================================================================
// PERMISSION TYPES (from backend Policy.get_viewer_permissions)
// =============================================================================

export type MemberPermissions = {
  can_change_role: boolean;
  can_suspend: boolean;
  can_remove: boolean;
  can_ban: boolean;
  can_reactivate: boolean;
};

export type RolePermissions = {
  can_edit: boolean;
  can_delete: boolean;
  can_modify_permissions: boolean;
};

export type MemberDetailWithPerms = MemberDetail &
  WithPermissions<MemberPermissions>;

export type RoleDetailWithPerms = RoleDetail &
  WithPermissions<RolePermissions>;

// =============================================================================
// INPUT TYPES
// =============================================================================

export type CreateRoleInput = {
  name: string;
  level: number;
  description?: string;
};

export type UpdateRoleInput = {
  name?: string;
  description?: string;
};

export type AddPermissionInput = {
  permission_id: string;
  scope: string;
};

export type RemovePermissionInput = {
  permission_id: string;
};

export type ChangeRoleInput = {
  role_id: string;
};

export type MemberActionInput = {
  reason?: string;
};

// =============================================================================
// QUERY PARAMS
// =============================================================================

export type MemberListParams = {
  search?: string;
  status?: MembershipStatus;
  role_id?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
};
