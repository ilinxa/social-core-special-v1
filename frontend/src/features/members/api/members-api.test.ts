import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchMembersApi,
  fetchMemberDetailApi,
  changeMemberRoleApi,
  suspendMemberApi,
  removeMemberApi,
  banMemberApi,
  reactivateMemberApi,
  leaveMemberApi,
} from "./members-api";

import type { PaginatedResponse } from "@/types";
import type { MemberListItem, MemberDetailWithPerms } from "@/types/members";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockMemberUser = {
  id: "user-1",
  email: "alice@example.com",
  username: "alice",
  display_name: "Alice Smith",
  avatar_url: null,
};

const mockMemberListItem: MemberListItem = {
  id: "mem-1",
  user: mockMemberUser,
  role_name: "Admin",
  role_level: 2,
  is_owner: false,
  status: "active",
  joined_at: "2026-01-01T00:00:00Z",
};

const mockPaginatedMembers: PaginatedResponse<MemberListItem> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockMemberListItem],
};

const mockMemberDetail: MemberDetailWithPerms = {
  id: "mem-1",
  user: mockMemberUser,
  account_type: "business",
  account_id: "acc-1",
  role: {
    id: "role-1",
    name: "Admin",
    account_type: "business",
    account_id: "acc-1",
    level: 2,
    is_system_role: true,
    description: "",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  is_owner: false,
  status: "active",
  joined_at: "2026-01-01T00:00:00Z",
  status_changed_at: null,
  status_reason: "",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_change_role: true,
    can_suspend: true,
    can_remove: true,
    can_ban: true,
    can_reactivate: false,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchMembersApi", () => {
  it("calls GET /business/<slug>/members/ with params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedMembers });

    const result = await fetchMembersApi("business", "test-biz", {
      search: "alice",
      status: "active",
    });

    expect(apiClient.get).toHaveBeenCalledWith("/business/test-biz/members/", {
      params: { search: "alice", status: "active" },
    });
    expect(result).toEqual(mockPaginatedMembers);
  });

  it("calls GET /platform/members/ for platform", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedMembers });

    await fetchMembersApi("platform", "platform");

    expect(apiClient.get).toHaveBeenCalledWith("/platform/members/", {
      params: undefined,
    });
  });
});

describe("fetchMemberDetailApi", () => {
  it("calls GET /business/<slug>/members/<id>/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockMemberDetail });

    const result = await fetchMemberDetailApi("business", "test-biz", "mem-1");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/",
    );
    expect(result._permissions.can_change_role).toBe(true);
  });

  it("calls GET /platform/members/<id>/ for platform", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockMemberDetail });

    await fetchMemberDetailApi("platform", "platform", "mem-1");

    expect(apiClient.get).toHaveBeenCalledWith("/platform/members/mem-1/");
  });
});

describe("changeMemberRoleApi", () => {
  it("calls PATCH /business/<slug>/members/<id>/role/", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: undefined });

    await changeMemberRoleApi("business", "test-biz", "mem-1", {
      role_id: "role-2",
    });

    expect(apiClient.patch).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/role/",
      { role_id: "role-2" },
    );
  });
});

describe("suspendMemberApi", () => {
  it("calls POST with reason", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await suspendMemberApi("business", "test-biz", "mem-1", {
      reason: "Policy violation",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/suspend/",
      { reason: "Policy violation" },
    );
  });

  it("sends empty object when no reason", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await suspendMemberApi("business", "test-biz", "mem-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/suspend/",
      {},
    );
  });
});

describe("removeMemberApi", () => {
  it("calls POST /business/<slug>/members/<id>/remove/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await removeMemberApi("business", "test-biz", "mem-1", {
      reason: "Left company",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/remove/",
      { reason: "Left company" },
    );
  });
});

describe("banMemberApi", () => {
  it("calls POST /business/<slug>/members/<id>/ban/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await banMemberApi("business", "test-biz", "mem-1", {
      reason: "Spam",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/ban/",
      { reason: "Spam" },
    );
  });
});

describe("reactivateMemberApi", () => {
  it("calls POST /business/<slug>/members/<id>/reactivate/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await reactivateMemberApi("business", "test-biz", "mem-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/members/mem-1/reactivate/",
      {},
    );
  });
});

describe("leaveMemberApi", () => {
  it("calls POST /business/<slug>/members/leave/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await leaveMemberApi("business", "test-biz");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/members/leave/",
      {},
    );
  });

  it("calls POST /platform/members/leave/ for platform", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await leaveMemberApi("platform", "platform");

    expect(apiClient.post).toHaveBeenCalledWith("/platform/members/leave/", {});
  });
});
