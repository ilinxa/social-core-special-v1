import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/utils";
import { ExplorePage } from "./ExplorePage";

// Mock next/navigation
const mockReplace = vi.fn();
const mockSearchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
}));

// Mock auth store
let mockIsAuthenticated = false;
vi.mock("@/stores/auth-store", () => ({
  useIsAuthenticated: () => mockIsAuthenticated,
}));

// Mock child components to avoid deep rendering
vi.mock("./AllTabContent", () => ({
  AllTabContent: ({ query, isAuthenticated }: { query: string; isAuthenticated: boolean }) => (
    <div data-testid="all-tab-content" data-query={query} data-auth={String(isAuthenticated)} />
  ),
}));

vi.mock("./BusinessSearchContent", () => ({
  BusinessSearchContent: () => <div data-testid="business-search-content" />,
}));

vi.mock("./UserSearchContent", () => ({
  UserSearchContent: () => <div data-testid="user-search-content" />,
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockIsAuthenticated = false;
  // Reset search params
  for (const key of [...mockSearchParams.keys()]) {
    mockSearchParams.delete(key);
  }
});

describe("ExplorePage", () => {
  it("renders heading and search bar", () => {
    renderWithProviders(<ExplorePage />);

    expect(screen.getByText("Explore")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toBeInTheDocument();
  });

  it("renders All and Businesses tabs for anonymous users", () => {
    renderWithProviders(<ExplorePage />);

    expect(screen.getByRole("tab", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Businesses" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Users" })).not.toBeInTheDocument();
  });

  it("renders Users tab for authenticated users", () => {
    mockIsAuthenticated = true;
    renderWithProviders(<ExplorePage />);

    expect(screen.getByRole("tab", { name: "Users" })).toBeInTheDocument();
  });

  it("shows All tab content by default", () => {
    renderWithProviders(<ExplorePage />);

    expect(screen.getByTestId("all-tab-content")).toBeInTheDocument();
    expect(screen.queryByTestId("business-search-content")).not.toBeInTheDocument();
  });

  it("shows business search content when tab=businesses", () => {
    mockSearchParams.set("tab", "businesses");
    renderWithProviders(<ExplorePage />);

    expect(screen.getByTestId("business-search-content")).toBeInTheDocument();
    expect(screen.queryByTestId("all-tab-content")).not.toBeInTheDocument();
  });

  it("passes query to AllTabContent", () => {
    mockSearchParams.set("q", "hello");
    renderWithProviders(<ExplorePage />);

    const content = screen.getByTestId("all-tab-content");
    expect(content).toHaveAttribute("data-query", "hello");
  });

  it("passes isAuthenticated to AllTabContent", () => {
    mockIsAuthenticated = true;
    renderWithProviders(<ExplorePage />);

    const content = screen.getByTestId("all-tab-content");
    expect(content).toHaveAttribute("data-auth", "true");
  });

  it("switches tab on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ExplorePage />);

    await user.click(screen.getByRole("tab", { name: "Businesses" }));

    expect(mockReplace).toHaveBeenCalledWith(
      expect.stringContaining("tab=businesses"),
      expect.objectContaining({ scroll: false }),
    );
  });
});
