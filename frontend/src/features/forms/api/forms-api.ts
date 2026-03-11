import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  FormTemplateList,
  FormTemplateDetailWithPerms,
  FormField,
  FormResponseList,
  FormResponseDetail,
  CreateTemplateInput,
  UpdateTemplateInput,
  CreateFieldInput,
  UpdateFieldInput,
  ReorderFieldItem,
  ForkTemplateInput,
  CreateResponseInput,
  UpdateResponseInput,
  ProcessResponseInput,
  VoidResponseInput,
  FormResponseListParams,
} from "@/types/forms";

// =============================================================================
// SYSTEM TEMPLATE LOOKUP
// =============================================================================

export async function fetchSystemTemplateApi(
  slug: string,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.get<FormTemplateDetailWithPerms>(
    `/forms/templates/system/${slug}/`,
  );
  return response.data;
}

// =============================================================================
// TEMPLATE APIs
// =============================================================================

export async function fetchTemplatesApi(
  accountType: string,
  accountId: string,
  params?: Record<string, unknown>,
): Promise<PaginatedResponse<FormTemplateList>> {
  const response = await apiClient.get<PaginatedResponse<FormTemplateList>>(
    `/forms/${accountType}/${accountId}/templates/`,
    { params },
  );
  return response.data;
}

export async function createTemplateApi(
  accountType: string,
  accountId: string,
  data: CreateTemplateInput,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.post<FormTemplateDetailWithPerms>(
    `/forms/${accountType}/${accountId}/templates/`,
    data,
  );
  return response.data;
}

export async function fetchTemplateDetailApi(
  formId: string,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.get<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/`,
  );
  return response.data;
}

export async function updateTemplateApi(
  formId: string,
  data: UpdateTemplateInput,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.patch<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/`,
    data,
  );
  return response.data;
}

export async function deleteTemplateApi(formId: string): Promise<void> {
  await apiClient.delete(`/forms/templates/${formId}/`);
}

export async function publishTemplateApi(
  formId: string,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.post<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/publish/`,
    {},
  );
  return response.data;
}

export async function archiveTemplateApi(
  formId: string,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.post<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/archive/`,
    {},
  );
  return response.data;
}

export async function unarchiveTemplateApi(
  formId: string,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.post<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/unarchive/`,
    {},
  );
  return response.data;
}

export async function createEditDraftApi(
  formId: string,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.post<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/edit-draft/`,
    {},
  );
  return response.data;
}

export async function forkTemplateApi(
  formId: string,
  data: ForkTemplateInput,
): Promise<FormTemplateDetailWithPerms> {
  const response = await apiClient.post<FormTemplateDetailWithPerms>(
    `/forms/templates/${formId}/fork/`,
    data,
  );
  return response.data;
}

export async function fetchLibraryApi(
  params?: Record<string, unknown>,
): Promise<PaginatedResponse<FormTemplateList>> {
  const response = await apiClient.get<PaginatedResponse<FormTemplateList>>(
    "/forms/templates/library/",
    { params },
  );
  return response.data;
}

// =============================================================================
// FIELD APIs
// =============================================================================

export async function addFieldApi(
  formId: string,
  data: CreateFieldInput,
): Promise<FormField> {
  const response = await apiClient.post<FormField>(
    `/forms/templates/${formId}/fields/`,
    data,
  );
  return response.data;
}

export async function updateFieldApi(
  templateId: string,
  fieldId: string,
  data: UpdateFieldInput,
): Promise<FormField> {
  const response = await apiClient.patch<FormField>(
    `/forms/templates/${templateId}/fields/${fieldId}/`,
    data,
  );
  return response.data;
}

export async function deleteFieldApi(
  templateId: string,
  fieldId: string,
): Promise<void> {
  await apiClient.delete(
    `/forms/templates/${templateId}/fields/${fieldId}/`,
  );
}

export async function reorderFieldsApi(
  templateId: string,
  fields: ReorderFieldItem[],
): Promise<FormField[]> {
  const response = await apiClient.post<FormField[]>(
    `/forms/templates/${templateId}/fields/reorder/`,
    { fields },
  );
  return response.data;
}

// =============================================================================
// RESPONSE APIs
// =============================================================================

export async function fetchResponsesApi(
  formId: string,
  params?: FormResponseListParams,
): Promise<PaginatedResponse<FormResponseList>> {
  const response = await apiClient.get<PaginatedResponse<FormResponseList>>(
    `/forms/templates/${formId}/responses/`,
    { params },
  );
  return response.data;
}

export async function createResponseApi(
  formId: string,
  data: CreateResponseInput,
): Promise<FormResponseDetail> {
  const response = await apiClient.post<FormResponseDetail>(
    `/forms/templates/${formId}/responses/`,
    data,
  );
  return response.data;
}

export async function fetchResponseDetailApi(
  responseId: string,
): Promise<FormResponseDetail> {
  const response = await apiClient.get<FormResponseDetail>(
    `/forms/responses/${responseId}/`,
  );
  return response.data;
}

export async function updateResponseApi(
  responseId: string,
  data: UpdateResponseInput,
): Promise<FormResponseDetail> {
  const response = await apiClient.patch<FormResponseDetail>(
    `/forms/responses/${responseId}/`,
    data,
  );
  return response.data;
}

export async function submitResponseApi(
  responseId: string,
): Promise<FormResponseDetail> {
  const response = await apiClient.post<FormResponseDetail>(
    `/forms/responses/${responseId}/submit/`,
    {},
  );
  return response.data;
}

export async function processResponseApi(
  responseId: string,
  data?: ProcessResponseInput,
): Promise<FormResponseDetail> {
  const response = await apiClient.post<FormResponseDetail>(
    `/forms/responses/${responseId}/process/`,
    data ?? {},
  );
  return response.data;
}

export async function voidResponseApi(
  responseId: string,
  data?: VoidResponseInput,
): Promise<FormResponseDetail> {
  const response = await apiClient.post<FormResponseDetail>(
    `/forms/responses/${responseId}/void/`,
    data ?? {},
  );
  return response.data;
}

export async function fetchMyResponsesApi(
  params?: Record<string, unknown>,
): Promise<PaginatedResponse<FormResponseList>> {
  const response = await apiClient.get<PaginatedResponse<FormResponseList>>(
    "/forms/me/responses/",
    { params },
  );
  return response.data;
}

// =============================================================================
// FILE UPLOAD
// =============================================================================

/** Upload a file for use in form field values. Returns the URL. */
export async function uploadFormFileApi(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<{ url: string }>(
    "/forms/upload/",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data.url;
}
