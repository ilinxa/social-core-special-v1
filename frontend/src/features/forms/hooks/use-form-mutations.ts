import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  createTemplateApi,
  updateTemplateApi,
  deleteTemplateApi,
  publishTemplateApi,
  archiveTemplateApi,
  unarchiveTemplateApi,
  createEditDraftApi,
  forkTemplateApi,
  addFieldApi,
  updateFieldApi,
  deleteFieldApi,
  reorderFieldsApi,
  createResponseApi,
  updateResponseApi,
  submitResponseApi,
  processResponseApi,
  voidResponseApi,
} from "@/features/forms/api/forms-api";
import type {
  CreateTemplateInput,
  UpdateTemplateInput,
  ForkTemplateInput,
  CreateFieldInput,
  UpdateFieldInput,
  ReorderFieldItem,
  CreateResponseInput,
  UpdateResponseInput,
  ProcessResponseInput,
  VoidResponseInput,
} from "@/types/forms";

// =============================================================================
// TEMPLATE MUTATIONS
// =============================================================================

export function useCreateTemplate(accountType: string, accountId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateTemplateInput) =>
      createTemplateApi(accountType, accountId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
    },
  });
}

export function useUpdateTemplate(
  accountType: string,
  accountId: string,
  formId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateTemplateInput) => updateTemplateApi(formId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useDeleteTemplate(accountType: string, accountId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (formId: string) => deleteTemplateApi(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
    },
  });
}

export function usePublishTemplate(
  accountType: string,
  accountId: string,
  formId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => publishTemplateApi(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useArchiveTemplate(
  accountType: string,
  accountId: string,
  formId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => archiveTemplateApi(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useUnarchiveTemplate(
  accountType: string,
  accountId: string,
  formId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => unarchiveTemplateApi(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useCreateEditDraft(
  accountType: string,
  accountId: string,
  formId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => createEditDraftApi(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(accountType, accountId),
      });
    },
  });
}

export function useForkTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      formId,
      data,
    }: {
      formId: string;
      data: ForkTemplateInput;
    }) => forkTemplateApi(formId, data),
    onSuccess: (_data, { data }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.templates(
          data.new_owner_type,
          data.new_owner_id,
        ),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.library(),
      });
    },
  });
}

// =============================================================================
// FIELD MUTATIONS
// =============================================================================

export function useAddField(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateFieldInput) => addFieldApi(formId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useUpdateField(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      fieldId,
      data,
    }: {
      fieldId: string;
      data: UpdateFieldInput;
    }) => updateFieldApi(formId, fieldId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useDeleteField(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (fieldId: string) => deleteFieldApi(formId, fieldId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

export function useReorderFields(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (fields: ReorderFieldItem[]) =>
      reorderFieldsApi(formId, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.detail(formId),
      });
    },
  });
}

// =============================================================================
// RESPONSE MUTATIONS
// =============================================================================

export function useCreateResponse(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateResponseInput) =>
      createResponseApi(formId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responses(formId),
      });
    },
  });
}

export function useUpdateResponse(responseId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateResponseInput) =>
      updateResponseApi(responseId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responseDetail(responseId),
      });
    },
  });
}

export function useSubmitResponse(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (responseId: string) => submitResponseApi(responseId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responses(formId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.myResponses(),
      });
    },
  });
}

export function useProcessResponse(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      responseId,
      data,
    }: {
      responseId: string;
      data?: ProcessResponseInput;
    }) => processResponseApi(responseId, data),
    onSuccess: (_data, { responseId }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responses(formId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responseDetail(responseId),
      });
    },
  });
}

export function useVoidResponse(formId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      responseId,
      data,
    }: {
      responseId: string;
      data?: VoidResponseInput;
    }) => voidResponseApi(responseId, data),
    onSuccess: (_data, { responseId }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responses(formId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.forms.responseDetail(responseId),
      });
    },
  });
}
