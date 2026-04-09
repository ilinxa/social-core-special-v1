/**
 * Governance transaction API functions.
 *
 * Uses governanceApiClient which attaches governance token.
 */

import { governanceApiClient } from "@/lib/governance-api-client";
import type { PaginatedResponse } from "@/types";
import type { GovernanceTransactionListParams } from "@/types/governance";
import type { TransactionListItem } from "@/types/transactions";

export async function listGovernanceTransactionsApi(
  params?: GovernanceTransactionListParams,
): Promise<PaginatedResponse<TransactionListItem>> {
  const response = await governanceApiClient.get<
    PaginatedResponse<TransactionListItem>
  >("/transactions/", { params });
  return response.data;
}
