import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { ConnectButton } from "../ConnectButton";
import type { ActiveTransactionSummary } from "@/types/organization";

// Mock auth store
vi.mock("@/stores/auth-store", () => ({
  useIsAuthenticated: vi.fn(() => true),
}));

// Mock network mutations
const mockConnectMutate = vi.fn();
const mockDisconnectMutate = vi.fn();
vi.mock("@/features/network/hooks/use-network-mutations", () => ({
  useConnectUser: () => ({
    mutate: mockConnectMutate,
    isPending: false,
  }),
  useDisconnectUser: () => ({
    mutate: mockDisconnectMutate,
    isPending: false,
  }),
}));

// Mock transaction mutations
const mockCancelMutate = vi.fn();
const mockAcceptMutate = vi.fn();
const mockDenyMutate = vi.fn();
vi.mock("@/features/transactions/hooks/use-transaction-mutations", () => ({
  useCancelTransaction: () => ({
    mutate: mockCancelMutate,
    isPending: false,
  }),
  useAcceptTransaction: () => ({
    mutate: mockAcceptMutate,
    isPending: false,
  }),
  useDenyTransaction: () => ({
    mutate: mockDenyMutate,
    isPending: false,
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ConnectButton", () => {
  it("renders Connect button when no connection", () => {
    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus={null}
        connectionId={null}
        activeConnectionTransaction={null}
      />,
    );

    expect(screen.getByRole("button", { name: "Connect" })).toBeInTheDocument();
  });

  it("opens dialog with note field when clicking Connect", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus={null}
        connectionId={null}
        activeConnectionTransaction={null}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Connect" }));
    expect(screen.getByText("Send Connection Request")).toBeInTheDocument();
    expect(screen.getByText("Note (optional)")).toBeInTheDocument();
  });

  it("renders Cancel Request when pending as initiator", () => {
    const pendingTxn: ActiveTransactionSummary = {
      id: "txn-1",
      type: "user_connection_request",
      status: "pending",
      mode: "request",
      viewer_role: "initiator",
    };

    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus={null}
        connectionId={null}
        activeConnectionTransaction={pendingTxn}
      />,
    );

    expect(screen.getByRole("button", { name: "Cancel Request" })).toBeInTheDocument();
  });

  it("renders Accept and Decline when pending as target", () => {
    const pendingTxn: ActiveTransactionSummary = {
      id: "txn-1",
      type: "user_connection_request",
      status: "pending",
      mode: "request",
      viewer_role: "target",
    };

    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus={null}
        connectionId={null}
        activeConnectionTransaction={pendingTxn}
      />,
    );

    expect(screen.getByRole("button", { name: /Accept/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Decline/i })).toBeInTheDocument();
  });

  it("calls accept mutation when clicking Accept", async () => {
    const user = userEvent.setup();
    const pendingTxn: ActiveTransactionSummary = {
      id: "txn-1",
      type: "user_connection_request",
      status: "pending",
      mode: "request",
      viewer_role: "target",
    };

    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus={null}
        connectionId={null}
        activeConnectionTransaction={pendingTxn}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Accept/i }));
    expect(mockAcceptMutate).toHaveBeenCalledWith(
      { transactionId: "txn-1" },
      expect.any(Object),
    );
  });

  it("renders Connected button when actively connected", () => {
    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus="active"
        connectionId="conn-1"
        activeConnectionTransaction={null}
      />,
    );

    expect(screen.getByRole("button", { name: "Connected" })).toBeInTheDocument();
  });

  it("shows Disconnect text on hover of Connected button", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus="active"
        connectionId="conn-1"
        activeConnectionTransaction={null}
      />,
    );

    const btn = screen.getByRole("button", { name: "Connected" });
    await user.hover(btn);
    expect(btn).toHaveTextContent("Disconnect");
  });

  it("returns null when not authenticated", async () => {
    const { useIsAuthenticated } = await import("@/stores/auth-store") as any;
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    const { container } = renderWithProviders(
      <ConnectButton
        targetUserId="user-1"
        targetUsername="jane"
        connectionStatus={null}
        connectionId={null}
        activeConnectionTransaction={null}
      />,
    );

    expect(container.innerHTML).toBe("");

    // Restore
    vi.mocked(useIsAuthenticated).mockReturnValue(true);
  });
});
