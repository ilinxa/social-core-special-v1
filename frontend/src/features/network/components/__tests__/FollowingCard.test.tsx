import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { FollowingCard } from "../FollowingCard";
import type { FollowingItem } from "@/types/network";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockFollowingBusiness: FollowingItem = {
  id: "follow-1",
  followee_type: "business",
  followee_id: "biz-1",
  followee_name: "Acme Corp",
  followee_slug: "acme-corp",
  created_at: "2026-01-15T10:00:00Z",
};

const mockFollowingPlatform: FollowingItem = {
  id: "follow-2",
  followee_type: "platform",
  followee_id: "plat-1",
  followee_name: "Main Platform",
  followee_slug: null,
  created_at: "2026-01-20T10:00:00Z",
};

describe("FollowingCard", () => {
  it("renders business following with name and type badge", () => {
    render(
      <FollowingCard
        item={mockFollowingBusiness}
        onUnfollow={vi.fn()}
      />,
    );

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("business")).toBeInTheDocument();
    expect(screen.getByText(/Following since/)).toBeInTheDocument();
  });

  it("renders platform following with correct type badge", () => {
    render(
      <FollowingCard
        item={mockFollowingPlatform}
        onUnfollow={vi.fn()}
      />,
    );

    expect(screen.getByText("Main Platform")).toBeInTheDocument();
    expect(screen.getByText("platform")).toBeInTheDocument();
  });

  it("links to business profile for business type", () => {
    render(
      <FollowingCard
        item={mockFollowingBusiness}
        onUnfollow={vi.fn()}
      />,
    );

    const link = screen.getByRole("link", { name: "Acme Corp" });
    expect(link).toHaveAttribute("href", "/business/acme-corp");
  });

  it("opens confirm dialog and calls onUnfollow", async () => {
    const handleUnfollow = vi.fn();
    const user = userEvent.setup();

    render(
      <FollowingCard
        item={mockFollowingBusiness}
        onUnfollow={handleUnfollow}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Unfollow" }));

    // Dialog should be visible
    expect(screen.getByText("Unfollow?")).toBeInTheDocument();

    // Click confirm in dialog
    const buttons = screen.getAllByRole("button", { name: /Unfollow/i });
    await user.click(buttons[buttons.length - 1]);

    expect(handleUnfollow).toHaveBeenCalledWith("follow-1");
  });
});
