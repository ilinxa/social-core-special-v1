import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmActionDialog } from "./ConfirmActionDialog";

describe("ConfirmActionDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: "Confirm Action",
    description: "Are you sure you want to proceed?",
    onConfirm: vi.fn(),
  };

  it("renders title and description when open", () => {
    render(<ConfirmActionDialog {...defaultProps} />);
    expect(screen.getByText("Confirm Action")).toBeInTheDocument();
    expect(screen.getByText("Are you sure you want to proceed?")).toBeInTheDocument();
  });

  it("renders confirm and cancel buttons", () => {
    render(<ConfirmActionDialog {...defaultProps} />);
    expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button is clicked", async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(<ConfirmActionDialog {...defaultProps} onConfirm={onConfirm} />);

    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(onConfirm).toHaveBeenCalledWith(undefined);
  });

  it("uses custom confirm label", () => {
    render(<ConfirmActionDialog {...defaultProps} confirmLabel="Delete" />);
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("shows reason field when showReasonField is true", () => {
    render(<ConfirmActionDialog {...defaultProps} showReasonField />);
    expect(screen.getByLabelText(/Reason/)).toBeInTheDocument();
  });

  it("passes reason to onConfirm", async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmActionDialog
        {...defaultProps}
        showReasonField
        onConfirm={onConfirm}
      />,
    );

    await user.type(screen.getByLabelText(/Reason/), "Policy violation");
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(onConfirm).toHaveBeenCalledWith("Policy violation");
  });

  it("disables confirm when reason is required but empty", () => {
    render(
      <ConfirmActionDialog
        {...defaultProps}
        showReasonField
        reasonRequired
      />,
    );
    expect(screen.getByRole("button", { name: "Confirm" })).toBeDisabled();
  });

  it("enables confirm when reason is required and provided", async () => {
    const user = userEvent.setup();
    render(
      <ConfirmActionDialog
        {...defaultProps}
        showReasonField
        reasonRequired
      />,
    );

    await user.type(screen.getByLabelText(/Reason/), "Some reason");
    expect(screen.getByRole("button", { name: "Confirm" })).toBeEnabled();
  });

  it("shows processing text when loading", () => {
    render(<ConfirmActionDialog {...defaultProps} isLoading />);
    expect(screen.getByRole("button", { name: "Processing..." })).toBeDisabled();
  });

  it("uses custom reason label", () => {
    render(
      <ConfirmActionDialog
        {...defaultProps}
        showReasonField
        reasonLabel="Justification"
      />,
    );
    expect(screen.getByLabelText(/Justification/)).toBeInTheDocument();
  });
});
