import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";

import { renderWithProviders } from "@/test/utils";
import type { BusinessAccountWithPerms } from "@/types/organization";

import { BusinessProfileView } from "./BusinessProfileView";

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
      social_links: { twitter: "https://twitter.com/acme" },
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

describe("BusinessProfileView", () => {
  it("renders display_name when present", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByRole("heading", { name: "Acme Corporation", level: 2 })).toBeInTheDocument();
  });

  it("falls back to legal_name when display_name is empty", () => {
    const business = createMockBusiness({}, { display_name: "" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByRole("heading", { name: "Acme Corp", level: 2 })).toBeInTheDocument();
  });

  it("renders tagline", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Building the future")).toBeInTheDocument();
  });

  it("renders description in About card", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("A great company")).toBeInTheDocument();
  });

  it("does not render About card when description is empty", () => {
    const business = createMockBusiness({}, { description: "" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByText("About")).not.toBeInTheDocument();
  });

  it("renders industry in Details card", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Details")).toBeInTheDocument();
    expect(screen.getByText("Technology")).toBeInTheDocument();
  });

  it("renders company_size with employee label in Details card", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("51-200 employees")).toBeInTheDocument();
  });

  it("renders website link in Contact card", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Contact")).toBeInTheDocument();
    const websiteText = screen.getByText("https://acme.com");
    const websiteLink = websiteText.closest("a");
    expect(websiteLink).toHaveAttribute("href", "https://acme.com");
    expect(websiteLink).toHaveAttribute("target", "_blank");
  });

  it("renders email link in Contact card", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    const emailLink = screen.getByRole("link", { name: /info@acme\.com/i });
    expect(emailLink).toHaveAttribute("href", "mailto:info@acme.com");
  });

  it("renders phone in Contact card", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("+1234567890")).toBeInTheDocument();
  });

  it("does not render Contact card when no contact info is present", () => {
    const business = createMockBusiness(
      {},
      { website: "", contact_email: "", contact_phone: "" },
    );

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByText("Contact")).not.toBeInTheDocument();
  });

  it("renders social links", () => {
    const business = createMockBusiness();

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Social Links")).toBeInTheDocument();
    const twitterLink = screen.getByRole("link", { name: /twitter/i });
    expect(twitterLink).toHaveAttribute("href", "https://twitter.com/acme");
    expect(twitterLink).toHaveAttribute("target", "_blank");
  });

  it("does not render Social Links card when social_links is empty", () => {
    const business = createMockBusiness({}, { social_links: {} });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByText("Social Links")).not.toBeInTheDocument();
  });

  it("shows Private badge when is_public is false", () => {
    const business = createMockBusiness({}, { is_public: false });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Private")).toBeInTheDocument();
  });

  it("does not show Private badge when is_public is true", () => {
    const business = createMockBusiness({}, { is_public: true });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByText("Private")).not.toBeInTheDocument();
  });

  it("shows Verified badge when verification_status is verified", () => {
    const business = createMockBusiness({ verification_status: "verified" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("does not show Verified badge when verification_status is not verified", () => {
    const business = createMockBusiness({ verification_status: "pending" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByText("Verified")).not.toBeInTheDocument();
  });

  it("shows cover image when present", () => {
    const business = createMockBusiness(
      {},
      { cover_image: "https://example.com/cover.jpg" },
    );

    renderWithProviders(<BusinessProfileView business={business} />);

    const img = screen.getByAltText("Acme Corporation cover");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/cover.jpg");
  });

  it("does not show cover image when not present", () => {
    const business = createMockBusiness({}, { cover_image: null });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByAltText(/cover/i)).not.toBeInTheDocument();
  });

  it("renders founded year when present", () => {
    const business = createMockBusiness({}, { founded_year: 2020 });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("2020")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    const business = createMockBusiness({ status_display: "Active" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders business type in Details card", () => {
    const business = createMockBusiness({ business_type_display: "LLC" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("LLC")).toBeInTheDocument();
  });

  it("renders location when country and city are set", () => {
    const business = createMockBusiness({ country: "US", city: "San Francisco" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("San Francisco, United States")).toBeInTheDocument();
  });

  it("renders country only when city is empty", () => {
    const business = createMockBusiness({ country: "US", city: "" });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("United States")).toBeInTheDocument();
  });

  it("renders tags when present", () => {
    const business = createMockBusiness({}, { tags: ["technology", "saas"] });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.getByText("technology")).toBeInTheDocument();
    expect(screen.getByText("saas")).toBeInTheDocument();
  });

  it("does not render Tags card when tags are empty", () => {
    const business = createMockBusiness({}, { tags: [] });

    renderWithProviders(<BusinessProfileView business={business} />);

    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
  });
});
