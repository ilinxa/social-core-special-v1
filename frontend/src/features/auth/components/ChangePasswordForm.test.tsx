import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutateAsync = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/features/auth/hooks/use-auth-mutations", () => ({
  usePasswordChange: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ChangePasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderForm() {
    const { ChangePasswordForm } = await import(
      "@/features/auth/components/ChangePasswordForm"
    );
    return renderWithProviders(<ChangePasswordForm />);
  }

  it("renders both password fields", async () => {
    await renderForm();

    expect(screen.getByLabelText("Current Password")).toBeInTheDocument();
    expect(screen.getByLabelText("New Password")).toBeInTheDocument();
  });

  it("shows validation error for empty current password", async () => {
    const user = userEvent.setup();

    await renderForm();

    // Submit without filling anything
    await user.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/current password is required/i),
      ).toBeInTheDocument();
    });

    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("calls mutation with valid data", async () => {
    mockMutateAsync.mockResolvedValue(undefined);
    const user = userEvent.setup();

    await renderForm();

    await user.type(screen.getByLabelText("Current Password"), "oldPass123!");
    await user.type(screen.getByLabelText("New Password"), "newSecurePass1!");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        current_password: "oldPass123!",
        new_password: "newSecurePass1!",
      });
    });
  });

  it("shows incorrect password error on invalid_credentials", async () => {
    const user = userEvent.setup();

    const { ApiError } = await import("@/lib/api-client");
    mockMutateAsync.mockRejectedValue(
      new ApiError(401, "Invalid credentials", "invalid_credentials"),
    );

    await renderForm();

    await user.type(screen.getByLabelText("Current Password"), "wrongPass1!");
    await user.type(screen.getByLabelText("New Password"), "newSecurePass1!");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/current password is incorrect/i),
      ).toBeInTheDocument();
    });
  });
});
