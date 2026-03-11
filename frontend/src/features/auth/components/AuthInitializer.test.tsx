import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { useAuthStore } from "@/stores/auth-store";
import { useMembershipStore } from "@/stores/membership-store";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockSilentRefresh = vi.fn();
const mockFetchCurrentUser = vi.fn();
const mockFetchMyMemberships = vi.fn();

vi.mock("@/features/auth/api/auth-api", () => ({
  silentRefreshApi: (...args: unknown[]) => mockSilentRefresh(...args),
  clearSessionCookie: vi.fn(),
}));

vi.mock("@/features/users/api/users-api", () => ({
  fetchCurrentUserApi: (...args: unknown[]) => mockFetchCurrentUser(...args),
}));

vi.mock("@/features/auth/api/membership-api", () => ({
  fetchMyMembershipsApi: (...args: unknown[]) => mockFetchMyMemberships(...args),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fakeUser = { id: "u-1", email: "test@example.com" };
const fakeMemberships = [
  { id: "m-1", account_type: "business", account_id: "b-1", status: "active", role: "owner" },
];

// Must import AFTER mocks are set up
async function loadAuthInitializer() {
  const mod = await import("@/features/auth/components/AuthInitializer");
  return mod.AuthInitializer;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AuthInitializer", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Reset stores to initial state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: false,
    });

    useMembershipStore.setState({
      memberships: [],
      isLoaded: false,
    });
  });

  it("sets user and memberships on successful init", async () => {
    mockSilentRefresh.mockResolvedValue(undefined);
    mockFetchCurrentUser.mockResolvedValue(fakeUser);
    mockFetchMyMemberships.mockResolvedValue(fakeMemberships);

    const AuthInitializer = await loadAuthInitializer();

    render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    await waitFor(() => {
      expect(useAuthStore.getState().isInitialized).toBe(true);
    });

    expect(useAuthStore.getState().user).toEqual(fakeUser);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useMembershipStore.getState().memberships).toEqual(fakeMemberships);
    expect(useMembershipStore.getState().isLoaded).toBe(true);
  });

  it("clears stores on silentRefresh failure", async () => {
    mockSilentRefresh.mockRejectedValue(new Error("refresh failed"));

    const AuthInitializer = await loadAuthInitializer();

    render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    await waitFor(() => {
      expect(useAuthStore.getState().isInitialized).toBe(true);
    });

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useMembershipStore.getState().memberships).toEqual([]);
    expect(useMembershipStore.getState().isLoaded).toBe(false);

    // fetchCurrentUser and fetchMyMemberships should NOT have been called
    expect(mockFetchCurrentUser).not.toHaveBeenCalled();
    expect(mockFetchMyMemberships).not.toHaveBeenCalled();
  });

  it("clears stores on fetchUser failure", async () => {
    mockSilentRefresh.mockResolvedValue(undefined);
    mockFetchCurrentUser.mockRejectedValue(new Error("user fetch failed"));
    mockFetchMyMemberships.mockResolvedValue(fakeMemberships);

    const AuthInitializer = await loadAuthInitializer();

    render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    await waitFor(() => {
      expect(useAuthStore.getState().isInitialized).toBe(true);
    });

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useMembershipStore.getState().memberships).toEqual([]);
  });

  it("always sets isInitialized even on failure", async () => {
    mockSilentRefresh.mockRejectedValue(new Error("network error"));

    const AuthInitializer = await loadAuthInitializer();

    render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    await waitFor(() => {
      expect(useAuthStore.getState().isInitialized).toBe(true);
    });
  });

  it("does not run when already initialized", async () => {
    useAuthStore.setState({ isInitialized: true });

    const AuthInitializer = await loadAuthInitializer();

    render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    // Give time for any potential async calls
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(mockSilentRefresh).not.toHaveBeenCalled();
    expect(mockFetchCurrentUser).not.toHaveBeenCalled();
    expect(mockFetchMyMemberships).not.toHaveBeenCalled();
  });

  it("double-mount protection — only one set of API calls", async () => {
    mockSilentRefresh.mockResolvedValue(undefined);
    mockFetchCurrentUser.mockResolvedValue(fakeUser);
    mockFetchMyMemberships.mockResolvedValue(fakeMemberships);

    const AuthInitializer = await loadAuthInitializer();

    // First render
    const { unmount } = render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    await waitFor(() => {
      expect(useAuthStore.getState().isInitialized).toBe(true);
    });

    unmount();

    // Second render (simulating StrictMode double-mount)
    render(
      <AuthInitializer>
        <div>child</div>
      </AuthInitializer>,
    );

    // Give time for any potential second run
    await new Promise((resolve) => setTimeout(resolve, 50));

    // silentRefresh should have been called exactly once
    expect(mockSilentRefresh).toHaveBeenCalledTimes(1);
    expect(mockFetchCurrentUser).toHaveBeenCalledTimes(1);
    expect(mockFetchMyMemberships).toHaveBeenCalledTimes(1);
  });
});
