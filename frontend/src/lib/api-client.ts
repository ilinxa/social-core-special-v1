import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import type { ApiErrorCode, ApiErrorResponse } from "@/types";
import { clearSessionCookie } from "@/lib/session-cookie";

// =============================================================================
// API ERROR CLASS
// =============================================================================

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isNotFound() {
    return this.status === 404;
  }

  get isUnauthorized() {
    return this.status === 401;
  }

  get isForbidden() {
    return this.status === 403;
  }

  get isValidation() {
    return this.status === 400 && this.code === "validation_error";
  }

  get isConflict() {
    return this.status === 409;
  }

  get isRateLimited() {
    return this.status === 429;
  }

  get retryAfter(): number | undefined {
    if (this.isRateLimited && this.details) {
      return this.details.retry_after as number | undefined;
    }
    return undefined;
  }
}

// =============================================================================
// TOKEN STORE (in-memory only — never localStorage)
// =============================================================================

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function clearTokens(): void {
  accessToken = null;
  cancelProactiveRefresh();
}

// =============================================================================
// PROACTIVE TOKEN REFRESH — Refresh before expiry to avoid 401 roundtrips
// =============================================================================

let refreshTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Schedule a proactive token refresh at 80% of the token lifetime.
 * For a 15-minute (900s) token, this refreshes at ~12 minutes.
 */
export function scheduleProactiveRefresh(expiresInSeconds: number): void {
  cancelProactiveRefresh();

  if (typeof window === "undefined" || expiresInSeconds <= 0) return;

  const refreshAtMs = Math.floor(expiresInSeconds * 0.8) * 1000;

  refreshTimer = setTimeout(async () => {
    refreshTimer = null;
    try {
      const { getDeviceInfo } = await import("@/lib/device-info");
      const response = await axios.post(
        `/api/v1/auth/refresh/`,
        getDeviceInfo(),
        { withCredentials: true },
      );

      const newToken = response.data?.access_token;
      if (typeof newToken === "string" && newToken) {
        setAccessToken(newToken);

        const newExpiry = response.data?.access_expires_in;
        if (typeof newExpiry === "number" && newExpiry > 0) {
          scheduleProactiveRefresh(newExpiry);
        }
      }
    } catch {
      // Proactive refresh failed silently — the reactive interceptor
      // will handle the 401 when the next API call happens.
    }
  }, refreshAtMs);
}

export function cancelProactiveRefresh(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

// =============================================================================
// AXIOS INSTANCE
// =============================================================================

export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// =============================================================================
// REQUEST INTERCEPTOR — Attach access token
// =============================================================================

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// =============================================================================
// RESPONSE INTERCEPTOR — Handle errors and token refresh
// =============================================================================

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else if (token) {
      resolve(token);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorResponse>) => {
    const originalRequest = error.config;
    if (!originalRequest || !error.response) {
      return Promise.reject(new ApiError(0, "Network error", "network_error"));
    }

    const { status, data } = error.response;
    const errorCode = (data?.error?.code ?? "unknown") as ApiErrorCode;
    const errorMessage = data?.error?.message ?? "An unexpected error occurred";
    const errorDetails = data?.error?.details;

    // Token expired, missing, or invalid — attempt refresh via HttpOnly cookie
    const isRecoverable401 =
      status === 401 &&
      (errorCode === "token_expired" || errorCode === "not_authenticated" || errorCode === "token_invalid");

    if (
      isRecoverable401 &&
      !(originalRequest as InternalAxiosRequestConfig & { _retry?: boolean })._retry
    ) {
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        });
      }

      (originalRequest as InternalAxiosRequestConfig & { _retry?: boolean })._retry = true;
      isRefreshing = true;

      try {
        // Web clients: refresh token is in HttpOnly cookie, sent automatically
        // Import inline to avoid circular dependency (api-client ← device-info is safe)
        const { getDeviceInfo } = await import("@/lib/device-info");
        const response = await axios.post(
          `/api/v1/auth/refresh/`,
          getDeviceInfo(),
          { withCredentials: true },
        );

        const newAccessToken = response.data?.access_token;
        if (typeof newAccessToken !== "string" || !newAccessToken) {
          throw new Error("Invalid refresh response");
        }
        setAccessToken(newAccessToken);

        const newExpiry = response.data?.access_expires_in;
        if (typeof newExpiry === "number" && newExpiry > 0) {
          scheduleProactiveRefresh(newExpiry);
        }

        processQueue(null, newAccessToken);

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // 429 on refresh = rate limited, NOT an auth failure.
        // Don't clear session or redirect — just fail the original request.
        const is429 =
          refreshError instanceof AxiosError && refreshError.response?.status === 429;
        if (is429) {
          processQueue(refreshError);
          return Promise.reject(
            new ApiError(429, "Too many requests", "rate_limit_exceeded"),
          );
        }

        processQueue(refreshError);
        clearTokens();
        clearSessionCookie();

        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Token already used — security breach, force re-login
    if (status === 401 && errorCode === "token_already_used") {
      clearTokens();
      clearSessionCookie();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(new ApiError(status, errorMessage, errorCode, errorDetails));
  },
);
