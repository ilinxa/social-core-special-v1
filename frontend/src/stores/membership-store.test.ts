import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";

import {
  useMembershipStore,
  useMemberships,
  useBusinessMemberships,
  usePlatformMembership,
  useMembershipsLoaded,
} from "./membership-store";

import type { Membership } from "@/types/rbac";

const mockBusinessMembership: Membership = {
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
};

const mockPlatformMembership: Membership = {
  id: "m2",
  account_type: "platform",
  account_id: "plat-1",
  account_name: "Platform",
  account_slug: "",
  account_max_members: 5,
  role: {
    id: "r2",
    name: "Admin",
    account_type: "platform",
    account_id: "plat-1",
    level: 1,
    is_system_role: true,
    description: "Platform admin",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  is_owner: false,
  status: "active",
  joined_at: "2026-02-01T00:00:00Z",
  permissions: [],
};

const mockSuspendedMembership: Membership = {
  ...mockBusinessMembership,
  id: "m3",
  account_id: "biz-2",
  account_name: "Suspended Co",
  account_slug: "suspended-co",
  status: "suspended",
};

describe("membership-store", () => {
  beforeEach(() => {
    useMembershipStore.setState({
      memberships: [],
      isLoaded: false,
    });
  });

  it("has correct initial state", () => {
    const { result } = renderHook(() => useMembershipStore());
    expect(result.current.memberships).toEqual([]);
    expect(result.current.isLoaded).toBe(false);
  });

  it("setMemberships sets memberships and isLoaded", () => {
    const { result } = renderHook(() => useMembershipStore());

    act(() => {
      result.current.setMemberships([mockBusinessMembership, mockPlatformMembership]);
    });

    expect(result.current.memberships).toHaveLength(2);
    expect(result.current.isLoaded).toBe(true);
  });

  it("clearMemberships resets state", () => {
    const { result } = renderHook(() => useMembershipStore());

    act(() => {
      result.current.setMemberships([mockBusinessMembership]);
    });

    act(() => {
      result.current.clearMemberships();
    });

    expect(result.current.memberships).toEqual([]);
    expect(result.current.isLoaded).toBe(false);
  });
});

describe("selector hooks", () => {
  beforeEach(() => {
    useMembershipStore.setState({
      memberships: [mockBusinessMembership, mockPlatformMembership, mockSuspendedMembership],
      isLoaded: true,
    });
  });

  it("useMemberships returns all memberships", () => {
    const { result } = renderHook(() => useMemberships());
    expect(result.current).toHaveLength(3);
  });

  it("useBusinessMemberships returns only active business memberships", () => {
    const { result } = renderHook(() => useBusinessMemberships());
    expect(result.current).toHaveLength(1);
    expect(result.current[0].account_slug).toBe("acme-corp");
  });

  it("usePlatformMembership returns active platform membership", () => {
    const { result } = renderHook(() => usePlatformMembership());
    expect(result.current).not.toBeNull();
    expect(result.current!.account_type).toBe("platform");
  });

  it("usePlatformMembership returns null when no platform membership", () => {
    useMembershipStore.setState({
      memberships: [mockBusinessMembership],
      isLoaded: true,
    });
    const { result } = renderHook(() => usePlatformMembership());
    expect(result.current).toBeNull();
  });

  it("useMembershipsLoaded returns isLoaded", () => {
    const { result } = renderHook(() => useMembershipsLoaded());
    expect(result.current).toBe(true);
  });
});
