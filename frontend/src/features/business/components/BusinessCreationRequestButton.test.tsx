import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { useAuthStore } from "@/stores/auth-store";
import { renderWithProviders } from "@/test/utils";
import { BusinessCreationRequestButton } from "./BusinessCreationRequestButton";

// =============================================================================
// MOCKS
// =============================================================================

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/features/transactions/api/transactions-api", () => ({
  fetchTransactionsApi: vi.fn(),
  checkRequestFormApi: vi.fn(),
  submitRequestFormResponseApi: vi.fn(),
  createRequestApi: vi.fn(),
}));

vi.mock("@/features/platform/api/platform-api", () => ({
  fetchPlatformAccountApi: vi.fn(),
}));

vi.mock("@/features/users/api/users-api", () => ({
  fetchCurrentUserApi: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { fetchTransactionsApi } from "@/features/transactions/api/transactions-api";

const mockFetchTransactions = fetchTransactionsApi as Mock;

// =============================================================================
// HELPERS
// =============================================================================

function makeTransaction(overrides: Record<string, unknown> = {}) {
  return {
    id: "tx-1",
    transaction_type: "business_creation_permission_request",
    mode: "request",
    status: "pending",
    category: "permission",
    initiator_type: "user",
    initiator_id: "user-1",
    initiator_name: "Test User",
    target_type: "account",
    target_id: "plat-1",
    target_name: "Platform",
    context_type: "platform",
    context_id: "plat-1",
    expires_at: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function setUser(canCreateBusiness: boolean) {
  useAuthStore.setState({
    user: {
      id: "user-1",
      email: "test@test.com",
      username: "testuser",
      is_active: true,
      is_verified: true,
      is_complete: true,
      can_create_business: canCreateBusiness,
      is_staff: false,
      is_superuser: false,
      date_joined: "2026-01-01T00:00:00Z",
      last_login: null,
      profile: {
        first_name: "Test",
        last_name: "User",
        full_name: "Test User",
        display_name: "Test User",
        phone: "",
        avatar_url: null,
        has_avatar: false,
        cover_image_url: null,
        has_cover_image: false,
        timezone: "UTC",
        language: "en",
        bio: "",
        country: "",
        city: "",
        tags: [],
        is_public: true,
      },
    },
    isAuthenticated: true,
    isInitialized: true,
  });
}

// =============================================================================
// TESTS
// =============================================================================

describe("BusinessCreationRequestButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: false,
    });
  });

  it("renders nothing when user can create business", () => {
    setUser(true);
    mockFetchTransactions.mockResolvedValue({ count: 0, results: [] });

    const { container } = renderWithProviders(<BusinessCreationRequestButton />);
    // The component renders null when approved, but separator is also part of it
    // With can_create_business=true, state is "approved" → returns null
    expect(container.innerHTML).toBe("");
  });

  it("shows 'Request Business Access' when no prior request exists", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({ count: 0, results: [] });

    renderWithProviders(<BusinessCreationRequestButton />);

    expect(
      await screen.findByText("Request Business Access"),
    ).toBeInTheDocument();
  });

  it("shows 'Request Pending' when an active request exists", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "pending" })],
    });

    renderWithProviders(<BusinessCreationRequestButton />);

    expect(await screen.findByText("Request Pending")).toBeInTheDocument();
    expect(screen.getByText("View")).toBeInTheDocument();
  });

  it("shows 'Action Needed' when info is requested", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "info_requested" })],
    });

    renderWithProviders(<BusinessCreationRequestButton />);

    expect(await screen.findByText("Action Needed")).toBeInTheDocument();
    expect(screen.getByText("Respond")).toBeInTheDocument();
  });

  it("navigates to activity detail when View is clicked", async () => {
    const user = userEvent.setup();
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "pending", id: "tx-123" })],
    });

    renderWithProviders(<BusinessCreationRequestButton />);

    const viewButton = await screen.findByText("View");
    await user.click(viewButton);

    expect(mockPush).toHaveBeenCalledWith("/activity/tx-123");
  });

  it("shows disabled button with cooldown message when in cooldown", async () => {
    setUser(false);
    const recentDate = new Date();
    recentDate.setDate(recentDate.getDate() - 10); // 10 days ago

    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [
        makeTransaction({
          status: "denied",
          created_at: recentDate.toISOString(),
        }),
      ],
    });

    renderWithProviders(<BusinessCreationRequestButton />);

    expect(
      await screen.findByText(/Available in 20 days/),
    ).toBeInTheDocument();
  });

  it("navigates to activity detail when Respond is clicked for info_requested", async () => {
    const user = userEvent.setup();
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "info_requested", id: "tx-456" })],
    });

    renderWithProviders(<BusinessCreationRequestButton />);

    const respondButton = await screen.findByText("Respond");
    await user.click(respondButton);

    expect(mockPush).toHaveBeenCalledWith("/activity/tx-456");
  });
});
