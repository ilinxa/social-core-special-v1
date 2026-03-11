import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { MyNetworkPage } from "../MyNetworkPage";
import type { UserConnectionItem, FollowingItem, NetworkStats } from "@/types/network";

// Mock network queries
const mockConnections: UserConnectionItem[] = [
  {
    id: "conn-1",
    other_user: {
      id: "u-1",
      username: "alice",
      display_name: "Alice Johnson",
      avatar_url: "",
    },
    note: "Colleague",
    status: "active",
    connected_at: "2026-02-15T10:00:00Z",
    created_at: "2026-02-10T10:00:00Z",
  },
  {
    id: "conn-2",
    other_user: {
      id: "u-2",
      username: "bob",
      display_name: "Bob Smith",
      avatar_url: "",
    },
    note: "",
    status: "active",
    connected_at: "2026-01-20T10:00:00Z",
    created_at: "2026-01-15T10:00:00Z",
  },
];

const mockFollowing: FollowingItem[] = [
  {
    id: "follow-1",
    followee_type: "business",
    followee_id: "biz-1",
    followee_name: "Acme Corp",
    followee_slug: "acme-corp",
    created_at: "2026-01-15T10:00:00Z",
  },
];

const mockStats: NetworkStats = {
  followers_count: 0,
  following_count: 1,
  connections_count: 2,
};

vi.mock("@/features/network/hooks/use-network-queries", () => ({
  useConnections: () => ({
    data: { count: 2, next: null, previous: null, results: mockConnections },
    isLoading: false,
  }),
  useFollowing: () => ({
    data: { count: 1, next: null, previous: null, results: mockFollowing },
    isLoading: false,
  }),
  useNetworkStats: () => ({
    data: mockStats,
  }),
}));

vi.mock("@/features/network/hooks/use-network-mutations", () => ({
  useDisconnectUser: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useUnfollow: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("MyNetworkPage", () => {
  it("renders page header with stats", () => {
    renderWithProviders(<MyNetworkPage />);

    expect(screen.getByText("My Network")).toBeInTheDocument();
    expect(screen.getByText("2 connections")).toBeInTheDocument();
    expect(screen.getByText("1 following")).toBeInTheDocument();
  });

  it("renders connections tab by default with connection cards", () => {
    renderWithProviders(<MyNetworkPage />);

    expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    expect(screen.getByText("Bob Smith")).toBeInTheDocument();
  });

  it("switches to following tab", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MyNetworkPage />);

    await user.click(screen.getByRole("tab", { name: /Following/i }));
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("filters connections by search", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MyNetworkPage />);

    const searchInput = screen.getByPlaceholderText("Search...");
    await user.type(searchInput, "alice");

    expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    expect(screen.queryByText("Bob Smith")).not.toBeInTheDocument();
  });

  it("shows empty state when no search results", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MyNetworkPage />);

    const searchInput = screen.getByPlaceholderText("Search...");
    await user.type(searchInput, "zzzzz");

    expect(screen.getByText("No connections match your search.")).toBeInTheDocument();
  });

  it("shows tab counts in tab labels", () => {
    renderWithProviders(<MyNetworkPage />);

    expect(screen.getByRole("tab", { name: /Connections \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Following \(1\)/i })).toBeInTheDocument();
  });
});
