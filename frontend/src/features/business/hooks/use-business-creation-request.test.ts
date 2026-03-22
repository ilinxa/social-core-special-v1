import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { createWrapper } from "@/test/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useBusinessCreationRequest } from "./use-business-creation-request";

// =============================================================================
// MOCKS
// =============================================================================

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

import {
  fetchTransactionsApi,
  checkRequestFormApi,
  submitRequestFormResponseApi,
  createRequestApi,
} from "@/features/transactions/api/transactions-api";
import { fetchPlatformAccountApi } from "@/features/platform/api/platform-api";
import { fetchCurrentUserApi } from "@/features/users/api/users-api";

const mockFetchTransactions = fetchTransactionsApi as Mock;
const mockCheckForm = checkRequestFormApi as Mock;
const mockSubmitForm = submitRequestFormResponseApi as Mock;
const mockCreateRequest = createRequestApi as Mock;
const mockFetchPlatform = fetchPlatformAccountApi as Mock;
const mockFetchUser = fetchCurrentUserApi as Mock;

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

describe("useBusinessCreationRequest", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: false,
    });
  });

  it("returns approved status when user can create business", async () => {
    setUser(true);
    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    // No query should fire, status should be approved immediately
    expect(result.current.state.status).toBe("approved");
    expect(mockFetchTransactions).not.toHaveBeenCalled();
  });

  it("returns loading status while fetching transactions", () => {
    setUser(false);
    mockFetchTransactions.mockReturnValue(new Promise(() => {})); // Never resolves

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    expect(result.current.state.status).toBe("loading");
  });

  it("returns can_request when no transactions exist", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({ count: 0, results: [] });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("can_request");
    });
  });

  it("returns has_pending when an active request exists", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "pending" })],
    });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("has_pending");
      expect(result.current.state.activeTransaction?.id).toBe("tx-1");
    });
  });

  it("returns has_pending for pending_review status", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "pending_review" })],
    });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("has_pending");
    });
  });

  it("returns has_info_requested when info is requested", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "info_requested" })],
    });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("has_info_requested");
      expect(result.current.state.activeTransaction?.id).toBe("tx-1");
    });
  });

  it("returns in_cooldown when denied recently", async () => {
    setUser(false);
    const recentDate = new Date();
    recentDate.setDate(recentDate.getDate() - 5); // 5 days ago

    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [
        makeTransaction({
          status: "denied",
          created_at: recentDate.toISOString(),
        }),
      ],
    });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("in_cooldown");
      expect(result.current.state.cooldownDaysRemaining).toBe(25);
    });
  });

  it("returns can_request when denied long ago (past cooldown)", async () => {
    setUser(false);
    const oldDate = new Date();
    oldDate.setDate(oldDate.getDate() - 45); // 45 days ago

    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [
        makeTransaction({
          status: "denied",
          created_at: oldDate.toISOString(),
        }),
      ],
    });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("can_request");
    });
  });

  it("auto-refreshes user when accepted transaction is detected", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({
      count: 1,
      results: [makeTransaction({ status: "accepted" })],
    });

    const freshUser = {
      ...useAuthStore.getState().user,
      can_create_business: true,
    };
    mockFetchUser.mockResolvedValue(freshUser);

    renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockFetchUser).toHaveBeenCalled();
    });
  });

  it("returns error status when query fails", async () => {
    setUser(false);
    mockFetchTransactions.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("error");
    });
  });

  it("handleRequestClick opens form dialog when form is required", async () => {
    setUser(false);
    mockFetchTransactions.mockResolvedValue({ count: 0, results: [] });
    mockFetchPlatform.mockResolvedValue({ id: "plat-1" });
    mockCheckForm.mockResolvedValue({
      form_required: true,
      form_mapping_id: "mapping-1",
      form_template: {
        id: "tmpl-1",
        name: "Business Creation Form",
        fields: [],
      },
    });

    const { result } = renderHook(() => useBusinessCreationRequest(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("can_request");
    });

    await act(async () => {
      await result.current.handleRequestClick();
    });

    expect(mockFetchPlatform).toHaveBeenCalled();
    expect(mockCheckForm).toHaveBeenCalledWith({
      transaction_type: "business_creation_permission_request",
      account_type: "platform",
      account_id: "plat-1",
    });
    await waitFor(() => {
      expect(result.current.formDialogOpen).toBe(true);
    });
    expect(result.current.formTemplateName).toBe("Business Creation Form");
  });
});
