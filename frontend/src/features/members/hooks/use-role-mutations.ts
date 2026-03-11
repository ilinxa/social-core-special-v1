import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  createRoleApi,
  updateRoleApi,
  deleteRoleApi,
  addPermissionToRoleApi,
  removePermissionFromRoleApi,
} from "@/features/members/api/roles-api";
import type { AccountType } from "@/types/rbac";
import type {
  CreateRoleInput,
  UpdateRoleInput,
  AddPermissionInput,
  RemovePermissionInput,
} from "@/types/members";

export function useCreateRole(accountType: AccountType, slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateRoleInput) =>
      createRoleApi(accountType, slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.list(accountType, slug) });
    },
  });
}

export function useUpdateRole(
  accountType: AccountType,
  slug: string,
  roleId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateRoleInput) =>
      updateRoleApi(accountType, slug, roleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.list(accountType, slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.detail(roleId) });
    },
  });
}

export function useDeleteRole(accountType: AccountType, slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (roleId: string) =>
      deleteRoleApi(accountType, slug, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.list(accountType, slug) });
    },
  });
}

export function useAddPermission(
  accountType: AccountType,
  slug: string,
  roleId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AddPermissionInput) =>
      addPermissionToRoleApi(accountType, slug, roleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.detail(roleId) });
    },
  });
}

export function useRemovePermission(
  accountType: AccountType,
  slug: string,
  roleId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RemovePermissionInput) =>
      removePermissionFromRoleApi(accountType, slug, roleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.detail(roleId) });
    },
  });
}
