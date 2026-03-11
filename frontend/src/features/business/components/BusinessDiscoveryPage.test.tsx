import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";

import type { BusinessAccountWithRelationship } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ slug: "acme" })),
}));

vi.mock("@/features/business/hooks/use-business-queries", () => ({
  useBusiness: vi.fn(),
}));

vi.mock("@/features/business/components/BusinessProfileView", () => ({
  BusinessProfileView: () => <div data-testid="profile-view">Profile View</div>,
  BusinessProfileSkeleton: () => <div data-testid="profile-skeleton">Skeleton</div>,
}));

vi.mock("@/features/business/components/RequestToJoinButton", () => ({
  RequestToJoinButton: () => <div data-testid="request-to-join">Request Button</div>,
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { renderWithProviders } from "@/test/utils";
import { useBusiness } from "@/features/business/hooks/use-business-queries";

// =============================================================================
// TEST DATA
// =============================================================================

const mockBusiness: BusinessAccountWithRelationship = {
  id: "biz-1",
  slug: "acme",
  legal_name: "Acme Corp",
  registration_number: "",
  tax_id: "",
  country: "US",
  city: "",
  legal_address: "",
  business_type: "llc",
  is_platform_branch: false,
  max_members: 6,
  open_member_request: false,
  business_type_display: "LLC",
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
    social_links: { twitter: "https://twitter.com/acme" },
    tags: [],
    is_public: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_view: true,
    can_edit: true,
    can_edit_profile: true,
    can_delete: false,
    can_change_slug: false,
    can_archive: false,
  },
};

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
});

describe("BusinessDiscoveryPage", () => {
  async function renderComponent() {
    const { BusinessDiscoveryPage } = await import("./BusinessDiscoveryPage");
    return renderWithProviders(<BusinessDiscoveryPage />);
  }

  it("shows skeleton while loading", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByTestId("profile-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows 'Business not found' when error occurs", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Not found"),
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByText("Business not found")).toBeInTheDocument();
    expect(
      screen.getByText("This business profile may not exist or is not accessible."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows 'Business not found' when data is undefined and not loading", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByText("Business not found")).toBeInTheDocument();
  });

  it("shows 'Private profile' when business is not public", async () => {
    const privateBusiness: BusinessAccountWithRelationship = {
      ...mockBusiness,
      profile: {
        ...mockBusiness.profile,
        is_public: false,
      },
    };

    vi.mocked(useBusiness).mockReturnValue({
      data: privateBusiness,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByText("Private profile")).toBeInTheDocument();
    expect(screen.getByText("This business profile is not public.")).toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows BusinessProfileView and RequestToJoinButton when business is public", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: mockBusiness,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByTestId("profile-view")).toBeInTheDocument();
    expect(screen.getByTestId("request-to-join")).toBeInTheDocument();
    expect(screen.queryByText("Business not found")).not.toBeInTheDocument();
    expect(screen.queryByText("Private profile")).not.toBeInTheDocument();
  });

  it("renders RequestToJoinButton without waiting for memberships", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: mockBusiness,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    // RequestToJoinButton is immediately rendered (no membershipsReady gate)
    expect(screen.getByTestId("request-to-join")).toBeInTheDocument();
  });
});
