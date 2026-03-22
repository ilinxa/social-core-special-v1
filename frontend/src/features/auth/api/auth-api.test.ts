import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  loginApi,
  registerApi,
  logoutApi,
  logoutAllApi,
  silentRefreshApi,
  verifyEmailApi,
  resendVerificationApi,
  passwordResetApi,
  passwordResetConfirmApi,
  passwordChangeApi,
  fetchSessionsApi,
  revokeSessionApi,
  googleOAuthInitApi,
  appleOAuthInitApi,
} from "./auth-api";

import type { AuthResponse, User } from "@/types";
import type { TokenRefreshResponse } from "@/features/auth/types";

// Mock the api-client module
vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
  setAccessToken: vi.fn(),
  clearTokens: vi.fn(),
  scheduleProactiveRefresh: vi.fn(),
}));

// Mock device-info module
vi.mock("@/lib/device-info", () => ({
  getDeviceInfo: () => ({
    device_id: "test-device-id",
    device_type: "web" as const,
    device_name: "Test Browser",
  }),
  getDeviceId: () => "test-device-id",
}));

// Import mocked functions
import { apiClient, setAccessToken, clearTokens, scheduleProactiveRefresh } from "@/lib/api-client";

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

const mockTokenResponse: TokenRefreshResponse = {
  access_token: "new-access-token",
  access_expires_in: 900,
  refresh_expires_in: 604800,
  token_type: "Bearer",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("loginApi", () => {
  it("calls POST /auth/login/ and sets access token", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockAuthResponse });

    const result = await loginApi({ email: "test@example.com", password: "password123" });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/login/", {
      email: "test@example.com",
      password: "password123",
      device_id: "test-device-id",
      device_type: "web",
      device_name: "Test Browser",
    });
    expect(setAccessToken).toHaveBeenCalledWith("mock-access-token");
    expect(scheduleProactiveRefresh).toHaveBeenCalledWith(900);
    expect(result).toEqual(mockAuthResponse);
  });
});

describe("registerApi", () => {
  it("calls POST /auth/register/ and sets access token", async () => {
    const registerResponse = { ...mockAuthResponse, is_new_user: true };
    vi.mocked(apiClient.post).mockResolvedValue({ data: registerResponse });

    const result = await registerApi({
      email: "new@example.com",
      username: "newuser",
      password: "password123",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/register/", {
      email: "new@example.com",
      username: "newuser",
      password: "password123",
      device_id: "test-device-id",
      device_type: "web",
      device_name: "Test Browser",
    });
    expect(setAccessToken).toHaveBeenCalledWith("mock-access-token");
    expect(scheduleProactiveRefresh).toHaveBeenCalledWith(900);
    expect(result.is_new_user).toBe(true);
  });
});

describe("silentRefreshApi", () => {
  it("calls POST /auth/refresh/ and sets access token", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockTokenResponse });

    const result = await silentRefreshApi();

    expect(apiClient.post).toHaveBeenCalledWith("/auth/refresh/", {
      device_id: "test-device-id",
      device_type: "web",
      device_name: "Test Browser",
    });
    expect(setAccessToken).toHaveBeenCalledWith("new-access-token");
    expect(scheduleProactiveRefresh).toHaveBeenCalledWith(900);
    expect(result).toEqual(mockTokenResponse);
  });
});

describe("logoutApi", () => {
  it("calls POST /auth/logout/ and clears tokens", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { message: "Logged out successfully" },
    });

    const result = await logoutApi();

    expect(apiClient.post).toHaveBeenCalledWith("/auth/logout/");
    expect(clearTokens).toHaveBeenCalled();
    expect(result.message).toBe("Logged out successfully");
  });
});

describe("logoutAllApi", () => {
  it("calls POST /auth/logout-all/ and clears tokens", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { message: "Logged out from 3 session(s)", sessions_revoked: 3 },
    });

    const result = await logoutAllApi();

    expect(apiClient.post).toHaveBeenCalledWith("/auth/logout-all/");
    expect(clearTokens).toHaveBeenCalled();
    expect(result.sessions_revoked).toBe(3);
  });
});

