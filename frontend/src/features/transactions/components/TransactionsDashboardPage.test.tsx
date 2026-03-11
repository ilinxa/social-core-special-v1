import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ slug: "test-biz" }),
}));

vi.mock("@/stores/membership-store", () => ({
  useBusinessMemberships: () => [
    {
      account_id: "biz-id-1",
      account_slug: "test-biz",
      account_type: "business",
      permissions: ["can_configure_transactions"],
    },
  ],
  usePlatformMembership: () => ({
    account_id: "plat-id-1",
    account_type: "platform",
    permissions: ["can_configure_transactions"],
  }),
}));

vi.mock("@/hooks/use-has-permission", () => ({
  useHasPermission: () => true,
}));

import {
  BusinessTransactionsDashboardPage,
  PlatformTransactionsDashboardPage,
} from "./TransactionsDashboardPage";

describe("BusinessTransactionsDashboardPage", () => {
  it("renders transaction dashboard cards", () => {
    render(<BusinessTransactionsDashboardPage />);
    expect(screen.getByText("Transactions")).toBeInTheDocument();
    expect(screen.getByText("Requests")).toBeInTheDocument();
    expect(screen.getByText("Invitations")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });
});

describe("PlatformTransactionsDashboardPage", () => {
  it("renders transaction dashboard cards", () => {
    render(<PlatformTransactionsDashboardPage />);
    expect(screen.getByText("Transactions")).toBeInTheDocument();
    expect(screen.getByText("Requests")).toBeInTheDocument();
    expect(screen.getByText("Invitations")).toBeInTheDocument();
  });
});
