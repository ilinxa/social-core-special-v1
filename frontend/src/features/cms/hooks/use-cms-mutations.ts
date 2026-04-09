/**
 * CMS Mutation Hooks
 * ===================
 * TanStack Query mutation hooks for all CMS write operations.
 * Each mutation invalidates related queries on success.
 *
 * Backend: apps.cms.api.views, apps.cms.api.views_business
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import {
  activateBlockTemplateApi,
  activateSectionTemplateApi,
  createApiKeyApi,
  createPageApi,
  createSiteApi,
  deactivateBlockTemplateApi,
  deactivateSectionTemplateApi,
  deleteMediaFileApi,
  deletePageApi,
  deleteSiteApi,
  exportPageApi,
  importPageApi,
  publishPageApi,
  revokeApiKeyApi,
  rollbackBlockApi,
  toggleBusinessCmsApi,
  unpublishPageApi,
  updateDraftContentApi,
  updateMediaFileApi,
  updatePageApi,
  updateSiteApi,
  uploadMediaFileApi,
} from "@/features/cms/api/cms-api";
import type {
  CmsApiContext,
  CreateApiKeyInput,
  CreatePageInput,
  CreateSiteInput,
  ImportPageInput,
  ToggleBusinessCmsInput,
  UpdateDraftContentInput,
  UpdateMediaInput,
  UpdatePageInput,
  UpdateSiteInput,
} from "@/features/cms/types";

// =============================================================================
// SITES
// =============================================================================

export function useCreateSite(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateSiteInput) => createSiteApi(ctx, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.sites() });
    },
  });
}

export function useUpdateSite(ctx: CmsApiContext, slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateSiteInput) => updateSiteApi(ctx, slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.site(slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.sites() });
    },
  });
}

export function useDeleteSite(ctx: CmsApiContext, slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteSiteApi(ctx, slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.sites() });
    },
  });
}

// =============================================================================
// PAGES
// =============================================================================

export function useCreatePage(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreatePageInput) => createPageApi(ctx, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.pages() });
    },
  });
}

export function useUpdatePage(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pageSlug,
      siteSlug,
      data,
    }: {
      pageSlug: string;
      siteSlug: string;
      data: UpdatePageInput;
    }) => updatePageApi(ctx, pageSlug, siteSlug, data),
    onSuccess: (_data, { pageSlug }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.page(pageSlug),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.pages() });
    },
  });
}

export function useDeletePage(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pageSlug,
      siteSlug,
    }: {
      pageSlug: string;
      siteSlug: string;
    }) => deletePageApi(ctx, pageSlug, siteSlug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.pages() });
    },
  });
}

export function usePublishPage(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pageSlug,
      siteSlug,
    }: {
      pageSlug: string;
      siteSlug: string;
    }) => publishPageApi(ctx, pageSlug, siteSlug),
    onSuccess: (_data, { pageSlug }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.page(pageSlug),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.pages() });
    },
  });
}

export function useUnpublishPage(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pageSlug,
      siteSlug,
    }: {
      pageSlug: string;
      siteSlug: string;
    }) => unpublishPageApi(ctx, pageSlug, siteSlug),
    onSuccess: (_data, { pageSlug }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.page(pageSlug),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.pages() });
    },
  });
}

export function useExportPage(ctx: CmsApiContext) {
  return useMutation({
    mutationFn: ({
      pageSlug,
      siteSlug,
    }: {
      pageSlug: string;
      siteSlug: string;
    }) => exportPageApi(ctx, pageSlug, siteSlug),
  });
}

export function useImportPage(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pageSlug,
      siteSlug,
      data,
    }: {
      pageSlug: string;
      siteSlug: string;
      data: ImportPageInput;
    }) => importPageApi(ctx, pageSlug, siteSlug, data),
    onSuccess: (_data, { pageSlug }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.page(pageSlug),
      });
    },
  });
}

// =============================================================================
// BLOCK PLACEMENTS (CONTENT)
// =============================================================================

export function useUpdateDraftContent(ctx: CmsApiContext, uuid: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateDraftContentInput) =>
      updateDraftContentApi(ctx, uuid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.blockPlacement(uuid),
      });
    },
  });
}

export function useRollbackContent(ctx: CmsApiContext, uuid: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (versionNumber: number) =>
      rollbackBlockApi(ctx, uuid, versionNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.blockPlacement(uuid),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.blockHistory(uuid),
      });
    },
  });
}

// =============================================================================
// TEMPLATE ACTIVATION (business context only)
// =============================================================================

export function useActivateSectionTemplate(businessSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      activateSectionTemplateApi(businessSlug, { template_id: templateId }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.librarySections(businessSlug),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.catalogSections(businessSlug),
      });
    },
    onError: () => {
      toast.error("Failed to activate template");
    },
  });
}

export function useDeactivateSectionTemplate(businessSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activationId: string) =>
      deactivateSectionTemplateApi(businessSlug, activationId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.librarySections(businessSlug),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.catalogSections(businessSlug),
      });
    },
    onError: () => {
      toast.error("Failed to deactivate template");
    },
  });
}

export function useActivateBlockTemplate(businessSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      activateBlockTemplateApi(businessSlug, { template_id: templateId }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.libraryBlocks(businessSlug),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.catalogBlocks(businessSlug),
      });
    },
    onError: () => {
      toast.error("Failed to activate template");
    },
  });
}

export function useDeactivateBlockTemplate(businessSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activationId: string) =>
      deactivateBlockTemplateApi(businessSlug, activationId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.libraryBlocks(businessSlug),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.catalogBlocks(businessSlug),
      });
    },
    onError: () => {
      toast.error("Failed to deactivate template");
    },
  });
}

// =============================================================================
// MEDIA
// =============================================================================

export function useUploadMediaFile(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => uploadMediaFileApi(ctx, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.mediaFiles() });
    },
  });
}

export function useUpdateMediaFile(ctx: CmsApiContext, uuid: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateMediaInput) =>
      updateMediaFileApi(ctx, uuid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.mediaFile(uuid),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.mediaFiles() });
    },
  });
}

export function useDeleteMediaFile(ctx: CmsApiContext, uuid: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteMediaFileApi(ctx, uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.mediaFiles() });
    },
  });
}

// =============================================================================
// API KEYS
// =============================================================================

export function useCreateApiKey(ctx: CmsApiContext) {
  // NOTE: Do NOT invalidate here — must show key reveal dialog first.
  // Caller invalidates after dialog closes.
  return useMutation({
    mutationFn: (data: CreateApiKeyInput) => createApiKeyApi(ctx, data),
  });
}

export function useRevokeApiKey(ctx: CmsApiContext) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (uuid: string) => revokeApiKeyApi(ctx, uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cms.apiKeys() });
    },
  });
}

// =============================================================================
// PLATFORM MANAGEMENT
// =============================================================================

export function useToggleBusinessCms(uuid: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ToggleBusinessCmsInput) =>
      toggleBusinessCmsApi(uuid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.cms.businessStatus(),
      });
    },
  });
}
