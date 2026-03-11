import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types";
import { useAuthStore } from "@/stores/auth-store";

import { UserMenu } from "./UserMenu";

// =============================================================================
// MOCKS
// =============================================================================

const mockLogoutMutate = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/home",
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
  useLogout: vi.fn(() => ({ mutate: mockLogoutMutate, isPending: false })),
}));

// =============================================================================
// FIXTURES
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

describe("UserMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
      isInitialized: true,
    });
  });

  it("renders the avatar trigger button with initials fallback", () => {
    render(<UserMenu />);

    const trigger = screen.getByRole("button");
    expect(trigger).toBeInTheDocument();
    expect(screen.getByText("JD")).toBeInTheDocument();
  });

  it("shows dropdown with Profile and Settings links when opened", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button"));

    expect(screen.getByRole("menuitem", { name: /profile/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /settings/i })).toBeInTheDocument();
  });

  it("shows user display name and email in the dropdown header", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button"));

    expect(screen.getByText("John")).toBeInTheDocument();
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("shows Log out menu item in the dropdown", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button"));

    expect(screen.getByRole("menuitem", { name: /log out/i })).toBeInTheDocument();
  });

  it("calls logout.mutate when Log out is clicked", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button"));
    await user.click(screen.getByRole("menuitem", { name: /log out/i }));

    expect(mockLogoutMutate).toHaveBeenCalledTimes(1);
  });

  it("shows first initial only when last name is missing", () => {
    useAuthStore.setState({
      user: {
        ...mockUser,
        profile: { ...mockUser.profile, first_name: "John", last_name: "" },
      },
      isAuthenticated: true,
      isInitialized: true,
    });

    render(<UserMenu />);

    expect(screen.getByText("J")).toBeInTheDocument();
  });
});
