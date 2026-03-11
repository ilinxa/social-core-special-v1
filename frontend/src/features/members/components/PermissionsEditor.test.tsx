import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { PermissionsEditor } from "./PermissionsEditor";
import type { Permission, RolePermission } from "@/types/members";

const mockPermissions: Permission[] = [
  {
    id: "perm-1",
    code: "can_manage_members",
    name: "Manage Members",
    description: "Can manage team members",
    category: "member_management",
    applicable_scopes: ["business", "platform"],
  },
  {
    id: "perm-2",
    code: "can_view_members",
    name: "View Members",
    description: "Can view member list",
    category: "member_management",
    applicable_scopes: ["business"],
  },
  {
    id: "perm-3",
    code: "can_create_form",
    name: "Create Forms",
    description: "Can create form templates",
    category: "forms",
    applicable_scopes: ["business"],
  },
];

const mockRolePermissions: RolePermission[] = [
  {
    id: "rp-1",
    permission: mockPermissions[0],
    scope: "business",
  },
];

describe("PermissionsEditor", () => {
  const defaultProps = {
    allPermissions: mockPermissions,
    rolePermissions: mockRolePermissions,
    canModify: true,
    onAdd: vi.fn(),
    onRemove: vi.fn(),
  };

  it("renders permissions grouped by category", () => {
    render(<PermissionsEditor {...defaultProps} />);

    expect(screen.getByText("member management")).toBeInTheDocument();
    expect(screen.getByText("forms")).toBeInTheDocument();
  });

  it("renders permission names", () => {
    render(<PermissionsEditor {...defaultProps} />);

    expect(screen.getByText("Manage Members")).toBeInTheDocument();
    expect(screen.getByText("View Members")).toBeInTheDocument();
    expect(screen.getByText("Create Forms")).toBeInTheDocument();
  });

  it("shows assigned permissions as checked", () => {
    render(<PermissionsEditor {...defaultProps} />);

    // "Manage Members" (perm-1) is assigned
    const manageSwitch = screen.getByRole("switch", { name: /Manage Members/i });
    expect(manageSwitch).toBeChecked();

    // Others are not
    const viewSwitch = screen.getByRole("switch", { name: /View Members/i });
    expect(viewSwitch).not.toBeChecked();

    const formSwitch = screen.getByRole("switch", { name: /Create Forms/i });
    expect(formSwitch).not.toBeChecked();
  });

  it("calls onAdd when toggling unassigned permission", async () => {
    const onAdd = vi.fn();
    const user = userEvent.setup();

    render(<PermissionsEditor {...defaultProps} onAdd={onAdd} />);

    const viewSwitch = screen.getByRole("switch", { name: /View Members/i });
    await user.click(viewSwitch);

    expect(onAdd).toHaveBeenCalledWith("perm-2", "business");
  });

  it("calls onRemove when toggling assigned permission", async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();

    render(<PermissionsEditor {...defaultProps} onRemove={onRemove} />);

    const manageSwitch = screen.getByRole("switch", { name: /Manage Members/i });
    await user.click(manageSwitch);

    expect(onRemove).toHaveBeenCalledWith("perm-1");
  });

  it("filters permissions by search", async () => {
    const user = userEvent.setup();

    render(<PermissionsEditor {...defaultProps} />);

    await user.type(screen.getByPlaceholderText("Search permissions..."), "form");

    expect(screen.getByText("Create Forms")).toBeInTheDocument();
    expect(screen.queryByText("Manage Members")).not.toBeInTheDocument();
  });

  it("shows empty message when no results", async () => {
    const user = userEvent.setup();

    render(<PermissionsEditor {...defaultProps} />);

    await user.type(screen.getByPlaceholderText("Search permissions..."), "zzz");

    expect(screen.getByText("No permissions match your search.")).toBeInTheDocument();
  });

  it("disables switches when canModify is false", () => {
    render(<PermissionsEditor {...defaultProps} canModify={false} />);

    const switches = screen.getAllByRole("switch");
    switches.forEach((s) => expect(s).toBeDisabled());
  });
});
