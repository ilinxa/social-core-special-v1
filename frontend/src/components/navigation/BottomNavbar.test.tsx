import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Membership } from "@/types/rbac";
import { useMembershipStore } from "@/stores/membership-store";

import { BottomNavbar } from "./BottomNavbar";

// =============================================================================
// MOCKS
// =============================================================================

let mockPathname = "/home";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => mockPathname,
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

// =============================================================================
// HELPERS
// =============================================================================

function makeMembership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: "mem-1",
    account_type: "business",
    account_id: "acc-1",
    account_name: "Acme Corp",
    account_slug: "acme",
    account_max_members: 6,
    role: {
      id: "role-1",
      name: "Manager",
      account_type: "business",
      account_id: "acc-1",
      level: 5,
      is_system_role: false,
      description: "",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    is_owner: false,
    status: "active",
    joined_at: "2026-01-01T00:00:00Z",
    permissions: [],
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("BottomNavbar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname = "/home";
    useMembershipStore.setState({ memberships: [], isLoaded: true });
  });

  describe("personal context", () => {
    it("shows 4 personal nav items + More button", () => {
      render(<BottomNavbar />);

      expect(screen.getByRole("link", { name: /home/i })).toHaveAttribute("href", "/home");
      expect(screen.getByRole("link", { name: /explore/i })).toHaveAttribute("href", "/explore");
      expect(screen.getByRole("link", { name: /alerts/i })).toHaveAttribute("href", "/notifications");
      expect(screen.getByRole("link", { name: /profile/i })).toHaveAttribute("href", "/profile");
      expect(screen.getByText("More")).toBeInTheDocument();
    });
  });

  describe("business context", () => {
    it("shows 4 business nav items with slug in URLs", () => {
      mockPathname = "/bconsole/acme/dashboard";
      useMembershipStore.setState({
        memberships: [
          makeMembership({ account_slug: "acme", account_name: "Acme Corp" }),
        ],
        isLoaded: true,
      });

      render(<BottomNavbar />);

      expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute(
        "href",
        "/bconsole/acme/dashboard",
      );
      expect(screen.getByRole("link", { name: /members/i })).toHaveAttribute(
        "href",
        "/bconsole/acme/members",
      );
      expect(screen.getByRole("link", { name: /forms/i })).toHaveAttribute(
        "href",
        "/bconsole/acme/forms",
      );
      expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute(
        "href",
        "/bconsole/acme/settings",
      );
    });
  });

  describe("platform context", () => {
    it("shows 4 platform nav items", () => {
      mockPathname = "/pconsole/dashboard";
      useMembershipStore.setState({
        memberships: [
          makeMembership({
            id: "mem-plat",
            account_type: "platform",
            account_id: "plat-1",
            account_name: "Platform",
            account_slug: "platform",
          }),
        ],
        isLoaded: true,
      });

      render(<BottomNavbar />);

      expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute(
        "href",
        "/pconsole/dashboard",
      );
      expect(screen.getByRole("link", { name: /businesses/i })).toHaveAttribute(
        "href",
        "/pconsole/businesses",
      );
      expect(screen.getByRole("link", { name: /members/i })).toHaveAttribute(
        "href",
        "/pconsole/members",
      );
      expect(screen.getByRole("link", { name: /cms/i })).toHaveAttribute(
        "href",
        "/cconsole/sites",
      );
    });
  });

  it("items change when switching from personal to business context", () => {
    // First render in personal context
    const { unmount } = render(<BottomNavbar />);
    expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /dashboard/i })).not.toBeInTheDocument();
    unmount();

    // Switch to business context
    mockPathname = "/bconsole/acme/dashboard";
    useMembershipStore.setState({
      memberships: [makeMembership({ account_slug: "acme" })],
      isLoaded: true,
    });

    render(<BottomNavbar />);
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /home/i })).not.toBeInTheDocument();
  });

  it("renders the More button as a non-link button element", () => {
    render(<BottomNavbar />);

    const moreButton = screen.getByText("More");
    // The More button is a <button> element, not a link
    expect(moreButton.closest("button")).toBeInTheDocument();
    expect(moreButton.closest("a")).not.toBeInTheDocument();
  });
});
