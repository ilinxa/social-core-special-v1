import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchRolesApi,
  fetchRoleDetailApi,
  fetchAllPermissionsApi,
} from "@/features/members/api/roles-api";
import type { AccountType } from "@/types/rbac";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function roleListQueryOptions(accountType: AccountType, slug: string) {
  return queryOptions({
    queryKey: queryKeys.roles.list(accountType, slug),
    queryFn: () => fetchRolesApi(accountType, slug),
    staleTime: 5 * 60 * 1000,
    enabled: !!slug,
  });
}

export function roleDetailQueryOptions(
  accountType: AccountType,
  slug: string,
  roleId: string,
) {
  return queryOptions({
    queryKey: queryKeys.roles.detail(roleId),
    queryFn: () => fetchRoleDetailApi(accountType, slug, roleId),
    staleTime: 5 * 60 * 1000,
    enabled: !!slug && !!roleId,
  });
}

export function allPermissionsQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.rbac.permissions(),
    queryFn: fetchAllPermissionsApi,
    staleTime: 30 * 60 * 1000,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useRoleList(accountType: AccountType, slug: string) {
  return useQuery(roleListQueryOptions(accountType, slug));
}

export function useRoleDetail(
  accountType: AccountType,
  slug: string,
  roleId: string,
) {
  return useQuery(roleDetailQueryOptions(accountType, slug, roleId));
}

export function useAllPermissions() {
  return useQuery(allPermissionsQueryOptions());
}
