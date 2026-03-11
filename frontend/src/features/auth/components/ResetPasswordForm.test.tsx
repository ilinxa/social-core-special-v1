import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutateAsync = vi.fn();
let mockTokenValue: string | null = null;

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => (key === "token" ? mockTokenValue : null),
  }),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/features/auth/hooks/use-auth-mutations", () => ({
  usePasswordResetConfirm: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ResetPasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTokenValue = null;
  });

  async function renderForm() {
    const { ResetPasswordForm } = await import(
      "@/features/auth/components/ResetPasswordForm"
    );
    return renderWithProviders(<ResetPasswordForm />);
  }

  it("shows invalid token message when no token in URL", async () => {
    mockTokenValue = null;

    await renderForm();

    expect(
      screen.getByText(/invalid reset link/i),
    ).toBeInTheDocument();

    // The password field should NOT be rendered
    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
  });

  it("renders form with new password field when token is present", async () => {
    mockTokenValue = "550e8400-e29b-41d4-a716-446655440000";

    await renderForm();

    expect(screen.getByLabelText("New Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset password/i })).toBeInTheDocument();
  });

  it("shows validation error for short password", async () => {
    mockTokenValue = "550e8400-e29b-41d4-a716-446655440000";
    const user = userEvent.setup();

    await renderForm();

    const passwordInput = screen.getByLabelText("New Password");
    await user.type(passwordInput, "short");
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Password must be at least 8 characters"),
      ).toBeInTheDocument();
    });

    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("calls mutation with valid data", async () => {
    const token = "550e8400-e29b-41d4-a716-446655440000";
    mockTokenValue = token;
    mockMutateAsync.mockResolvedValue(undefined);
    const user = userEvent.setup();

    await renderForm();

    const passwordInput = screen.getByLabelText("New Password");
    await user.type(passwordInput, "newSecurePass1!");
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        token,
        new_password: "newSecurePass1!",
      });
    });
  });

  it("shows expired token error on not_found API response", async () => {
    mockTokenValue = "550e8400-e29b-41d4-a716-446655440000";
    const user = userEvent.setup();

    const { ApiError } = await import("@/lib/api-client");
    mockMutateAsync.mockRejectedValue(
      new ApiError(404, "Not found", "not_found"),
    );

    await renderForm();

    const passwordInput = screen.getByLabelText("New Password");
    await user.type(passwordInput, "newSecurePass1!");
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/invalid or has expired/i),
      ).toBeInTheDocument();
    });
  });
});
