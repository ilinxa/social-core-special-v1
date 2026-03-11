import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { FollowButton } from "../FollowButton";
import type { ActiveTransactionSummary } from "@/types/organization";

// Mock auth store
vi.mock("@/stores/auth-store", () => ({
  useIsAuthenticated: vi.fn(() => true),
}));

// Mock network mutations
const mockFollowMutate = vi.fn();
const mockUnfollowMutate = vi.fn();
vi.mock("@/features/network/hooks/use-network-mutations", () => ({
  useFollow: () => ({
    mutate: mockFollowMutate,
    isPending: false,
  }),
  useUnfollow: () => ({
    mutate: mockUnfollowMutate,
    isPending: false,
  }),
}));

// Mock transaction mutations
const mockCancelMutate = vi.fn();
vi.mock("@/features/transactions/hooks/use-transaction-mutations", () => ({
  useCancelTransaction: () => ({
    mutate: mockCancelMutate,
    isPending: false,
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FollowButton", () => {
  it("renders Follow button when not following", () => {
    renderWithProviders(
      <FollowButton
        followeeType="business"
        followeeId="biz-1"
        followStatus={null}
        followId={null}
        activeFollowTransaction={null}
      />,
    );

    expect(screen.getByRole("button", { name: "Follow" })).toBeInTheDocument();
  });

  it("calls follow mutation on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <FollowButton
        followeeType="business"
        followeeId="biz-1"
        followStatus={null}
        followId={null}
        activeFollowTransaction={null}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Follow" }));
    expect(mockFollowMutate).toHaveBeenCalledWith(
      { followee_type: "business", followee_id: "biz-1" },
      expect.any(Object),
    );
  });

  it("renders Cancel Request when pending as initiator", () => {
    const pendingTxn: ActiveTransactionSummary = {
      id: "txn-1",
      type: "business_follow_request",
      status: "pending",
      mode: "request",
      viewer_role: "initiator",
    };

    renderWithProviders(
      <FollowButton
        followeeType="business"
        followeeId="biz-1"
        followStatus={null}
        followId={null}
        activeFollowTransaction={pendingTxn}
      />,
    );

    expect(screen.getByRole("button", { name: "Cancel Request" })).toBeInTheDocument();
  });

  it("renders Following button when actively following", () => {
    renderWithProviders(
      <FollowButton
        followeeType="business"
        followeeId="biz-1"
        followStatus="active"
        followId="follow-1"
        activeFollowTransaction={null}
      />,
    );

    expect(screen.getByRole("button", { name: "Following" })).toBeInTheDocument();
  });

  it("returns null when not authenticated", async () => {
    const authModule = await import("@/stores/auth-store") as any;
    vi.mocked(authModule.useIsAuthenticated).mockReturnValue(false);

    const { container } = renderWithProviders(
      <FollowButton
        followeeType="business"
        followeeId="biz-1"
        followStatus={null}
        followId={null}
        activeFollowTransaction={null}
      />,
    );

    expect(container.innerHTML).toBe("");

    // Restore
    vi.mocked(authModule.useIsAuthenticated).mockReturnValue(true);
  });

  it("shows Unfollow text on hover of Following button", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <FollowButton
        followeeType="business"
        followeeId="biz-1"
        followStatus="active"
        followId="follow-1"
        activeFollowTransaction={null}
      />,
    );

    const btn = screen.getByRole("button", { name: "Following" });
    await user.hover(btn);
    expect(btn).toHaveTextContent("Unfollow");
  });
});
