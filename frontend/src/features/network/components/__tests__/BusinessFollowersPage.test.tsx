import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { BusinessFollowersPage } from "../BusinessFollowersPage";
import type { FollowerItem, NetworkStats } from "@/types/network";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: "test-biz" }),
}));

// Mock membership store
vi.mock("@/stores/membership-store", () => ({
  useBusinessMemberships: () => [
    {
      account_type: "business",
      account_id: "biz-1",
      account_slug: "test-biz",
      status: "active",
      is_owner: true,
      permissions: [{ code: "can_manage_followers" }],
      role: { level: 0 },
    },
  ],
}));

// Mock useHasPermission
vi.mock("@/hooks/use-has-permission", () => ({
  useHasPermission: () => true,
}));

const mockFollowers: FollowerItem[] = [
  {
    id: "f-1",
    follower: {
      id: "u-1",
      username: "jane",
      display_name: "Jane Doe",
      avatar_url: "",
    },
    followee_type: "business",
    followee_id: "biz-1",
    followee_name: "Test Business",
    status: "active",
    created_at: "2026-02-15T10:00:00Z",
  },
];

const mockStats: NetworkStats = {
  followers_count: 1,
  following_count: 0,
  connections_count: 0,
};

// Mock network queries
vi.mock("@/features/network/hooks/use-network-queries", () => ({
  useBusinessFollowers: () => ({
    data: { count: 1, next: null, previous: null, results: mockFollowers },
    isLoading: false,
  }),
  useBusinessNetworkStats: () => ({
    data: mockStats,
  }),
}));

// Mock business query
vi.mock("@/features/business/hooks/use-business-queries", () => ({
  useBusiness: () => ({
    data: {
      id: "biz-1",
      slug: "test-biz",
      _permissions: { can_manage_followers: true },
    },
  }),
}));

// Mock network mutations
vi.mock("@/features/network/hooks/use-network-mutations", () => ({
  useRemoveBusinessFollower: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

describe("BusinessFollowersPage", () => {
  it("renders page header with follower count", () => {
    renderWithProviders(<BusinessFollowersPage />);

    expect(screen.getByText("Followers")).toBeInTheDocument();
    expect(screen.getByText("1 followers")).toBeInTheDocument();
  });

  it("renders follower cards", () => {
    renderWithProviders(<BusinessFollowersPage />);

    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("@jane")).toBeInTheDocument();
  });

  it("shows Remove button when user has permission", () => {
    renderWithProviders(<BusinessFollowersPage />);

    expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();
  });
});
