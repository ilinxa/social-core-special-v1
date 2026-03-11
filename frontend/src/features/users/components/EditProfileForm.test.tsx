import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { User, UserProfile } from "@/types";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/profile/edit",
  useParams: () => ({}),
}));

const mockUser: User = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "john@example.com",
  username: "johndoe",
  is_active: true,
  is_verified: true,
  is_complete: true,
  can_create_business: false,
  is_staff: false,
  is_superuser: false,
  date_joined: "2026-01-15T00:00:00Z",
  last_login: null,
  profile: {
    first_name: "John",
    last_name: "Doe",
    full_name: "John Doe",
    display_name: "John",
    phone: "+1234567890",
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
};

const mockProfile: UserProfile = mockUser.profile;

vi.mock("@/stores/auth-store", () => ({
  useUser: vi.fn(() => mockUser),
  useAuthStore: vi.fn((selector: (s: unknown) => unknown) =>
    selector({ user: mockUser, isAuthenticated: true, isInitialized: true }),
  ),
}));

vi.mock("@/features/users/hooks/use-user-queries", () => ({
  useProfile: vi.fn(() => ({ data: mockProfile, isLoading: false })),
}));

const mockUpdateProfileMutateAsync = vi.fn();

vi.mock("@/features/users/hooks/use-user-mutations", () => ({
  useUpdateProfile: vi.fn(() => ({
    mutateAsync: mockUpdateProfileMutateAsync,
    isPending: false,
  })),
  useUploadAvatar: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteAvatar: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUploadCoverImage: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteCoverImage: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}));


vi.mock("@/hooks/use-city-data", () => ({
  useCitiesForCountry: vi.fn(() => []),
}));

vi.mock("@/features/explore/hooks/use-explore-queries", () => ({
  useTagSuggestions: vi.fn(() => ({ data: [] })),
}));

import { renderWithProviders } from "@/test/utils";

beforeEach(() => {
  vi.clearAllMocks();
  mockUpdateProfileMutateAsync.mockResolvedValue(mockProfile);
});

describe("EditProfileForm", () => {
  async function renderComponent() {
    const { EditProfileForm } = await import("./EditProfileForm");
    return renderWithProviders(<EditProfileForm />);
  }

  it("renders all form fields with current values", async () => {
    await renderComponent();

    expect(screen.getByLabelText("First name")).toHaveValue("John");
    expect(screen.getByLabelText("Last name")).toHaveValue("Doe");
    expect(screen.getByLabelText("Phone")).toHaveValue("+1234567890");
  });

  it("renders Cancel and Save buttons", async () => {
    await renderComponent();

    expect(screen.getByRole("link", { name: /cancel/i })).toHaveAttribute("href", "/profile");
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("fires profile mutation when profile fields changed", async () => {
    const user = userEvent.setup();
    await renderComponent();

    const firstNameInput = screen.getByLabelText("First name");
    await user.clear(firstNameInput);
    await user.type(firstNameInput, "Jane");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockUpdateProfileMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ first_name: "Jane" }),
      );
    });
  });

  it("navigates to /profile on successful save", async () => {
    const user = userEvent.setup();
    await renderComponent();

    const firstNameInput = screen.getByLabelText("First name");
    await user.clear(firstNameInput);
    await user.type(firstNameInput, "Jane");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/profile");
    });
  });

  it("renders photo and profile information sections", async () => {
    await renderComponent();

    expect(screen.getByText("Photo")).toBeInTheDocument();
    expect(screen.getByText("Profile Information")).toBeInTheDocument();
  });

  it("renders bio, country, city, and tags fields", async () => {
    await renderComponent();

    expect(screen.getByLabelText("Bio")).toBeInTheDocument();
    expect(screen.getByText("Country")).toBeInTheDocument();
    expect(screen.getByText("City")).toBeInTheDocument();
    expect(screen.getByText("Tags")).toBeInTheDocument();
  });

  it("includes bio in profile mutation payload when changed", async () => {
    const user = userEvent.setup();
    await renderComponent();

    const bioInput = screen.getByLabelText("Bio");
    await user.type(bioInput, "Hello world");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockUpdateProfileMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ bio: "Hello world" }),
      );
    });
  });
});
