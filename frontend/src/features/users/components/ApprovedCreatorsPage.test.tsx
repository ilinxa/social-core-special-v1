import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";
import type { ApprovedCreatorItem, PaginatedResponse } from "@/types";

import { ApprovedCreatorsPage } from "./ApprovedCreatorsPage";

// =============================================================================
// MOCKS
// =============================================================================

const mockFetchApprovedCreators = vi.fn();

vi.mock("@/features/users/api/users-api", () => ({
  fetchApprovedCreatorsApi: (...args: unknown[]) => mockFetchApprovedCreators(...args),
  fetchCurrentUserApi: vi.fn(),
  fetchProfileApi: vi.fn(),
  fetchUserByUsernameApi: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// =============================================================================
// HELPERS
// =============================================================================

function makeCreator(overrides: Partial<ApprovedCreatorItem> = {}): ApprovedCreatorItem {
  return {
    id: "user-1",
    email: "alice@test.com",
    username: "alice_creator",
    display_name: "Alice Creator",
    avatar_url: null,
    can_create_business: true,
    date_joined: "2026-01-15T00:00:00Z",
    ...overrides,
  };
}

function makePaginatedResponse(
  results: ApprovedCreatorItem[],
  count?: number,
): PaginatedResponse<ApprovedCreatorItem> {
  return {
    count: count ?? results.length,
    next: null,
    previous: null,
    results,
  };
}

// =============================================================================
// TESTS
// =============================================================================

describe("ApprovedCreatorsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and search input", async () => {
    mockFetchApprovedCreators.mockResolvedValue(makePaginatedResponse([]));

    renderWithProviders(<ApprovedCreatorsPage />);

    expect(screen.getByText("Approved Business Creators")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument();
  });

  it("shows user cards from API data", async () => {
    const creators = [
      makeCreator({ id: "u1", display_name: "Alice Creator", email: "alice@test.com" }),
      makeCreator({ id: "u2", display_name: "Bob Builder", email: "bob@test.com", username: "bob_builder" }),
    ];
    mockFetchApprovedCreators.mockResolvedValue(makePaginatedResponse(creators));

    renderWithProviders(<ApprovedCreatorsPage />);

    await waitFor(() => {
      expect(screen.getByText("Alice Creator")).toBeInTheDocument();
    });
    expect(screen.getByText("Bob Builder")).toBeInTheDocument();
    expect(screen.getByText("alice@test.com")).toBeInTheDocument();
    expect(screen.getByText("bob@test.com")).toBeInTheDocument();
  });

  it("shows empty state when no users", async () => {
    mockFetchApprovedCreators.mockResolvedValue(makePaginatedResponse([]));

    renderWithProviders(<ApprovedCreatorsPage />);

    await waitFor(() => {
      expect(screen.getByText("No users have been approved yet.")).toBeInTheDocument();
    });
  });

  it("shows search-specific empty state", async () => {
    // First render with results, then search returns empty
    mockFetchApprovedCreators
      .mockResolvedValueOnce(makePaginatedResponse([makeCreator()]))
      .mockResolvedValueOnce(makePaginatedResponse([]));

    const user = userEvent.setup();
    renderWithProviders(<ApprovedCreatorsPage />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText("Alice Creator")).toBeInTheDocument();
    });

    // Type in search
    await user.type(screen.getByPlaceholderText(/search by name/i), "nonexistent");

    await waitFor(() => {
      expect(screen.getByText("No users match your search.")).toBeInTheDocument();
    });
  });

  it("shows count of creators", async () => {
    const creators = [
      makeCreator({ id: "u1", display_name: "Alice Creator" }),
      makeCreator({ id: "u2", display_name: "Bob Builder" }),
    ];
    mockFetchApprovedCreators.mockResolvedValue(makePaginatedResponse(creators));

    renderWithProviders(<ApprovedCreatorsPage />);

    await waitFor(() => {
      expect(screen.getByText("2 approved creators")).toBeInTheDocument();
    });
  });

  it("links creator cards to user profile", async () => {
    mockFetchApprovedCreators.mockResolvedValue(
      makePaginatedResponse([makeCreator({ username: "alice_creator" })]),
    );

    renderWithProviders(<ApprovedCreatorsPage />);

    await waitFor(() => {
      expect(screen.getByText("Alice Creator")).toBeInTheDocument();
    });

    const link = screen.getByRole("link", { name: /alice creator/i });
    expect(link).toHaveAttribute("href", "/users/alice_creator");
  });

  it("shows pagination controls when multiple pages exist", async () => {
    const creators = [makeCreator()];
    mockFetchApprovedCreators.mockResolvedValue({
      count: 25,
      next: "http://test/api/v1/platform/approved-creators/?page=2",
      previous: null,
      results: creators,
    });

    renderWithProviders(<ApprovedCreatorsPage />);

    await waitFor(() => {
      expect(screen.getByText("Alice Creator")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /next/i })).not.toBeDisabled();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
  });
});
