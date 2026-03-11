// =============================================================================
// AUTH FEATURE TYPES — Matches backend apps.auth.serializers
// =============================================================================

// --- Request Types ---

export interface LoginCredentials {
  email: string;
  password: string;
  device_id?: string;
  device_type?: "web" | "ios" | "android" | "desktop" | "unknown";
  device_name?: string;
}

export interface RegisterData extends LoginCredentials {
  username: string;
  referred_by?: string;
}

export interface VerifyEmailData {
  email: string;
  code: string;
}

export interface ResendVerificationData {
  email: string;
}

export interface PasswordResetData {
  email: string;
}

export interface PasswordResetConfirmData {
  token: string;
  new_password: string;
}

export interface PasswordChangeData {
  current_password: string;
  new_password: string;
}

// --- Response Types ---

export interface MessageResponse {
  message: string;
}

export interface VerifyEmailResponse {
  message: string;
  user_id: string;
}

export interface LogoutAllResponse {
  message: string;
  sessions_revoked: number;
}

export interface TokenRefreshResponse {
  access_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
  token_type: "Bearer";
}

export interface OAuthInitResponse {
  authorization_url: string;
}

// --- Session Types ---

export interface DeviceSession {
  id: string;
  device_id: string;
  device_name: string;
  device_type: "web" | "ios" | "android" | "desktop" | "unknown";
  ip_address: string | null;
  location: string;
  last_activity: string;
  is_active: boolean;
  is_current: boolean;
  created_at: string;
}
