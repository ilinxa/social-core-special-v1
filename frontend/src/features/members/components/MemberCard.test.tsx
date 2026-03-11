import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { MemberCard } from "./MemberCard";
import type { MemberListItem } from "@/types/members";

const mockMember: MemberListItem = {
  id: "mem-1",
  user: {
    id: "user-1",
    email: "alice@example.com",
    username: "alice",
    display_name: "Alice Smith",
    avatar_url: null,
  },
  role_name: "Admin",
  role_level: 2,
  is_owner: false,
  status: "active",
  joined_at: "2026-01-15T00:00:00Z",
};

describe("MemberCard", () => {
  it("renders member name and email", () => {
    render(<MemberCard member={mockMember} />);

    expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("renders role badge", () => {
    render(<MemberCard member={mockMember} />);

    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<MemberCard member={mockMember} />);

    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders owner badge when is_owner is true", () => {
    render(<MemberCard member={{ ...mockMember, is_owner: true }} />);

    expect(screen.getByText("Owner")).toBeInTheDocument();
  });

  it("does not render owner badge when is_owner is false", () => {
    render(<MemberCard member={mockMember} />);

    expect(screen.queryByText("Owner")).not.toBeInTheDocument();
  });

  it("renders initials when no avatar", () => {
    render(<MemberCard member={mockMember} />);

    expect(screen.getByText("AS")).toBeInTheDocument();
  });

  it("falls back to username initials when no display_name", () => {
    const member = {
      ...mockMember,
      user: { ...mockMember.user, display_name: "" },
    };
    render(<MemberCard member={member} />);

    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(<MemberCard member={mockMember} onClick={onClick} />);

    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders suspended status", () => {
    render(
      <MemberCard member={{ ...mockMember, status: "suspended" }} />,
    );

    expect(screen.getByText("Suspended")).toBeInTheDocument();
  });
});
