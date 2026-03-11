import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";

import { renderWithProviders } from "@/test/utils";
import type { PlatformAccountWithPerms } from "@/types/organization";

import { PlatformProfileView } from "./PlatformProfileView";

// =============================================================================
// TEST DATA
// =============================================================================

function createMockPlatform(
  overrides: Partial<PlatformAccountWithPerms> = {},
  profileOverrides: Partial<PlatformAccountWithPerms["profile"]> = {},
): PlatformAccountWithPerms {
  return {
    id: "plat-1",
    is_configured: true,
    max_members: 5,
    open_member_request: false,
    settings: {},
    profile: {
      name: "My Platform",
      tagline: "The best platform",
      description: "Platform description",
      logo: null,
      favicon: null,
      primary_color: "#3B82F6",
      secondary_color: "#10B981",
      contact_email: "admin@platform.com",
      contact_phone: "+1234567890",
      address: "123 Main St",
      social_links: { twitter: "https://twitter.com/platform" },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      ...profileOverrides,
    },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    _permissions: {
      can_view: true,
      can_edit_profile: true,
      can_edit_settings: true,
    },
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("PlatformProfileView", () => {
  it("renders platform name", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByRole("heading", { name: "My Platform", level: 2 })).toBeInTheDocument();
  });

  it("renders tagline", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("The best platform")).toBeInTheDocument();
  });

  it("does not render tagline when empty", () => {
    const account = createMockPlatform({}, { tagline: "" });

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.queryByText("The best platform")).not.toBeInTheDocument();
  });

  it("renders description in About card", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("Platform description")).toBeInTheDocument();
  });

  it("does not render About card when description is empty", () => {
    const account = createMockPlatform({}, { description: "" });

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.queryByText("About")).not.toBeInTheDocument();
  });

  it("renders color swatches for branding", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("Branding")).toBeInTheDocument();
    expect(screen.getByText("Primary color")).toBeInTheDocument();
    expect(screen.getByText("#3B82F6")).toBeInTheDocument();
    expect(screen.getByText("Secondary color")).toBeInTheDocument();
    expect(screen.getByText("#10B981")).toBeInTheDocument();
  });

  it("renders color swatch with correct background color via aria-label", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByLabelText("Primary color: #3B82F6")).toBeInTheDocument();
    expect(screen.getByLabelText("Secondary color: #10B981")).toBeInTheDocument();
  });

  it("does not render Branding card when no colors are set", () => {
    const account = createMockPlatform({}, { primary_color: "", secondary_color: "" });

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.queryByText("Branding")).not.toBeInTheDocument();
  });

  it("renders contact email as link", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("Contact")).toBeInTheDocument();
    const emailLink = screen.getByRole("link", { name: /admin@platform\.com/i });
    expect(emailLink).toHaveAttribute("href", "mailto:admin@platform.com");
  });

  it("renders contact phone", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("+1234567890")).toBeInTheDocument();
  });

  it("renders address", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });

  it("does not render Contact card when no contact info is present", () => {
    const account = createMockPlatform(
      {},
      { contact_email: "", contact_phone: "", address: "" },
    );

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.queryByText("Contact")).not.toBeInTheDocument();
  });

  it("renders social links", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("Social Links")).toBeInTheDocument();
    const twitterLink = screen.getByRole("link", { name: /twitter/i });
    expect(twitterLink).toHaveAttribute("href", "https://twitter.com/platform");
    expect(twitterLink).toHaveAttribute("target", "_blank");
  });

  it("does not render Social Links card when social_links is empty", () => {
    const account = createMockPlatform({}, { social_links: {} });

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.queryByText("Social Links")).not.toBeInTheDocument();
  });

  it("renders avatar fallback with first letter of name", () => {
    const account = createMockPlatform();

    renderWithProviders(<PlatformProfileView account={account} />);

    expect(screen.getByText("M")).toBeInTheDocument();
  });
});
