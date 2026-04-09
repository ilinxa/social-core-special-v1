/**
 * Governance query hooks — TanStack Query wrappers for governance read operations.
 */

import { queryOptions, useQuery } from "@tanstack/react-query";

import { listGovernanceAuditApi } from "@/features/governance/api/governance-audit-api";
import {
  getGovernanceBusinessApi,
  listGovernanceBusinessesApi,
  listGovernanceVerificationApi,
} from "@/features/governance/api/governance-business-api";
import {
  getGovernanceMemberApi,
  listGovernanceMembersApi,
} from "@/features/governance/api/governance-members-api";
import { listGovernanceApprovedCreatorsApi } from "@/features/governance/api/governance-approved-creators-api";
import { listGovernanceTransactionsApi } from "@/features/governance/api/governance-transactions-api";
import { queryKeys } from "@/lib/query-keys";
import type {
  GovernanceAuditListParams,
  GovernanceBusinessListParams,
  GovernanceMemberListParams,
  GovernanceTransactionListParams,
} from "@/types/governance";

// =============================================================================
// QUERY OPTIONS FACTORIES
// =============================================================================

export function governanceBusinessesQueryOptions(
  params?: GovernanceBusinessListParams,
) {
  return queryOptions({
    queryKey: queryKeys.governance.businesses(params as Record<string, unknown>),
    queryFn: () => listGovernanceBusinessesApi(params),
    staleTime: 2 * 60 * 1000,
  });
}

export function governanceBusinessDetailQueryOptions(id: string) {
  return queryOptions({
    queryKey: queryKeys.governance.businessDetail(id),
    queryFn: () => getGovernanceBusinessApi(id),
    staleTime: 60 * 1000,
    enabled: !!id,
  });
}

export function governanceVerificationQueryOptions(params?: {
  page?: number;
  page_size?: number;
}) {
  return queryOptions({
    queryKey: queryKeys.governance.verification(params),
    queryFn: () => listGovernanceVerificationApi(params),
    staleTime: 2 * 60 * 1000,
  });
}

// =============================================================================
// HOOKS
// =============================================================================

export function useGovernanceBusinesses(params?: GovernanceBusinessListParams) {
  return useQuery(governanceBusinessesQueryOptions(params));
}

export function useGovernanceBusiness(id: string) {
  return useQuery(governanceBusinessDetailQueryOptions(id));
}

export function useGovernanceVerification(params?: {
  page?: number;
  page_size?: number;
}) {
  return useQuery(governanceVerificationQueryOptions(params));
}

// =============================================================================
// AUDIT LOG
// =============================================================================

export function governanceAuditQueryOptions(
  params?: GovernanceAuditListParams,
) {
  return queryOptions({
    queryKey: queryKeys.governance.auditLogs(params as Record<string, unknown>),
    queryFn: () => listGovernanceAuditApi(params),
    staleTime: 60 * 1000,
  });
}

export function useGovernanceAuditLogs(params?: GovernanceAuditListParams) {
  return useQuery(governanceAuditQueryOptions(params));
}

// =============================================================================
// MEMBERS
// =============================================================================

export function governanceMembersQueryOptions(
  params?: GovernanceMemberListParams,
) {
  return queryOptions({
    queryKey: queryKeys.governance.members(params as Record<string, unknown>),
    queryFn: () => listGovernanceMembersApi(params),
    staleTime: 2 * 60 * 1000,
  });
}

export function governanceMemberDetailQueryOptions(id: string) {
  return queryOptions({
    queryKey: queryKeys.governance.memberDetail(id),
    queryFn: () => getGovernanceMemberApi(id),
    staleTime: 60 * 1000,
    enabled: !!id,
  });
}

export function useGovernanceMembers(params?: GovernanceMemberListParams) {
  return useQuery(governanceMembersQueryOptions(params));
}

export function useGovernanceMember(id: string) {
  return useQuery(governanceMemberDetailQueryOptions(id));
}

// =============================================================================
// TRANSACTIONS
// =============================================================================

export function governanceTransactionsQueryOptions(
  params?: GovernanceTransactionListParams,
) {
  return queryOptions({
    queryKey: queryKeys.governance.transactions(
      params as Record<string, unknown>,
    ),
    queryFn: () => listGovernanceTransactionsApi(params),
    staleTime: 2 * 60 * 1000,
  });
}

export function useGovernanceTransactions(
  params?: GovernanceTransactionListParams,
) {
  return useQuery(governanceTransactionsQueryOptions(params));
}

// =============================================================================
// APPROVED CREATORS
// =============================================================================

export function governanceApprovedCreatorsQueryOptions(
  params?: Record<string, unknown>,
) {
  return queryOptions({
    queryKey: queryKeys.governance.approvedCreators(params),
    queryFn: () => listGovernanceApprovedCreatorsApi(params),
    staleTime: 2 * 60 * 1000,
  });
}

export function useGovernanceApprovedCreators(
  params?: Record<string, unknown>,
) {
  return useQuery(governanceApprovedCreatorsQueryOptions(params));
}
