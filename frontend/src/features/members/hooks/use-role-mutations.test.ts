import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";
import {
  useCreateRole,
  useUpdateRole,
  useDeleteRole,
  useAddPermission,
  useRemovePermission,
} from "./use-role-mutations";

vi.mock("@/features/members/api/roles-api", () => ({
  createRoleApi: vi.fn().mockResolvedValue({ id: "new-role" }),
  updateRoleApi: vi.fn().mockResolvedValue({ id: "role-1" }),
  deleteRoleApi: vi.fn().mockResolvedValue(undefined),
  addPermissionToRoleApi: vi.fn().mockResolvedValue(undefined),
  removePermissionFromRoleApi: vi.fn().mockResolvedValue(undefined),
}));

import {
  createRoleApi,
  updateRoleApi,
  deleteRoleApi,
  addPermissionToRoleApi,
  removePermissionFromRoleApi,
} from "@/features/members/api/roles-api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useCreateRole", () => {
  it("calls createRoleApi with correct args", async () => {
    const { result } = renderHook(
      () => useCreateRole("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ name: "Editor", level: 5 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createRoleApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      { name: "Editor", level: 5 },
    );
  });
});

describe("useUpdateRole", () => {
  it("calls updateRoleApi with correct args", async () => {
    const { result } = renderHook(
      () => useUpdateRole("business", "test-biz", "role-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ name: "Senior Editor" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateRoleApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "role-1",
      { name: "Senior Editor" },
    );
  });
});

describe("useDeleteRole", () => {
  it("calls deleteRoleApi with correct args", async () => {
    const { result } = renderHook(
      () => useDeleteRole("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate("role-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteRoleApi).toHaveBeenCalledWith("business", "test-biz", "role-1");
  });
});

describe("useAddPermission", () => {
  it("calls addPermissionToRoleApi with correct args", async () => {
    const { result } = renderHook(
      () => useAddPermission("business", "test-biz", "role-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ permission_id: "perm-1", scope: "business" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addPermissionToRoleApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "role-1",
      { permission_id: "perm-1", scope: "business" },
    );
  });
});

describe("useRemovePermission", () => {
  it("calls removePermissionFromRoleApi with correct args", async () => {
    const { result } = renderHook(
      () => useRemovePermission("business", "test-biz", "role-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ permission_id: "perm-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removePermissionFromRoleApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "role-1",
      { permission_id: "perm-1" },
    );
  });
});
