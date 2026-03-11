import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { BusinessAccountWithPerms } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ slug: "acme" })),
}));

vi.mock("@/features/business/hooks/use-business-queries", () => ({
  useBusiness: vi.fn(),
}));

vi.mock("@/features/business/components/BusinessProfileEditForm", () => ({
  BusinessProfileEditForm: () => <div data-testid="edit-form">Edit Form</div>,
}));

vi.mock("@/features/business/components/BusinessProfileView", () => ({
  BusinessProfileView: () => <div data-testid="profile-view">Profile View</div>,
  BusinessProfileSkeleton: () => <div data-testid="profile-skeleton">Skeleton</div>,
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { renderWithProviders } from "@/test/utils";
import { useBusiness } from "@/features/business/hooks/use-business-queries";

// =============================================================================
// TEST DATA
// =============================================================================

const mockBusiness: BusinessAccountWithPerms = {
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

describe("BusinessConsoleProfilePage", () => {
  async function renderComponent() {
    const { BusinessConsoleProfilePage } = await import("./BusinessConsoleProfilePage");
    return renderWithProviders(<BusinessConsoleProfilePage />);
  }

  it("shows skeleton while loading", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByTestId("profile-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("edit-form")).not.toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows tabs with edit form active by default when can_edit_profile is true", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: mockBusiness,
      isLoading: false,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByRole("tab", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Preview" })).toBeInTheDocument();
    expect(screen.getByTestId("edit-form")).toBeInTheDocument();
    expect(screen.queryByTestId("profile-skeleton")).not.toBeInTheDocument();
  });

  it("switches to preview tab and shows profile view", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: mockBusiness,
      isLoading: false,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: "Preview" }));

    expect(screen.getByTestId("profile-view")).toBeInTheDocument();
  });

  it("shows read-only view without tabs when can_edit_profile is false", async () => {
    const readOnlyBusiness: BusinessAccountWithPerms = {
      ...mockBusiness,
      _permissions: {
        ...mockBusiness._permissions,
        can_edit_profile: false,
      },
    };

    vi.mocked(useBusiness).mockReturnValue({
      data: readOnlyBusiness,
      isLoading: false,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByTestId("profile-view")).toBeInTheDocument();
    expect(screen.queryByTestId("edit-form")).not.toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("renders Profile heading", async () => {
    vi.mocked(useBusiness).mockReturnValue({
      data: mockBusiness,
      isLoading: false,
    } as ReturnType<typeof useBusiness>);

    await renderComponent();

    expect(screen.getByRole("heading", { name: "Profile", level: 1 })).toBeInTheDocument();
  });
});
