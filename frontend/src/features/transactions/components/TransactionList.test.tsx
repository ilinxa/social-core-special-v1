import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { TransactionList } from "./TransactionList";
import type { PaginatedResponse } from "@/types";
import type { TransactionListItem, TransactionListParams } from "@/types/transactions";

const mockItem: TransactionListItem = {
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

const mockData: PaginatedResponse<TransactionListItem> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockItem],
};

const defaultParams: TransactionListParams = {};

describe("TransactionList", () => {
  it("renders title", () => {
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
      />,
    );
    expect(screen.getByText("Transactions")).toBeInTheDocument();
  });

  it("renders custom title", () => {
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
        title="Incoming Requests"
      />,
    );
    expect(screen.getByText("Incoming Requests")).toBeInTheDocument();
  });

  it("shows loading skeletons", () => {
    const { container } = render(
      <TransactionList
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
        isLoading
      />,
    );
    // Skeletons rendered
    const skeletons = container.querySelectorAll('[class*="skeleton" i], [data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty message when no results", () => {
    render(
      <TransactionList
        data={{ count: 0, next: null, previous: null, results: [] }}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
      />,
    );
    expect(screen.getByText("No transactions found.")).toBeInTheDocument();
  });

  it("renders transaction cards", () => {
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
      />,
    );
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("renders status filter tabs", () => {
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pending" })).toBeInTheDocument();
  });

  it("calls onParamsChange when status tab clicked", async () => {
    const handleChange = vi.fn();
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={handleChange}
        onTransactionClick={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Pending" }));
    expect(handleChange).toHaveBeenCalledWith(
      expect.objectContaining({ status: "pending", page: 1 }),
    );
  });

  it("calls onTransactionClick when card clicked", async () => {
    const handleClick = vi.fn();
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={handleClick}
      />,
    );

    // Click the transaction card (the button inside the list)
    const cards = screen.getAllByRole("button");
    // Find the card button (not a filter tab)
    const cardButton = cards.find(
      (btn) => btn.textContent?.includes("Alice"),
    );
    if (cardButton) {
      await userEvent.click(cardButton);
      expect(handleClick).toHaveBeenCalledWith("txn-1");
    }
  });

  it("renders header action", () => {
    render(
      <TransactionList
        data={mockData}
        params={defaultParams}
        onParamsChange={vi.fn()}
        onTransactionClick={vi.fn()}
        headerAction={<button>Create</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument();
  });
});
