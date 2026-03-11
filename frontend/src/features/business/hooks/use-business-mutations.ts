import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  archiveBusinessApi,
  createBusinessApi,
  deleteBusinessApi,
  updateBusinessApi,
  updateBusinessProfileApi,
  type CreateBusinessData,
  type UpdateBusinessData,
  type UpdateBusinessProfileData,
} from "@/features/business/api/business-api";
import { queryKeys } from "@/lib/query-keys";

export function useCreateBusiness() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateBusinessData) => createBusinessApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.business.my() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.memberships() });
    },
  });
}

export function useUpdateBusiness(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateBusinessData) =>
      updateBusinessApi(slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.business.detail(slug) });
    },
  });
}

export function useUpdateBusinessProfile(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateBusinessProfileData) =>
      updateBusinessProfileApi(slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.business.detail(slug) });
    },
  });
}

export function useArchiveBusiness(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => archiveBusinessApi(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.business.detail(slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.business.my() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.memberships() });
    },
  });
}

export function useDeleteBusiness(slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => deleteBusinessApi(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.business.my() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.memberships() });
    },
  });
}
