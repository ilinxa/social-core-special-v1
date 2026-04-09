/**
 * CMS Query Hooks
 * ================
 * TanStack Query hooks for all CMS read operations.
 * All hooks accept a CmsApiContext to support both platform and business contexts.
 *
 * Backend: apps.cms.api.views, apps.cms.api.views_business
 */

import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchAdminBlockTemplatesApi,
  fetchAdminSectionTemplatesApi,
  fetchBlockHistoryApi,
  fetchBlockPlacementApi,
  fetchBusinessActivationsApi,
  fetchBusinessCmsStatusApi,
  fetchCatalogBlocksApi,
  fetchCatalogSectionsApi,
  fetchLibraryBlocksApi,
  fetchLibrarySectionsApi,
  fetchMediaFileApi,
  fetchMediaFilesApi,
  fetchPageApi,
  fetchPagesApi,
  fetchSiteApi,
  fetchSitesApi,
  fetchApiKeysApi,
} from "@/features/cms/api/cms-api";
import type { CmsApiContext } from "@/features/cms/types";

// =============================================================================
// SITES
// =============================================================================

export function sitesQueryOptions(
  ctx: CmsApiContext,
  params?: Record<string, unknown>,
) {
  return queryOptions({
    queryKey: queryKeys.cms.sites(params),
    queryFn: () => fetchSitesApi(ctx, params),
    staleTime: 30_000,
  });
}

export function useSites(ctx: CmsApiContext, params?: Record<string, unknown>) {
  return useQuery(sitesQueryOptions(ctx, params));
}

export function siteQueryOptions(ctx: CmsApiContext, slug: string) {
  return queryOptions({
    queryKey: queryKeys.cms.site(slug),
    queryFn: () => fetchSiteApi(ctx, slug),
    staleTime: 60_000,
    enabled: !!slug,
  });
}

export function useSite(ctx: CmsApiContext, slug: string) {
  return useQuery(siteQueryOptions(ctx, slug));
}

// =============================================================================
// PAGES
// =============================================================================

export function pagesQueryOptions(
  ctx: CmsApiContext,
  params?: { site?: string; status?: string },
) {
  return queryOptions({
    queryKey: queryKeys.cms.pages(params),
    queryFn: () => fetchPagesApi(ctx, params),
    staleTime: 30_000,
  });
}

export function usePages(
  ctx: CmsApiContext,
  params?: { site?: string; status?: string },
) {
  return useQuery(pagesQueryOptions(ctx, params));
}

export function pageQueryOptions(
  ctx: CmsApiContext,
  slug: string,
  params?: { site?: string; depth?: "full" },
) {
  return queryOptions({
    queryKey: queryKeys.cms.page(slug),
    queryFn: () => fetchPageApi(ctx, slug, params),
    staleTime: 60_000,
    enabled: !!slug,
  });
}

export function usePage(
  ctx: CmsApiContext,
  slug: string,
  params?: { site?: string; depth?: "full" },
) {
  return useQuery(pageQueryOptions(ctx, slug, params));
}

// =============================================================================
// BLOCK PLACEMENTS
// =============================================================================

export function blockPlacementQueryOptions(ctx: CmsApiContext, uuid: string) {
  return queryOptions({
    queryKey: queryKeys.cms.blockPlacement(uuid),
    queryFn: () => fetchBlockPlacementApi(ctx, uuid),
    staleTime: 10_000,
    enabled: !!uuid,
  });
}

export function useBlockPlacement(ctx: CmsApiContext, uuid: string) {
  return useQuery(blockPlacementQueryOptions(ctx, uuid));
}

export function blockHistoryQueryOptions(
  ctx: CmsApiContext,
  uuid: string,
  params?: Record<string, unknown>,
) {
  return queryOptions({
    queryKey: queryKeys.cms.blockHistory(uuid),
    queryFn: () => fetchBlockHistoryApi(ctx, uuid, params),
    staleTime: 30_000,
    enabled: !!uuid,
  });
}

export function useBlockHistory(
  ctx: CmsApiContext,
  uuid: string,
  params?: Record<string, unknown>,
) {
  return useQuery(blockHistoryQueryOptions(ctx, uuid, params));
}

// =============================================================================
// TEMPLATE CATALOG (business context only)
// =============================================================================

export function catalogSectionsQueryOptions(businessSlug: string) {
  return queryOptions({
    queryKey: queryKeys.cms.catalogSections(businessSlug),
    queryFn: () => fetchCatalogSectionsApi(businessSlug),
    staleTime: 5 * 60_000,
    enabled: !!businessSlug,
  });
}

export function useCatalogSections(businessSlug: string) {
  return useQuery(catalogSectionsQueryOptions(businessSlug));
}

