vi.mock("@/features/users/api/users-api", () => ({
  checkUsernameApi: vi.fn(),
}));

import React from "react";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { useUsernameCheck } from "./use-username-check";
import { checkUsernameApi } from "@/features/users/api/users-api";

const mockedCheckUsernameApi = vi.mocked(checkUsernameApi);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useUsernameCheck", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns isCurrent when username matches currentUsername (case-insensitive)", () => {
    const { result } = renderHook(
      () => useUsernameCheck("TestUser", "testuser"),
      { wrapper: createWrapper() },
    );

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toEqual({
      isChecking: false,
      isAvailable: true,
      isCurrent: true,
    });
    expect(mockedCheckUsernameApi).not.toHaveBeenCalled();
  });

  it("returns null availability for invalid format", () => {
    const { result } = renderHook(
      () => useUsernameCheck("ab", "testuser"),
      { wrapper: createWrapper() },
    );

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toEqual({
      isChecking: false,
      isAvailable: null,
      isCurrent: false,
    });
    expect(mockedCheckUsernameApi).not.toHaveBeenCalled();
  });

  it("returns null availability for empty username", () => {
    const { result } = renderHook(
      () => useUsernameCheck("", "testuser"),
      { wrapper: createWrapper() },
    );

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toEqual({
      isChecking: false,
      isAvailable: null,
      isCurrent: false,
    });
  });

  it("calls API for valid different username", async () => {
    mockedCheckUsernameApi.mockResolvedValue({
      available: true,
      is_current: false,
    });

    const { result } = renderHook(
      () => useUsernameCheck("newname", "testuser"),
      { wrapper: createWrapper() },
    );

    // Advance past debounce, then restore real timers for waitFor polling
    act(() => {
      vi.advanceTimersByTime(500);
    });
    vi.useRealTimers();

    await waitFor(() => {
      expect(result.current).toEqual({
        isChecking: false,
        isAvailable: true,
        isCurrent: false,
      });
    });

    expect(mockedCheckUsernameApi).toHaveBeenCalledWith("newname");
  });

  it("reports unavailable username from API", async () => {
    mockedCheckUsernameApi.mockResolvedValue({
      available: false,
      is_current: false,
    });

    const { result } = renderHook(
      () => useUsernameCheck("taken", "testuser"),
      { wrapper: createWrapper() },
    );

    // Advance past debounce, then restore real timers for waitFor polling
    act(() => {
      vi.advanceTimersByTime(500);
    });
    vi.useRealTimers();

    await waitFor(() => {
      expect(result.current).toEqual({
        isChecking: false,
        isAvailable: false,
        isCurrent: false,
      });
    });

    expect(mockedCheckUsernameApi).toHaveBeenCalledWith("taken");
  });
});
