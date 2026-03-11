import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockUser = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "john@example.com",
  username: "johndoe",
  is_active: true,
  is_verified: true,
  profile: { display_name: "John Doe" },
};

vi.mock("@/stores/auth-store", () => ({
  useUser: vi.fn(() => mockUser),
  useAuthStore: vi.fn((selector: (s: unknown) => unknown) =>
    selector({ user: mockUser, isAuthenticated: true, isInitialized: true, logout: vi.fn() }),
  ),
}));

const mockUpdateUsernameMutateAsync = vi.fn();
const mockDeactivateMutateAsync = vi.fn();

vi.mock("@/features/users/hooks/use-user-mutations", () => ({
  useUpdateUsername: vi.fn(() => ({
    mutateAsync: mockUpdateUsernameMutateAsync,
    isPending: false,
  })),
  useDeactivateAccount: vi.fn(() => ({
    mutateAsync: mockDeactivateMutateAsync,
    isPending: false,
  })),
}));

vi.mock("@/features/users/hooks/use-username-check", () => ({
  useUsernameCheck: vi.fn(() => ({
    isChecking: false,
    isAvailable: null,
    isCurrent: true,
  })),
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdateUsernameMutateAsync.mockResolvedValue({});
    mockDeactivateMutateAsync.mockResolvedValue({});
  });

  async function renderPage() {
    const mod = await import("./page");
    return renderWithProviders(<mod.default />);
  }

  it("renders settings heading", async () => {
    await renderPage();
    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
  });

  it("renders username section with current username", async () => {
    await renderPage();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByDisplayValue("johndoe")).toBeInTheDocument();
  });

  it("renders danger zone section", async () => {
    await renderPage();
    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deactivate" })).toBeInTheDocument();
  });

  it("disables Update Username button when username unchanged", async () => {
    await renderPage();
    const btn = screen.getByRole("button", { name: /update username/i });
    expect(btn).toBeDisabled();
  });

  it("enables Update Username button when username changed", async () => {
    const user = userEvent.setup();
    await renderPage();

    const input = screen.getByDisplayValue("johndoe");
    await user.clear(input);
    await user.type(input, "newusername");

    const btn = screen.getByRole("button", { name: /update username/i });
    expect(btn).toBeEnabled();
  });

  it("calls update username mutation on submit", async () => {
    const user = userEvent.setup();
    await renderPage();

    const input = screen.getByDisplayValue("johndoe");
    await user.clear(input);
    await user.type(input, "newusername");
    await user.click(screen.getByRole("button", { name: /update username/i }));

    await waitFor(() => {
      expect(mockUpdateUsernameMutateAsync).toHaveBeenCalledWith({ username: "newusername" });
    });
  });

  it("opens deactivation dialog on button click", async () => {
    const user = userEvent.setup();
    await renderPage();

    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    expect(screen.getByText("Deactivate your account?")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/type 'deactivate'/i)).toBeInTheDocument();
  });

  it("disables Deactivate Account button until confirmation typed", async () => {
    const user = userEvent.setup();
    await renderPage();

    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    const confirmBtn = screen.getByRole("button", { name: /deactivate account/i });
    expect(confirmBtn).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/type 'deactivate'/i), "deactivate");
    expect(confirmBtn).toBeEnabled();
  });

  it("calls deactivate mutation and redirects on confirm", async () => {
    const user = userEvent.setup();
    await renderPage();

    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    await user.type(screen.getByPlaceholderText(/type 'deactivate'/i), "deactivate");
    await user.click(screen.getByRole("button", { name: /deactivate account/i }));

    await waitFor(() => {
      expect(mockDeactivateMutateAsync).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });
});
