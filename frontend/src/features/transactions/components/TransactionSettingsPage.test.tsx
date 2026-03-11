import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";

// =============================================================================
// MOCKS
// =============================================================================

const mockUseHasPermission = vi.fn();
vi.mock("@/hooks/use-has-permission", () => ({
  useHasPermission: (...args: unknown[]) => mockUseHasPermission(...args),
}));

const mockUseBusiness = vi.fn();
const mockUsePlatformAccount = vi.fn();
const mockUpdateBusinessApi = vi.fn();
const mockUpdatePlatformSettingsApi = vi.fn();

vi.mock("@/features/business/hooks/use-business-queries", () => ({
  useBusiness: (...args: unknown[]) => mockUseBusiness(...args),
}));

vi.mock("@/features/platform/hooks/use-platform-queries", () => ({
  usePlatformAccount: () => mockUsePlatformAccount(),
}));

vi.mock("@/features/business/api/business-api", () => ({
  updateBusinessApi: (...args: unknown[]) => mockUpdateBusinessApi(...args),
}));

vi.mock("@/features/platform/api/platform-api", () => ({
  updatePlatformSettingsApi: (...args: unknown[]) => mockUpdatePlatformSettingsApi(...args),
}));

vi.mock("@/features/transactions/hooks/use-transaction-queries", () => ({
  useTransactionTypes: () => ({ data: [], isLoading: false }),
  useFormMappings: () => ({ data: [], isLoading: false }),
}));

vi.mock("@/features/transactions/hooks/use-transaction-mutations", () => ({
  useCreateFormMapping: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteFormMapping: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/features/forms/hooks/use-form-queries", () => ({
  useTemplateList: () => ({ data: { results: [] } }),
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { TransactionSettingsPage } from "./TransactionSettingsPage";

// =============================================================================
// HELPERS
// =============================================================================

function renderPage(props: {
  accountType: "business" | "platform";
  accountId?: string;
  slug?: string;
  maxMembers?: number;
}) {
  return render(
    <TransactionSettingsPage
      accountType={props.accountType}
      accountId={props.accountId ?? "acc-1"}
      slug={props.slug}
      maxMembers={props.maxMembers}
    />,
    { wrapper: createWrapper() },
  );
}

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
  mockUseHasPermission.mockReturnValue(true);
  mockUseBusiness.mockReturnValue({
    data: { open_member_request: false },
    refetch: vi.fn(),
  });
  mockUsePlatformAccount.mockReturnValue({
    data: { open_member_request: false },
    refetch: vi.fn(),
  });
  mockUpdateBusinessApi.mockResolvedValue({});
  mockUpdatePlatformSettingsApi.mockResolvedValue({});
});

describe("MemberRequestToggle", () => {
  it("shows toggle when maxMembers > 1 and slug is provided", () => {
    renderPage({ accountType: "business", slug: "test-biz", maxMembers: 6 });

    expect(screen.getByText("Membership Requests")).toBeInTheDocument();
    expect(screen.getByText("Accept membership requests")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "Toggle membership requests" })).toBeInTheDocument();
  });

  it("shows toggle when maxMembers is 0 (unlimited)", () => {
    renderPage({ accountType: "business", slug: "test-biz", maxMembers: 0 });

    expect(screen.getByText("Membership Requests")).toBeInTheDocument();
  });

  it("hides toggle when maxMembers is 1 (owner-only)", () => {
    renderPage({ accountType: "business", slug: "test-biz", maxMembers: 1 });

    expect(screen.queryByText("Membership Requests")).not.toBeInTheDocument();
  });

  it("hides toggle when slug is not provided", () => {
    renderPage({ accountType: "business", maxMembers: 6 });

    expect(screen.queryByText("Membership Requests")).not.toBeInTheDocument();
  });

  it("switch reflects current open_member_request state (off)", () => {
    mockUseBusiness.mockReturnValue({
      data: { open_member_request: false },
      refetch: vi.fn(),
    });

    renderPage({ accountType: "business", slug: "test-biz", maxMembers: 6 });

    const toggle = screen.getByRole("switch", { name: "Toggle membership requests" });
    expect(toggle).not.toBeChecked();
  });

  it("switch reflects current open_member_request state (on)", () => {
    mockUseBusiness.mockReturnValue({
      data: { open_member_request: true },
      refetch: vi.fn(),
    });

    renderPage({ accountType: "business", slug: "test-biz", maxMembers: 6 });

    const toggle = screen.getByRole("switch", { name: "Toggle membership requests" });
    expect(toggle).toBeChecked();
  });

  it("calls updateBusinessApi when business toggle is clicked", async () => {
    const refetch = vi.fn();
    mockUseBusiness.mockReturnValue({
      data: { open_member_request: false },
      refetch,
    });
    mockUpdateBusinessApi.mockResolvedValue({});

    renderPage({ accountType: "business", slug: "test-biz", maxMembers: 6 });

    const toggle = screen.getByRole("switch", { name: "Toggle membership requests" });
    await userEvent.click(toggle);

    expect(mockUpdateBusinessApi).toHaveBeenCalledWith("test-biz", {
      open_member_request: true,
    });
  });

  it("calls updatePlatformSettingsApi when platform toggle is clicked", async () => {
    const refetch = vi.fn();
    mockUsePlatformAccount.mockReturnValue({
      data: { open_member_request: false },
      refetch,
    });
    mockUpdatePlatformSettingsApi.mockResolvedValue({});

    renderPage({ accountType: "platform", slug: "platform", maxMembers: 5 });

    const toggle = screen.getByRole("switch", { name: "Toggle membership requests" });
    await userEvent.click(toggle);

    expect(mockUpdatePlatformSettingsApi).toHaveBeenCalledWith({
      open_member_request: true,
    });
  });
});

describe("TransactionSettingsPage", () => {
  it("renders heading", () => {
    renderPage({ accountType: "business" });

    expect(screen.getByText("Transaction Settings")).toBeInTheDocument();
  });

  it("shows empty state when no configurable types", () => {
    renderPage({ accountType: "business" });

    expect(
      screen.getByText("No configurable transaction types available."),
    ).toBeInTheDocument();
  });

  it("shows access denied when user lacks can_configure_transactions", () => {
    mockUseHasPermission.mockReturnValue(false);

    renderPage({ accountType: "business" });

    expect(screen.getByText("Transaction Settings")).toBeInTheDocument();
    expect(
      screen.getByText("You do not have permission to configure transaction settings."),
    ).toBeInTheDocument();
    // Should NOT show the settings content
    expect(
      screen.queryByText("No configurable transaction types available."),
    ).not.toBeInTheDocument();
  });

  it("checks can_configure_transactions with correct account context", () => {
    renderPage({ accountType: "business", accountId: "biz-123" });

    expect(mockUseHasPermission).toHaveBeenCalledWith(
      "can_configure_transactions",
      "business",
      "biz-123",
    );
  });
});
