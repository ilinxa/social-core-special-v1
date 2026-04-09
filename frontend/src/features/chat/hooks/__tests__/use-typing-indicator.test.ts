import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { useTypingIndicator } from "../use-typing-indicator";
import type { WsClient } from "@/lib/ws-client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createMockWs(
  overrides: Partial<Pick<WsClient, "send" | "state">> = {},
): WsClient {
  return {
    send: vi.fn(),
    get state() {
      return "connected" as const;
    },
    ...overrides,
    // Unused members — stub just enough to satisfy the type
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(() => vi.fn()),
    onStateChange: vi.fn(() => vi.fn()),
  } as unknown as WsClient;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useTypingIndicator", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("onKeystroke sends typing.start via WS", () => {
    const ws = createMockWs();

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    expect(ws.send).toHaveBeenCalledWith({
      type: "typing.start",
      conversation_id: "conv-1",
    });
  });

  it("onKeystroke throttles — second call within 2s does NOT send", () => {
    const ws = createMockWs();

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    expect(ws.send).toHaveBeenCalledTimes(1);

    // Second keystroke within 2s throttle window
    act(() => {
      vi.advanceTimersByTime(500);
      result.current.onKeystroke();
    });

    // Still only 1 send (the first typing.start)
    expect(ws.send).toHaveBeenCalledTimes(1);
  });

  it("allows typing.start again after throttle window expires", () => {
    const ws = createMockWs();

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    expect(ws.send).toHaveBeenCalledTimes(1);

    // Advance past the 2s throttle
    act(() => {
      vi.advanceTimersByTime(2100);
    });

    act(() => {
      result.current.onKeystroke();
    });

    // typing.stop from the 3s idle timeout fires at ~3s, plus new typing.start
    // The second onKeystroke should have sent a new typing.start
    const typingStartCalls = vi.mocked(ws.send).mock.calls.filter(
      (call) => (call[0] as Record<string, unknown>).type === "typing.start",
    );
    expect(typingStartCalls).toHaveLength(2);
  });

  it("after 3s idle, typing.stop is sent automatically", () => {
    const ws = createMockWs();

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    expect(ws.send).toHaveBeenCalledTimes(1);
    expect(ws.send).toHaveBeenCalledWith({
      type: "typing.start",
      conversation_id: "conv-1",
    });

    // Advance 3s (TYPING_TIMEOUT_MS)
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(ws.send).toHaveBeenCalledWith({
      type: "typing.stop",
      conversation_id: "conv-1",
    });
  });

  it("stopTyping sends typing.stop immediately", () => {
    const ws = createMockWs();

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    // Start typing first
    act(() => {
      result.current.onKeystroke();
    });

    // Then stop immediately
    act(() => {
      result.current.stopTyping();
    });

    expect(ws.send).toHaveBeenLastCalledWith({
      type: "typing.stop",
      conversation_id: "conv-1",
    });
  });

  it("stopTyping clears the idle timer (no duplicate typing.stop)", () => {
    const ws = createMockWs();

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    // Stop immediately
    act(() => {
      result.current.stopTyping();
    });

    const callCountAfterStop = vi.mocked(ws.send).mock.calls.length;

    // Advance past idle timeout — should NOT fire another typing.stop
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(ws.send).toHaveBeenCalledTimes(callCountAfterStop);
  });

  it("does not send if WS is null", () => {
    const { result } = renderHook(() => useTypingIndicator(null, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    // No error thrown, no sends (ws is null so there's nothing to assert on
    // except that no error was thrown)
    expect(true).toBe(true);
  });

  it("does not send if WS state is not 'connected'", () => {
    const ws = createMockWs();
    // Override the state getter to return "disconnected"
    Object.defineProperty(ws, "state", {
      get: () => "disconnected",
      configurable: true,
    });

    const { result } = renderHook(() => useTypingIndicator(ws, "conv-1"));

    act(() => {
      result.current.onKeystroke();
    });

    expect(ws.send).not.toHaveBeenCalled();
  });
});
