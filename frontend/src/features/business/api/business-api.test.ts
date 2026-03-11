import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchMyBusinessesApi,
  fetchBusinessApi,
  createBusinessApi,
  updateBusinessApi,
  deleteBusinessApi,
} from "./business-api";

import type {
  BusinessAccountList,
  BusinessAccountWithPerms,
} from "@/types/organization";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockBusinessProfile = {
  display_name: "Test Business",
  tagline: "",
  description: "",
  logo: null,
  cover_image: null,
  website: "",
  contact_email: "",
  contact_phone: "",
  industry: "",
  company_size: "",
  founded_year: null,
  social_links: {},
  tags: [],
  is_public: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockBusiness: BusinessAccountWithPerms = {
  id: "biz-1",
  slug: "test-biz",
  legal_name: "Test Business LLC",
  registration_number: "",
  tax_id: "",
  country: "US",
  city: "",
  legal_address: "",
  business_type: "llc",
  is_platform_branch: false,
  max_members: 6,
  open_member_request: false,
  business_type_display: "LLC",
  status: "active",
  status_display: "Active",
  verification_status: "unverified",
  verification_status_display: "Unverified",
  verified_at: null,
  settings: {},
  profile: mockBusinessProfile,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_view: true,
    can_edit: true,
    can_edit_profile: true,
    can_delete: true,
    can_change_slug: true,
    can_archive: true,
  },
};

const mockBusinessListItem: BusinessAccountList = {
  id: "biz-1",
  slug: "test-biz",
  legal_name: "Test Business LLC",
  country: "US",
  city: "",
  business_type: "llc",
  is_platform_branch: false,
  max_members: 6,
  open_member_request: false,
  status: "active",
  verification_status: "unverified",
  profile: mockBusinessProfile,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchMyBusinessesApi", () => {
  it("calls GET /business/my/ and returns list", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [mockBusinessListItem] });

    const result = await fetchMyBusinessesApi();

    expect(apiClient.get).toHaveBeenCalledWith("/business/my/");
    expect(result).toEqual([mockBusinessListItem]);
  });

  it("returns empty list when user has no businesses", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const result = await fetchMyBusinessesApi();

    expect(result).toEqual([]);
  });
});

describe("fetchBusinessApi", () => {
  it("calls GET /business/:slug/ and returns account", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBusiness });

    const result = await fetchBusinessApi("test-biz");

    expect(apiClient.get).toHaveBeenCalledWith("/business/test-biz/");
    expect(result).toEqual(mockBusiness);
  });
});

describe("createBusinessApi", () => {
  it("calls POST /business/ with payload", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockBusiness });

    const result = await createBusinessApi({
      legal_name: "Test Business LLC",
      country: "US",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/business/", {
      legal_name: "Test Business LLC",
      country: "US",
    });
    expect(result).toEqual(mockBusiness);
  });
});

describe("updateBusinessApi", () => {
  it("calls PATCH /business/:slug/ with payload", async () => {
    const updated = { ...mockBusiness, legal_name: "Updated LLC" };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });

    const result = await updateBusinessApi("test-biz", { legal_name: "Updated LLC" });

    expect(apiClient.patch).toHaveBeenCalledWith("/business/test-biz/", {
      legal_name: "Updated LLC",
    });
    expect(result.legal_name).toBe("Updated LLC");
  });
});

describe("deleteBusinessApi", () => {
  it("calls DELETE /business/:slug/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await deleteBusinessApi("test-biz");

    expect(apiClient.delete).toHaveBeenCalledWith("/business/test-biz/");
  });
});
