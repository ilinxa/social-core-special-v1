import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types";
import { useAuthStore } from "@/stores/auth-store";

import { AuthGuard } from "./AuthGuard";

// =============================================================================
// MOCKS
// =============================================================================

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/settings",
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
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("AuthGuard", () => {
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
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    );

    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    // Skeleton is rendered (the container div exists)
    expect(document.querySelector(".h-64")).toBeInTheDocument();
  });

  it("redirects to /login when initialized but not authenticated", () => {
    useAuthStore.setState({ isInitialized: true, isAuthenticated: false });

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    );

    expect(mockReplace).toHaveBeenCalledWith(
      "/login?callbackUrl=%2Fsettings",
    );
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("preserves callbackUrl with encoded pathname in redirect", () => {
    useAuthStore.setState({ isInitialized: true, isAuthenticated: false });

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    );

    const callArg = mockReplace.mock.calls[0][0] as string;
    expect(callArg).toContain("callbackUrl=");
    expect(callArg).toContain(encodeURIComponent("/settings"));
  });

  it("renders children when authenticated and initialized", () => {
    useAuthStore.setState({
      user: createMockUser(),
      isAuthenticated: true,
      isInitialized: true,
    });

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
