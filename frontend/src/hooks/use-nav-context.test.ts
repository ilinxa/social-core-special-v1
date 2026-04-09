import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useMembershipStore } from "@/stores/membership-store";
import { useNavContext } from "@/hooks/use-nav-context";
import type { Membership } from "@/types/rbac";

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
    account_max_members: 6,
    role: {
      id: "role-1",
      name: "Manager",
      account_type: "business",
      account_id: "acc-1",
      level: 5,
      is_system_role: false,
      description: "",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    is_owner: false,
    status: "active",
    joined_at: "2026-01-01T00:00:00Z",
    permissions: [],
    ...overrides,
  };
}

describe("useNavContext", () => {
  afterEach(() => {
    useMembershipStore.setState({ memberships: [], isLoaded: false });
  });

  it("returns personal context for /home", () => {
    mockUsePathname.mockReturnValue("/home");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({ type: "personal" });
  });

  it("returns personal context for /profile", () => {
    mockUsePathname.mockReturnValue("/profile");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({ type: "personal" });
  });

  it("returns personal context for /settings", () => {
    mockUsePathname.mockReturnValue("/settings");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({ type: "personal" });
  });

  it("returns personal context for /explore", () => {
    mockUsePathname.mockReturnValue("/explore");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({ type: "personal" });
  });

  it("returns personal context for public business discovery (/business/acme)", () => {
    mockUsePathname.mockReturnValue("/business/acme");
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "acme" })],
      isLoaded: true,
    });
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({ type: "personal" });
  });

  it("returns business context for /bconsole/acme/dashboard", () => {
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "acme", account_id: "acc-1", account_name: "Acme Corp" })],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "business",
      slug: "acme",
      accountId: "acc-1",
      accountName: "Acme Corp",
    });
  });

  it("returns business context for /bconsole/globex/members", () => {
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "globex", account_id: "acc-2", account_name: "Globex" })],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/bconsole/globex/members");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "business",
      slug: "globex",
      accountId: "acc-2",
      accountName: "Globex",
    });
  });

  it("returns business context with fallback values when membership not found", () => {
    useMembershipStore.setState({ memberships: [], isLoaded: true });
    mockUsePathname.mockReturnValue("/bconsole/unknown/dashboard");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "business",
      slug: "unknown",
      accountId: "",
      accountName: "unknown",
    });
  });

  it("ignores suspended memberships for business context", () => {
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "acme", status: "suspended" })],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "business",
      slug: "acme",
      accountId: "",
      accountName: "acme",
    });
  });

  it("returns platform context for /pconsole/dashboard", () => {
    useMembershipStore.setState({
      memberships: [
        makeMembership({ account_type: "platform", account_id: "plat-1", account_slug: "" }),
      ],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/pconsole/dashboard");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "platform",
      accountId: "plat-1",
    });
  });

  it("returns platform context for legacy /pconsole/cms/sites (redirect pending)", () => {
    useMembershipStore.setState({
      memberships: [
        makeMembership({ account_type: "platform", account_id: "plat-1", account_slug: "" }),
      ],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/pconsole/cms/sites");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "platform",
      accountId: "plat-1",
    });
  });

  // =========================================================================
  // CMS Console (cconsole) — platform mode
  // =========================================================================

  it("returns CMS platform context for /cconsole/sites", () => {
    useMembershipStore.setState({
      memberships: [
        makeMembership({ account_type: "platform", account_id: "plat-1", account_slug: "" }),
      ],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/cconsole/sites");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "cms",
      mode: "platform",
      accountId: "plat-1",
    });
  });

  it("returns CMS platform context for /cconsole/templates", () => {
    useMembershipStore.setState({
      memberships: [
        makeMembership({ account_type: "platform", account_id: "plat-1", account_slug: "" }),
      ],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/cconsole/templates");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "cms",
      mode: "platform",
      accountId: "plat-1",
    });
  });

  it("returns CMS platform context for /cconsole (root)", () => {
    useMembershipStore.setState({
      memberships: [
        makeMembership({ account_type: "platform", account_id: "plat-1", account_slug: "" }),
      ],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/cconsole");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "cms",
      mode: "platform",
      accountId: "plat-1",
    });
  });

  // =========================================================================
  // CMS Console (cconsole) — business mode
  // =========================================================================

  it("returns CMS business context for /cconsole/acme/sites", () => {
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "acme", account_id: "acc-1", account_name: "Acme Corp" })],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/cconsole/acme/sites");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "cms",
      mode: "business",
      slug: "acme",
      accountId: "acc-1",
      accountName: "Acme Corp",
    });
  });

  it("returns CMS business context for /cconsole/acme/catalog", () => {
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "acme", account_id: "acc-1", account_name: "Acme Corp" })],
      isLoaded: true,
    });
    mockUsePathname.mockReturnValue("/cconsole/acme/catalog");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "cms",
      mode: "business",
      slug: "acme",
      accountId: "acc-1",
      accountName: "Acme Corp",
    });
  });

  it("returns CMS business context with fallback when membership not found", () => {
    useMembershipStore.setState({ memberships: [], isLoaded: true });
    mockUsePathname.mockReturnValue("/cconsole/unknown/sites");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "cms",
      mode: "business",
      slug: "unknown",
      accountId: "",
      accountName: "unknown",
    });
  });

  it("returns platform context with fallback when no platform membership", () => {
    useMembershipStore.setState({ memberships: [], isLoaded: true });
    mockUsePathname.mockReturnValue("/pconsole/dashboard");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({
      type: "platform",
      accountId: "",
    });
  });

  it("returns personal context for root /", () => {
    mockUsePathname.mockReturnValue("/");
    const { result } = renderHook(() => useNavContext());
    expect(result.current).toEqual({ type: "personal" });
  });
});
