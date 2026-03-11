import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => ({ slug: "test-biz" }),
}));

const mockBusinessMemberships = vi.fn();
const mockPlatformMembership = vi.fn();

vi.mock("@/stores/membership-store", () => ({
  useBusinessMemberships: () => mockBusinessMemberships(),
  usePlatformMembership: () => mockPlatformMembership(),
  useMembershipStore: { getState: () => ({ setMemberships: vi.fn() }) },
}));

vi.mock("@/features/auth/api/membership-api", () => ({
  fetchMyMembershipsApi: vi.fn().mockResolvedValue([]),
}));

// Mock the OwnershipTransferDialog to isolate SettingsPage tests
vi.mock("@/features/members/components/OwnershipTransferDialog", () => ({
  OwnershipTransferDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="transfer-dialog">Transfer Dialog</div> : null,
}));

// Mock ConfirmActionDialog to isolate
vi.mock("@/components/common/ConfirmActionDialog", () => ({
  ConfirmActionDialog: ({
    open,
    title,
    onConfirm,
    isLoading,
  }: {
    open: boolean;
    title: string;
    onConfirm: () => void;
    isLoading?: boolean;
  }) =>
    open ? (
      <div data-testid="leave-dialog">
        <span>{title}</span>
        <button onClick={onConfirm} disabled={isLoading}>
          Confirm Leave
        </button>
      </div>
    ) : null,
}));

const mockMutate = vi.fn();
vi.mock("@/features/members/hooks/use-member-mutations", () => ({
  useLeaveMember: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

vi.mock("@/features/business/hooks/use-business-mutations", () => ({
  useArchiveBusiness: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteBusiness: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/features/business/hooks/use-business-queries", () => ({
  useBusiness: () => ({ data: undefined }),
}));

vi.mock("@/features/business/components/VerificationSection", () => ({
  VerificationSection: () => null,
}));

import { BusinessSettingsPage, PlatformSettingsPage } from "./SettingsPage";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("BusinessSettingsPage", () => {
  it("renders settings heading", () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: false },
    ]);

    renderWithProviders(<BusinessSettingsPage />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("shows danger zone for owner", () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: true },
    ]);

    renderWithProviders(<BusinessSettingsPage />);
    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
    expect(screen.getByText("Transfer Ownership")).toBeInTheDocument();
  });

  it("hides danger zone for non-owner", () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: false },
    ]);

    renderWithProviders(<BusinessSettingsPage />);
    expect(screen.queryByText("Danger Zone")).not.toBeInTheDocument();
    expect(screen.queryByText("Transfer Ownership")).not.toBeInTheDocument();
  });

  it("opens transfer dialog when Transfer button clicked", async () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: true },
    ]);

    renderWithProviders(<BusinessSettingsPage />);

    expect(screen.queryByTestId("transfer-dialog")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Transfer" }));

    expect(screen.getByTestId("transfer-dialog")).toBeInTheDocument();
  });

  it("shows leave section for non-owner member", () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: false },
    ]);

    renderWithProviders(<BusinessSettingsPage />);
    expect(screen.getByText("Membership")).toBeInTheDocument();
    expect(screen.getByText("Leave business")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Leave" })).toBeInTheDocument();
  });

  it("hides leave section for owner", () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: true },
    ]);

    renderWithProviders(<BusinessSettingsPage />);
    expect(screen.queryByText("Leave business")).not.toBeInTheDocument();
  });

  it("opens leave confirmation dialog when Leave button clicked", async () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: false },
    ]);

    renderWithProviders(<BusinessSettingsPage />);

    expect(screen.queryByTestId("leave-dialog")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Leave" }));

    expect(screen.getByTestId("leave-dialog")).toBeInTheDocument();
    expect(screen.getByText("Leave business?")).toBeInTheDocument();
  });

  it("calls leaveMutation.mutate when confirmed", async () => {
    mockBusinessMemberships.mockReturnValue([
      { account_id: "biz-1", account_slug: "test-biz", is_owner: false },
    ]);

    renderWithProviders(<BusinessSettingsPage />);

    await userEvent.click(screen.getByRole("button", { name: "Leave" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm Leave" }));

    expect(mockMutate).toHaveBeenCalledTimes(1);
  });
});

describe("PlatformSettingsPage", () => {
  it("shows danger zone for platform owner", () => {
    mockPlatformMembership.mockReturnValue({
      account_id: "plat-1",
      is_owner: true,
    });

    renderWithProviders(<PlatformSettingsPage />);
    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
    expect(screen.getByText("Transfer Ownership")).toBeInTheDocument();
  });

  it("hides danger zone for non-owner", () => {
    mockPlatformMembership.mockReturnValue({
      account_id: "plat-1",
      is_owner: false,
    });

    renderWithProviders(<PlatformSettingsPage />);
    expect(screen.queryByText("Danger Zone")).not.toBeInTheDocument();
  });

  it("shows leave section for platform non-owner", () => {
    mockPlatformMembership.mockReturnValue({
      account_id: "plat-1",
      is_owner: false,
    });

    renderWithProviders(<PlatformSettingsPage />);
    expect(screen.getByText("Leave platform")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Leave" })).toBeInTheDocument();
  });

  it("hides leave section for platform owner", () => {
    mockPlatformMembership.mockReturnValue({
      account_id: "plat-1",
      is_owner: true,
    });

    renderWithProviders(<PlatformSettingsPage />);
    expect(screen.queryByText("Leave platform")).not.toBeInTheDocument();
  });
});
