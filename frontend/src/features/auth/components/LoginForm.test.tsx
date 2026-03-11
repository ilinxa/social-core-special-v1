import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { LoginForm } from "./LoginForm";

// Mock next/navigation
const mockSearchParams = vi.fn(() => new URLSearchParams());
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => mockSearchParams(),
}));

// Mock the login mutation
const mockMutateAsync = vi.fn();
vi.mock("@/features/auth/hooks/use-auth-mutations", () => ({
  useLogin: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
  useGoogleOAuth: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useAppleOAuth: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all form fields", () => {
    renderWithProviders(<LoginForm />);

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
    expect(screen.getByText(/sign up/i)).toBeInTheDocument();
  });

  it("shows validation errors for empty fields", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/enter a valid email/i)).toBeInTheDocument();
    });
  });

  it("calls login mutation with valid data", async () => {
    mockMutateAsync.mockResolvedValue({});
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123",
      });
    });
  });

  it("displays invalid credentials error", async () => {
    const { ApiError } = await import("@/lib/api-client");
    mockMutateAsync.mockRejectedValue(
      new ApiError(401, "Invalid credentials", "invalid_credentials"),
    );

    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "wrongpassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
    });
  });

  it("displays rate limit error", async () => {
    const { ApiError } = await import("@/lib/api-client");
    mockMutateAsync.mockRejectedValue(
      new ApiError(429, "Rate limited", "rate_limit_exceeded", { retry_after: 30 }),
    );

    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/too many attempts.*30 seconds/i)).toBeInTheDocument();
    });
  });

  it("has OAuth buttons", () => {
    renderWithProviders(<LoginForm />);

    expect(screen.getByRole("button", { name: /google/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apple/i })).toBeInTheDocument();
  });

  it("shows verified banner when ?verified=true", () => {
    mockSearchParams.mockReturnValue(new URLSearchParams("verified=true"));

    renderWithProviders(<LoginForm />);

    expect(
      screen.getByText(/email verified successfully/i),
    ).toBeInTheDocument();
  });
});
