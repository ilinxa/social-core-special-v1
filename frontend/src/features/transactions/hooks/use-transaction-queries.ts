import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchTransactionsApi,
  fetchTransactionDetailApi,
  fetchTransactionTypesApi,
  fetchFormMappingsApi,
  fetchTransactionFormResponseApi,
} from "@/features/transactions/api/transactions-api";
import type { TransactionListParams } from "@/types/transactions";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function transactionListQueryOptions(params?: TransactionListParams) {
  return queryOptions({
    queryKey: queryKeys.transactions.list(params as Record<string, unknown>),
    queryFn: () => fetchTransactionsApi(params),
    staleTime: 1 * 60 * 1000,
    enabled: !!params,
  });
}

export function transactionDetailQueryOptions(transactionId: string) {
  return queryOptions({
    queryKey: queryKeys.transactions.detail(transactionId),
    queryFn: () => fetchTransactionDetailApi(transactionId),
    staleTime: 1 * 60 * 1000,
    enabled: !!transactionId,
  });
}

export function transactionTypesQueryOptions(contextType?: string) {
  return queryOptions({
    queryKey: queryKeys.transactions.types(contextType),
    queryFn: () => fetchTransactionTypesApi(contextType),
    staleTime: 30 * 60 * 1000,
  });
}

export function formMappingsQueryOptions(
  accountType: string,
  accountId: string,
) {
  return queryOptions({
    queryKey: queryKeys.transactions.formMappings(accountType, accountId),
    queryFn: () =>
      fetchFormMappingsApi({ account_type: accountType, account_id: accountId }),
    staleTime: 5 * 60 * 1000,
    enabled: !!accountId,
  });
}

export function transactionFormResponseQueryOptions(transactionId: string) {
  return queryOptions({
    queryKey: queryKeys.transactions.formResponse(transactionId),
    queryFn: () => fetchTransactionFormResponseApi(transactionId),
    staleTime: 2 * 60 * 1000,
    enabled: !!transactionId,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useTransactionList(params?: TransactionListParams) {
  return useQuery(transactionListQueryOptions(params));
}

export function useTransactionDetail(transactionId: string) {
  return useQuery(transactionDetailQueryOptions(transactionId));
}

export function useTransactionTypes(contextType?: string) {
  return useQuery(transactionTypesQueryOptions(contextType));
}

export function useFormMappings(accountType: string, accountId: string) {
  return useQuery(formMappingsQueryOptions(accountType, accountId));
}

export function useTransactionFormResponse(transactionId: string) {
  return useQuery(transactionFormResponseQueryOptions(transactionId));
}
