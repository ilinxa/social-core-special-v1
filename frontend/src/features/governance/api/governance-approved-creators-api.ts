/**
 * Governance approved creators API functions.
 *
 * Uses governanceApiClient which attaches governance token.
 */

import { governanceApiClient } from "@/lib/governance-api-client";
import type { ApprovedCreatorItem, PaginatedResponse } from "@/types";

export async function listGovernanceApprovedCreatorsApi(
  params?: Record<string, unknown>,
): Promise<PaginatedResponse<ApprovedCreatorItem>> {
  const response = await governanceApiClient.get<
    PaginatedResponse<ApprovedCreatorItem>
  >("/approved-creators/", { params });
  return response.data;
}
