/**
 * Governance token manager — sessionStorage-based.
 *
 * The governance token is a short-lived JWT (default 30 min) with
 * token_scope="governance". It lives in sessionStorage:
 * - Survives page refresh within the same tab
 * - Lost on tab close (per-tab isolation)
 * - Separate from the standard access token (in-memory Zustand)
 *
 * Decision 6: sessionStorage for governance token.
 */

const TOKEN_KEY = "governance_token";
const EXPIRY_KEY = "governance_token_expires_at";

export function setGovernanceToken(token: string, expiresIn: number): void {
  if (typeof window === "undefined") return;
  const expiresAt = Date.now() + expiresIn * 1000;
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(EXPIRY_KEY, expiresAt.toString());
}

export function getGovernanceToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) return null;

  // Check expiry
  if (!isGovernanceTokenValid()) {
    clearGovernanceToken();
    return null;
  }

  return token;
}

export function clearGovernanceToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(EXPIRY_KEY);
}

export function isGovernanceTokenValid(): boolean {
  if (typeof window === "undefined") return false;
  const token = sessionStorage.getItem(TOKEN_KEY);
  const expiresAt = sessionStorage.getItem(EXPIRY_KEY);
  if (!token || !expiresAt) return false;
  return Date.now() < Number(expiresAt);
}

export function getGovernanceTimeRemaining(): number {
  if (typeof window === "undefined") return 0;
  const expiresAt = sessionStorage.getItem(EXPIRY_KEY);
  if (!expiresAt) return 0;
  const remaining = Math.max(0, Number(expiresAt) - Date.now());
  return Math.floor(remaining / 1000);
}
