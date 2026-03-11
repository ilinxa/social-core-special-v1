import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { VerifyEmailForm } from "./VerifyEmailForm";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams("email=test@example.com"),
}));

const mockVerifyAsync = vi.fn();
const mockResendMutate = vi.fn();

vi.mock("@/features/auth/hooks/use-auth-mutations", () => ({
  useVerifyEmail: () => ({
    mutateAsync: mockVerifyAsync,
    isPending: false,
  }),
  useResendVerification: () => ({
    mutate: mockResendMutate,
    isPending: false,
  }),
}));

describe("VerifyEmailForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with pre-filled email", () => {
    renderWithProviders(<VerifyEmailForm />);

    expect(screen.getByLabelText("Email")).toHaveValue("test@example.com");
    expect(screen.getByLabelText("Verification Code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /verify email/i })).toBeInTheDocument();
    expect(screen.getByText(/resend code/i)).toBeInTheDocument();
  });

  it("email field is disabled when pre-filled from params", () => {
    renderWithProviders(<VerifyEmailForm />);
    expect(screen.getByLabelText("Email")).toBeDisabled();
  });

  it("shows validation error for invalid code", async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerifyEmailForm />);

    await user.type(screen.getByLabelText("Verification Code"), "abc");
    await user.click(screen.getByRole("button", { name: /verify email/i }));

    await waitFor(() => {
      expect(screen.getByText(/6 digits/i)).toBeInTheDocument();
    });
  });

  it("calls verify mutation with valid code", async () => {
    mockVerifyAsync.mockResolvedValue({});
    const user = userEvent.setup();
    renderWithProviders(<VerifyEmailForm />);

    await user.type(screen.getByLabelText("Verification Code"), "123456");
    await user.click(screen.getByRole("button", { name: /verify email/i }));

    await waitFor(() => {
      expect(mockVerifyAsync).toHaveBeenCalledWith({
        email: "test@example.com",
        code: "123456",
      });
    });
  });
});
