import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { User, UserProfile } from "@/types";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/profile",
  useParams: () => ({}),
}));

const mockUser: User = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "john@example.com",
  username: "johndoe",
  is_active: true,
  is_verified: true,
  is_complete: true,
  can_create_business: true,
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
    timezone: "America/New_York",
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
}));

vi.mock("@/features/users/hooks/use-user-queries", () => ({
  useProfile: vi.fn(() => ({ data: mockProfile, isLoading: false })),
}));

import { renderWithProviders } from "@/test/utils";
import { useUser } from "@/stores/auth-store";
import { useProfile } from "@/features/users/hooks/use-user-queries";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useUser).mockReturnValue(mockUser);
  vi.mocked(useProfile).mockReturnValue({ data: mockProfile, isLoading: false } as ReturnType<typeof useProfile>);
});

describe("ProfileView", () => {
  async function renderComponent() {
    const { ProfileView } = await import("./ProfileView");
    return renderWithProviders(<ProfileView />);
  }

  it("renders display name and username", async () => {
    await renderComponent();

    expect(screen.getByRole("heading", { name: "John", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("@johndoe")).toBeInTheDocument();
  });

  it("renders email", async () => {
    await renderComponent();

    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("renders profile details", async () => {
    await renderComponent();

    // "John" appears both as display_name (h2) and first_name detail row — verify both exist
    const johns = screen.getAllByText("John");
    expect(johns.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Doe")).toBeInTheDocument();
    expect(screen.getByText("+1234567890")).toBeInTheDocument();
    expect(screen.getByText("America/New York")).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();
  });

  it("renders verification badge", async () => {
    await renderComponent();

    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("renders member since date", async () => {
    await renderComponent();

    expect(screen.getByText(/January 15, 2026/)).toBeInTheDocument();
  });

  it("navigates to edit page on button click", async () => {
    const user = userEvent.setup();
    await renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));
    expect(mockPush).toHaveBeenCalledWith("/profile/edit");
  });

  it("shows loading skeleton when profile is loading", async () => {
    vi.mocked(useProfile).mockReturnValue({ data: undefined, isLoading: true } as ReturnType<typeof useProfile>);
    await renderComponent();

    expect(screen.queryByText("@johndoe")).not.toBeInTheDocument();
  });

  it("shows avatar fallback when no avatar", async () => {
    await renderComponent();

    expect(screen.getByText("J")).toBeInTheDocument();
  });

  it("renders bio in About card when present", async () => {
    const profileWithBio: UserProfile = { ...mockProfile, bio: "Full-stack developer" };
    vi.mocked(useProfile).mockReturnValue({ data: profileWithBio, isLoading: false } as ReturnType<typeof useProfile>);
    await renderComponent();

    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("Full-stack developer")).toBeInTheDocument();
  });

  it("does not render About card when bio is empty", async () => {
    await renderComponent();

    expect(screen.queryByText("About")).not.toBeInTheDocument();
  });

  it("renders location when country and city are set", async () => {
    const profileWithLocation: UserProfile = { ...mockProfile, country: "US", city: "New York" };
    vi.mocked(useProfile).mockReturnValue({ data: profileWithLocation, isLoading: false } as ReturnType<typeof useProfile>);
    await renderComponent();

    expect(screen.getByText("New York, United States")).toBeInTheDocument();
  });

  it("renders tags when present", async () => {
    const profileWithTags: UserProfile = { ...mockProfile, tags: ["developer", "react"] };
    vi.mocked(useProfile).mockReturnValue({ data: profileWithTags, isLoading: false } as ReturnType<typeof useProfile>);
    await renderComponent();

    expect(screen.getByText("Tags")).toBeInTheDocument();
    expect(screen.getByText("developer")).toBeInTheDocument();
    expect(screen.getByText("react")).toBeInTheDocument();
  });

  it("does not render Tags card when tags are empty", async () => {
    await renderComponent();

    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
  });
});
