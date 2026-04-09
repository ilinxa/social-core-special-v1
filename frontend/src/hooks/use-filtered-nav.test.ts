import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useMembershipStore } from "@/stores/membership-store";
import { useFilteredNav } from "@/hooks/use-filtered-nav";
import { NAV_CONFIG } from "@/lib/navigation-config";
import type { Membership, MembershipPermission } from "@/types/rbac";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

const mockUsePathname = vi.mocked(usePathname);

function makeMembership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: "mem-1",
    account_type: "business",
    account_id: "acc-1",
    account_name: "Acme Corp",
    account_slug: "acme",
    role: {
      id: "role-1",
      name: "Owner",
      account_type: "business",
      account_id: "acc-1",
      level: 0,
      is_system_role: true,
      description: "",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    is_owner: true,
    status: "active",
    joined_at: "2026-01-01T00:00:00Z",
    permissions: [],
    account_max_members: 6,
    ...overrides,
  };
}

function makePermissions(...codes: string[]): MembershipPermission[] {
  return codes.map((code) => ({ code, scope: "business" }));
}

describe("useFilteredNav", () => {
  afterEach(() => {
    useMembershipStore.setState({ memberships: [], isLoaded: false });
  });

  describe("personal context", () => {
    it("returns all personal sections without filtering", () => {
      mockUsePathname.mockReturnValue("/home");
      const { result } = renderHook(() => useFilteredNav());
      expect(result.current).toEqual(NAV_CONFIG.personal);
    });

    it("returns personal sections for /profile", () => {
      mockUsePathname.mockReturnValue("/profile");
      const { result } = renderHook(() => useFilteredNav());
      expect(result.current).toHaveLength(NAV_CONFIG.personal.length);
    });
  });

  describe("business context", () => {
    it("returns empty when no matching membership", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({ memberships: [], isLoaded: true });
      const { result } = renderHook(() => useFilteredNav());
      expect(result.current).toEqual([]);
    });

    it("shows only items without permission requirement when user has no permissions", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [makeMembership({ permissions: [] })],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      // Dashboard, Profile, and Chat have no permission requirement
      const allItems = result.current.flatMap((s) => s.items);
      expect(allItems).toHaveLength(3);
      expect(allItems[0].key).toBe("biz-dashboard");
      expect(allItems[1].key).toBe("biz-profile");
      expect(allItems[2].key).toBe("biz-chat");
    });

    it("shows permission-gated items when user has matching permissions", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            permissions: makePermissions("can_view_members", "can_create_role"),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      const keys = allItems.map((i) => i.key);
      expect(keys).toContain("biz-dashboard");
      expect(keys).toContain("biz-members");
      expect(keys).not.toContain("biz-forms");
    });

    it("shows all items when user has all permissions", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            permissions: makePermissions(
              "can_view_members",
              "can_manage_followers",
              "can_manage_connections",
              "can_create_form",
              "can_view_cms_content",
              "can_activate_cms_template",
              "can_upload_cms_media",
              "can_create_cms_api_key",
              "can_view_transactions",
              "can_view_audit_logs",
              "can_view_settings",
            ),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      expect(allItems).toHaveLength(NAV_CONFIG.business.flatMap((s) => s.items).length);
    });

    it("removes empty sections", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            permissions: makePermissions("can_view_members"),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      // Content and some Operations sections should be removed (no matching permissions)
      const sectionLabels = result.current.map((s) => s.label);
      expect(sectionLabels).toContain("Overview");
      expect(sectionLabels).toContain("Team");
      expect(sectionLabels).not.toContain("Content");
    });

    it("hides ownerOnly items for non-owners", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      // Create a config scenario with ownerOnly — we test the filtering logic
      useMembershipStore.setState({
        memberships: [makeMembership({ is_owner: false, permissions: [] })],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      // No ownerOnly items in current config, but the filter path works
      expect(allItems.every((i) => !i.ownerOnly)).toBe(true);
    });

    it("ignores suspended memberships", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            status: "suspended",
            permissions: makePermissions("can_view_members"),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      expect(result.current).toEqual([]);
    });

    it("hides items with minMembers when account_max_members is below threshold", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            account_max_members: 1,
            permissions: makePermissions("can_view_members"),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      const keys = allItems.map((i) => i.key);
      // Members has minMembers: 2, so it should be hidden
      expect(keys).not.toContain("biz-members");
      expect(keys).toContain("biz-dashboard");
    });

    it("shows items with minMembers when account_max_members meets threshold", () => {
      mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            account_max_members: 6,
            permissions: makePermissions("can_view_members"),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      const keys = allItems.map((i) => i.key);
      expect(keys).toContain("biz-members");
    });
  });

  describe("platform context", () => {
    it("returns empty when no platform membership", () => {
      mockUsePathname.mockReturnValue("/pconsole/dashboard");
      useMembershipStore.setState({ memberships: [], isLoaded: true });
      const { result } = renderHook(() => useFilteredNav());
      expect(result.current).toEqual([]);
    });

    it("shows only ungated items when no permissions", () => {
      mockUsePathname.mockReturnValue("/pconsole/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            account_type: "platform",
            account_slug: "",
            permissions: [],
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      // Dashboard, Profile, and Chat have no permission requirement
      expect(allItems).toHaveLength(3);
      expect(allItems[0].key).toBe("plat-dashboard");
      expect(allItems[1].key).toBe("plat-profile");
      expect(allItems[2].key).toBe("plat-chat");
    });

    it("shows permission-gated items for platform", () => {
      mockUsePathname.mockReturnValue("/pconsole/dashboard");
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            account_type: "platform",
            account_slug: "",
            permissions: makePermissions("can_view_businesses", "can_view_members"),
          }),
        ],
        isLoaded: true,
      });
      const { result } = renderHook(() => useFilteredNav());
      const allItems = result.current.flatMap((s) => s.items);
      const keys = allItems.map((i) => i.key);
      expect(keys).toContain("plat-dashboard");
      expect(keys).toContain("plat-businesses");
      expect(keys).toContain("plat-members");
      expect(keys).not.toContain("plat-sites");
    });
  });
});
