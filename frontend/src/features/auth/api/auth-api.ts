import { apiClient, setAccessToken, clearTokens, scheduleProactiveRefresh } from "@/lib/api-client";
import { getDeviceInfo } from "@/lib/device-info";
import { setSessionCookie, clearSessionCookie } from "@/lib/session-cookie";
import type { AuthResponse } from "@/types";
import type {
  DeviceSession,
  LoginCredentials,
  LogoutAllResponse,
  MessageResponse,
  OAuthInitResponse,
  PasswordChangeData,
  PasswordResetConfirmData,
  PasswordResetData,
  RegisterData,
  ResendVerificationData,
  TokenRefreshResponse,
  VerifyEmailData,
  VerifyEmailResponse,
} from "@/features/auth/types";

export { setSessionCookie, clearSessionCookie };

// =============================================================================
// CORE AUTH
// =============================================================================

export async function loginApi(data: LoginCredentials): Promise<AuthResponse> {
  const deviceInfo = getDeviceInfo();
  const response = await apiClient.post<AuthResponse>("/auth/login/", {
    ...data,
    ...deviceInfo,
  });
  setAccessToken(response.data.tokens.access_token);
  scheduleProactiveRefresh(response.data.tokens.access_expires_in);
  setSessionCookie();
  return response.data;
}

export async function registerApi(data: RegisterData): Promise<AuthResponse> {
  const deviceInfo = getDeviceInfo();
  const response = await apiClient.post<AuthResponse>("/auth/register/", {
    ...data,
    ...deviceInfo,
  });
  setAccessToken(response.data.tokens.access_token);
  scheduleProactiveRefresh(response.data.tokens.access_expires_in);
  setSessionCookie();
  return response.data;
}

export async function silentRefreshApi(): Promise<TokenRefreshResponse> {
  const deviceInfo = getDeviceInfo();
  const response = await apiClient.post<TokenRefreshResponse>("/auth/refresh/", deviceInfo);
  setAccessToken(response.data.access_token);
  scheduleProactiveRefresh(response.data.access_expires_in);
  setSessionCookie();
  return response.data;
}

export async function logoutApi(): Promise<MessageResponse> {
  const response = await apiClient.post<MessageResponse>("/auth/logout/");
  clearTokens();
  clearSessionCookie();
  return response.data;
}

export async function logoutAllApi(): Promise<LogoutAllResponse> {
  const response = await apiClient.post<LogoutAllResponse>("/auth/logout-all/");
  clearTokens();
  clearSessionCookie();
  return response.data;
}

// =============================================================================
// EMAIL VERIFICATION
// =============================================================================

export async function verifyEmailApi(data: VerifyEmailData): Promise<VerifyEmailResponse> {
  const response = await apiClient.post<VerifyEmailResponse>("/auth/verify-email/", data);
  return response.data;
}

export async function resendVerificationApi(
  data: ResendVerificationData,
): Promise<MessageResponse> {
  const response = await apiClient.post<MessageResponse>("/auth/resend-verification/", data);
  return response.data;
}

// =============================================================================
// PASSWORD
// =============================================================================

export async function passwordResetApi(data: PasswordResetData): Promise<MessageResponse> {
  const response = await apiClient.post<MessageResponse>("/auth/password/reset/", data);
  return response.data;
}

export async function passwordResetConfirmApi(
  data: PasswordResetConfirmData,
): Promise<MessageResponse> {
  const response = await apiClient.post<MessageResponse>("/auth/password/reset/confirm/", data);
  return response.data;
}

export async function passwordChangeApi(data: PasswordChangeData): Promise<MessageResponse> {
  const response = await apiClient.post<MessageResponse>("/auth/password/change/", data);
  return response.data;
}

// =============================================================================
// SESSIONS
// =============================================================================

export async function fetchSessionsApi(): Promise<DeviceSession[]> {
  const response = await apiClient.get<DeviceSession[]>("/auth/sessions/");
  return response.data;
}

export async function revokeSessionApi(sessionId: string): Promise<MessageResponse> {
  const response = await apiClient.delete<MessageResponse>(`/auth/sessions/${sessionId}/`);
  return response.data;
}

// =============================================================================
// OAUTH
// =============================================================================

export async function googleOAuthInitApi(redirectTo?: string): Promise<OAuthInitResponse> {
  const params = new URLSearchParams({ device_type: "web" });
  if (redirectTo) params.set("redirect_to", redirectTo);
  const response = await apiClient.get<OAuthInitResponse>(
    `/auth/oauth/google/?${params.toString()}`,
  );
  return response.data;
}

export async function appleOAuthInitApi(redirectTo?: string): Promise<OAuthInitResponse> {
  const params = new URLSearchParams({ device_type: "web" });
  if (redirectTo) params.set("redirect_to", redirectTo);
  const response = await apiClient.get<OAuthInitResponse>(
    `/auth/oauth/apple/?${params.toString()}`,
  );
  return response.data;
}
