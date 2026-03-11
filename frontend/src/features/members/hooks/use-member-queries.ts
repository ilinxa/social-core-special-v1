import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchMembersApi,
  fetchMemberDetailApi,
} from "@/features/members/api/members-api";
import type { AccountType } from "@/types/rbac";
import type { MemberListParams } from "@/types/members";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function memberListQueryOptions(
  accountType: AccountType,
  slug: string,
  params?: MemberListParams,
) {
  return queryOptions({
    queryKey: queryKeys.members.list(accountType, slug, params as Record<string, unknown>),
    queryFn: () => fetchMembersApi(accountType, slug, params),
    staleTime: 2 * 60 * 1000,
    enabled: !!slug,
  });
}

export function memberDetailQueryOptions(
  accountType: AccountType,
  slug: string,
  membershipId: string,
) {
  return queryOptions({
    queryKey: queryKeys.members.detail(membershipId),
    queryFn: () => fetchMemberDetailApi(accountType, slug, membershipId),
    staleTime: 2 * 60 * 1000,
    enabled: !!slug && !!membershipId,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useMemberList(
  accountType: AccountType,
  slug: string,
  params?: MemberListParams,
) {
  return useQuery(memberListQueryOptions(accountType, slug, params));
}

export function useMemberDetail(
  accountType: AccountType,
  slug: string,
  membershipId: string,
) {
  return useQuery(memberDetailQueryOptions(accountType, slug, membershipId));
}
