/**
 * Governance mutation hooks — TanStack Query wrappers for governance actions.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  archiveBusinessApi,
  reactivateBusinessApi,
  suspendBusinessApi,
  transferOwnershipApi,
} from "@/features/governance/api/governance-business-api";
import { governanceMemberActionApi } from "@/features/governance/api/governance-members-api";
import { queryKeys } from "@/lib/query-keys";

export function useSuspendBusiness() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      suspendBusinessApi(id, reason),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.businessDetail(id),
      });
    },
  });
}

export function useReactivateBusiness() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string }) => reactivateBusinessApi(id),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.businessDetail(id),
      });
    },
  });
}

export function useArchiveBusiness() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string }) => archiveBusinessApi(id),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.businessDetail(id),
      });
    },
  });
}

export function useTransferOwnership() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      newOwnerId,
      reason,
    }: {
      id: string;
      newOwnerId: string;
      reason?: string;
    }) => transferOwnershipApi(id, newOwnerId, reason),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.businessDetail(id),
      });
    },
  });
}

export function useGovernanceMemberAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      action,
      reason,
    }: {
      id: string;
      action: string;
      reason?: string;
    }) => governanceMemberActionApi(id, action, reason),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.governance.memberDetail(id),
      });
    },
  });
}
