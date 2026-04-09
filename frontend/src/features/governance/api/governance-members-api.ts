/**
 * Governance member API functions.
 *
 * Uses governanceApiClient which attaches governance token.
 */

import { governanceApiClient } from "@/lib/governance-api-client";
import type { PaginatedResponse } from "@/types";
import type {
  GovernanceMember,
  GovernanceMemberDetailWithPerms,
  GovernanceMemberListParams,
} from "@/types/governance";

export async function listGovernanceMembersApi(
  params?: GovernanceMemberListParams,
): Promise<PaginatedResponse<GovernanceMember>> {
  const response = await governanceApiClient.get<
    PaginatedResponse<GovernanceMember>
  >("/members/", { params });
  return response.data;
}

export async function getGovernanceMemberApi(
  id: string,
): Promise<GovernanceMemberDetailWithPerms> {
  const response =
    await governanceApiClient.get<GovernanceMemberDetailWithPerms>(
      `/members/${id}/`,
    );
  return response.data;
}

export async function governanceMemberActionApi(
  id: string,
  action: string,
  reason?: string,
): Promise<void> {
  await governanceApiClient.post(`/members/${id}/action/`, {
    action,
    reason: reason ?? "",
  });
}
