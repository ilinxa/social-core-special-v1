import { describe, it, expect, vi, beforeEach } from "vitest";

import { fetchMyMembershipsApi } from "./membership-api";

import type { Membership } from "@/types/rbac";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockMemberships: Membership[] = [
  {
    id: "m1",
    account_type: "business",
    account_id: "biz-1",
    account_name: "Acme Corp",
    account_slug: "acme-corp",
    account_max_members: 6,
    role: {
      id: "r1",
      name: "Owner",
      account_type: "business",
      account_id: "biz-1",
      level: 1,
      is_system_role: true,
      description: "Business owner",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    is_owner: true,
    status: "active",
    joined_at: "2026-01-01T00:00:00Z",
    permissions: [{ code: "manage_members", scope: "business" }],
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchMyMembershipsApi", () => {
  it("calls GET /users/me/memberships/ and returns memberships", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockMemberships });

    const result = await fetchMyMembershipsApi();

    expect(apiClient.get).toHaveBeenCalledWith("/users/me/memberships/");
    expect(result).toEqual(mockMemberships);
    expect(result).toHaveLength(1);
  });

  it("returns empty array when user has no memberships", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const result = await fetchMyMembershipsApi();

    expect(apiClient.get).toHaveBeenCalledWith("/users/me/memberships/");
    expect(result).toEqual([]);
  });
});
