import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Membership } from "@/types/rbac";
import { useMembershipStore } from "@/stores/membership-store";
import { useAuthStore } from "@/stores/auth-store";
import { renderWithProviders } from "@/test/utils";

import { AccountSwitcher } from "./AccountSwitcher";

// =============================================================================
// MOCKS
// =============================================================================

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => mockPathname,
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock transaction API for BusinessCreationRequestButton
vi.mock("@/features/transactions/api/transactions-api", () => ({
  fetchTransactionsApi: vi.fn().mockResolvedValue({ count: 0, results: [] }),
  checkRequestFormApi: vi.fn(),
  submitRequestFormResponseApi: vi.fn(),
  createRequestApi: vi.fn(),
}));

vi.mock("@/features/platform/api/platform-api", () => ({
  fetchPlatformAccountApi: vi.fn(),
}));

vi.mock("@/features/users/api/users-api", () => ({
  fetchCurrentUserApi: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

let mockPathname = "/home";

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

function setAuthUser(canCreateBusiness: boolean) {
  useAuthStore.setState({
    user: {
      id: "user-1",
      email: "test@test.com",
      username: "testuser",
      is_active: true,
      is_verified: true,
      is_complete: true,
      can_create_business: canCreateBusiness,
      is_staff: false,
      is_superuser: false,
      date_joined: "2026-01-01T00:00:00Z",
      last_login: null,
      profile: {
        first_name: "Test",
        last_name: "User",
        full_name: "Test User",
        display_name: "Test User",
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
    },
    isAuthenticated: true,
    isInitialized: true,
  });
}

// =============================================================================
// TESTS
// =============================================================================

describe("AccountSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname = "/home";
    useMembershipStore.setState({ memberships: [], isLoaded: true });
    useAuthStore.setState({ user: null, isAuthenticated: false, isInitialized: false });
  });

  it("shows 'Personal' as current context label when on personal route", () => {
    renderWithProviders(<AccountSwitcher />);

    const trigger = screen.getByRole("combobox", { name: /switch account context/i });
    expect(trigger).toHaveTextContent("Personal");
  });

  it("lists personal + business memberships in the popover", async () => {
    const user = userEvent.setup();

    useMembershipStore.setState({
      memberships: [
        makeMembership({ id: "mem-1", account_name: "Acme Corp", account_slug: "acme" }),
        makeMembership({
          id: "mem-2",
          account_name: "Beta Inc",
          account_slug: "beta",
          account_id: "acc-2",
        }),
      ],
      isLoaded: true,
    });

    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));

    // "Personal" appears twice: once in the trigger, once in the popover list
    const personalItems = screen.getAllByText("Personal");
    expect(personalItems.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Beta Inc")).toBeInTheDocument();
  });

  it("lists platform option when user has a platform membership", async () => {
    const user = userEvent.setup();

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

    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));

    expect(screen.getByText("Platform")).toBeInTheDocument();
  });

  it("calls router.push when clicking a non-active item", async () => {
    const user = userEvent.setup();

    useMembershipStore.setState({
      memberships: [
        makeMembership({ id: "mem-1", account_name: "Acme Corp", account_slug: "acme" }),
      ],
      isLoaded: true,
    });

    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));
    await user.click(screen.getByText("Acme Corp"));

    expect(mockPush).toHaveBeenCalledWith("/bconsole/acme/dashboard");
  });

  it("does not call router.push when clicking the already-active item", async () => {
    const user = userEvent.setup();

    // Already on personal route, clicking Personal should not navigate
    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));

    // "Personal" appears in both the trigger and the popover list.
    // The popover list item is the last one rendered in the DOM.
    const personalItems = screen.getAllByText("Personal");
    await user.click(personalItems[personalItems.length - 1]);

    expect(mockPush).not.toHaveBeenCalled();
  });

  it("shows business context as active when on a business route", async () => {
    const user = userEvent.setup();
    mockPathname = "/bconsole/acme/dashboard";

    useMembershipStore.setState({
      memberships: [
        makeMembership({ id: "mem-1", account_name: "Acme Corp", account_slug: "acme" }),
      ],
      isLoaded: true,
    });

    renderWithProviders(<AccountSwitcher />);

    // Trigger should show the business name
    const trigger = screen.getByRole("combobox", { name: /switch account context/i });
    expect(trigger).toHaveTextContent("Acme Corp");

    // Open popover and verify the active item does not trigger navigation
    await user.click(trigger);
    // "Acme Corp" appears in both the trigger and the popover list
    const acmeItems = screen.getAllByText("Acme Corp");
    await user.click(acmeItems[acmeItems.length - 1]);
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("shows 'Create Business' when user can_create_business is true", async () => {
    const user = userEvent.setup();
    setAuthUser(true);

    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));

    expect(screen.getByText("Create Business")).toBeInTheDocument();
  });

  it("shows 'Request Business Access' when user can_create_business is false", async () => {
    const user = userEvent.setup();
    setAuthUser(false);

    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));

    expect(await screen.findByText("Request Business Access")).toBeInTheDocument();
    expect(screen.queryByText("Create Business")).not.toBeInTheDocument();
  });

  it("shows neither Create nor Request when user is not authenticated", async () => {
    const user = userEvent.setup();
    // user is null (default from beforeEach)

    renderWithProviders(<AccountSwitcher />);

    await user.click(screen.getByRole("combobox", { name: /switch account context/i }));

    expect(screen.queryByText("Create Business")).not.toBeInTheDocument();
    expect(screen.queryByText("Request Business Access")).not.toBeInTheDocument();
  });
});
