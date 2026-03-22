import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";

import { useAuthStore, useUser, useIsAuthenticated, useIsInitialized } from "./auth-store";

import type { User } from "@/types";

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
  last_login: "2026-02-24T00:00:00Z",
  profile: {
    first_name: "Test",
    last_name: "User",
    full_name: "Test User",
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

describe("auth-store", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: false,
    });
  });

  it("has correct initial state", () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isInitialized).toBe(false);
  });

  it("setUser sets user and isAuthenticated", () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setUser(mockUser);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("clearUser clears user and isAuthenticated", () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setUser(mockUser);
    });

    act(() => {
      result.current.clearUser();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("setInitialized sets isInitialized", () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setInitialized();
    });

    expect(result.current.isInitialized).toBe(true);
  });
});

describe("selector hooks", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isInitialized: false,
    });
  });

  it("useUser returns user", () => {
    useAuthStore.setState({ user: mockUser });
    const { result } = renderHook(() => useUser());
    expect(result.current).toEqual(mockUser);
  });

  it("useIsAuthenticated returns isAuthenticated", () => {
    useAuthStore.setState({ isAuthenticated: true });
    const { result } = renderHook(() => useIsAuthenticated());
    expect(result.current).toBe(true);
  });

  it("useIsInitialized returns isInitialized", () => {
    useAuthStore.setState({ isInitialized: true });
    const { result } = renderHook(() => useIsInitialized());
    expect(result.current).toBe(true);
  });
});
