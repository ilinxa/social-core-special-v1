/**
 * CMS helper — common CMS operations for tests.
 *
 * Provides API-based CMS site, page, and API key setup.
 * NOTE: CMS admin endpoints use the `cms/admin/` prefix.
 * Pages are flat (not nested under sites) — `site_id` is in the request body.
 * Publish/unpublish require `?site=<site_slug>` query parameter.
 */

import type { ApiClient } from '../lib/api-client';

/** Create a CMS site via API. */
export async function createCmsSiteViaApi(
  api: ApiClient,
  data: {
    name: string;
    slug?: string;
    description?: string;
  },
): Promise<{ id: string; slug: string; name: string }> {
  const res = await api.post('cms/admin/sites/', data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createCmsSiteViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; slug: string; name: string };
}

/** Create a CMS page via API. Pages are NOT nested under sites. */
export async function createCmsPageViaApi(
  api: ApiClient,
  data: {
    site_id: string;
    title: string;
    slug: string;
    path: string;
    page_type: string;
    order: number;
    description?: string;
    metadata?: Record<string, unknown> | null;
    is_required?: boolean;
  },
): Promise<{ id: string; slug: string; status: string }> {
  const res = await api.post('cms/admin/pages/', data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createCmsPageViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; slug: string; status: string };
}

/** Publish a CMS page via API. Requires site query param. */
export async function publishCmsPageViaApi(
  api: ApiClient,
  siteSlug: string,
  pageSlug: string,
): Promise<void> {
  const res = await api.post(`cms/admin/pages/${pageSlug}/publish/?site=${siteSlug}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`publishCmsPageViaApi failed (${res.status}): ${body}`);
  }
}

/** Unpublish a CMS page via API. Requires site query param. */
export async function unpublishCmsPageViaApi(
  api: ApiClient,
  siteSlug: string,
  pageSlug: string,
): Promise<void> {
  const res = await api.post(`cms/admin/pages/${pageSlug}/unpublish/?site=${siteSlug}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`unpublishCmsPageViaApi failed (${res.status}): ${body}`);
  }
}

/** Create a CMS API key via API. Requires site_id (UUID). */
export async function createCmsApiKeyViaApi(
  api: ApiClient,
  data: {
    site_id: string;
    name: string;
    allowed_origins?: string[];
    rate_limit?: number;
    expires_at?: string | null;
  },
): Promise<{ id: string; key: string }> {
  const res = await api.post('cms/admin/api-keys/', data);
  return (await res.json()) as { id: string; key: string };
}

/** List CMS sites via API. */
export async function listCmsSitesViaApi(
  api: ApiClient,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get('cms/admin/sites/');
  return (await res.json()) as { results: Record<string, unknown>[] };
}

// ---------------------------------------------------------------------------
// Admin — Pages (extended)
// ---------------------------------------------------------------------------

/** Get a CMS page via API with optional depth. */
export async function getCmsPageViaApi(
  api: ApiClient,
  siteSlug: string,
  pageSlug: string,
  depth?: string,
): Promise<Record<string, unknown>> {
  const qs = depth ? `?site=${siteSlug}&depth=${depth}` : `?site=${siteSlug}`;
  const res = await api.get(`cms/admin/pages/${pageSlug}/${qs}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getCmsPageViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Delete a CMS site via API. */
export async function deleteCmsSiteViaApi(
  api: ApiClient,
  slug: string,
): Promise<void> {
  const res = await api.delete(`cms/admin/sites/${slug}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`deleteCmsSiteViaApi failed (${res.status}): ${body}`);
  }
}

