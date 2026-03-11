import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchPlatformAccountApi,
  updatePlatformProfileApi,
  updatePlatformSettingsApi,
} from "./platform-api";

import type {
  PlatformAccountWithPerms,
  PlatformProfile,
} from "@/types/organization";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockPlatformProfile: PlatformProfile = {
  name: "Test Platform",
  tagline: "A test platform",
  description: "",
  logo: null,
  favicon: null,
  primary_color: "#000000",
  secondary_color: "#ffffff",
  contact_email: "admin@platform.com",
  contact_phone: "",
  address: "",
  social_links: {},
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockPlatformAccount: PlatformAccountWithPerms = {
  id: "plat-1",
  is_configured: true,
  max_members: 5,
  open_member_request: false,
  settings: {},
  profile: mockPlatformProfile,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_view: true,
    can_edit_profile: true,
    can_edit_settings: true,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchPlatformAccountApi", () => {
  it("calls GET /platform/account/ and returns account", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPlatformAccount });

    const result = await fetchPlatformAccountApi();

    expect(apiClient.get).toHaveBeenCalledWith("/platform/account/");
    expect(result).toEqual(mockPlatformAccount);
  });
});

describe("updatePlatformProfileApi", () => {
  it("calls PATCH /platform/profile/ with data", async () => {
    const updated = { ...mockPlatformProfile, name: "Updated Platform" };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });

    const result = await updatePlatformProfileApi({ name: "Updated Platform" });

    expect(apiClient.patch).toHaveBeenCalledWith(
      "/platform/profile/",
      { name: "Updated Platform" },
      { headers: undefined },
    );
    expect(result.name).toBe("Updated Platform");
  });
});

describe("updatePlatformSettingsApi", () => {
  it("calls PATCH /platform/settings/ with data", async () => {
    const updated = { ...mockPlatformAccount, settings: { feature_x: true } };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });

    const result = await updatePlatformSettingsApi({ settings: { feature_x: true } });

    expect(apiClient.patch).toHaveBeenCalledWith("/platform/settings/", {
      settings: { feature_x: true },
    });
    expect(result.settings).toEqual({ feature_x: true });
  });
});
