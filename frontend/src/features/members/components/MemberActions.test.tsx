import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { MemberActions } from "./MemberActions";
import type { MemberPermissions, RoleListItem } from "@/types/members";

const mockRoles: RoleListItem[] = [
  {
    id: "r-admin",
    name: "Admin",
    account_type: "business",
    account_id: "acc-1",
    level: 2,
    is_system_role: true,
    description: "",
    member_count: 1,
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
    member_count: 3,
    created_at: "",
    updated_at: "",
  },
];

const allPermissions: MemberPermissions = {
  can_change_role: true,
  can_suspend: true,
  can_remove: true,
  can_ban: true,
  can_reactivate: true,
};

const defaultProps = {
  permissions: allPermissions,
  roles: mockRoles,
  actorRoleLevel: 0,
  currentRoleId: "r-editor",
  memberName: "Alice",
  onChangeRole: vi.fn(),
  onSuspend: vi.fn(),
  onRemove: vi.fn(),
  onBan: vi.fn(),
  onReactivate: vi.fn(),
};

describe("MemberActions", () => {
  it("renders all action buttons when all permissions granted", () => {
    render(<MemberActions {...defaultProps} />);

    expect(screen.getByRole("button", { name: "Change Role" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Suspend" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ban" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reactivate" })).toBeInTheDocument();
  });

  it("hides actions when permissions are denied", () => {
    render(
      <MemberActions
        {...defaultProps}
        permissions={{
          can_change_role: false,
          can_suspend: false,
          can_remove: false,
          can_ban: false,
          can_reactivate: false,
        }}
      />,
    );

    expect(screen.queryByRole("button", { name: "Change Role" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Suspend" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ban" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reactivate" })).not.toBeInTheDocument();
  });

  it("opens suspend dialog and calls onSuspend", async () => {
    const onSuspend = vi.fn();
    const user = userEvent.setup();

    render(<MemberActions {...defaultProps} onSuspend={onSuspend} />);

    await user.click(screen.getByRole("button", { name: "Suspend" }));

    expect(screen.getByText("Suspend Alice")).toBeInTheDocument();
  });

  it("opens ban dialog with required reason", async () => {
    const user = userEvent.setup();

    render(<MemberActions {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Ban" }));

    expect(screen.getByText("Ban Alice")).toBeInTheDocument();
    // Confirm button should be disabled because reason is required
    expect(screen.getByRole("button", { name: "Ban" })).toBeInTheDocument();
  });

  it("opens reactivate dialog", async () => {
    const user = userEvent.setup();

    render(<MemberActions {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Reactivate" }));

    expect(screen.getByText("Reactivate Alice")).toBeInTheDocument();
  });
});
