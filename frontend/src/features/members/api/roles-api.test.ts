import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchRolesApi,
  fetchRoleDetailApi,
  createRoleApi,
  updateRoleApi,
  deleteRoleApi,
  addPermissionToRoleApi,
  removePermissionFromRoleApi,
  fetchAllPermissionsApi,
} from "./roles-api";

import type { RoleListItem, RoleDetailWithPerms, Permission } from "@/types/members";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockRoleListItem: RoleListItem = {
  id: "role-1",
  name: "Admin",
  account_type: "business",
  account_id: "acc-1",
  level: 2,
  is_system_role: true,
  description: "Administrator role",
  member_count: 3,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockRoleDetail: RoleDetailWithPerms = {
  id: "role-1",
  name: "Admin",
  account_type: "business",
  account_id: "acc-1",
  level: 2,
  is_system_role: true,
  description: "Administrator role",
  role_permissions: [
    {
      id: "rp-1",
      permission: {
        id: "perm-1",
        code: "can_manage_members",
        name: "Manage Members",
        description: "Can manage team members",
        category: "member_management",
        applicable_scopes: ["business", "platform"],
      },
      scope: "business",
    },
  ],
  permission_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_edit: true,
    can_delete: false,
    can_modify_permissions: true,
  },
};

const mockPermission: Permission = {
  id: "perm-1",
  code: "can_manage_members",
  name: "Manage Members",
  description: "Can manage team members",
  category: "member_management",
  applicable_scopes: ["business", "platform"],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchRolesApi", () => {
  it("calls GET /business/<slug>/roles/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [mockRoleListItem],
    });

    const result = await fetchRolesApi("business", "test-biz");

    expect(apiClient.get).toHaveBeenCalledWith("/business/test-biz/roles/");
    expect(result).toEqual([mockRoleListItem]);
  });

  it("calls GET /platform/roles/ for platform", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    await fetchRolesApi("platform", "platform");

    expect(apiClient.get).toHaveBeenCalledWith("/platform/roles/");
  });
});

describe("fetchRoleDetailApi", () => {
  it("calls GET /business/<slug>/roles/<id>/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockRoleDetail });

    const result = await fetchRoleDetailApi("business", "test-biz", "role-1");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/business/test-biz/roles/role-1/",
    );
    expect(result._permissions.can_edit).toBe(true);
  });
});

describe("createRoleApi", () => {
  it("calls POST /business/<slug>/roles/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockRoleDetail });

    const result = await createRoleApi("business", "test-biz", {
      name: "Editor",
      level: 5,
      description: "Can edit content",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/business/test-biz/roles/", {
      name: "Editor",
      level: 5,
      description: "Can edit content",
    });
    expect(result.id).toBe("role-1");
  });
});

describe("updateRoleApi", () => {
  it("calls PATCH /business/<slug>/roles/<id>/", async () => {
    const updated = { ...mockRoleDetail, name: "Senior Admin" };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });

    const result = await updateRoleApi("business", "test-biz", "role-1", {
      name: "Senior Admin",
    });

    expect(apiClient.patch).toHaveBeenCalledWith(
      "/business/test-biz/roles/role-1/",
      { name: "Senior Admin" },
    );
    expect(result.name).toBe("Senior Admin");
  });
});

describe("deleteRoleApi", () => {
  it("calls DELETE /business/<slug>/roles/<id>/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await deleteRoleApi("business", "test-biz", "role-1");

    expect(apiClient.delete).toHaveBeenCalledWith(
      "/business/test-biz/roles/role-1/",
    );
  });
});

describe("addPermissionToRoleApi", () => {
  it("calls POST /business/<slug>/roles/<id>/permissions/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await addPermissionToRoleApi("business", "test-biz", "role-1", {
      permission_id: "perm-1",
      scope: "business",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/business/test-biz/roles/role-1/permissions/",
      { permission_id: "perm-1", scope: "business" },
    );
  });
});

describe("removePermissionFromRoleApi", () => {
  it("calls DELETE /business/<slug>/roles/<id>/permissions/ with data", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await removePermissionFromRoleApi("business", "test-biz", "role-1", {
      permission_id: "perm-1",
    });

    expect(apiClient.delete).toHaveBeenCalledWith(
      "/business/test-biz/roles/role-1/permissions/",
      { data: { permission_id: "perm-1" } },
    );
  });
});

describe("fetchAllPermissionsApi", () => {
  it("calls GET /rbac/permissions/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [mockPermission],
    });

    const result = await fetchAllPermissionsApi();

    expect(apiClient.get).toHaveBeenCalledWith("/rbac/permissions/");
    expect(result).toEqual([mockPermission]);
  });
});