/** Delete a CMS page via API. */
export async function deleteCmsPageViaApi(
  api: ApiClient,
  siteSlug: string,
  pageSlug: string,
): Promise<void> {
  const res = await api.delete(`cms/admin/pages/${pageSlug}/?site=${siteSlug}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`deleteCmsPageViaApi failed (${res.status}): ${body}`);
  }
}

/** Export a CMS page as JSON. */
export async function exportCmsPageViaApi(
  api: ApiClient,
  siteSlug: string,
  pageSlug: string,
): Promise<Record<string, unknown>> {
  const res = await api.post(`cms/admin/pages/${pageSlug}/export/?site=${siteSlug}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`exportCmsPageViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Import content into a CMS page. */
export async function importCmsPageViaApi(
  api: ApiClient,
  siteSlug: string,
  pageSlug: string,
  data: Record<string, unknown>,
): Promise<void> {
  const res = await api.post(`cms/admin/pages/${pageSlug}/import/?site=${siteSlug}`, data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`importCmsPageViaApi failed (${res.status}): ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Admin — Block Placements
// ---------------------------------------------------------------------------

/** Update draft content of a block placement. */
export async function updateBlockPlacementViaApi(
  api: ApiClient,
  uuid: string,
  draftContent: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const res = await api.patch(`cms/admin/block-placements/${uuid}/`, {
    draft_content: draftContent,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`updateBlockPlacementViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Get version history for a block placement. */
export async function getBlockHistoryViaApi(
  api: ApiClient,
  uuid: string,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(`cms/admin/block-placements/${uuid}/history/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getBlockHistoryViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Rollback a block placement to a specific version. */
export async function rollbackBlockViaApi(
  api: ApiClient,
  uuid: string,
  versionNumber: number,
): Promise<void> {
  const res = await api.post(
    `cms/admin/block-placements/${uuid}/rollback/${versionNumber}/`,
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`rollbackBlockViaApi failed (${res.status}): ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Admin — Media
// ---------------------------------------------------------------------------

/** Delete a CMS media file via API. */
export async function deleteCmsMediaViaApi(
  api: ApiClient,
  uuid: string,
): Promise<void> {
  const res = await api.delete(`cms/admin/media/files/${uuid}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`deleteCmsMediaViaApi failed (${res.status}): ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Admin — API Keys (extended)
// ---------------------------------------------------------------------------

/** Revoke a CMS API key via API. */
export async function revokeCmsApiKeyViaApi(
  api: ApiClient,
  uuid: string,
): Promise<void> {
  const res = await api.delete(`cms/admin/api-keys/${uuid}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`revokeCmsApiKeyViaApi failed (${res.status}): ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Admin — Templates
// ---------------------------------------------------------------------------

/** List CMS templates by type (sections or blocks). */
export async function listCmsTemplatesViaApi(
  api: ApiClient,
  type: 'sections' | 'blocks',
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(`cms/admin/templates/${type}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`listCmsTemplatesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Create a CMS template via API. */
export async function createCmsTemplateViaApi(
  api: ApiClient,
  type: 'sections' | 'blocks',
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const res = await api.post(`cms/admin/templates/${type}/`, data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createCmsTemplateViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Admin — Business CMS Management
// ---------------------------------------------------------------------------

/** Enable or disable CMS for a business via admin API. */
export async function enableCmsForBusinessViaApi(
  api: ApiClient,
  businessUuid: string,
  enabled: boolean,
): Promise<void> {
  const res = await api.patch(`cms/admin/businesses/${businessUuid}/`, {
    cms_enabled: enabled,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`enableCmsForBusinessViaApi failed (${res.status}): ${body}`);
  }
}

/** Get template activations for a business. */
export async function getBusinessActivationsViaApi(
  api: ApiClient,
  businessUuid: string,
): Promise<Record<string, unknown>> {
  const res = await api.get(`cms/admin/businesses/${businessUuid}/activations/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getBusinessActivationsViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Business CMS — Sites
// ---------------------------------------------------------------------------

/** Create a CMS site for a business. */
export async function createBusinessCmsSiteViaApi(
  api: ApiClient,
  businessSlug: string,
  data: { name: string; slug?: string; description?: string },
): Promise<{ id: string; slug: string; name: string }> {
  const res = await api.post(`cms/business/${businessSlug}/sites/`, data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createBusinessCmsSiteViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; slug: string; name: string };
}

/** List CMS sites for a business. */
export async function listBusinessCmsSitesViaApi(
  api: ApiClient,
  businessSlug: string,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(`cms/business/${businessSlug}/sites/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`listBusinessCmsSitesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Get a business CMS site detail (includes _permissions). */
export async function getBusinessCmsSiteViaApi(
  api: ApiClient,
  businessSlug: string,
  siteSlug: string,
): Promise<Record<string, unknown>> {
  const res = await api.get(`cms/business/${businessSlug}/sites/${siteSlug}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getBusinessCmsSiteViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Business CMS — Pages
// ---------------------------------------------------------------------------

/** Create a CMS page for a business. */
export async function createBusinessCmsPageViaApi(
  api: ApiClient,
  businessSlug: string,
  data: {
    site_id: string;
    title: string;
    slug: string;
    path: string;
    page_type: string;
    order: number;
  },
): Promise<{ id: string; slug: string; status: string }> {
  const res = await api.post(`cms/business/${businessSlug}/pages/`, data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createBusinessCmsPageViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; slug: string; status: string };
}

/** Publish a business CMS page. */
export async function publishBusinessCmsPageViaApi(
  api: ApiClient,
  businessSlug: string,
  siteSlug: string,
  pageSlug: string,
): Promise<void> {
  const res = await api.post(
    `cms/business/${businessSlug}/pages/${pageSlug}/publish/?site=${siteSlug}`,
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`publishBusinessCmsPageViaApi failed (${res.status}): ${body}`);
  }
}

/** Unpublish a business CMS page. */
export async function unpublishBusinessCmsPageViaApi(
  api: ApiClient,
  businessSlug: string,
  siteSlug: string,
  pageSlug: string,
): Promise<void> {
  const res = await api.post(
    `cms/business/${businessSlug}/pages/${pageSlug}/unpublish/?site=${siteSlug}`,
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`unpublishBusinessCmsPageViaApi failed (${res.status}): ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Business CMS — Templates (Catalog & Library)
// ---------------------------------------------------------------------------

/** Browse available templates in the catalog. */
export async function listCatalogTemplatesViaApi(
  api: ApiClient,
  businessSlug: string,
  type: 'sections' | 'blocks',
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(`cms/business/${businessSlug}/catalog/${type}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`listCatalogTemplatesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** List activated templates in the library. */
export async function listLibraryTemplatesViaApi(
  api: ApiClient,
  businessSlug: string,
  type: 'sections' | 'blocks',
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(`cms/business/${businessSlug}/library/${type}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`listLibraryTemplatesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Activate a template from the catalog into the library. */
export async function activateTemplateViaApi(
  api: ApiClient,
  businessSlug: string,
  templateId: string,
  type: 'sections' | 'blocks',
): Promise<Record<string, unknown>> {
  const res = await api.post(`cms/business/${businessSlug}/library/${type}/`, {
    template_id: templateId,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`activateTemplateViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Deactivate a template from the library. */
export async function deactivateTemplateViaApi(
  api: ApiClient,
  businessSlug: string,
  activationUuid: string,
  type: 'sections' | 'blocks',
): Promise<void> {
  const res = await api.delete(
    `cms/business/${businessSlug}/library/${type}/${activationUuid}/`,
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`deactivateTemplateViaApi failed (${res.status}): ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Business CMS — API Keys
// ---------------------------------------------------------------------------

/** Create an API key for a business CMS site. */
export async function createBusinessCmsApiKeyViaApi(
  api: ApiClient,
  businessSlug: string,
  data: { site_id: string; name: string; allowed_origins?: string[]; rate_limit?: number },
): Promise<{ id: string; key: string }> {
  const res = await api.post(`cms/business/${businessSlug}/api-keys/`, data);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createBusinessCmsApiKeyViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; key: string };
}

// ---------------------------------------------------------------------------
// Public CMS API (API key auth, no bearer token)
// ---------------------------------------------------------------------------

/**
 * Get a published site via the public CMS API.
 * Uses raw fetch with X-CMS-API-Key header instead of ApiClient.
 */
export async function getPublicSiteViaApi(
  backendUrl: string,
  apiKey: string,
  siteSlug: string,
): Promise<Response> {
  return fetch(`${backendUrl}/api/v1/cms/public/sites/${siteSlug}/`, {
    method: 'GET',
    headers: {
      'X-CMS-API-Key': apiKey,
      Accept: 'application/json',
    },
  });
}

/**
 * Get a published page via the public CMS API.
 * Uses raw fetch with X-CMS-API-Key header instead of ApiClient.
 */
export async function getPublicPageViaApi(
  backendUrl: string,
  apiKey: string,
  pageSlug: string,
  depth?: string,
): Promise<Response> {
  const qs = depth ? `?depth=${depth}` : '';
  return fetch(`${backendUrl}/api/v1/cms/public/pages/${pageSlug}/${qs}`, {
    method: 'GET',
    headers: {
      'X-CMS-API-Key': apiKey,
      Accept: 'application/json',
    },
  });
}
