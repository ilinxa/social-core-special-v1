import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { MemberProfile } from "./MemberProfile";
import type { MemberDetail } from "@/types/members";

const mockMember: MemberDetail = {
  id: "mem-1",
  user: {
    id: "user-1",
    email: "alice@example.com",
    username: "alice",
    display_name: "Alice Smith",
    avatar_url: null,
  },
  account_type: "business",
  account_id: "acc-1",
  role: {
    id: "role-1",
    name: "Admin",
    account_type: "business",
    account_id: "acc-1",
    level: 2,
    is_system_role: true,
    description: "",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  is_owner: false,
  status: "active",
  joined_at: "2026-01-15T00:00:00Z",
  status_changed_at: null,
  status_reason: "",
  created_at: "2026-01-15T00:00:00Z",
  updated_at: "2026-01-15T00:00:00Z",
};

describe("MemberProfile", () => {
  it("renders user display name", () => {
    render(<MemberProfile member={mockMember} />);

    expect(screen.getByText("Alice Smith")).toBeInTheDocument();
  });

  it("renders user email", () => {
    render(<MemberProfile member={mockMember} />);

    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("renders username", () => {
    render(<MemberProfile member={mockMember} />);

    expect(screen.getByText("@alice")).toBeInTheDocument();
  });

  it("renders role name and level", () => {
    render(<MemberProfile member={mockMember} />);

    expect(screen.getByText("Admin")).toBeInTheDocument();
    expect(screen.getByText("(Level 2)")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<MemberProfile member={mockMember} />);

    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders owner badge when is_owner", () => {
    render(<MemberProfile member={{ ...mockMember, is_owner: true }} />);

    expect(screen.getByText("Owner")).toBeInTheDocument();
  });

  it("renders status reason when present", () => {
    render(
      <MemberProfile
        member={{
          ...mockMember,
          status: "suspended",
          status_reason: "Policy violation",
          status_changed_at: "2026-02-01T00:00:00Z",
        }}
      />,
    );

    expect(screen.getByText("Policy violation")).toBeInTheDocument();
  });

  it("renders initials for avatar fallback", () => {
    render(<MemberProfile member={mockMember} />);

    expect(screen.getByText("AS")).toBeInTheDocument();
  });
});
