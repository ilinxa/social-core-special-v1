import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockUseTransactionList = vi.fn();

vi.mock("@/features/transactions/hooks/use-transaction-queries", () => ({
  useTransactionList: (...args: unknown[]) => mockUseTransactionList(...args),
}));

import { UserTransactionsPage } from "./UserTransactionsPage";

function makeTxn(overrides: Record<string, unknown> = {}) {
  return {
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
    created_at: "2026-03-01T10:00:00Z",
    ...overrides,
  };
}

describe("UserTransactionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeletons while fetching", () => {
    mockUseTransactionList.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<UserTransactionsPage />);
    expect(screen.getByText("Activity")).toBeInTheDocument();
    // Should render skeleton elements
    expect(screen.queryByText("No transactions found.")).not.toBeInTheDocument();
  });

  it("renders empty state when no transactions", () => {
    mockUseTransactionList.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
    });

    render(<UserTransactionsPage />);
    expect(screen.getByText("No transactions found.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Invitations and requests you send or receive will appear here.",
      ),
    ).toBeInTheDocument();
  });

  it("groups transactions by category in collapsible cards", () => {
    mockUseTransactionList.mockReturnValue({
      data: {
        results: [
          makeTxn({ id: "t1", category: "membership" }),
          makeTxn({ id: "t2", category: "membership", transaction_type: "business_membership_request", mode: "request" }),
          makeTxn({ id: "t3", category: "ownership", transaction_type: "business_ownership_transfer" }),
        ],
        count: 3,
        next: null,
        previous: null,
      },
      isLoading: false,
    });

    render(<UserTransactionsPage />);
    expect(screen.getByText("Membership")).toBeInTheDocument();
    expect(screen.getByText("Ownership")).toBeInTheDocument();
    // Category counts
    expect(screen.getByText("2")).toBeInTheDocument(); // membership count
    expect(screen.getByText("1")).toBeInTheDocument(); // ownership count
  });

  it("shows pending count badge for categories with pending items", () => {
    mockUseTransactionList.mockReturnValue({
      data: {
        results: [
          makeTxn({ id: "t1", status: "pending" }),
          makeTxn({ id: "t2", status: "accepted" }),
          makeTxn({ id: "t3", status: "info_requested" }),
        ],
        count: 3,
        next: null,
        previous: null,
      },
      isLoading: false,
    });

    render(<UserTransactionsPage />);
    expect(screen.getByText("2 pending")).toBeInTheDocument();
  });

  it("navigates to transaction detail on click", async () => {
    const user = userEvent.setup();
    mockUseTransactionList.mockReturnValue({
      data: {
        results: [makeTxn({ id: "txn-abc" })],
        count: 1,
        next: null,
        previous: null,
      },
      isLoading: false,
    });

    render(<UserTransactionsPage />);
    await user.click(screen.getByText("Alice"));
    expect(mockPush).toHaveBeenCalledWith("/activity/txn-abc");
  });

  it("filters by role tab", async () => {
    const user = userEvent.setup();
    mockUseTransactionList.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
    });

    render(<UserTransactionsPage />);

    // Click "Sent" tab
    await user.click(screen.getByText("Sent"));
    expect(mockUseTransactionList).toHaveBeenCalledWith(
      expect.objectContaining({ role: "initiator" }),
    );

    // Click "Received" tab
    await user.click(screen.getByText("Received"));
    expect(mockUseTransactionList).toHaveBeenCalledWith(
      expect.objectContaining({ role: "target" }),
    );
  });

  it("filters by status", async () => {
    const user = userEvent.setup();
    mockUseTransactionList.mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
    });

    render(<UserTransactionsPage />);

    const select = screen.getByDisplayValue("All Statuses");
    await user.selectOptions(select, "pending");

    expect(mockUseTransactionList).toHaveBeenCalledWith(
      expect.objectContaining({ status: "pending" }),
    );
  });

  it("displays transaction type labels correctly", () => {
    mockUseTransactionList.mockReturnValue({
      data: {
        results: [
          makeTxn({ id: "t1", transaction_type: "business_membership_invitation" }),
          makeTxn({ id: "t2", transaction_type: "business_ownership_transfer", category: "ownership" }),
        ],
        count: 2,
        next: null,
        previous: null,
      },
      isLoading: false,
    });

    render(<UserTransactionsPage />);
    expect(screen.getByText("Membership Invitation")).toBeInTheDocument();
    expect(screen.getByText("Ownership Transfer")).toBeInTheDocument();
  });

  it("does not render categories with zero transactions", () => {
    mockUseTransactionList.mockReturnValue({
      data: {
        results: [makeTxn({ category: "membership" })],
        count: 1,
        next: null,
        previous: null,
      },
      isLoading: false,
    });

    render(<UserTransactionsPage />);
    expect(screen.getByText("Membership")).toBeInTheDocument();
    expect(screen.queryByText("Ownership")).not.toBeInTheDocument();
    expect(screen.queryByText("Verification")).not.toBeInTheDocument();
    expect(screen.queryByText("Social")).not.toBeInTheDocument();
  });
});
