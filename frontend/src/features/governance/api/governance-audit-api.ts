/**
 * Governance audit API functions.
 *
 * Uses governanceApiClient which attaches governance token.
 */

import { governanceApiClient } from "@/lib/governance-api-client";
import type { PaginatedResponse } from "@/types";
import type {
  GovernanceAuditListParams,
  GovernanceAuditLog,
} from "@/types/governance";

export async function listGovernanceAuditApi(
  params?: GovernanceAuditListParams,
): Promise<PaginatedResponse<GovernanceAuditLog>> {
  const response = await governanceApiClient.get<
    PaginatedResponse<GovernanceAuditLog>
  >("/audit/", { params });
  return response.data;
}
