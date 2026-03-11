import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { PlatformAccountWithPerms } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("@/features/platform/hooks/use-platform-queries", () => ({
  usePlatformAccount: vi.fn(),
}));

vi.mock("@/features/platform/components/PlatformProfileEditForm", () => ({
  PlatformProfileEditForm: () => <div data-testid="edit-form">Edit Form</div>,
}));

vi.mock("@/features/platform/components/PlatformProfileView", () => ({
  PlatformProfileView: () => <div data-testid="profile-view">Profile View</div>,
  PlatformProfileSkeleton: () => <div data-testid="profile-skeleton">Skeleton</div>,
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { renderWithProviders } from "@/test/utils";
import { usePlatformAccount } from "@/features/platform/hooks/use-platform-queries";

// =============================================================================
// TEST DATA
// =============================================================================

const mockPlatform: PlatformAccountWithPerms = {
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
  },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_view: true,
    can_edit_profile: true,
    can_edit_settings: true,
  },
};

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PlatformConsoleProfilePage", () => {
  async function renderComponent() {
    const { PlatformConsoleProfilePage } = await import("./PlatformConsoleProfilePage");
    return renderWithProviders(<PlatformConsoleProfilePage />);
  }

  it("shows skeleton while loading", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByTestId("profile-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("edit-form")).not.toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows tabs with edit form active by default when can_edit_profile is true", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: mockPlatform,
      isLoading: false,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByRole("tab", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Preview" })).toBeInTheDocument();
    expect(screen.getByTestId("edit-form")).toBeInTheDocument();
    expect(screen.queryByTestId("profile-skeleton")).not.toBeInTheDocument();
  });

  it("switches to preview tab and shows profile view", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: mockPlatform,
      isLoading: false,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: "Preview" }));

    expect(screen.getByTestId("profile-view")).toBeInTheDocument();
  });

  it("shows read-only view without tabs when can_edit_profile is false", async () => {
    const readOnlyPlatform: PlatformAccountWithPerms = {
      ...mockPlatform,
      _permissions: {
        ...mockPlatform._permissions,
        can_edit_profile: false,
      },
    };

    vi.mocked(usePlatformAccount).mockReturnValue({
      data: readOnlyPlatform,
      isLoading: false,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByTestId("profile-view")).toBeInTheDocument();
    expect(screen.queryByTestId("edit-form")).not.toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("renders Profile heading", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: mockPlatform,
      isLoading: false,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByRole("heading", { name: "Profile", level: 1 })).toBeInTheDocument();
  });
});
