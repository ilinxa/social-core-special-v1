import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  createInvitationApi,
  createRequestApi,
  acceptTransactionApi,
  denyTransactionApi,
  cancelTransactionApi,
  dismissTransactionApi,
  requestInfoApi,
  resubmitTransactionApi,
  approveTransactionApi,
  updateTransactionFormResponseApi,
  createFormMappingApi,
  deleteFormMappingApi,
} from "@/features/transactions/api/transactions-api";
import type {
  CreateInvitationInput,
  CreateRequestInput,
  AcceptInput,
  DenyInput,
  RequestInfoInput,
  FormResponseUpdateInput,
  CreateFormMappingInput,
} from "@/types/transactions";

// =============================================================================
// TRANSACTION CREATION
// =============================================================================

export function useCreateInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateInvitationInput) => createInvitationApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.all,
      });
    },
  });
}

export function useCreateRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateRequestInput) => createRequestApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.all,
      });
    },
  });
}

// =============================================================================
// TRANSACTION ACTIONS
// =============================================================================

function useTransactionAction(
  actionFn: (id: string, data?: unknown) => Promise<unknown>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      data,
    }: {
      transactionId: string;
      data?: unknown;
    }) => actionFn(transactionId, data),
    onSuccess: (_result, { transactionId }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.detail(transactionId),
      });
    },
  });
}

export function useAcceptTransaction() {
  return useTransactionAction((id, data) =>
    acceptTransactionApi(id, data as AcceptInput | undefined),
  );
}

export function useDenyTransaction() {
  return useTransactionAction((id, data) =>
    denyTransactionApi(id, data as DenyInput | undefined),
  );
}

export function useCancelTransaction() {
  return useTransactionAction((id) => cancelTransactionApi(id));
}

export function useDismissTransaction() {
  return useTransactionAction((id) => dismissTransactionApi(id));
}

export function useRequestInfo() {
  return useTransactionAction((id, data) =>
    requestInfoApi(id, data as RequestInfoInput),
  );
}

export function useResubmitTransaction() {
  return useTransactionAction((id) => resubmitTransactionApi(id));
}

export function useApproveTransaction() {
  return useTransactionAction((id) => approveTransactionApi(id));
}

// =============================================================================
// FORM RESPONSE
// =============================================================================

export function useUpdateTransactionFormResponse(transactionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FormResponseUpdateInput) =>
      updateTransactionFormResponseApi(transactionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.formResponse(transactionId),
      });
    },
  });
}

// =============================================================================
// FORM MAPPINGS
// =============================================================================

export function useCreateFormMapping(
  accountType: string,
  accountId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateFormMappingInput) => createFormMappingApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.formMappings(accountType, accountId),
      });
    },
  });
}

export function useDeleteFormMapping(
  accountType: string,
  accountId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mappingId: string) => deleteFormMappingApi(mappingId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.formMappings(accountType, accountId),
      });
    },
  });
}
