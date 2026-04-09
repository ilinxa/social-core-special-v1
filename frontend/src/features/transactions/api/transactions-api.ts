import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  TransactionListItem,
  TransactionDetailWithPerms,
  TransactionTypeInfo,
  TransactionFormMapping,
  TransactionFormResponse,
  CreateInvitationInput,
  CreateRequestInput,
  AcceptInput,
  DenyInput,
  RequestInfoInput,
  FormResponseUpdateInput,
  CreateFormMappingInput,
  TransactionListParams,
} from "@/types/transactions";

// =============================================================================
// TRANSACTION CRUD
// =============================================================================

export async function fetchTransactionsApi(
  params?: TransactionListParams,
): Promise<PaginatedResponse<TransactionListItem>> {
  const response = await apiClient.get<PaginatedResponse<TransactionListItem>>(
    "/transactions/",
    { params },
  );
  return response.data;
}

export async function fetchTransactionDetailApi(
  transactionId: string,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.get<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/`,
  );
  return response.data;
}

export async function createInvitationApi(
  data: CreateInvitationInput,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    "/transactions/invitation/",
    data,
  );
  return response.data;
}

export async function createRequestApi(
  data: CreateRequestInput,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    "/transactions/request/",
    data,
  );
  return response.data;
}

// =============================================================================
// TRANSACTION ACTIONS
// =============================================================================

export async function acceptTransactionApi(
  transactionId: string,
  data?: AcceptInput,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/accept/`,
    data ?? {},
  );
  return response.data;
}

export async function denyTransactionApi(
  transactionId: string,
  data?: DenyInput,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/deny/`,
    data ?? {},
  );
  return response.data;
}

export async function cancelTransactionApi(
  transactionId: string,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/cancel/`,
    {},
  );
  return response.data;
}

export async function dismissTransactionApi(
  transactionId: string,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/dismiss/`,
    {},
  );
  return response.data;
}

export async function requestInfoApi(
  transactionId: string,
  data: RequestInfoInput,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/request-info/`,
    data,
  );
  return response.data;
}

export async function resubmitTransactionApi(
  transactionId: string,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/resubmit/`,
    {},
  );
  return response.data;
}

export async function approveTransactionApi(
  transactionId: string,
): Promise<TransactionDetailWithPerms> {
  const response = await apiClient.post<TransactionDetailWithPerms>(
    `/transactions/${transactionId}/approve/`,
    {},
  );
  return response.data;
}

// =============================================================================
// FORM RESPONSE
// =============================================================================

export async function fetchTransactionFormResponseApi(
  transactionId: string,
): Promise<TransactionFormResponse> {
  const response = await apiClient.get<TransactionFormResponse>(
    `/transactions/${transactionId}/form-response/`,
  );
  return response.data;
}

export async function updateTransactionFormResponseApi(
  transactionId: string,
  data: FormResponseUpdateInput,
): Promise<TransactionFormResponse> {
  const response = await apiClient.patch<TransactionFormResponse>(
    `/transactions/${transactionId}/form-response/`,
    data,
  );
  return response.data;
}

// =============================================================================
// TYPES & FORM MAPPINGS
// =============================================================================

export async function fetchTransactionTypesApi(
  contextType?: string,
): Promise<TransactionTypeInfo[]> {
  const response = await apiClient.get<TransactionTypeInfo[]>(
    "/transactions/types/",
    { params: contextType ? { context_type: contextType } : undefined },
  );
  return response.data;
}

export async function fetchFormMappingsApi(
  params?: Record<string, unknown>,
): Promise<TransactionFormMapping[]> {
  const response = await apiClient.get<TransactionFormMapping[]>(
    "/transactions/form-mappings/",
    { params },
  );
  return response.data;
}

export async function createFormMappingApi(
  data: CreateFormMappingInput,
): Promise<TransactionFormMapping> {
  const response = await apiClient.post<TransactionFormMapping>(
    "/transactions/form-mappings/",
    data,
  );
  return response.data;
}

export async function deleteFormMappingApi(
  mappingId: string,
): Promise<void> {
  await apiClient.delete(`/transactions/form-mappings/${mappingId}/`);
}

// =============================================================================
// TRANSACTION REQUIRED FORM
// =============================================================================

export async function fetchRequiredFormApi(
  transactionId: string,
): Promise<{ form_template: FormTemplateForTransaction | null; is_required: boolean }> {
  const response = await apiClient.get<{
    form_template: FormTemplateForTransaction | null;
    is_required: boolean;
  }>(`/transactions/${transactionId}/required-form/`);
  return response.data;
}

/** Submit a form response for a transaction's required form (bypasses membership check). */
export async function submitRequiredFormApi(
  transactionId: string,
  data: Record<string, unknown>,
): Promise<{ id: string }> {
  const response = await apiClient.post<{ id: string }>(
    `/transactions/${transactionId}/required-form/`,
    { data },
  );
  return response.data;
}

// =============================================================================
// REQUEST FORM CHECK (pre-creation form lookup + submit)
// =============================================================================

export type RequestFormCheckResult = {
  form_required: boolean;
  form_mapping_id?: string;
  form_template_id?: string;
  form_template?: FormTemplateForTransaction | null;
};

/** Check if a form mapping exists for creating a request to this account. */
export async function checkRequestFormApi(params: {
  transaction_type: string;
  account_type: string;
  account_id: string;
}): Promise<RequestFormCheckResult> {
  const response = await apiClient.get<RequestFormCheckResult>(
    "/transactions/form-mappings/check/",
    { params },
  );
  return response.data;
}

/** Submit a form response before creating a request (pre-transaction form submission).
 *  Accepts either a mapping ID string (dynamic mapping path) or an object with
 *  form_template_id + account context (static config path). */
export async function submitRequestFormResponseApi(
  paramsOrMappingId:
    | string
    | {
        form_template_id: string;
        account_type: string;
        account_id: string;
      },
  data: Record<string, unknown>,
): Promise<{ form_response_id: string }> {
  const body =
    typeof paramsOrMappingId === "string"
      ? { form_mapping_id: paramsOrMappingId, data }
      : { ...paramsOrMappingId, data };
  const response = await apiClient.post<{ form_response_id: string }>(
    "/transactions/form-mappings/check/",
    body,
  );
  return response.data;
}

/** Minimal form template type returned by the required-form endpoint. */
export type FormTemplateForTransaction = {
  id: string;
  name: string;
  fields: Array<{
    id: string;
    field_key: string;
    field_type: string;
    label: string;
    description: string;
    placeholder: string;
    order: number;
    options: unknown[];
    validation_rules: Record<string, unknown>;
    is_required: boolean;
    is_hidden: boolean;
  }>;
};
