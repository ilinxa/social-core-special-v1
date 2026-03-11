import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types";
import { useAuthStore } from "@/stores/auth-store";

import { AdminGuard } from "./AdminGuard";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// =============================================================================
// HELPERS
// =============================================================================

function createMockUser(overrides: Partial<User> = {}): User {
  return {
    id: "u-1",
    email: "test@example.com",
    username: "testuser",
    is_active: true,
    is_verified: true,
    is_complete: true,
    can_create_business: true,
    is_staff: false,
    is_superuser: false,
    date_joined: "2026-01-01T00:00:00Z",
    last_login: null,
    profile: {
      first_name: "Test",
      last_name: "User",
      full_name: "Test User",
      display_name: "testuser",
      phone: "",
      avatar_url: null,
      has_avatar: false,
      timezone: "UTC",
      language: "en",
      bio: "",
      country: "",
      city: "",
      tags: [],
      is_public: true,
    },
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("AdminGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: false,
    });
  });

  it("shows loading skeleton while not initialized", () => {
    useAuthStore.setState({ isInitialized: false });

    render(
      <AdminGuard>
        <div>Admin Content</div>
      </AdminGuard>,
    );

    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
    expect(document.querySelector(".h-64")).toBeInTheDocument();
  });

  it("shows Access Denied for non-staff, non-superuser", () => {
    const regularUser = createMockUser({ is_staff: false, is_superuser: false });

    useAuthStore.setState({
      user: regularUser,
      isAuthenticated: true,
      isInitialized: true,
    });

    render(
      <AdminGuard>
        <div>Admin Content</div>
      </AdminGuard>,
    );

    expect(screen.getByText("Access Denied")).toBeInTheDocument();
    expect(
      screen.getByText("You do not have administrator access."),
    ).toBeInTheDocument();
    expect(screen.getByText("Back to Home")).toBeInTheDocument();
    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
  });

  it("renders children when user is_staff", () => {
    const staffUser = createMockUser({ is_staff: true });

    useAuthStore.setState({
      user: staffUser,
      isAuthenticated: true,
      isInitialized: true,
    });

    render(
      <AdminGuard>
        <div>Admin Content</div>
      </AdminGuard>,
    );

    expect(screen.getByText("Admin Content")).toBeInTheDocument();
  });

  it("renders children when user is_superuser", () => {
    const superUser = createMockUser({ is_superuser: true });

    useAuthStore.setState({
      user: superUser,
      isAuthenticated: true,
      isInitialized: true,
    });

    render(
      <AdminGuard>
        <div>Admin Content</div>
      </AdminGuard>,
    );

    expect(screen.getByText("Admin Content")).toBeInTheDocument();
  });
});
