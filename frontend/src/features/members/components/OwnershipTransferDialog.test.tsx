import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";
import { OwnershipTransferDialog } from "./OwnershipTransferDialog";

const mockMutate = vi.hoisted(() => vi.fn());

vi.mock("@/features/members/api/members-api", () => ({
  fetchMembersApi: vi.fn().mockResolvedValue({
    count: 2,
    next: null,
    previous: null,
    results: [
      {
        id: "mem-1",
        user: {
          id: "user-1",
          email: "alice@test.com",
          username: "alice",
          display_name: "Alice Smith",
          avatar_url: null,
        },
        role_name: "Admin",
        role_level: 2,
        is_owner: false,
        status: "active",
        joined_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "mem-owner",
        user: {
          id: "user-owner",
          email: "owner@test.com",
          username: "owner",
          display_name: "Owner User",
          avatar_url: null,
        },
        role_name: "Owner",
        role_level: 0,
        is_owner: true,
        status: "active",
        joined_at: "2026-01-01T00:00:00Z",
      },
    ],
  }),
}));

vi.mock("@/features/transactions/hooks/use-transaction-mutations", () => ({
  useCreateInvitation: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

function renderDialog(props?: { accountType?: "business" | "platform"; accountId?: string }) {
  return render(
    <OwnershipTransferDialog
      open
      onOpenChange={vi.fn()}
      accountType={props?.accountType ?? "business"}
      slug="test-biz"
      accountId={props?.accountId ?? "biz-id-1"}
    />,
    { wrapper: createWrapper() },
  );
}

describe("OwnershipTransferDialog", () => {
  it("renders dialog title", () => {
    renderDialog();
    expect(screen.getByText("Transfer Ownership")).toBeInTheDocument();
  });

  it("shows eligible members (excludes owner)", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });
    // Owner should NOT appear in the list
    expect(screen.queryByText("Owner User")).not.toBeInTheDocument();
  });

  it("advances to confirm step when member selected", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Alice Smith"));

    expect(screen.getByText("Warning")).toBeInTheDocument();
    expect(
      screen.getByText(/You will be demoted to Base Member/),
    ).toBeInTheDocument();
  });

  it("requires confirmation phrase to enable transfer button", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Alice Smith"));

    const transferBtn = screen.getByRole("button", {
      name: "Transfer Ownership",
    });
    expect(transferBtn).toBeDisabled();

    const input = screen.getByPlaceholderText("transfer ownership");
    await userEvent.type(input, "wrong phrase");
    expect(transferBtn).toBeDisabled();

    await userEvent.clear(input);
    await userEvent.type(input, "transfer ownership");
    expect(transferBtn).toBeEnabled();
  });

  it("calls createInvitation with correct args when confirmed", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Alice Smith"));

    const input = screen.getByPlaceholderText("transfer ownership");
    await userEvent.type(input, "transfer ownership");

    await userEvent.click(
      screen.getByRole("button", { name: "Transfer Ownership" }),
    );

    expect(mockMutate).toHaveBeenCalledWith(
      {
        transaction_type: "business_ownership_transfer",
        target_user_id: "user-1",
        context_type: "business",
        context_id: "biz-id-1",
      },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("can go back to member selection", async () => {
    renderDialog();
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Alice Smith"));
    expect(screen.getByText("Warning")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Back" }));

    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });
    expect(screen.queryByText("Warning")).not.toBeInTheDocument();
  });

  it("uses platform_ownership_transfer for platform accounts", async () => {
    renderDialog({ accountType: "platform", accountId: "plat-id-1" });

    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Alice Smith"));

    const input = screen.getByPlaceholderText("transfer ownership");
    await userEvent.type(input, "transfer ownership");

    await userEvent.click(
      screen.getByRole("button", { name: "Transfer Ownership" }),
    );

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        transaction_type: "platform_ownership_transfer",
        context_type: "platform",
        context_id: "plat-id-1",
      }),
      expect.anything(),
    );
  });
});
