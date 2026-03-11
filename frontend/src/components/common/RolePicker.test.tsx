import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RolePicker } from "./RolePicker";
import type { RoleListItem } from "@/types/members";

const mockRoles: RoleListItem[] = [
  {
    id: "r-owner",
    name: "Owner",
    account_type: "business",
    account_id: "acc-1",
    level: 0,
    is_system_role: true,
    description: "",
    member_count: 1,
    created_at: "",
    updated_at: "",
  },
  {
    id: "r-admin",
    name: "Admin",
    account_type: "business",
    account_id: "acc-1",
    level: 2,
    is_system_role: true,
    description: "",
    member_count: 3,
    created_at: "",
    updated_at: "",
  },
  {
    id: "r-editor",
    name: "Editor",
    account_type: "business",
    account_id: "acc-1",
    level: 5,
    is_system_role: false,
    description: "",
    member_count: 5,
    created_at: "",
    updated_at: "",
  },
  {
    id: "r-member",
    name: "Base Member",
    account_type: "business",
    account_id: "acc-1",
    level: 10,
    is_system_role: true,
    description: "",
    member_count: 8,
    created_at: "",
    updated_at: "",
  },
];

describe("RolePicker", () => {
  it("renders with label", () => {
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={0}
        value=""
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Role")).toBeInTheDocument();
  });

  it("filters out Owner role (level 0)", async () => {
    const user = userEvent.setup();
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={0}
        value=""
        onChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("combobox"));

    expect(screen.queryByText(/Owner/)).not.toBeInTheDocument();
    expect(screen.getByText(/Admin/)).toBeInTheDocument();
    expect(screen.getByText(/Editor/)).toBeInTheDocument();
    expect(screen.getByText(/Base Member/)).toBeInTheDocument();
  });

  it("filters out roles at or below actor level", async () => {
    const user = userEvent.setup();
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={2}
        value=""
        onChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("combobox"));

    // Admin (level 2) should be filtered out — cannot assign roles at own level
    expect(screen.queryByText(/Admin/)).not.toBeInTheDocument();
    expect(screen.getByText(/Editor/)).toBeInTheDocument();
    expect(screen.getByText(/Base Member/)).toBeInTheDocument();
  });

  it("calls onChange when a role is selected", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={0}
        value=""
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByText(/Editor/));

    expect(onChange).toHaveBeenCalledWith("r-editor");
  });

  it("shows error message when provided", () => {
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={0}
        value=""
        onChange={vi.fn()}
        error="Role is required"
      />,
    );
    expect(screen.getByText("Role is required")).toBeInTheDocument();
  });

  it("supports custom label", () => {
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={0}
        value=""
        onChange={vi.fn()}
        label="Assign Role"
      />,
    );
    expect(screen.getByText("Assign Role")).toBeInTheDocument();
  });

  it("shows required indicator", () => {
    render(
      <RolePicker
        roles={mockRoles}
        actorRoleLevel={0}
        value=""
        onChange={vi.fn()}
        required
      />,
    );
    expect(screen.getByText("Role *")).toBeInTheDocument();
  });
});
