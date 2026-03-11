import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  changeMemberRoleApi,
  suspendMemberApi,
  removeMemberApi,
  banMemberApi,
  reactivateMemberApi,
  leaveMemberApi,
} from "@/features/members/api/members-api";
import type { AccountType } from "@/types/rbac";
import type { ChangeRoleInput, MemberActionInput } from "@/types/members";

function useMemberMutation(
  accountType: AccountType,
  slug: string,
  mutationFn: (membershipId: string, data?: MemberActionInput) => Promise<void>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ membershipId, data }: { membershipId: string; data?: MemberActionInput }) =>
      mutationFn(membershipId, data),
    onSuccess: (_data, { membershipId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.members.list(accountType, slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.members.detail(membershipId) });
    },
  });
}

export function useChangeMemberRole(accountType: AccountType, slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ membershipId, data }: { membershipId: string; data: ChangeRoleInput }) =>
      changeMemberRoleApi(accountType, slug, membershipId, data),
    onSuccess: (_data, { membershipId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.members.list(accountType, slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.members.detail(membershipId) });
    },
  });
}

export function useSuspendMember(accountType: AccountType, slug: string) {
  return useMemberMutation(accountType, slug, (membershipId, data) =>
    suspendMemberApi(accountType, slug, membershipId, data),
  );
}

export function useRemoveMember(accountType: AccountType, slug: string) {
  return useMemberMutation(accountType, slug, (membershipId, data) =>
    removeMemberApi(accountType, slug, membershipId, data),
  );
}

export function useBanMember(accountType: AccountType, slug: string) {
  return useMemberMutation(accountType, slug, (membershipId, data) =>
    banMemberApi(accountType, slug, membershipId, data),
  );
}

export function useReactivateMember(accountType: AccountType, slug: string) {
  return useMemberMutation(accountType, slug, (membershipId) =>
    reactivateMemberApi(accountType, slug, membershipId),
  );
}

export function useLeaveMember(accountType: AccountType, slug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => leaveMemberApi(accountType, slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.members.list(accountType, slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.memberships() });
    },
  });
}
