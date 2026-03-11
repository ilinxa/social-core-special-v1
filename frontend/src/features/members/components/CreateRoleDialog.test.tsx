import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { CreateRoleDialog } from "./CreateRoleDialog";

describe("CreateRoleDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    actorRoleLevel: 0,
    onSubmit: vi.fn(),
  };

  it("renders form fields when open", () => {
    render(<CreateRoleDialog {...defaultProps} />);

    expect(screen.getByLabelText(/Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Level/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
  });

  it("disables submit when name is empty", () => {
    render(<CreateRoleDialog {...defaultProps} />);

    expect(screen.getByRole("button", { name: "Create Role" })).toBeDisabled();
  });

  it("submits with valid data", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();

    render(<CreateRoleDialog {...defaultProps} onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/Name/), "Editor");
    await user.type(screen.getByLabelText(/Level/), "5");
    await user.click(screen.getByRole("button", { name: "Create Role" }));

    expect(onSubmit).toHaveBeenCalledWith({
      name: "Editor",
      level: 5,
      description: undefined,
    });
  });

  it("submits with description", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();

    render(<CreateRoleDialog {...defaultProps} onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/Name/), "Editor");
    await user.type(screen.getByLabelText(/Level/), "5");
    await user.type(screen.getByLabelText(/Description/), "Can edit content");
    await user.click(screen.getByRole("button", { name: "Create Role" }));

    expect(onSubmit).toHaveBeenCalledWith({
      name: "Editor",
      level: 5,
      description: "Can edit content",
    });
  });

  it("shows minimum level hint", () => {
    render(<CreateRoleDialog {...defaultProps} actorRoleLevel={2} />);

    expect(screen.getByText(/Must be greater than 2/)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<CreateRoleDialog {...defaultProps} isLoading />);

    expect(screen.getByRole("button", { name: "Creating..." })).toBeDisabled();
  });

  it("clears form after successful submit", async () => {
    const user = userEvent.setup();

    render(<CreateRoleDialog {...defaultProps} />);

    await user.type(screen.getByLabelText(/Name/), "Editor");
    await user.type(screen.getByLabelText(/Level/), "5");
    await user.click(screen.getByRole("button", { name: "Create Role" }));

    expect(screen.getByLabelText(/Name/)).toHaveValue("");
  });
});