describe("verifyEmailApi", () => {
  it("calls POST /auth/verify-email/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { message: "Email verified successfully", user_id: mockUser.id },
    });

    const result = await verifyEmailApi({ email: "test@example.com", code: "123456" });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/verify-email/", {
      email: "test@example.com",
      code: "123456",
    });
    expect(result.user_id).toBe(mockUser.id);
  });
});

describe("resendVerificationApi", () => {
  it("calls POST /auth/resend-verification/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { message: "If an account exists with this email, a verification link has been sent" },
    });

    await resendVerificationApi({ email: "test@example.com" });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/resend-verification/", {
      email: "test@example.com",
    });
  });
});

describe("passwordResetApi", () => {
  it("calls POST /auth/password/reset/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        message: "If an account exists with this email, a password reset link has been sent",
      },
    });

    await passwordResetApi({ email: "test@example.com" });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/password/reset/", {
      email: "test@example.com",
    });
  });
});

describe("passwordResetConfirmApi", () => {
  it("calls POST /auth/password/reset/confirm/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { message: "Password has been reset successfully" },
    });

    await passwordResetConfirmApi({
      token: "550e8400-e29b-41d4-a716-446655440000",
      new_password: "newpassword123",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/password/reset/confirm/", {
      token: "550e8400-e29b-41d4-a716-446655440000",
      new_password: "newpassword123",
    });
  });
});

describe("passwordChangeApi", () => {
  it("calls POST /auth/password/change/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { message: "Password changed successfully" },
    });

    await passwordChangeApi({
      current_password: "oldpassword",
      new_password: "newpassword123",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/password/change/", {
      current_password: "oldpassword",
      new_password: "newpassword123",
    });
  });
});

describe("fetchSessionsApi", () => {
  it("calls GET /auth/sessions/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const result = await fetchSessionsApi();

    expect(apiClient.get).toHaveBeenCalledWith("/auth/sessions/");
    expect(result).toEqual([]);
  });
});

describe("revokeSessionApi", () => {
  it("calls DELETE /auth/sessions/:id/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({
      data: { message: "Session revoked successfully" },
    });

    const result = await revokeSessionApi("session-id");

    expect(apiClient.delete).toHaveBeenCalledWith("/auth/sessions/session-id/");
    expect(result.message).toBe("Session revoked successfully");
  });
});

describe("googleOAuthInitApi", () => {
  it("calls GET /auth/oauth/google/ with params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { authorization_url: "https://accounts.google.com/..." },
    });

    const result = await googleOAuthInitApi("/dashboard");

    expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining("/auth/oauth/google/"));
    expect(result.authorization_url).toBe("https://accounts.google.com/...");
  });
});

describe("appleOAuthInitApi", () => {
  it("calls GET /auth/oauth/apple/ with params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { authorization_url: "https://appleid.apple.com/..." },
    });

    const result = await appleOAuthInitApi("/dashboard");

    expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining("/auth/oauth/apple/"));
    expect(result.authorization_url).toBe("https://appleid.apple.com/...");
  });
});

// =============================================================================
// ERROR PROPAGATION
// =============================================================================

describe("error propagation", () => {
  it("loginApi propagates rejection on failure", async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("Invalid credentials"));

    await expect(
      loginApi({ email: "test@example.com", password: "wrong" }),
    ).rejects.toThrow("Invalid credentials");
  });

  it("registerApi propagates rejection on failure", async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("Email already exists"));

    await expect(
      registerApi({ email: "existing@example.com", username: "existinguser", password: "pass123" }),
    ).rejects.toThrow("Email already exists");
  });

  it("silentRefreshApi propagates rejection on failure", async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("Token expired"));

    await expect(silentRefreshApi()).rejects.toThrow("Token expired");
  });

  it("fetchSessionsApi propagates rejection on failure", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("Unauthorized"));

    await expect(fetchSessionsApi()).rejects.toThrow("Unauthorized");
  });
});
