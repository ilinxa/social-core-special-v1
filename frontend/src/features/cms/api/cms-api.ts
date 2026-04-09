/**
 * CMS API Functions
 * ==================
 * Typed async functions for all CMS REST endpoints.
 * Context-aware: platform admin (/cms/admin/) or business (/cms/business/{slug}/).
 *
 * Backend: apps.cms.api.views, apps.cms.api.views_business
 */

import { apiClient } from "@/lib/api-client";
import type {
  ActivateTemplateInput,
  BusinessCmsStatus,
  CmsApiContext,
  CmsApiKey,
  CmsApiKeyCreated,
  CmsBlockActivation,
  CmsBlockPlacement,
  CmsBlockPlacementWithPerms,
  CmsBlockTemplate,
  CmsContentVersion,
  CmsMediaFile,
  CmsMediaFileWithPerms,
  CmsPage,
  CmsPageDetail,
  CmsPageDetailWithPerms,
  CmsPageExport,
  CmsSectionActivation,
  CmsSectionTemplate,
  CmsSite,
  CmsSiteWithPerms,
  CmsTemplateCatalogBlock,
  CmsTemplateCatalogSection,
  CreateApiKeyInput,
  CreatePageInput,
  CreateSiteInput,
  ImportPageInput,
  PaginatedCmsResponse,
  ToggleBusinessCmsInput,
  UpdateDraftContentInput,
  UpdateMediaInput,
  UpdatePageInput,
  UpdateSiteInput,
} from "@/features/cms/types";

// =============================================================================
// HELPERS
// =============================================================================

function cmsBaseUrl(ctx: CmsApiContext): string {
  if (ctx.type === "platform") return "/cms/admin";
  return `/cms/business/${ctx.businessSlug}`;
}

// =============================================================================
// SITES
// =============================================================================

