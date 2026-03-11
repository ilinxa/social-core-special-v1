import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchTemplatesApi,
  fetchTemplateDetailApi,
  fetchLibraryApi,
  fetchResponsesApi,
  fetchResponseDetailApi,
  fetchMyResponsesApi,
} from "@/features/forms/api/forms-api";
import type { FormResponseListParams } from "@/types/forms";

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function templateListQueryOptions(
  accountType: string,
  accountId: string,
  params?: Record<string, unknown>,
) {
  return queryOptions({
    queryKey: queryKeys.forms.templates(accountType, accountId),
    queryFn: () => fetchTemplatesApi(accountType, accountId, params),
    staleTime: 2 * 60 * 1000,
    enabled: !!accountId,
  });
}

export function templateDetailQueryOptions(formId: string) {
  return queryOptions({
    queryKey: queryKeys.forms.detail(formId),
    queryFn: () => fetchTemplateDetailApi(formId),
    staleTime: 2 * 60 * 1000,
    enabled: !!formId,
  });
}

export function libraryQueryOptions(params?: Record<string, unknown>) {
  return queryOptions({
    queryKey: queryKeys.forms.library(),
    queryFn: () => fetchLibraryApi(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function responseListQueryOptions(
  formId: string,
  params?: FormResponseListParams,
) {
  return queryOptions({
    queryKey: queryKeys.forms.responses(formId, params as Record<string, unknown>),
    queryFn: () => fetchResponsesApi(formId, params),
    staleTime: 2 * 60 * 1000,
    enabled: !!formId,
  });
}

export function responseDetailQueryOptions(responseId: string) {
  return queryOptions({
    queryKey: queryKeys.forms.responseDetail(responseId),
    queryFn: () => fetchResponseDetailApi(responseId),
    staleTime: 2 * 60 * 1000,
    enabled: !!responseId,
  });
}

export function myResponsesQueryOptions(params?: Record<string, unknown>) {
  return queryOptions({
    queryKey: queryKeys.forms.myResponses(),
    queryFn: () => fetchMyResponsesApi(params),
    staleTime: 2 * 60 * 1000,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

export function useTemplateList(
  accountType: string,
  accountId: string,
  params?: Record<string, unknown>,
) {
  return useQuery(templateListQueryOptions(accountType, accountId, params));
}

export function useTemplateDetail(formId: string) {
  return useQuery(templateDetailQueryOptions(formId));
}

export function useLibrary(params?: Record<string, unknown>) {
  return useQuery(libraryQueryOptions(params));
}

export function useResponseList(
  formId: string,
  params?: FormResponseListParams,
) {
  return useQuery(responseListQueryOptions(formId, params));
}

export function useResponseDetail(responseId: string) {
  return useQuery(responseDetailQueryOptions(responseId));
}

export function useMyResponses(params?: Record<string, unknown>) {
  return useQuery(myResponsesQueryOptions(params));
}
