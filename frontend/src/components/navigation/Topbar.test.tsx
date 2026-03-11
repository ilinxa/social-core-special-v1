import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types";
import { useAuthStore } from "@/stores/auth-store";

import { Topbar } from "./Topbar";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next-themes", () => ({
  useTheme: vi.fn(() => ({ theme: "system", setTheme: vi.fn() })),
}));

vi.mock("@/features/auth/hooks/use-auth-mutations", () => ({
  useLogout: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/stores/membership-store", () => ({
  useMembershipStore: Object.assign(
    vi.fn((selector: (s: Record<string, unknown>) => unknown) => {
      const state = { memberships: [], isLoaded: true };
      return selector ? selector(state) : state;
    }),
    { setState: vi.fn(), getState: vi.fn(() => ({ memberships: [], isLoaded: true })) },
  ),
  useBusinessMemberships: vi.fn(() => []),
  usePlatformMembership: vi.fn(() => null),
  useMemberships: vi.fn(() => []),
  useMembershipsLoaded: vi.fn(() => true),
}));

// =============================================================================
// HELPERS
// =============================================================================

const mockUser: User = {
  id: "user-1",
  email: "john@example.com",
  username: "john_doe",
  is_active: true,
  is_verified: true,
  is_complete: true,
  can_create_business: true,
  is_staff: false,
  is_superuser: false,
  date_joined: "2026-01-01",
  last_login: null,
  profile: {
    first_name: "John",
    last_name: "Doe",
    full_name: "John Doe",
    display_name: "John",
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
};

// =============================================================================
// TESTS
// =============================================================================

describe("Topbar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: true,
    });
  });

  describe("public variant", () => {
    it("shows Sign In and Register links when not authenticated", () => {
      render(<Topbar variant="public" />);

      expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/login");
      expect(screen.getByRole("link", { name: /register/i })).toHaveAttribute("href", "/register");
    });

    it("shows the app name linking to root", () => {
      render(<Topbar variant="public" />);

      const brand = screen.getByRole("link", { name: /socialmedia adv/i });
      expect(brand).toHaveAttribute("href", "/");
    });

    it("shows About and Contact nav links", () => {
      render(<Topbar variant="public" />);

      expect(screen.getByRole("link", { name: /about/i })).toHaveAttribute("href", "/about");
      expect(screen.getByRole("link", { name: /contact/i })).toHaveAttribute("href", "/contact");
    });

    it("shows Go to App + user menu when authenticated", () => {
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isInitialized: true,
      });

      render(<Topbar variant="public" />);

      expect(screen.getByRole("link", { name: /go to app/i })).toHaveAttribute("href", "/home");
      // Sign In / Register should NOT be shown
      expect(screen.queryByRole("link", { name: /sign in/i })).not.toBeInTheDocument();
    });
  });

  describe("authenticated variant", () => {
    it("shows user menu trigger (avatar button)", () => {
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isInitialized: true,
      });

      render(<Topbar variant="authenticated" />);

      // The avatar trigger is a button containing the avatar fallback text
      const avatarButton = screen.getByRole("button");
      expect(avatarButton).toBeInTheDocument();
      // Fallback initials should be "JD" (John Doe)
      expect(screen.getByText("JD")).toBeInTheDocument();
    });

    it("shows the app name linking to /home", () => {
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isInitialized: true,
      });

      render(<Topbar variant="authenticated" />);

      const brand = screen.getByRole("link", { name: /socialmedia adv/i });
      expect(brand).toHaveAttribute("href", "/home");
    });
  });
});