export async function fetchSitesApi(
  ctx: CmsApiContext,
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsSite>> {
  const response = await apiClient.get<PaginatedCmsResponse<CmsSite>>(
    `${cmsBaseUrl(ctx)}/sites/`,
    { params },
  );
  return response.data;
}

export async function fetchSiteApi(
  ctx: CmsApiContext,
  slug: string,
): Promise<CmsSiteWithPerms | CmsSite> {
  const response = await apiClient.get(`${cmsBaseUrl(ctx)}/sites/${slug}/`);
  return response.data;
}

export async function createSiteApi(
  ctx: CmsApiContext,
  data: CreateSiteInput,
): Promise<CmsSite> {
  const response = await apiClient.post<CmsSite>(
    `${cmsBaseUrl(ctx)}/sites/`,
    data,
  );
  return response.data;
}

export async function updateSiteApi(
  ctx: CmsApiContext,
  slug: string,
  data: UpdateSiteInput,
): Promise<CmsSite> {
  const response = await apiClient.patch<CmsSite>(
    `${cmsBaseUrl(ctx)}/sites/${slug}/`,
    data,
  );
  return response.data;
}

export async function deleteSiteApi(
  ctx: CmsApiContext,
  slug: string,
): Promise<void> {
  await apiClient.delete(`${cmsBaseUrl(ctx)}/sites/${slug}/`);
}

// =============================================================================
// PAGES
// =============================================================================

export async function fetchPagesApi(
  ctx: CmsApiContext,
  params?: { site?: string; status?: string },
): Promise<PaginatedCmsResponse<CmsPage>> {
  const response = await apiClient.get<PaginatedCmsResponse<CmsPage>>(
    `${cmsBaseUrl(ctx)}/pages/`,
    { params },
  );
  return response.data;
}

export async function fetchPageApi(
  ctx: CmsApiContext,
  slug: string,
  params?: { site?: string; depth?: "full" },
): Promise<CmsPageDetailWithPerms | CmsPageDetail | CmsPage> {
  const response = await apiClient.get(
    `${cmsBaseUrl(ctx)}/pages/${slug}/`,
    { params },
  );
  return response.data;
}

export async function createPageApi(
  ctx: CmsApiContext,
  data: CreatePageInput,
): Promise<CmsPage> {
  const response = await apiClient.post<CmsPage>(
    `${cmsBaseUrl(ctx)}/pages/`,
    data,
  );
  return response.data;
}

export async function updatePageApi(
  ctx: CmsApiContext,
  pageSlug: string,
  siteSlug: string,
  data: UpdatePageInput,
): Promise<CmsPage> {
  const response = await apiClient.patch<CmsPage>(
    `${cmsBaseUrl(ctx)}/pages/${pageSlug}/`,
    data,
    { params: { site: siteSlug } },
  );
  return response.data;
}

export async function deletePageApi(
  ctx: CmsApiContext,
  pageSlug: string,
  siteSlug: string,
): Promise<void> {
  await apiClient.delete(`${cmsBaseUrl(ctx)}/pages/${pageSlug}/`, {
    params: { site: siteSlug },
  });
}

export async function publishPageApi(
  ctx: CmsApiContext,
  pageSlug: string,
  siteSlug: string,
): Promise<CmsPage> {
  const response = await apiClient.post<CmsPage>(
    `${cmsBaseUrl(ctx)}/pages/${pageSlug}/publish/`,
    null,
    { params: { site: siteSlug } },
  );
  return response.data;
}

export async function unpublishPageApi(
  ctx: CmsApiContext,
  pageSlug: string,
  siteSlug: string,
): Promise<CmsPage> {
  const response = await apiClient.post<CmsPage>(
    `${cmsBaseUrl(ctx)}/pages/${pageSlug}/unpublish/`,
    null,
    { params: { site: siteSlug } },
  );
  return response.data;
}

export async function exportPageApi(
  ctx: CmsApiContext,
  pageSlug: string,
  siteSlug: string,
): Promise<CmsPageExport> {
  const response = await apiClient.post<CmsPageExport>(
    `${cmsBaseUrl(ctx)}/pages/${pageSlug}/export/`,
    null,
    { params: { site: siteSlug } },
  );
  return response.data;
}

export async function importPageApi(
  ctx: CmsApiContext,
  pageSlug: string,
  siteSlug: string,
  data: ImportPageInput,
): Promise<CmsPage> {
  const response = await apiClient.post<CmsPage>(
    `${cmsBaseUrl(ctx)}/pages/${pageSlug}/import/`,
    data,
    { params: { site: siteSlug } },
  );
  return response.data;
}

// =============================================================================
// BLOCK PLACEMENTS
// =============================================================================

export async function fetchBlockPlacementApi(
  ctx: CmsApiContext,
  uuid: string,
): Promise<CmsBlockPlacementWithPerms | CmsBlockPlacement> {
  const response = await apiClient.get(
    `${cmsBaseUrl(ctx)}/block-placements/${uuid}/`,
  );
  return response.data;
}

export async function updateDraftContentApi(
  ctx: CmsApiContext,
  uuid: string,
  data: UpdateDraftContentInput,
): Promise<CmsBlockPlacement> {
  const response = await apiClient.patch<CmsBlockPlacement>(
    `${cmsBaseUrl(ctx)}/block-placements/${uuid}/`,
    data,
  );
  return response.data;
}

export async function fetchBlockHistoryApi(
  ctx: CmsApiContext,
  uuid: string,
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsContentVersion>> {
  const response = await apiClient.get<PaginatedCmsResponse<CmsContentVersion>>(
    `${cmsBaseUrl(ctx)}/block-placements/${uuid}/history/`,
    { params },
  );
  return response.data;
}

export async function rollbackBlockApi(
  ctx: CmsApiContext,
  uuid: string,
  versionNumber: number,
): Promise<CmsBlockPlacement> {
  const response = await apiClient.post<CmsBlockPlacement>(
    `${cmsBaseUrl(ctx)}/block-placements/${uuid}/rollback/${versionNumber}/`,
  );
  return response.data;
}

// =============================================================================
// TEMPLATE CATALOG (business context only)
// =============================================================================

export async function fetchCatalogSectionsApi(
  businessSlug: string,
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsTemplateCatalogSection>> {
  const response = await apiClient.get<
    PaginatedCmsResponse<CmsTemplateCatalogSection>
  >(`/cms/business/${businessSlug}/catalog/sections/`, { params });
  return response.data;
}

export async function fetchCatalogBlocksApi(
  businessSlug: string,
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsTemplateCatalogBlock>> {
  const response = await apiClient.get<
    PaginatedCmsResponse<CmsTemplateCatalogBlock>
  >(`/cms/business/${businessSlug}/catalog/blocks/`, { params });
  return response.data;
}

// =============================================================================
// TEMPLATE LIBRARY (business context only)
// =============================================================================

export async function fetchLibrarySectionsApi(
  businessSlug: string,
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsSectionActivation>> {
  const response = await apiClient.get<
    PaginatedCmsResponse<CmsSectionActivation>
  >(`/cms/business/${businessSlug}/library/sections/`, { params });
  return response.data;
}

export async function activateSectionTemplateApi(
  businessSlug: string,
  data: ActivateTemplateInput,
): Promise<CmsSectionActivation> {
  const response = await apiClient.post<CmsSectionActivation>(
    `/cms/business/${businessSlug}/library/sections/`,
    data,
  );
  return response.data;
}

export async function deactivateSectionTemplateApi(
  businessSlug: string,
  activationId: string,
): Promise<void> {
  await apiClient.delete(
    `/cms/business/${businessSlug}/library/sections/${activationId}/`,
  );
}

export async function fetchLibraryBlocksApi(
  businessSlug: string,
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsBlockActivation>> {
  const response = await apiClient.get<
    PaginatedCmsResponse<CmsBlockActivation>
  >(`/cms/business/${businessSlug}/library/blocks/`, { params });
  return response.data;
}

export async function activateBlockTemplateApi(
  businessSlug: string,
  data: ActivateTemplateInput,
): Promise<CmsBlockActivation> {
  const response = await apiClient.post<CmsBlockActivation>(
    `/cms/business/${businessSlug}/library/blocks/`,
    data,
  );
  return response.data;
}

export async function deactivateBlockTemplateApi(
  businessSlug: string,
  activationId: string,
): Promise<void> {
  await apiClient.delete(
    `/cms/business/${businessSlug}/library/blocks/${activationId}/`,
  );
}

// =============================================================================
// TEMPLATES — ADMIN (platform context only, read-only browsing)
// =============================================================================

export async function fetchAdminSectionTemplatesApi(
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsSectionTemplate>> {
  const response = await apiClient.get<
    PaginatedCmsResponse<CmsSectionTemplate>
  >("/cms/admin/templates/sections/", { params });
  return response.data;
}

export async function fetchAdminBlockTemplatesApi(
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<CmsBlockTemplate>> {
  const response = await apiClient.get<
    PaginatedCmsResponse<CmsBlockTemplate>
  >("/cms/admin/templates/blocks/", { params });
  return response.data;
}

// =============================================================================
// MEDIA
// =============================================================================

export async function fetchMediaFilesApi(
  ctx: CmsApiContext,
  params?: { folder?: string; type?: string },
): Promise<PaginatedCmsResponse<CmsMediaFile>> {
  const response = await apiClient.get<PaginatedCmsResponse<CmsMediaFile>>(
    `${cmsBaseUrl(ctx)}/media/files/`,
    { params },
  );
  return response.data;
}

export async function fetchMediaFileApi(
  ctx: CmsApiContext,
  uuid: string,
): Promise<CmsMediaFileWithPerms | CmsMediaFile> {
  const response = await apiClient.get(
    `${cmsBaseUrl(ctx)}/media/files/${uuid}/`,
  );
  return response.data;
}

export async function uploadMediaFileApi(
  ctx: CmsApiContext,
  formData: FormData,
): Promise<CmsMediaFile> {
  const response = await apiClient.post<CmsMediaFile>(
    `${cmsBaseUrl(ctx)}/media/files/`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
}

export async function updateMediaFileApi(
  ctx: CmsApiContext,
  uuid: string,
  data: UpdateMediaInput,
): Promise<CmsMediaFile> {
  const response = await apiClient.patch<CmsMediaFile>(
    `${cmsBaseUrl(ctx)}/media/files/${uuid}/`,
    data,
  );
  return response.data;
}

export async function deleteMediaFileApi(
  ctx: CmsApiContext,
  uuid: string,
): Promise<void> {
  await apiClient.delete(`${cmsBaseUrl(ctx)}/media/files/${uuid}/`);
}

// =============================================================================
// API KEYS
// =============================================================================

export async function fetchApiKeysApi(
  ctx: CmsApiContext,
  siteId?: string,
): Promise<CmsApiKey[]> {
  const response = await apiClient.get<CmsApiKey[]>(
    `${cmsBaseUrl(ctx)}/api-keys/`,
    { params: siteId ? { site: siteId } : undefined },
  );
  return response.data;
}

export async function createApiKeyApi(
  ctx: CmsApiContext,
  data: CreateApiKeyInput,
): Promise<CmsApiKeyCreated> {
  const response = await apiClient.post<CmsApiKeyCreated>(
    `${cmsBaseUrl(ctx)}/api-keys/`,
    data,
  );
  return response.data;
}

export async function revokeApiKeyApi(
  ctx: CmsApiContext,
  uuid: string,
): Promise<void> {
  await apiClient.delete(`${cmsBaseUrl(ctx)}/api-keys/${uuid}/`);
}

// =============================================================================
// PLATFORM MANAGEMENT (platform admin only)
// =============================================================================

export async function fetchBusinessCmsStatusApi(
  params?: Record<string, unknown>,
): Promise<PaginatedCmsResponse<BusinessCmsStatus>> {
  const response = await apiClient.get<PaginatedCmsResponse<BusinessCmsStatus>>(
    "/cms/admin/businesses/",
    { params },
  );
  return response.data;
}

export async function toggleBusinessCmsApi(
  uuid: string,
  data: ToggleBusinessCmsInput,
): Promise<{ id: string; cms_enabled: boolean }> {
  const response = await apiClient.patch<{ id: string; cms_enabled: boolean }>(
    `/cms/admin/businesses/${uuid}/`,
    data,
  );
  return response.data;
}

export async function fetchBusinessActivationsApi(
  uuid: string,
): Promise<{
  section_templates: CmsSectionActivation[];
  block_templates: CmsBlockActivation[];
}> {
  const response = await apiClient.get(
    `/cms/admin/businesses/${uuid}/activations/`,
  );
  return response.data;
}
