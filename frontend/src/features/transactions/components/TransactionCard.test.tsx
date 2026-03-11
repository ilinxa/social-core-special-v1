import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { TransactionCard } from "./TransactionCard";
import type { TransactionListItem } from "@/types/transactions";

const mockTransaction: TransactionListItem = {
  id: "txn-1",
  transaction_type: "business_membership_invitation",
  mode: "invitation",
  status: "pending",
  category: "membership",
  initiator_name: "Alice",
  target_name: "Bob",
  context_type: "business",
  context_id: "biz-1",
  expires_at: null,
  created_at: "2026-01-15T10:00:00Z",
};

describe("TransactionCard", () => {
  it("renders initiator and target names", () => {
    render(<TransactionCard transaction={mockTransaction} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("renders category badge", () => {
    render(<TransactionCard transaction={mockTransaction} />);
    expect(screen.getByText("Membership")).toBeInTheDocument();
  });

  it("renders mode", () => {
    render(<TransactionCard transaction={mockTransaction} />);
    expect(screen.getByText("invitation")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<TransactionCard transaction={mockTransaction} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("renders date", () => {
    render(<TransactionCard transaction={mockTransaction} />);
    expect(screen.getByText(/2026/)).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const handleClick = vi.fn();
    render(
      <TransactionCard transaction={mockTransaction} onClick={handleClick} />,
    );

    // Click the main card area (the inner button, not action buttons)
    const buttons = screen.getAllByRole("button");
    await userEvent.click(buttons[0]);
    expect(handleClick).toHaveBeenCalledOnce();
  });

  // =========================================================================
  // Cancel button
  // =========================================================================

  it("shows cancel button for pending transactions when onCancel is provided", () => {
    const handleCancel = vi.fn();
    render(
      <TransactionCard
        transaction={mockTransaction}
        onCancel={handleCancel}
      />,
    );
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("does not show cancel button for accepted transactions", () => {
    const handleCancel = vi.fn();
    render(
      <TransactionCard
        transaction={{ ...mockTransaction, status: "accepted" }}
        onCancel={handleCancel}
      />,
    );
    expect(screen.queryByText("Cancel")).not.toBeInTheDocument();
  });

  it("does not show cancel button when onCancel is not provided", () => {
    render(<TransactionCard transaction={mockTransaction} />);
    expect(screen.queryByText("Cancel")).not.toBeInTheDocument();
  });

  it("shows confirmation dialog and calls onCancel", async () => {
    const user = userEvent.setup();
    const handleCancel = vi.fn();
    render(
      <TransactionCard
        transaction={mockTransaction}
        onCancel={handleCancel}
      />,
    );

    await user.click(screen.getByText("Cancel"));

    // Confirmation dialog should appear
    expect(screen.getByText(/Are you sure you want to cancel this transaction/)).toBeInTheDocument();

    // Confirm the cancel — the confirm button label inside dialog is "Cancel"
    const dialogButtons = screen.getAllByRole("button", { name: /^Cancel$/i });
    // The last "Cancel" button is the confirm action in the dialog
    await user.click(dialogButtons[dialogButtons.length - 1]);
    expect(handleCancel).toHaveBeenCalledWith("txn-1");
  });

  // =========================================================================
  // Accept button
  // =========================================================================

  it("shows accept button for pending transactions when onAccept is provided", () => {
    render(
      <TransactionCard
        transaction={mockTransaction}
        onAccept={vi.fn()}
      />,
    );
    expect(screen.getByText("Accept")).toBeInTheDocument();
  });

  it("does not show accept button for non-pending transactions", () => {
    render(
      <TransactionCard
        transaction={{ ...mockTransaction, status: "accepted" }}
        onAccept={vi.fn()}
      />,
    );
    expect(screen.queryByText("Accept")).not.toBeInTheDocument();
  });

  it("calls onAccept with transaction id when accept is clicked", async () => {
    const user = userEvent.setup();
    const handleAccept = vi.fn();
    render(
      <TransactionCard
        transaction={mockTransaction}
        onAccept={handleAccept}
      />,
    );

    await user.click(screen.getByText("Accept"));
    expect(handleAccept).toHaveBeenCalledWith("txn-1");
  });

  // =========================================================================
  // Deny button
  // =========================================================================

  it("shows deny button for pending transactions when onDeny is provided", () => {
    render(
      <TransactionCard
        transaction={mockTransaction}
        onDeny={vi.fn()}
      />,
    );
    expect(screen.getByText("Deny")).toBeInTheDocument();
  });

  it("does not show deny button for non-pending transactions", () => {
    render(
      <TransactionCard
        transaction={{ ...mockTransaction, status: "denied" }}
        onDeny={vi.fn()}
      />,
    );
    expect(screen.queryByText("Deny")).not.toBeInTheDocument();
  });

  it("shows deny confirmation dialog with reason field", async () => {
    const user = userEvent.setup();
    const handleDeny = vi.fn();
    render(
      <TransactionCard
        transaction={mockTransaction}
        onDeny={handleDeny}
      />,
    );

    await user.click(screen.getByText("Deny"));

    // Dialog should appear
    expect(screen.getByText("Deny Request")).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to deny this request/)).toBeInTheDocument();

    // Should have a reason field
    expect(screen.getByLabelText(/Reason/)).toBeInTheDocument();
  });

  it("calls onDeny with transaction id and reason when confirmed", async () => {
    const user = userEvent.setup();
    const handleDeny = vi.fn();
    render(
      <TransactionCard
        transaction={mockTransaction}
        onDeny={handleDeny}
      />,
    );

    await user.click(screen.getByText("Deny"));
    await user.type(screen.getByLabelText(/Reason/), "Not eligible");

    // Click the confirm "Deny" button in the dialog
    const denyButtons = screen.getAllByRole("button", { name: /^Deny$/i });
    await user.click(denyButtons[denyButtons.length - 1]);

    expect(handleDeny).toHaveBeenCalledWith("txn-1", "Not eligible");
  });

  // =========================================================================
  // Both accept and deny together
  // =========================================================================

  it("shows both accept and deny buttons when both callbacks provided", () => {
    render(
      <TransactionCard
        transaction={mockTransaction}
        onAccept={vi.fn()}
        onDeny={vi.fn()}
      />,
    );
    expect(screen.getByText("Accept")).toBeInTheDocument();
    expect(screen.getByText("Deny")).toBeInTheDocument();
  });

  it("disables action buttons when isActioning is true", () => {
    render(
      <TransactionCard
        transaction={mockTransaction}
        onAccept={vi.fn()}
        onDeny={vi.fn()}
        isActioning
      />,
    );
    expect(screen.getByText("Accept")).toBeDisabled();
    expect(screen.getByText("Deny")).toBeDisabled();
  });
});
