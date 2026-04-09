/**
 * Governance API client — Axios instance for governance endpoints.
 *
 * Uses the governance token from sessionStorage (not the standard
 * access token from in-memory store). Governance endpoints live at
 * /api/v1/governance/* and require a governance-scoped JWT.
 *
 * On 403 governance_auth_required: clears token, redirects to authenticate.
 */

import axios from "axios";
import type { InternalAxiosRequestConfig } from "axios";

import { getGovernanceToken, clearGovernanceToken } from "@/lib/governance-token";

export const governanceApiClient = axios.create({
  baseURL: "/api/v1/governance",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// Attach governance token to every request
governanceApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getGovernanceToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
);

// Handle governance auth errors
governanceApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window === "undefined") return Promise.reject(error);

    const status = error?.response?.status;
    const code = error?.response?.data?.error?.code;

    if (
      status === 403 &&
      (code === "governance_auth_required" || code === "permission_denied")
    ) {
      clearGovernanceToken();
      const callbackUrl = encodeURIComponent(window.location.pathname);
      window.location.href = `/gconsole/authenticate?callbackUrl=${callbackUrl}`;
      return new Promise(() => {}); // Never resolves — page is navigating
    }

    if (status === 401) {
      // Governance token expired or standard token invalid
      clearGovernanceToken();
      const callbackUrl = encodeURIComponent(window.location.pathname);
      window.location.href = `/gconsole/authenticate?callbackUrl=${callbackUrl}`;
      return new Promise(() => {});
    }

    return Promise.reject(error);
  },
);
