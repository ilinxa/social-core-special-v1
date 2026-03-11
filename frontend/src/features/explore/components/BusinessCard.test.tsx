import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";

import { renderWithProviders } from "@/test/utils";
import type { ExploreBusiness } from "@/types/explore";
import { BusinessCard } from "./BusinessCard";

const baseBusiness: ExploreBusiness = {
  id: "biz-1",
  slug: "acme-corp",
  legal_name: "ACME Corporation",
  country: "US",
  city: "New York",
  business_type: "llc",
  is_platform_branch: false,
  open_member_request: false,
  is_verified: false,
  profile: {
    display_name: "ACME Corp",
    tagline: "Building the future",
    logo: null,
    industry: "Technology",
    company_size: "11-50",
    tags: ["saas", "tech", "ai", "startup"],
    website: "https://acme.com",
  },
  search_rank: 0.95,
};

describe("BusinessCard", () => {
  it("renders business name and tagline", () => {
    renderWithProviders(<BusinessCard business={baseBusiness} />);

    expect(screen.getByText("ACME Corp")).toBeInTheDocument();
    expect(screen.getByText("Building the future")).toBeInTheDocument();
  });

  it("links to /business/[slug]", () => {
    renderWithProviders(<BusinessCard business={baseBusiness} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/business/acme-corp");
  });

  it("shows verified badge when verified", () => {
    renderWithProviders(<BusinessCard business={{ ...baseBusiness, is_verified: true }} />);

    expect(screen.getByLabelText("Verified")).toBeInTheDocument();
  });

  it("does not show verified badge when not verified", () => {
    renderWithProviders(<BusinessCard business={baseBusiness} />);

    expect(screen.queryByLabelText("Verified")).not.toBeInTheDocument();
  });

  it("renders tags with overflow indicator", () => {
    renderWithProviders(<BusinessCard business={baseBusiness} />);

    expect(screen.getByText("saas")).toBeInTheDocument();
    expect(screen.getByText("tech")).toBeInTheDocument();
    expect(screen.getByText("ai")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("renders location", () => {
    renderWithProviders(<BusinessCard business={baseBusiness} />);

    expect(screen.getByText("New York, US")).toBeInTheDocument();
  });

  it("renders industry", () => {
    renderWithProviders(<BusinessCard business={baseBusiness} />);

    expect(screen.getByText("Technology")).toBeInTheDocument();
  });
});
