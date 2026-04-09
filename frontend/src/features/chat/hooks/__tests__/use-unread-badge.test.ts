import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";

import { useChatStore } from "@/stores/chat-store";
import { createWrapper } from "@/test/utils";

// Mock the use-chat-queries module before importing the hook
vi.mock("@/features/chat/hooks/use-chat-queries", () => ({
  useUnreadCounts: vi.fn(() => ({ data: null })),
}));

import { useUnreadBadge, useScopeUnreadBadge } from "../use-unread-badge";

// =============================================================================
// SETUP
// =============================================================================

afterEach(() => {
  useChatStore.setState({
    typingUsers: {},
    onlineUsers: new Set(),
    wsState: "disconnected",
    unreadCounts: {},
    seenWatermarks: {},
    deliveredWatermarks: {},
  });
});

// =============================================================================
// TESTS
// =============================================================================

describe("useUnreadBadge", () => {
  it("returns 0 when no unread counts", () => {
    useChatStore.setState({ unreadCounts: {} });

    const { result } = renderHook(() => useUnreadBadge(), {
      wrapper: createWrapper(),
    });

    expect(result.current).toBe(0);
  });

  it("returns sum of all unread counts", () => {
    useChatStore.setState({
      unreadCounts: {
        global: 3,
        "business:biz-1": 5,
        "platform:plat-1": 2,
      },
    });

    const { result } = renderHook(() => useUnreadBadge(), {
      wrapper: createWrapper(),
    });

    expect(result.current).toBe(10);
  });

  it("returns sum with single scope", () => {
    useChatStore.setState({
      unreadCounts: { global: 7 },
    });

    const { result } = renderHook(() => useUnreadBadge(), {
      wrapper: createWrapper(),
    });

    expect(result.current).toBe(7);
  });
});

describe("useScopeUnreadBadge", () => {
  it("returns specific scope count", () => {
    useChatStore.setState({
      unreadCounts: {
        global: 3,
        "business:biz-1": 5,
      },
    });

    const { result } = renderHook(
      () => useScopeUnreadBadge("business:biz-1"),
      { wrapper: createWrapper() },
    );

    expect(result.current).toBe(5);
  });

  it("returns 0 for unknown scope key", () => {
    useChatStore.setState({
      unreadCounts: { global: 3 },
    });

    const { result } = renderHook(
      () => useScopeUnreadBadge("business:unknown"),
      { wrapper: createWrapper() },
    );

    expect(result.current).toBe(0);
  });
});
