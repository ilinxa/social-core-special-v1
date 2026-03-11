import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Membership } from "@/types/rbac";
import { useMembershipStore } from "@/stores/membership-store";

import { PlatformGuard } from "./PlatformGuard";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockFetchMyMembershipsApi = vi.fn<() => Promise<Membership[]>>();

vi.mock("@/features/auth/api/membership-api", () => ({
  fetchMyMembershipsApi: (...args: unknown[]) => mockFetchMyMembershipsApi(...(args as [])),
}));

// =============================================================================
// HELPERS
// =============================================================================

function createMockMembership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: "m-plat-1",
    account_type: "platform",
    account_id: "plat-1",
    account_name: "Platform",
    account_slug: "platform",
    account_max_members: 5,
    role: {
      id: "r-plat-1",
      name: "Platform Member",
      account_type: "platform",
      account_id: "plat-1",
      level: 10,
      is_system_role: true,
      description: "Default platform member role",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    is_owner: false,
    status: "active",
    joined_at: "2026-01-15T00:00:00Z",
    permissions: [{ code: "view_platform", scope: "platform" }],
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("PlatformGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useMembershipStore.setState({
      memberships: [],
      isLoaded: false,
    });
  });

  it("shows loading skeleton while memberships are not loaded", () => {
    useMembershipStore.setState({ isLoaded: false });

    render(
      <PlatformGuard>
        <div>Platform Content</div>
      </PlatformGuard>,
    );

    expect(screen.queryByText("Platform Content")).not.toBeInTheDocument();
    expect(document.querySelector(".h-64")).toBeInTheDocument();
  });

  it("renders children when an active platform membership exists", () => {
    const membership = createMockMembership();

    useMembershipStore.setState({
      memberships: [membership],
      isLoaded: true,
    });

    render(
      <PlatformGuard>
        <div>Platform Content</div>
      </PlatformGuard>,
    );

    expect(screen.getByText("Platform Content")).toBeInTheDocument();
    expect(mockFetchMyMembershipsApi).not.toHaveBeenCalled();
  });

  it("triggers revalidation when no platform membership is in cache", async () => {
    const membership = createMockMembership();
    mockFetchMyMembershipsApi.mockResolvedValue([membership]);

    useMembershipStore.setState({
      memberships: [],
      isLoaded: true,
    });

    render(
      <PlatformGuard>
        <div>Platform Content</div>
      </PlatformGuard>,
    );

    expect(mockFetchMyMembershipsApi).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText("Platform Content")).toBeInTheDocument();
    });
  });

  it("shows Access Denied after revalidation confirms no membership", async () => {
    mockFetchMyMembershipsApi.mockResolvedValue([]);

    useMembershipStore.setState({
      memberships: [],
      isLoaded: true,
    });

    render(
      <PlatformGuard>
        <div>Platform Content</div>
      </PlatformGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText("Access Denied")).toBeInTheDocument();
    });

    expect(
      screen.getByText("You do not have an active platform membership."),
    ).toBeInTheDocument();
    expect(screen.getByText("Back to Home")).toBeInTheDocument();
    expect(screen.queryByText("Platform Content")).not.toBeInTheDocument();
  });

  it("shows Pending Review message for pending_approval membership", () => {
    const pendingMembership = createMockMembership({ status: "pending_approval" });

    useMembershipStore.setState({
      memberships: [pendingMembership],
      isLoaded: true,
    });

    render(
      <PlatformGuard>
        <div>Platform Content</div>
      </PlatformGuard>,
    );

    expect(screen.getByText("Pending Review")).toBeInTheDocument();
    expect(
      screen.getByText(/pending document review/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Platform Content")).not.toBeInTheDocument();
  });
});