export function catalogBlocksQueryOptions(businessSlug: string) {
  return queryOptions({
    queryKey: queryKeys.cms.catalogBlocks(businessSlug),
    queryFn: () => fetchCatalogBlocksApi(businessSlug),
    staleTime: 5 * 60_000,
    enabled: !!businessSlug,
  });
}

export function useCatalogBlocks(businessSlug: string) {
  return useQuery(catalogBlocksQueryOptions(businessSlug));
}

// =============================================================================
// TEMPLATE LIBRARY (business context only)
// =============================================================================

export function librarySectionsQueryOptions(businessSlug: string) {
  return queryOptions({
    queryKey: queryKeys.cms.librarySections(businessSlug),
    queryFn: () => fetchLibrarySectionsApi(businessSlug),
    staleTime: 5 * 60_000,
    enabled: !!businessSlug,
  });
}

export function useLibrarySections(businessSlug: string) {
  return useQuery(librarySectionsQueryOptions(businessSlug));
}

export function libraryBlocksQueryOptions(businessSlug: string) {
  return queryOptions({
    queryKey: queryKeys.cms.libraryBlocks(businessSlug),
    queryFn: () => fetchLibraryBlocksApi(businessSlug),
    staleTime: 5 * 60_000,
    enabled: !!businessSlug,
  });
}

export function useLibraryBlocks(businessSlug: string) {
  return useQuery(libraryBlocksQueryOptions(businessSlug));
}

// =============================================================================
// ADMIN TEMPLATES (platform context only, read-only browsing)
// =============================================================================

/** Returns CmsSectionTemplate (SectionTemplateOutputSerializer), not catalog type */
export function adminSectionTemplatesQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.cms.adminSectionTemplates(),
    queryFn: () => fetchAdminSectionTemplatesApi(),
    staleTime: 5 * 60_000,
  });
}

export function useAdminSectionTemplates() {
  return useQuery(adminSectionTemplatesQueryOptions());
}

/** Returns CmsBlockTemplate (BlockTemplateOutputSerializer), not catalog type */
export function adminBlockTemplatesQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.cms.adminBlockTemplates(),
    queryFn: () => fetchAdminBlockTemplatesApi(),
    staleTime: 5 * 60_000,
  });
}

export function useAdminBlockTemplates() {
  return useQuery(adminBlockTemplatesQueryOptions());
}

// =============================================================================
// MEDIA
// =============================================================================

export function mediaFilesQueryOptions(
  ctx: CmsApiContext,
  params?: { folder?: string; type?: string },
) {
  return queryOptions({
    queryKey: queryKeys.cms.mediaFiles(params),
    queryFn: () => fetchMediaFilesApi(ctx, params),
    staleTime: 60_000,
  });
}

export function useMediaFiles(
  ctx: CmsApiContext,
  params?: { folder?: string; type?: string },
) {
  return useQuery(mediaFilesQueryOptions(ctx, params));
}

export function mediaFileQueryOptions(ctx: CmsApiContext, uuid: string) {
  return queryOptions({
    queryKey: queryKeys.cms.mediaFile(uuid),
    queryFn: () => fetchMediaFileApi(ctx, uuid),
    staleTime: 60_000,
    enabled: !!uuid,
  });
}

export function useMediaFile(ctx: CmsApiContext, uuid: string) {
  return useQuery(mediaFileQueryOptions(ctx, uuid));
}

// =============================================================================
// API KEYS
// =============================================================================

export function apiKeysQueryOptions(ctx: CmsApiContext, siteId?: string) {
  return queryOptions({
    queryKey: queryKeys.cms.apiKeys(siteId),
    queryFn: () => fetchApiKeysApi(ctx, siteId),
    staleTime: 5 * 60_000,
  });
}

export function useApiKeys(ctx: CmsApiContext, siteId?: string) {
  return useQuery(apiKeysQueryOptions(ctx, siteId));
}

// =============================================================================
// PLATFORM MANAGEMENT
// =============================================================================

export function businessCmsStatusQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.cms.businessStatus(),
    queryFn: () => fetchBusinessCmsStatusApi(),
    staleTime: 5 * 60_000,
  });
}

export function useBusinessCmsStatus() {
  return useQuery(businessCmsStatusQueryOptions());
}

export function businessActivationsQueryOptions(uuid: string) {
  return queryOptions({
    queryKey: queryKeys.cms.businessActivations(uuid),
    queryFn: () => fetchBusinessActivationsApi(uuid),
    staleTime: 5 * 60_000,
    enabled: !!uuid,
  });
}

export function useBusinessActivations(uuid: string) {
  return useQuery(businessActivationsQueryOptions(uuid));
}
