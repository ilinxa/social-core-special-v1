import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { RoleCard } from "./RoleCard";
import type { RoleListItem } from "@/types/members";

const mockRole: RoleListItem = {
  id: "role-1",
  name: "Admin",
  account_type: "business",
  account_id: "acc-1",
  level: 2,
  is_system_role: true,
  description: "Full administrative access",
  member_count: 3,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("RoleCard", () => {
  it("renders role name", () => {
    render(<RoleCard role={mockRole} />);

    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders level", () => {
    render(<RoleCard role={mockRole} />);

    expect(screen.getByText("Level 2")).toBeInTheDocument();
  });

  it("renders member count", () => {
    render(<RoleCard role={mockRole} />);

    expect(screen.getByText("3 members")).toBeInTheDocument();
  });

  it("renders singular member count", () => {
    render(<RoleCard role={{ ...mockRole, member_count: 1 }} />);

    expect(screen.getByText("1 member")).toBeInTheDocument();
  });

  it("renders system badge for system roles", () => {
    render(<RoleCard role={mockRole} />);

    expect(screen.getByText("System")).toBeInTheDocument();
  });

  it("does not render system badge for custom roles", () => {
    render(<RoleCard role={{ ...mockRole, is_system_role: false }} />);

    expect(screen.queryByText("System")).not.toBeInTheDocument();
  });

  it("renders description when present", () => {
    render(<RoleCard role={mockRole} />);

    expect(screen.getByText("Full administrative access")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(<RoleCard role={mockRole} onClick={onClick} />);

    await user.click(screen.getByText("Admin"));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
