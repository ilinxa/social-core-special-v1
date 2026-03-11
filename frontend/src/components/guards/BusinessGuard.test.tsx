import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Membership } from "@/types/rbac";
import { useMembershipStore } from "@/stores/membership-store";

import { BusinessGuard } from "./BusinessGuard";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: "acme-corp" }),
}));

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
    id: "m-1",
    account_type: "business",
    account_id: "acc-1",
    account_name: "Acme Corp",
    account_slug: "acme-corp",
    account_max_members: 6,
    role: {
      id: "r-1",
      name: "Member",
      account_type: "business",
      account_id: "acc-1",
      level: 10,
      is_system_role: true,
      description: "Default member role",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    is_owner: false,
    status: "active",
    joined_at: "2026-01-15T00:00:00Z",
    permissions: [{ code: "view_dashboard", scope: "business" }],
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("BusinessGuard", () => {
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
      <BusinessGuard>
        <div>Business Content</div>
      </BusinessGuard>,
    );

    expect(screen.queryByText("Business Content")).not.toBeInTheDocument();
    expect(document.querySelector(".h-64")).toBeInTheDocument();
  });

  it("renders children when user has an active membership matching slug", () => {
    const membership = createMockMembership();

    useMembershipStore.setState({
      memberships: [membership],
      isLoaded: true,
    });

    render(
      <BusinessGuard>
        <div>Business Content</div>
      </BusinessGuard>,
    );

    expect(screen.getByText("Business Content")).toBeInTheDocument();
    expect(mockFetchMyMembershipsApi).not.toHaveBeenCalled();
  });

  it("triggers revalidation when slug is not found in cached memberships", async () => {
    const membership = createMockMembership();
    mockFetchMyMembershipsApi.mockResolvedValue([membership]);

    useMembershipStore.setState({
      memberships: [],
      isLoaded: true,
    });

    render(
      <BusinessGuard>
        <div>Business Content</div>
      </BusinessGuard>,
    );

    expect(mockFetchMyMembershipsApi).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText("Business Content")).toBeInTheDocument();
    });
  });

  it("shows Access Denied after revalidation confirms no membership", async () => {
    mockFetchMyMembershipsApi.mockResolvedValue([]);

    useMembershipStore.setState({
      memberships: [],
      isLoaded: true,
    });

    render(
      <BusinessGuard>
        <div>Business Content</div>
      </BusinessGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText("Access Denied")).toBeInTheDocument();
    });

    expect(
      screen.getByText("You do not have an active membership for this business."),
    ).toBeInTheDocument();
    expect(screen.getByText("Back to Home")).toBeInTheDocument();
    expect(screen.queryByText("Business Content")).not.toBeInTheDocument();
  });

  it("denies access when membership exists but status is not active", async () => {
    const suspendedMembership = createMockMembership({ status: "suspended" });
    mockFetchMyMembershipsApi.mockResolvedValue([suspendedMembership]);

    useMembershipStore.setState({
      memberships: [suspendedMembership],
      isLoaded: true,
    });

    render(
      <BusinessGuard>
        <div>Business Content</div>
      </BusinessGuard>,
    );

    await waitFor(() => {
      expect(screen.getByText("Access Denied")).toBeInTheDocument();
    });

    expect(screen.queryByText("Business Content")).not.toBeInTheDocument();
  });

  it("shows Pending Review message for pending_approval membership", () => {
    const pendingMembership = createMockMembership({ status: "pending_approval" });

    useMembershipStore.setState({
      memberships: [pendingMembership],
      isLoaded: true,
    });

    render(
      <BusinessGuard>
        <div>Business Content</div>
      </BusinessGuard>,
    );

    expect(screen.getByText("Pending Review")).toBeInTheDocument();
    expect(
      screen.getByText(/pending document review/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Business Content")).not.toBeInTheDocument();
  });
});
