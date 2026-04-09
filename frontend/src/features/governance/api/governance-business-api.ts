/**
 * Governance business API functions.
 *
 * Uses governanceApiClient which attaches governance token
 * and handles auth errors (redirect to step-up auth).
 */

import { governanceApiClient } from "@/lib/governance-api-client";
import type { PaginatedResponse } from "@/types";
import type {
  GovernanceBusiness,
  GovernanceBusinessDetail,
  GovernanceBusinessDetailWithPerms,
  GovernanceBusinessListParams,
} from "@/types/governance";

export async function listGovernanceBusinessesApi(
  params?: GovernanceBusinessListParams,
): Promise<PaginatedResponse<GovernanceBusiness>> {
  const response = await governanceApiClient.get<
    PaginatedResponse<GovernanceBusiness>
  >("/businesses/", { params });
  return response.data;
}

export async function getGovernanceBusinessApi(
  id: string,
): Promise<GovernanceBusinessDetailWithPerms> {
  const response =
    await governanceApiClient.get<GovernanceBusinessDetailWithPerms>(
      `/businesses/${id}/`,
    );
  return response.data;
}

export async function suspendBusinessApi(
  id: string,
  reason: string,
): Promise<GovernanceBusinessDetail> {
  const response = await governanceApiClient.post<GovernanceBusinessDetail>(
    `/businesses/${id}/suspend/`,
    { reason },
  );
  return response.data;
}

export async function reactivateBusinessApi(
  id: string,
): Promise<GovernanceBusinessDetail> {
  const response = await governanceApiClient.post<GovernanceBusinessDetail>(
    `/businesses/${id}/reactivate/`,
  );
  return response.data;
}

export async function archiveBusinessApi(
  id: string,
): Promise<GovernanceBusinessDetail> {
  const response = await governanceApiClient.post<GovernanceBusinessDetail>(
    `/businesses/${id}/archive/`,
  );
  return response.data;
}

export async function transferOwnershipApi(
  id: string,
  newOwnerId: string,
  reason?: string,
): Promise<void> {
  await governanceApiClient.post(`/businesses/${id}/transfer-ownership/`, {
    new_owner_id: newOwnerId,
    reason: reason ?? "",
  });
}

export async function listGovernanceVerificationApi(
  params?: { page?: number; page_size?: number },
): Promise<PaginatedResponse<GovernanceBusiness>> {
  const response = await governanceApiClient.get<
    PaginatedResponse<GovernanceBusiness>
  >("/verification/", { params });
  return response.data;
}
