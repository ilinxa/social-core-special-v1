import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { ActionButtons } from "./ActionButtons";
import type { TransactionPermissions } from "@/types/transactions";

const allPermissions: TransactionPermissions = {
  can_accept: true,
  can_approve: true,
  can_deny: true,
  can_cancel: true,
  can_dismiss: true,
  can_request_info: true,
  can_resubmit: true,
  can_view_form: true,
};

const noPermissions: TransactionPermissions = {
  can_accept: false,
  can_approve: false,
  can_deny: false,
  can_cancel: false,
  can_dismiss: false,
  can_request_info: false,
  can_resubmit: false,
  can_view_form: false,
};

describe("ActionButtons", () => {
  it("renders all buttons when all permissions granted", () => {
    render(<ActionButtons permissions={allPermissions} />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deny" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dismiss" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request Info" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resubmit" })).toBeInTheDocument();
  });

  it("renders no buttons when no permissions", () => {
    render(<ActionButtons permissions={noPermissions} />);
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Deny" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("calls onApprove when Approve clicked", async () => {
    const handleApprove = vi.fn();
    render(
      <ActionButtons
        permissions={allPermissions}
        onApprove={handleApprove}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(handleApprove).toHaveBeenCalledOnce();
  });

  it("calls onAccept when Accept clicked", async () => {
    const handleAccept = vi.fn();
    render(
      <ActionButtons
        permissions={allPermissions}
        onAccept={handleAccept}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(handleAccept).toHaveBeenCalledOnce();
  });

  it("calls onDismiss when Dismiss clicked", async () => {
    const handleDismiss = vi.fn();
    render(
      <ActionButtons
        permissions={allPermissions}
        onDismiss={handleDismiss}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(handleDismiss).toHaveBeenCalledOnce();
  });

  it("calls onRequestInfo when Request Info clicked", async () => {
    const handleRequestInfo = vi.fn();
    render(
      <ActionButtons
        permissions={allPermissions}
        onRequestInfo={handleRequestInfo}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Request Info" }));
    expect(handleRequestInfo).toHaveBeenCalledOnce();
  });

  it("calls onResubmit when Resubmit clicked", async () => {
    const handleResubmit = vi.fn();
    render(
      <ActionButtons
        permissions={allPermissions}
        onResubmit={handleResubmit}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Resubmit" }));
    expect(handleResubmit).toHaveBeenCalledOnce();
  });

  it("only renders buttons for granted permissions", () => {
    const partial: TransactionPermissions = {
      ...noPermissions,
      can_accept: true,
      can_deny: true,
    };
    render(<ActionButtons permissions={partial} />);

    expect(screen.getByRole("button", { name: "Accept" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deny" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Dismiss" })).not.toBeInTheDocument();
  });

  it("disables buttons when isLoading", () => {
    render(
      <ActionButtons permissions={allPermissions} isLoading />,
    );
    expect(screen.getByRole("button", { name: "Accept" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Deny" })).toBeDisabled();
  });
});
