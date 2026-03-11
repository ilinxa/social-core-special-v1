import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";

import type { UserPublicWithPerms } from "@/types";

// =============================================================================
// MOCKS
// =============================================================================

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ username: "johndoe" })),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/features/users/hooks/use-user-queries", () => ({
  useUserByUsername: vi.fn(),
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { renderWithProviders } from "@/test/utils";
import { useUserByUsername } from "@/features/users/hooks/use-user-queries";

// =============================================================================
// TEST DATA
// =============================================================================

function createMockUser(
  overrides: Partial<UserPublicWithPerms> = {},
  permOverrides: Partial<UserPublicWithPerms["_permissions"]> = {},
): UserPublicWithPerms {
  return {
    id: "550e8400-e29b-41d4-a716-446655440000",
    username: "johndoe",
    is_verified: true,
    is_complete: true,
    date_joined: "2026-01-15T00:00:00Z",
    profile: {
      first_name: "John",
      last_name: "Doe",
      full_name: "John Doe",
      display_name: "John Doe",
      avatar_url: null,
      has_avatar: false,
      bio: "Hello, I'm a developer",
      country: "US",
      city: "New York",
      tags: ["developer", "react"],
      is_public: true,
    },
    _permissions: {
      is_own_profile: false,
      can_edit_profile: false,
      ...permOverrides,
    },
    ...overrides,
  };
}

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
});

describe("UserPublicProfilePage", () => {
  async function renderComponent() {
    const { UserPublicProfilePage } = await import("./UserPublicProfilePage");
    return renderWithProviders(<UserPublicProfilePage />);
  }

  it("shows skeleton while loading", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.queryByText("User not found")).not.toBeInTheDocument();
    expect(screen.queryByText("johndoe")).not.toBeInTheDocument();
  });

  it("shows 'User not found' when error occurs", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Not found"),
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("User not found")).toBeInTheDocument();
    expect(
      screen.getByText("This user profile may not exist or is not accessible."),
    ).toBeInTheDocument();
  });

  it("shows 'User not found' when data is undefined and not loading", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("User not found")).toBeInTheDocument();
  });

  it("renders profile with display name and username", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser(),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getAllByText("John Doe").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("@johndoe")).toBeInTheDocument();
  });

  it("renders bio section", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser(),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("Hello, I'm a developer")).toBeInTheDocument();
  });

  it("renders tags", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser(),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("developer")).toBeInTheDocument();
    expect(screen.getByText("react")).toBeInTheDocument();
  });

  it("shows verified badge for verified users", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser(),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("shows unverified badge for unverified users", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser({ is_verified: false }),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("Unverified")).toBeInTheDocument();
  });

  it("shows 'Edit Profile' button when viewing own profile", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser({}, { is_own_profile: true, can_edit_profile: true }),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByRole("button", { name: /edit profile/i })).toBeInTheDocument();
  });

  it("hides 'Edit Profile' button when viewing another user's profile", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser(),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.queryByRole("button", { name: /edit profile/i })).not.toBeInTheDocument();
  });

  it("handles null profile gracefully", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser({ profile: null }),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText("@johndoe")).toBeInTheDocument();
    expect(screen.queryByText("About")).not.toBeInTheDocument();
    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
  });

  it("shows member since date", async () => {
    vi.mocked(useUserByUsername).mockReturnValue({
      data: createMockUser(),
      isLoading: false,
      error: null,
    } as ReturnType<typeof useUserByUsername>);

    await renderComponent();

    expect(screen.getByText(/member since/i)).toBeInTheDocument();
    expect(screen.getByText(/january 15, 2026/i)).toBeInTheDocument();
  });
});
