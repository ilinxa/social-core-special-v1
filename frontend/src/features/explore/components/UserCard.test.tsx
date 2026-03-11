import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";

import { renderWithProviders } from "@/test/utils";
import type { ExploreUser } from "@/types/explore";
import { UserCard } from "./UserCard";

const baseUser: ExploreUser = {
  id: "user-1",
  username: "johndoe",
  email: "john@example.com",
  is_verified: false,
  display_name: "John Doe",
  profile: {
    first_name: "John",
    last_name: "Doe",
    bio: "Full-stack developer building web applications",
    avatar_url: null,
    country: "US",
    city: "San Francisco",
    tags: ["developer", "react"],
  },
  search_rank: 0.8,
};

describe("UserCard", () => {
  it("renders display name and username", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("@johndoe")).toBeInTheDocument();
  });

  it("renders bio", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    expect(screen.getByText("Full-stack developer building web applications")).toBeInTheDocument();
  });

  it("links to user profile", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/users/johndoe");
  });

  it("shows verified badge when verified", () => {
    renderWithProviders(<UserCard user={{ ...baseUser, is_verified: true }} />);

    expect(screen.getByLabelText("Verified")).toBeInTheDocument();
  });

  it("does not show verified badge when not verified", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    expect(screen.queryByLabelText("Verified")).not.toBeInTheDocument();
  });

  it("renders location", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    expect(screen.getByText("San Francisco, US")).toBeInTheDocument();
  });

  it("renders tags", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    expect(screen.getByText("developer")).toBeInTheDocument();
    expect(screen.getByText("react")).toBeInTheDocument();
  });

  it("renders avatar initials as fallback", () => {
    renderWithProviders(<UserCard user={baseUser} />);

    expect(screen.getByText("JD")).toBeInTheDocument();
  });
});
