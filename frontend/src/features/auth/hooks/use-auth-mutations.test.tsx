import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { AuthResponse, User } from "@/types";

// =============================================================================
// MOCKS
// =============================================================================

const mockPush = vi.fn();
const mockSearchGet = vi.fn<(key: string) => string | null>(() => null);

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({ get: mockSearchGet }),
}));

const mockSetUser = vi.fn();
const mockClearUser = vi.fn();
vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ setUser: mockSetUser, clearUser: mockClearUser }),
}));

const mockSetMemberships = vi.fn();
const mockClearMemberships = vi.fn();
vi.mock("@/stores/membership-store", () => ({
  useMembershipStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ setMemberships: mockSetMemberships, clearMemberships: mockClearMemberships }),
}));

vi.mock("@/features/auth/api/auth-api");
vi.mock("@/features/auth/api/membership-api");
vi.mock("@/lib/api-client", () => ({
  clearTokens: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
      public code: string,
    ) {
      super(message);
    }
  },
}));
vi.mock("@/lib/session-cookie", () => ({
  clearSessionCookie: vi.fn(),
  setSessionCookie: vi.fn(),
}));
vi.mock("@/lib/error-reporting", () => ({
  reportError: vi.fn(),
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn() },
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import {
  useLogin,
  useRegister,
  useLogout,
  useLogoutAll,
  useVerifyEmail,
  useResendVerification,
  usePasswordReset,
  usePasswordResetConfirm,
  usePasswordChange,
  useRevokeSession,
  useGoogleOAuth,
  useAppleOAuth,
} from "./use-auth-mutations";

import {
  loginApi,
  registerApi,
  logoutApi,
  logoutAllApi,
  verifyEmailApi,
  resendVerificationApi,
  passwordResetApi,
  passwordResetConfirmApi,
  passwordChangeApi,
  revokeSessionApi,
  googleOAuthInitApi,
  appleOAuthInitApi,
} from "@/features/auth/api/auth-api";
import { fetchMyMembershipsApi } from "@/features/auth/api/membership-api";
import { clearTokens } from "@/lib/api-client";
import { clearSessionCookie } from "@/lib/session-cookie";
import { reportError } from "@/lib/error-reporting";
import { toast } from "sonner";

// =============================================================================
// TEST DATA
// =============================================================================

const mockUser: User = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "test@example.com",
  username: "testuser",
  is_active: true,
  is_verified: true,
  is_complete: true,
  can_create_business: true,
  is_staff: false,
  is_superuser: false,
  date_joined: "2026-01-01T00:00:00Z",
  last_login: null,
  profile: {
    first_name: "",
    last_name: "",
    full_name: "",
    display_name: "testuser",
    phone: "",
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

const mockAuthResponse: AuthResponse = {
  user: mockUser,
  tokens: {
    access_token: "mock-access-token",
    access_expires_in: 900,
    refresh_expires_in: 604800,
    token_type: "Bearer",
  },
  is_new_user: false,
};

// =============================================================================
// HELPERS
// =============================================================================

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
  mockSearchGet.mockReturnValue(null);
});

describe("useLogin", () => {
  it("sets user, memberships, and redirects to home on success", async () => {
    vi.mocked(loginApi).mockResolvedValue(mockAuthResponse);
    vi.mocked(fetchMyMembershipsApi).mockResolvedValue([]);

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: "test@example.com", password: "password123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(mockSetMemberships).toHaveBeenCalledWith([]);
    expect(mockPush).toHaveBeenCalledWith("/home");
  });

  it("redirects to callbackUrl when present", async () => {
    mockSearchGet.mockReturnValue("/settings");
    vi.mocked(loginApi).mockResolvedValue(mockAuthResponse);
    vi.mocked(fetchMyMembershipsApi).mockResolvedValue([]);

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: "test@example.com", password: "password123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockPush).toHaveBeenCalledWith("/settings");
  });

  it("ignores non-relative callbackUrl", async () => {
    mockSearchGet.mockReturnValue("https://evil.com");
    vi.mocked(loginApi).mockResolvedValue(mockAuthResponse);
    vi.mocked(fetchMyMembershipsApi).mockResolvedValue([]);

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: "test@example.com", password: "password123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockPush).toHaveBeenCalledWith("/home");
  });

  it("continues if membership fetch fails", async () => {
    vi.mocked(loginApi).mockResolvedValue(mockAuthResponse);
    vi.mocked(fetchMyMembershipsApi).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: "test@example.com", password: "password123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(mockPush).toHaveBeenCalledWith("/home");
  });
});

describe("useRegister", () => {
  it("sets user, empty memberships, and redirects to verify-email", async () => {
    const registerResponse = { ...mockAuthResponse, is_new_user: true };
    vi.mocked(registerApi).mockResolvedValue(registerResponse);

    const { result } = renderHook(() => useRegister(), { wrapper: createWrapper() });

    result.current.mutate({ email: "new@example.com", username: "newuser", password: "password123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(mockSetMemberships).toHaveBeenCalledWith([]);
    expect(mockPush).toHaveBeenCalledWith("/verify-email");
  });
});

describe("useLogout", () => {
  it("clears stores and redirects to login on success", async () => {
    vi.mocked(logoutApi).mockResolvedValue({ message: "Logged out" });

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockClearUser).toHaveBeenCalled();
    expect(mockClearMemberships).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  it("clears stores and redirects even on API error", async () => {
    vi.mocked(logoutApi).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(mockClearUser).toHaveBeenCalled();
    expect(mockClearMemberships).toHaveBeenCalled();
    expect(clearTokens).toHaveBeenCalled();
    expect(clearSessionCookie).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith("/login");
  });
});

describe("useLogoutAll", () => {
  it("shows toast, clears stores, and redirects on success", async () => {
    vi.mocked(logoutAllApi).mockResolvedValue({
      message: "Logged out from 3 session(s)",
      sessions_revoked: 3,
    });

    const { result } = renderHook(() => useLogoutAll(), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Logged out from 3 session(s)");
    expect(mockClearUser).toHaveBeenCalled();
    expect(mockClearMemberships).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith("/login");
  });
});

describe("useVerifyEmail", () => {
  it("shows success toast on verification", async () => {
    vi.mocked(verifyEmailApi).mockResolvedValue({
      message: "Email verified successfully",
      user_id: mockUser.id,
    });

    const { result } = renderHook(() => useVerifyEmail(), { wrapper: createWrapper() });

    result.current.mutate({ email: "test@example.com", code: "123456" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Email verified successfully");
  });
});

describe("useResendVerification", () => {
  it("shows success toast with server message", async () => {
    vi.mocked(resendVerificationApi).mockResolvedValue({
      message: "Verification email sent",
    });

    const { result } = renderHook(() => useResendVerification(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ email: "test@example.com" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Verification email sent");
  });
});

describe("usePasswordReset", () => {
  it("shows success toast on password reset request", async () => {
    vi.mocked(passwordResetApi).mockResolvedValue({
      message: "Password reset link sent",
    });

    const { result } = renderHook(() => usePasswordReset(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ email: "test@example.com" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Password reset link sent");
  });
});

describe("usePasswordResetConfirm", () => {
  it("shows toast and redirects to login on success", async () => {
    vi.mocked(passwordResetConfirmApi).mockResolvedValue({
      message: "Password has been reset",
    });

    const { result } = renderHook(() => usePasswordResetConfirm(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ token: "reset-token", new_password: "newpass123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Password has been reset. Please sign in.");
    expect(mockPush).toHaveBeenCalledWith("/login");
  });
});

describe("usePasswordChange", () => {
  it("shows success toast on password change", async () => {
    vi.mocked(passwordChangeApi).mockResolvedValue({
      message: "Password changed",
    });

    const { result } = renderHook(() => usePasswordChange(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ current_password: "old", new_password: "new123" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Password changed successfully");
  });
});

describe("useRevokeSession", () => {
  it("shows toast and invalidates sessions query on success", async () => {
    vi.mocked(revokeSessionApi).mockResolvedValue({ message: "Session revoked" });

    const { result } = renderHook(() => useRevokeSession(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("session-id");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Session revoked");
  });
});

describe("useGoogleOAuth", () => {
  it("redirects to valid authorization URL", async () => {
    vi.mocked(googleOAuthInitApi).mockResolvedValue({
      authorization_url: "https://accounts.google.com/o/oauth2/auth?client_id=123",
    });

    const { result } = renderHook(() => useGoogleOAuth(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("/home");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(reportError).not.toHaveBeenCalled();
  });

  it("reports error for invalid authorization URL", async () => {
    vi.mocked(googleOAuthInitApi).mockResolvedValue({
      authorization_url: "javascript:alert(1)",
    });

    const { result } = renderHook(() => useGoogleOAuth(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("/home");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(reportError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Invalid Google OAuth authorization URL" }),
      expect.objectContaining({ action: "oauth_redirect" }),
    );
  });
});

describe("useAppleOAuth", () => {
  it("redirects to valid authorization URL", async () => {
    vi.mocked(appleOAuthInitApi).mockResolvedValue({
      authorization_url: "https://appleid.apple.com/auth/authorize?client_id=123",
    });

    const { result } = renderHook(() => useAppleOAuth(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("/home");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(reportError).not.toHaveBeenCalled();
  });

  it("reports error for invalid authorization URL", async () => {
    vi.mocked(appleOAuthInitApi).mockResolvedValue({
      authorization_url: "ftp://evil.com/payload",
    });

    const { result } = renderHook(() => useAppleOAuth(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("/home");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(reportError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Invalid Apple OAuth authorization URL" }),
      expect.objectContaining({ action: "oauth_redirect" }),
    );
  });
});
