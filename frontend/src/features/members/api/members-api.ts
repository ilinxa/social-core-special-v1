import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  MemberListItem,
  MemberDetailWithPerms,
  MemberListParams,
  ChangeRoleInput,
  MemberActionInput,
} from "@/types/members";
import type { AccountType } from "@/types/rbac";

// =============================================================================
// URL BUILDER
// =============================================================================

function buildMemberUrl(
  accountType: AccountType,
  slug?: string,
  membershipId?: string,
  action?: string,
): string {
  const base =
    accountType === "business"
      ? `/business/${slug}/members`
      : "/platform/members";

  if (membershipId && action) return `${base}/${membershipId}/${action}/`;
  if (membershipId) return `${base}/${membershipId}/`;
  if (action) return `${base}/${action}/`;
  return `${base}/`;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function fetchMembersApi(
  accountType: AccountType,
  slug: string,
  params?: MemberListParams,
): Promise<PaginatedResponse<MemberListItem>> {
  const response = await apiClient.get<PaginatedResponse<MemberListItem>>(
    buildMemberUrl(accountType, slug),
    { params },
  );
  return response.data;
}

export async function fetchMemberDetailApi(
  accountType: AccountType,
  slug: string,
  membershipId: string,
): Promise<MemberDetailWithPerms> {
  const response = await apiClient.get<MemberDetailWithPerms>(
    buildMemberUrl(accountType, slug, membershipId),
  );
  return response.data;
}

export async function changeMemberRoleApi(
  accountType: AccountType,
  slug: string,
  membershipId: string,
  data: ChangeRoleInput,
): Promise<void> {
  await apiClient.patch(
    buildMemberUrl(accountType, slug, membershipId, "role"),
    data,
  );
}

export async function suspendMemberApi(
  accountType: AccountType,
  slug: string,
  membershipId: string,
  data?: MemberActionInput,
): Promise<void> {
  await apiClient.post(
    buildMemberUrl(accountType, slug, membershipId, "suspend"),
    data ?? {},
  );
}

export async function removeMemberApi(
  accountType: AccountType,
  slug: string,
  membershipId: string,
  data?: MemberActionInput,
): Promise<void> {
  await apiClient.post(
    buildMemberUrl(accountType, slug, membershipId, "remove"),
    data ?? {},
  );
}

export async function banMemberApi(
  accountType: AccountType,
  slug: string,
  membershipId: string,
  data?: MemberActionInput,
): Promise<void> {
  await apiClient.post(
    buildMemberUrl(accountType, slug, membershipId, "ban"),
    data ?? {},
  );
}

export async function reactivateMemberApi(
  accountType: AccountType,
  slug: string,
  membershipId: string,
): Promise<void> {
  await apiClient.post(
    buildMemberUrl(accountType, slug, membershipId, "reactivate"),
    {},
  );
}

export async function leaveMemberApi(
  accountType: AccountType,
  slug: string,
): Promise<void> {
  await apiClient.post(
    buildMemberUrl(accountType, slug, undefined, "leave"),
    {},
  );
}
