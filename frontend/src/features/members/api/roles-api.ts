import { apiClient } from "@/lib/api-client";
import type {
  RoleListItem,
  RoleDetailWithPerms,
  CreateRoleInput,
  UpdateRoleInput,
  AddPermissionInput,
  RemovePermissionInput,
  Permission,
} from "@/types/members";
import type { AccountType } from "@/types/rbac";

// =============================================================================
// URL BUILDER
// =============================================================================

function buildRoleUrl(
  accountType: AccountType,
  slug?: string,
  roleId?: string,
  suffix?: string,
): string {
  const base =
    accountType === "business"
      ? `/business/${slug}/roles`
      : "/platform/roles";

  if (roleId && suffix) return `${base}/${roleId}/${suffix}/`;
  if (roleId) return `${base}/${roleId}/`;
  return `${base}/`;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function fetchRolesApi(
  accountType: AccountType,
  slug: string,
): Promise<RoleListItem[]> {
  const response = await apiClient.get<RoleListItem[]>(
    buildRoleUrl(accountType, slug),
  );
  return response.data;
}

export async function fetchRoleDetailApi(
  accountType: AccountType,
  slug: string,
  roleId: string,
): Promise<RoleDetailWithPerms> {
  const response = await apiClient.get<RoleDetailWithPerms>(
    buildRoleUrl(accountType, slug, roleId),
  );
  return response.data;
}

export async function createRoleApi(
  accountType: AccountType,
  slug: string,
  data: CreateRoleInput,
): Promise<RoleDetailWithPerms> {
  const response = await apiClient.post<RoleDetailWithPerms>(
    buildRoleUrl(accountType, slug),
    data,
  );
  return response.data;
}

export async function updateRoleApi(
  accountType: AccountType,
  slug: string,
  roleId: string,
  data: UpdateRoleInput,
): Promise<RoleDetailWithPerms> {
  const response = await apiClient.patch<RoleDetailWithPerms>(
    buildRoleUrl(accountType, slug, roleId),
    data,
  );
  return response.data;
}

export async function deleteRoleApi(
  accountType: AccountType,
  slug: string,
  roleId: string,
): Promise<void> {
  await apiClient.delete(buildRoleUrl(accountType, slug, roleId));
}

export async function addPermissionToRoleApi(
  accountType: AccountType,
  slug: string,
  roleId: string,
  data: AddPermissionInput,
): Promise<void> {
  await apiClient.post(
    buildRoleUrl(accountType, slug, roleId, "permissions"),
    data,
  );
}

export async function removePermissionFromRoleApi(
  accountType: AccountType,
  slug: string,
  roleId: string,
  data: RemovePermissionInput,
): Promise<void> {
  await apiClient.delete(
    buildRoleUrl(accountType, slug, roleId, "permissions"),
    { data },
  );
}

export async function fetchAllPermissionsApi(): Promise<Permission[]> {
  const response = await apiClient.get<Permission[]>("/rbac/permissions/");
  return response.data;
}
