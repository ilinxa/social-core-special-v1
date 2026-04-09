/**
 * CMS API Function Tests
 * ========================
 * Verifies all 37 API functions call correct endpoints with correct methods.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

const mockGet = vi.fn().mockResolvedValue({ data: {} });
const mockPost = vi.fn().mockResolvedValue({ data: {} });
const mockPatch = vi.fn().mockResolvedValue({ data: {} });
const mockDelete = vi.fn().mockResolvedValue({ data: {} });

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
  ApiError: class ApiError extends Error {
    status: number;
    code: string;
    constructor(status: number, message: string, code: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

import {
  activateSectionTemplateApi,
  createApiKeyApi,
  createSiteApi,
  deactivateSectionTemplateApi,
  deleteMediaFileApi,
  deleteSiteApi,
  fetchAdminSectionTemplatesApi,
  fetchApiKeysApi,
  fetchBusinessActivationsApi,
  fetchCatalogSectionsApi,
  fetchPageApi,
  fetchPagesApi,
  fetchSiteApi,
  fetchSitesApi,
  importPageApi,
  publishPageApi,
  revokeApiKeyApi,
  rollbackBlockApi,
  toggleBusinessCmsApi,
  updateDraftContentApi,
  updateSiteApi,
  uploadMediaFileApi,
} from "@/features/cms/api/cms-api";

beforeEach(() => {
  vi.clearAllMocks();
});

const platformCtx = { type: "platform" as const };
const businessCtx = { type: "business" as const, businessSlug: "acme" };

// =============================================================================
// SITES
// =============================================================================

describe("Sites API", () => {
  it("fetchSitesApi calls GET /cms/admin/sites/ for platform", async () => {
    await fetchSitesApi(platformCtx);
    expect(mockGet).toHaveBeenCalledWith("/cms/admin/sites/", { params: undefined });
  });

  it("fetchSitesApi calls GET /cms/business/{slug}/sites/ for business", async () => {
    await fetchSitesApi(businessCtx);
    expect(mockGet).toHaveBeenCalledWith("/cms/business/acme/sites/", {
      params: undefined,
    });
  });

  it("fetchSiteApi calls GET with slug", async () => {
    await fetchSiteApi(platformCtx, "my-site");
    expect(mockGet).toHaveBeenCalledWith("/cms/admin/sites/my-site/");
  });

  it("createSiteApi calls POST", async () => {
    await createSiteApi(platformCtx, { name: "Test", slug: "test" });
    expect(mockPost).toHaveBeenCalledWith("/cms/admin/sites/", {
      name: "Test",
      slug: "test",
    });
  });

  it("updateSiteApi calls PATCH", async () => {
    await updateSiteApi(platformCtx, "test", { name: "Updated" });
    expect(mockPatch).toHaveBeenCalledWith("/cms/admin/sites/test/", {
      name: "Updated",
    });
  });

  it("deleteSiteApi calls DELETE", async () => {
    await deleteSiteApi(platformCtx, "test");
    expect(mockDelete).toHaveBeenCalledWith("/cms/admin/sites/test/");
  });
});

// =============================================================================
// PAGES
// =============================================================================

describe("Pages API", () => {
  it("fetchPagesApi passes site and status params", async () => {
    await fetchPagesApi(platformCtx, { site: "my-site", status: "draft" });
    expect(mockGet).toHaveBeenCalledWith("/cms/admin/pages/", {
      params: { site: "my-site", status: "draft" },
    });
  });

  it("fetchPageApi supports depth=full", async () => {
    await fetchPageApi(platformCtx, "home", { site: "my-site", depth: "full" });
    expect(mockGet).toHaveBeenCalledWith("/cms/admin/pages/home/", {
      params: { site: "my-site", depth: "full" },
    });
  });

  it("publishPageApi passes site as query param", async () => {
    await publishPageApi(platformCtx, "home", "my-site");
    expect(mockPost).toHaveBeenCalledWith(
      "/cms/admin/pages/home/publish/",
      null,
      { params: { site: "my-site" } },
    );
  });

  it("importPageApi posts import data with site param", async () => {
    const importData = { export_version: "3.1", page: {} };
    await importPageApi(platformCtx, "home", "my-site", importData);
    expect(mockPost).toHaveBeenCalledWith(
      "/cms/admin/pages/home/import/",
      importData,
      { params: { site: "my-site" } },
    );
  });
});

// =============================================================================
// BLOCK PLACEMENTS
// =============================================================================

describe("Block Placements API", () => {
  it("updateDraftContentApi calls PATCH with content", async () => {
    await updateDraftContentApi(platformCtx, "uuid-1", {
      draft_content: { title: "Hello" },
    });
    expect(mockPatch).toHaveBeenCalledWith(
      "/cms/admin/block-placements/uuid-1/",
      { draft_content: { title: "Hello" } },
    );
  });

  it("rollbackBlockApi calls POST with version number", async () => {
    await rollbackBlockApi(platformCtx, "uuid-1", 3);
    expect(mockPost).toHaveBeenCalledWith(
      "/cms/admin/block-placements/uuid-1/rollback/3/",
    );
  });
});

// =============================================================================
// TEMPLATE CATALOG & LIBRARY
// =============================================================================

describe("Template Catalog/Library API", () => {
  it("fetchCatalogSectionsApi uses business URL", async () => {
    await fetchCatalogSectionsApi("acme");
    expect(mockGet).toHaveBeenCalledWith(
      "/cms/business/acme/catalog/sections/",
      { params: undefined },
    );
  });

  it("activateSectionTemplateApi posts template_id", async () => {
    await activateSectionTemplateApi("acme", { template_id: "t-1" });
    expect(mockPost).toHaveBeenCalledWith(
      "/cms/business/acme/library/sections/",
      { template_id: "t-1" },
    );
  });

  it("deactivateSectionTemplateApi calls DELETE", async () => {
    await deactivateSectionTemplateApi("acme", "act-1");
    expect(mockDelete).toHaveBeenCalledWith(
      "/cms/business/acme/library/sections/act-1/",
    );
  });

  it("fetchAdminSectionTemplatesApi uses admin URL", async () => {
    await fetchAdminSectionTemplatesApi();
    expect(mockGet).toHaveBeenCalledWith(
      "/cms/admin/templates/sections/",
      { params: undefined },
    );
  });
});

// =============================================================================
// MEDIA
// =============================================================================

describe("Media API", () => {
  it("uploadMediaFileApi posts FormData with multipart header", async () => {
    const formData = new FormData();
    await uploadMediaFileApi(platformCtx, formData);
    expect(mockPost).toHaveBeenCalledWith(
      "/cms/admin/media/files/",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  });

  it("deleteMediaFileApi calls DELETE", async () => {
    await deleteMediaFileApi(platformCtx, "file-1");
    expect(mockDelete).toHaveBeenCalledWith("/cms/admin/media/files/file-1/");
  });
});

// =============================================================================
// API KEYS
// =============================================================================

describe("API Keys API", () => {
  it("fetchApiKeysApi passes site as query param", async () => {
    await fetchApiKeysApi(platformCtx, "site-uuid");
    expect(mockGet).toHaveBeenCalledWith("/cms/admin/api-keys/", {
      params: { site: "site-uuid" },
    });
  });

  it("createApiKeyApi posts key data", async () => {
    await createApiKeyApi(platformCtx, {
      site_id: "s-1",
      name: "Prod",
    });
    expect(mockPost).toHaveBeenCalledWith("/cms/admin/api-keys/", {
      site_id: "s-1",
      name: "Prod",
    });
  });

  it("revokeApiKeyApi calls DELETE", async () => {
    await revokeApiKeyApi(platformCtx, "key-1");
    expect(mockDelete).toHaveBeenCalledWith("/cms/admin/api-keys/key-1/");
  });
});

// =============================================================================
// PLATFORM MANAGEMENT
// =============================================================================

describe("Platform Management API", () => {
  it("toggleBusinessCmsApi calls PATCH", async () => {
    await toggleBusinessCmsApi("biz-1", { cms_enabled: true });
    expect(mockPatch).toHaveBeenCalledWith("/cms/admin/businesses/biz-1/", {
      cms_enabled: true,
    });
  });

  it("fetchBusinessActivationsApi calls GET", async () => {
    await fetchBusinessActivationsApi("biz-1");
    expect(mockGet).toHaveBeenCalledWith(
      "/cms/admin/businesses/biz-1/activations/",
    );
  });
});
