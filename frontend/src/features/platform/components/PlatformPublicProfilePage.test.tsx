import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";

import type { PlatformAccountWithPerms } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("@/features/platform/hooks/use-platform-queries", () => ({
  usePlatformAccount: vi.fn(),
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

describe("PlatformPublicProfilePage", () => {
  async function renderComponent() {
    const { PlatformPublicProfilePage } = await import("./PlatformPublicProfilePage");
    return renderWithProviders(<PlatformPublicProfilePage />);
  }

  it("shows skeleton while loading", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByTestId("profile-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows error message when error occurs", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to load"),
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByText("Platform profile not available")).toBeInTheDocument();
    expect(
      screen.getByText("The platform profile could not be loaded."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("profile-view")).not.toBeInTheDocument();
  });

  it("shows error message when data is undefined and not loading", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByText("Platform profile not available")).toBeInTheDocument();
  });

  it("shows PlatformProfileView on success", async () => {
    vi.mocked(usePlatformAccount).mockReturnValue({
      data: mockPlatform,
      isLoading: false,
      error: null,
    } as ReturnType<typeof usePlatformAccount>);

    await renderComponent();

    expect(screen.getByTestId("profile-view")).toBeInTheDocument();
    expect(screen.queryByText("Platform profile not available")).not.toBeInTheDocument();
  });
});
