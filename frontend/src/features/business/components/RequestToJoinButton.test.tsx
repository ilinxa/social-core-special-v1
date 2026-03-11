import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { BusinessAccountWithRelationship } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

const mockCreateMutate = vi.fn();
const mockCancelMutate = vi.fn();
const mockInvalidateQueries = vi.fn();

vi.mock("@/stores/auth-store", () => ({
  useIsAuthenticated: vi.fn(() => true),
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQueryClient: vi.fn(() => ({
      invalidateQueries: mockInvalidateQueries,
    })),
  };
});

vi.mock("@/features/transactions/hooks/use-transaction-mutations", () => ({
  useCreateRequest: vi.fn(() => ({
    mutate: mockCreateMutate,
    isPending: false,
  })),
  useCancelTransaction: vi.fn(() => ({
    mutate: mockCancelMutate,
    isPending: false,
  })),
}));

vi.mock("@/features/transactions/api/transactions-api", () => ({
  checkRequestFormApi: vi.fn(() =>
    Promise.resolve({ form_required: false }),
  ),
  submitRequestFormResponseApi: vi.fn(() =>
    Promise.resolve({ form_response_id: "resp-1" }),
  ),
}));

vi.mock("@/features/transactions/components/RequestWithFormDialog", () => ({
  RequestWithFormDialog: vi.fn(() => null),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { renderWithProviders } from "@/test/utils";
import { useIsAuthenticated } from "@/stores/auth-store";
import {
  useCreateRequest,
  useCancelTransaction,
} from "@/features/transactions/hooks/use-transaction-mutations";
import {
  checkRequestFormApi,
} from "@/features/transactions/api/transactions-api";
import { toast } from "sonner";
import { RequestToJoinButton } from "./RequestToJoinButton";

// =============================================================================
// TEST DATA
// =============================================================================

const mockBusiness: BusinessAccountWithRelationship = {
  id: "biz-123",
  slug: "acme",
  legal_name: "Acme Corp",
  registration_number: "",
  tax_id: "",
  country: "US",
  city: "",
  legal_address: "",
  business_type: "llc",
  business_type_display: "LLC",
  is_platform_branch: false,
  max_members: 6,
  open_member_request: true,
  status: "active",
  status_display: "Active",
  verification_status: "verified",
  verification_status_display: "Verified",
  verified_at: "2026-01-01T00:00:00Z",
  settings: {},
  profile: {
    display_name: "Acme Corporation",
    tagline: "Building the future",
    description: "A great company",
    logo: null,
    cover_image: null,
    website: "https://acme.com",
    contact_email: "info@acme.com",
    contact_phone: "+1234567890",
    industry: "Technology",
    company_size: "51-200",
    founded_year: 2020,
    social_links: {},
    tags: [],
    is_public: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_view: true,
    can_edit: false,
    can_edit_profile: false,
    can_delete: false,
    can_change_slug: false,
    can_archive: false,
  },
  _relationship: {
    membership_status: null,
    active_transaction: null,
  },
};

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useIsAuthenticated).mockReturnValue(true);
  vi.mocked(useCreateRequest).mockReturnValue({
    mutate: mockCreateMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useCreateRequest>);
  vi.mocked(useCancelTransaction).mockReturnValue({
    mutate: mockCancelMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useCancelTransaction>);
  vi.mocked(checkRequestFormApi).mockResolvedValue({ form_required: false });
});

describe("RequestToJoinButton", () => {
  it("renders 'Request to Join' when no active transaction and no membership", () => {
    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    expect(screen.getByRole("button", { name: "Request to Join" })).toBeInTheDocument();
  });

  it("returns null when not authenticated", () => {
    vi.mocked(useIsAuthenticated).mockReturnValue(false);

    const { container } = renderWithProviders(
      <RequestToJoinButton business={mockBusiness} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("returns null when open_member_request is false", () => {
    const closedBusiness = { ...mockBusiness, open_member_request: false };

    const { container } = renderWithProviders(
      <RequestToJoinButton business={closedBusiness} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("returns null when user has active membership", () => {
    const memberBusiness: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: "active",
        active_transaction: null,
      },
    };

    const { container } = renderWithProviders(
      <RequestToJoinButton business={memberBusiness} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("returns null when user has pending_approval membership", () => {
    const pendingBusiness: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: "pending_approval",
        active_transaction: null,
      },
    };

    const { container } = renderWithProviders(
      <RequestToJoinButton business={pendingBusiness} />,
    );

    expect(container.innerHTML).toBe("");
  });

  // =========================================================================
  // No form required — direct request
  // =========================================================================

  it("checks for form mapping then creates request directly when no form required", async () => {
    const user = userEvent.setup();

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    await user.click(screen.getByRole("button", { name: "Request to Join" }));

    await waitFor(() => {
      expect(checkRequestFormApi).toHaveBeenCalledWith({
        transaction_type: "business_membership_request",
        account_type: "business",
        account_id: "biz-123",
      });
    });

    await waitFor(() => {
      expect(mockCreateMutate).toHaveBeenCalledTimes(1);
    });

    expect(mockCreateMutate.mock.calls[0][0]).toEqual({
      transaction_type: "business_membership_request",
      target_account_type: "business",
      target_account_id: "biz-123",
      form_response_id: undefined,
    });
  });

  it("shows success toast on successful request", async () => {
    const user = userEvent.setup();
    mockCreateMutate.mockImplementation((_data: unknown, options: { onSuccess?: () => void }) => {
      options.onSuccess?.();
    });

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    await user.click(screen.getByRole("button", { name: "Request to Join" }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Request sent", {
        description: "Your membership request has been submitted.",
      });
    });
  });

  it("invalidates business detail query on successful request", async () => {
    const user = userEvent.setup();
    mockCreateMutate.mockImplementation((_data: unknown, options: { onSuccess?: () => void }) => {
      options.onSuccess?.();
    });

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    await user.click(screen.getByRole("button", { name: "Request to Join" }));

    await waitFor(() => {
      expect(mockInvalidateQueries).toHaveBeenCalledWith({
        queryKey: ["business", "detail", "acme"],
      });
    });
  });

  it("shows error toast on failed request", async () => {
    const user = userEvent.setup();
    mockCreateMutate.mockImplementation(
      (_data: unknown, options: { onError?: (error: Error) => void }) => {
        options.onError?.(new Error("Quota exceeded"));
      },
    );

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    await user.click(screen.getByRole("button", { name: "Request to Join" }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Request failed", {
        description: "Quota exceeded",
      });
    });
  });

  it("disables button and shows 'Sending...' while pending", () => {
    vi.mocked(useCreateRequest).mockReturnValue({
      mutate: mockCreateMutate,
      isPending: true,
    } as unknown as ReturnType<typeof useCreateRequest>);

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    const button = screen.getByRole("button", { name: "Sending..." });
    expect(button).toBeDisabled();
  });

  // =========================================================================
  // Form required — opens dialog
  // =========================================================================

  it("opens form dialog when form mapping exists", async () => {
    const user = userEvent.setup();
    vi.mocked(checkRequestFormApi).mockResolvedValue({
      form_required: true,
      form_mapping_id: "mapping-1",
      form_template: {
        id: "tmpl-1",
        name: "Application Form",
        fields: [],
      },
    });

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    await user.click(screen.getByRole("button", { name: "Request to Join" }));

    await waitFor(() => {
      expect(checkRequestFormApi).toHaveBeenCalled();
    });

    expect(mockCreateMutate).not.toHaveBeenCalled();
  });

  it("falls back to direct request when form check fails", async () => {
    const user = userEvent.setup();
    vi.mocked(checkRequestFormApi).mockRejectedValue(new Error("Network error"));

    renderWithProviders(<RequestToJoinButton business={mockBusiness} />);

    await user.click(screen.getByRole("button", { name: "Request to Join" }));

    await waitFor(() => {
      expect(mockCreateMutate).toHaveBeenCalledTimes(1);
    });
  });

  // =========================================================================
  // Pending request — shows Cancel button (from _relationship)
  // =========================================================================

  it("shows 'Cancel Request' when _relationship has an active request", () => {
    const businessWithRequest: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: null,
        active_transaction: {
          id: "txn-abc",
          type: "business_membership_request",
          status: "pending",
          mode: "request",
        },
      },
    };

    renderWithProviders(<RequestToJoinButton business={businessWithRequest} />);

    expect(screen.getByRole("button", { name: "Cancel Request" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request to Join" })).not.toBeInTheDocument();
  });

  it("calls cancel mutation with transaction ID from _relationship", async () => {
    const user = userEvent.setup();
    const businessWithRequest: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: null,
        active_transaction: {
          id: "txn-abc",
          type: "business_membership_request",
          status: "pending",
          mode: "request",
        },
      },
    };

    renderWithProviders(<RequestToJoinButton business={businessWithRequest} />);

    await user.click(screen.getByRole("button", { name: "Cancel Request" }));

    expect(mockCancelMutate).toHaveBeenCalledTimes(1);
    expect(mockCancelMutate.mock.calls[0][0]).toEqual({
      transactionId: "txn-abc",
    });
  });

  it("shows success toast on successful cancel", async () => {
    const user = userEvent.setup();
    const businessWithRequest: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: null,
        active_transaction: {
          id: "txn-abc",
          type: "business_membership_request",
          status: "pending",
          mode: "request",
        },
      },
    };
    mockCancelMutate.mockImplementation((_data: unknown, options: { onSuccess?: () => void }) => {
      options.onSuccess?.();
    });

    renderWithProviders(<RequestToJoinButton business={businessWithRequest} />);

    await user.click(screen.getByRole("button", { name: "Cancel Request" }));

    expect(toast.success).toHaveBeenCalledWith("Request cancelled", {
      description: "Your membership request has been cancelled.",
    });
  });

  it("disables cancel button and shows 'Cancelling...' while pending", () => {
    const businessWithRequest: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: null,
        active_transaction: {
          id: "txn-abc",
          type: "business_membership_request",
          status: "pending",
          mode: "request",
        },
      },
    };
    vi.mocked(useCancelTransaction).mockReturnValue({
      mutate: mockCancelMutate,
      isPending: true,
    } as unknown as ReturnType<typeof useCancelTransaction>);

    renderWithProviders(<RequestToJoinButton business={businessWithRequest} />);

    const button = screen.getByRole("button", { name: "Cancelling..." });
    expect(button).toBeDisabled();
  });

  // =========================================================================
  // Pending invitation — shows informational message
  // =========================================================================

  it("shows 'Pending Invitation' when _relationship has an active invitation", () => {
    const businessWithInvitation: BusinessAccountWithRelationship = {
      ...mockBusiness,
      _relationship: {
        membership_status: null,
        active_transaction: {
          id: "txn-def",
          type: "business_membership_invitation",
          status: "pending",
          mode: "invitation",
        },
      },
    };

    renderWithProviders(<RequestToJoinButton business={businessWithInvitation} />);

    expect(screen.getByRole("button", { name: "Pending Invitation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pending Invitation" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Request to Join" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel Request" })).not.toBeInTheDocument();
  });
});
