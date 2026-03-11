import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { clearTokens } from "@/lib/api-client";
import { clearSessionCookie } from "@/lib/session-cookie";
import { reportError } from "@/lib/error-reporting";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/stores/auth-store";
import { useMembershipStore } from "@/stores/membership-store";
import { fetchMyMembershipsApi } from "@/features/auth/api/membership-api";
import {
  appleOAuthInitApi,
  googleOAuthInitApi,
  loginApi,
  logoutAllApi,
  logoutApi,
  passwordChangeApi,
  passwordResetApi,
  passwordResetConfirmApi,
  registerApi,
  resendVerificationApi,
  revokeSessionApi,
  verifyEmailApi,
} from "@/features/auth/api/auth-api";

// =============================================================================
// CORE AUTH MUTATIONS
// =============================================================================

export function useLogin() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  const setMemberships = useMembershipStore((s) => s.setMemberships);
  const router = useRouter();
  const searchParams = useSearchParams();

  return useMutation({
    mutationFn: loginApi,
    onSuccess: async (data) => {
      setUser(data.user);
      queryClient.setQueryData(queryKeys.users.me(), data.user);
      try {
        const memberships = await fetchMyMembershipsApi();
        setMemberships(memberships);
      } catch {
        // Non-critical: memberships will be fetched on next navigation
      }
      const callbackUrl = searchParams.get("callbackUrl");
      router.push(callbackUrl && callbackUrl.startsWith("/") ? callbackUrl : "/home");
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  const setMemberships = useMembershipStore((s) => s.setMemberships);
  const router = useRouter();

  return useMutation({
    mutationFn: registerApi,
    onSuccess: (data) => {
      setUser(data.user);
      queryClient.setQueryData(queryKeys.users.me(), data.user);
      setMemberships([]);
      router.push("/verify-email");
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const clearUser = useAuthStore((s) => s.clearUser);
  const clearMemberships = useMembershipStore((s) => s.clearMemberships);
  const router = useRouter();

  return useMutation({
    mutationFn: logoutApi,
    onSuccess: () => {
      clearUser();
      clearMemberships();
      queryClient.clear();
      router.push("/login");
    },
    onError: () => {
      clearUser();
      clearMemberships();
      clearTokens();
      clearSessionCookie();
      queryClient.clear();
      router.push("/login");
    },
  });
}

export function useLogoutAll() {
  const queryClient = useQueryClient();
  const clearUser = useAuthStore((s) => s.clearUser);
  const clearMemberships = useMembershipStore((s) => s.clearMemberships);
  const router = useRouter();

  return useMutation({
    mutationFn: logoutAllApi,
    onSuccess: (data) => {
      toast.success(data.message);
      clearUser();
      clearMemberships();
      queryClient.clear();
      router.push("/login");
    },
    onError: () => {
      toast.error("Failed to log out all sessions. Please try again.");
    },
  });
}

// =============================================================================
// EMAIL VERIFICATION MUTATIONS
// =============================================================================

export function useVerifyEmail() {
  return useMutation({
    mutationFn: verifyEmailApi,
    onSuccess: () => {
      toast.success("Email verified successfully");
    },
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: resendVerificationApi,
    onSuccess: (data) => {
      toast.success(data.message);
    },
    onError: () => {
      toast.error("Failed to resend verification email. Please try again.");
    },
  });
}

// =============================================================================
// PASSWORD MUTATIONS
// =============================================================================

export function usePasswordReset() {
  return useMutation({
    mutationFn: passwordResetApi,
    onSuccess: (data) => {
      toast.success(data.message);
    },
  });
}

export function usePasswordResetConfirm() {
  const router = useRouter();

  return useMutation({
    mutationFn: passwordResetConfirmApi,
    onSuccess: () => {
      toast.success("Password has been reset. Please sign in.");
      router.push("/login");
    },
  });
}

export function usePasswordChange() {
  return useMutation({
    mutationFn: passwordChangeApi,
    onSuccess: () => {
      toast.success("Password changed successfully");
    },
  });
}

// =============================================================================
// SESSION MUTATIONS
// =============================================================================

export function useRevokeSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: revokeSessionApi,
    onSuccess: () => {
      toast.success("Session revoked");
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.sessions() });
    },
    onError: () => {
      toast.error("Failed to revoke session. Please try again.");
    },
  });
}

// =============================================================================
// OAUTH MUTATIONS
// =============================================================================

function validateOAuthUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

export function useGoogleOAuth() {
  return useMutation({
    mutationFn: googleOAuthInitApi,
    onSuccess: (data) => {
      if (validateOAuthUrl(data.authorization_url)) {
        window.location.href = data.authorization_url;
      } else {
        reportError(new Error("Invalid Google OAuth authorization URL"), {
          action: "oauth_redirect",
        });
      }
    },
    onError: () => {
      toast.error("Failed to connect with Google. Please try again.");
    },
  });
}

export function useAppleOAuth() {
  return useMutation({
    mutationFn: appleOAuthInitApi,
    onSuccess: (data) => {
      if (validateOAuthUrl(data.authorization_url)) {
        window.location.href = data.authorization_url;
      } else {
        reportError(new Error("Invalid Apple OAuth authorization URL"), {
          action: "oauth_redirect",
        });
      }
    },
    onError: () => {
      toast.error("Failed to connect with Apple. Please try again.");
    },
  });
}
