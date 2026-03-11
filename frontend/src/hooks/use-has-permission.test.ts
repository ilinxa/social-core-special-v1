import { renderHook } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";

import { useHasPermission, useIsMember, useIsOwner } from "./use-has-permission";
import { useMembershipStore } from "@/stores/membership-store";

import type { Membership } from "@/types/rbac";

const mockMembership: Membership = {
  id: "m1",
  account_type: "business",
  account_id: "biz-1",
  account_name: "Test Biz",
  account_slug: "test-biz",
  account_max_members: 6,
  role: {
    id: "r1",
    name: "Manager",
    account_type: "business",
    account_id: "biz-1",
    level: 5,
    is_system_role: false,
    description: "",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  is_owner: false,
  status: "active",
  joined_at: "2026-01-01T00:00:00Z",
  permissions: [
    { code: "manage_members", scope: "business" },
    { code: "view_reports", scope: "business" },
  ],
};

const mockOwnerMembership: Membership = {
  ...mockMembership,
  id: "m2",
  account_id: "biz-2",
  is_owner: true,
};

beforeEach(() => {
  useMembershipStore.setState({
    memberships: [mockMembership, mockOwnerMembership],
    isLoaded: true,
  });
});

describe("useHasPermission", () => {
  it("returns true when user has the permission", () => {
    const { result } = renderHook(() => useHasPermission("manage_members", "business", "biz-1"));
    expect(result.current).toBe(true);
  });

  it("returns false when user lacks the permission", () => {
    const { result } = renderHook(() => useHasPermission("delete_business", "business", "biz-1"));
    expect(result.current).toBe(false);
  });

  it("returns false when no membership for account", () => {
    const { result } = renderHook(() => useHasPermission("manage_members", "business", "biz-999"));
    expect(result.current).toBe(false);
  });
});

describe("useIsMember", () => {
  it("returns true when user has active membership", () => {
    const { result } = renderHook(() => useIsMember("business", "biz-1"));
    expect(result.current).toBe(true);
  });

  it("returns false when no membership", () => {
    const { result } = renderHook(() => useIsMember("business", "biz-999"));
    expect(result.current).toBe(false);
  });
});

describe("useIsOwner", () => {
  it("returns true when user is owner", () => {
    const { result } = renderHook(() => useIsOwner("business", "biz-2"));
    expect(result.current).toBe(true);
  });

  it("returns false when user is member but not owner", () => {
    const { result } = renderHook(() => useIsOwner("business", "biz-1"));
    expect(result.current).toBe(false);
  });
});
