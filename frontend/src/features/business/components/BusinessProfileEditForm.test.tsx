import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { BusinessAccountWithPerms } from "@/types/organization";

const mockUpdateProfileMutateAsync = vi.fn();
const mockUpdateAccountMutateAsync = vi.fn();

vi.mock("@/features/business/hooks/use-business-mutations", () => ({
  useUpdateBusinessProfile: vi.fn(() => ({
    mutateAsync: mockUpdateProfileMutateAsync,
    isPending: false,
  })),
  useUpdateBusiness: vi.fn(() => ({
    mutateAsync: mockUpdateAccountMutateAsync,
    isPending: false,
  })),
}));

vi.mock("@/hooks/use-city-data", () => ({
  useCitiesForCountry: vi.fn(() => ["New York", "San Francisco"]),
}));

vi.mock("@/features/explore/hooks/use-explore-queries", () => ({
  useTagSuggestions: vi.fn(() => ({ data: [] })),
}));

import { renderWithProviders } from "@/test/utils";

// =============================================================================
// TEST DATA
// =============================================================================

function createMockBusiness(
  overrides: Partial<BusinessAccountWithPerms> = {},
  profileOverrides: Partial<BusinessAccountWithPerms["profile"]> = {},
): BusinessAccountWithPerms {
  return {
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
      social_links: {},
      tags: [],
      is_public: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      ...profileOverrides,
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
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
  mockUpdateProfileMutateAsync.mockResolvedValue({});
  mockUpdateAccountMutateAsync.mockResolvedValue({});
});

describe("BusinessProfileEditForm", () => {
  async function renderForm(business?: BusinessAccountWithPerms) {
    const { BusinessProfileEditForm } = await import("./BusinessProfileEditForm");
    return renderWithProviders(
      <BusinessProfileEditForm business={business ?? createMockBusiness()} />,
    );
  }

  it("renders all form sections", async () => {
    await renderForm();

    expect(screen.getByText("Images")).toBeInTheDocument();
    expect(screen.getByText("Basic Information")).toBeInTheDocument();
    expect(screen.getByText("Visibility")).toBeInTheDocument();
    expect(screen.getByText("Business Details")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    expect(screen.getByText("Contact Information")).toBeInTheDocument();
    expect(screen.getByText("Add tags to help people discover your business.")).toBeInTheDocument();
    // Social Links appears in both card header and SocialLinksEditor label
    expect(screen.getAllByText("Social Links").length).toBeGreaterThanOrEqual(1);
  });

  it("renders country name as read-only in Location card", async () => {
    await renderForm();

    expect(screen.getByText("United States")).toBeInTheDocument();
  });

  it("renders city combobox in Location card", async () => {
    await renderForm();

    expect(screen.getByText("City")).toBeInTheDocument();
  });

  it("renders display name field with current value", async () => {
    await renderForm();

    expect(screen.getByLabelText("Display name")).toHaveValue("Acme Corporation");
  });

  it("renders tagline field with current value", async () => {
    await renderForm();

    expect(screen.getByLabelText("Tagline")).toHaveValue("Building the future");
  });

  it("renders Save Changes button", async () => {
    await renderForm();

    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("fires only profile mutation when only profile fields changed", async () => {
    const user = userEvent.setup();
    await renderForm();

    const displayNameInput = screen.getByLabelText("Display name");
    await user.clear(displayNameInput);
    await user.type(displayNameInput, "New Name");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockUpdateProfileMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ display_name: "New Name" }),
      );
      expect(mockUpdateAccountMutateAsync).not.toHaveBeenCalled();
    });
  });

  it("fires only account mutation when only city changed", async () => {
    const user = userEvent.setup();
    const business = createMockBusiness({ city: "" });
    await renderForm(business);

    // City combobox is the third combobox (after Company size and City)
    // Company size shows "51-200 employees", City shows "Select city..."
    const comboboxes = screen.getAllByRole("combobox");
    const cityButton = comboboxes.find((el) => el.textContent?.includes("Select city"));
    expect(cityButton).toBeDefined();
    await user.click(cityButton!);
    const sfOption = await screen.findByRole("option", { name: /San Francisco/i });
    await user.click(sfOption);

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockUpdateAccountMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ city: "San Francisco" }),
      );
      expect(mockUpdateProfileMutateAsync).not.toHaveBeenCalled();
    });
  });

  it("fires both mutations when both profile and account fields changed", async () => {
    const user = userEvent.setup();
    const business = createMockBusiness({ city: "" });
    await renderForm(business);

    // Change display name (profile-level)
    const displayNameInput = screen.getByLabelText("Display name");
    await user.clear(displayNameInput);
    await user.type(displayNameInput, "New Name");

    // Change city (account-level)
    const comboboxes = screen.getAllByRole("combobox");
    const cityButton = comboboxes.find((el) => el.textContent?.includes("Select city"));
    expect(cityButton).toBeDefined();
    await user.click(cityButton!);
    const sfOption = await screen.findByRole("option", { name: /San Francisco/i });
    await user.click(sfOption);

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockUpdateProfileMutateAsync).toHaveBeenCalled();
      expect(mockUpdateAccountMutateAsync).toHaveBeenCalled();
    });
  });

  it("renders tags section", async () => {
    await renderForm();

    expect(screen.getByText("Add tags to help people discover your business.")).toBeInTheDocument();
  });

  it("shows industry field with current value", async () => {
    await renderForm();

    expect(screen.getByLabelText("Industry")).toHaveValue("Technology");
  });

  it("shows contact fields with current values", async () => {
    await renderForm();

    expect(screen.getByLabelText("Website")).toHaveValue("https://acme.com");
    expect(screen.getByLabelText("Contact email")).toHaveValue("info@acme.com");
    expect(screen.getByLabelText("Contact phone")).toHaveValue("+1234567890");
  });
});
