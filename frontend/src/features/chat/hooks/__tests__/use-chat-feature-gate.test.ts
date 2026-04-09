import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import type { ChatFeatureFlag } from "@/features/chat/utils/feature-gate-handler";

// =============================================================================
// MOCKS
// =============================================================================

const mockIsChatFeatureDisabled = vi.fn<(flag: ChatFeatureFlag) => boolean>();
const mockOnFeatureGateChange = vi.fn<(cb: () => void) => () => void>();
const mockUnsubscribe = vi.fn();

vi.mock("@/features/chat/utils/feature-gate-handler", () => ({
  isChatFeatureDisabled: (...args: [ChatFeatureFlag]) =>
    mockIsChatFeatureDisabled(...args),
  onFeatureGateChange: (...args: [() => void]) =>
    mockOnFeatureGateChange(...args),
}));

import { useChatFeatureEnabled } from "../use-chat-feature-gate";

// =============================================================================
// SETUP
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
  mockIsChatFeatureDisabled.mockReturnValue(false);
  mockOnFeatureGateChange.mockReturnValue(mockUnsubscribe);
});

// =============================================================================
// TESTS
// =============================================================================

describe("useChatFeatureEnabled", () => {
  it("returns true when feature is enabled (not disabled)", () => {
    mockIsChatFeatureDisabled.mockReturnValue(false);

    const { result } = renderHook(() => useChatFeatureEnabled("group"));

    expect(result.current).toBe(true);
  });

  it("returns false when feature is disabled", () => {
    mockIsChatFeatureDisabled.mockReturnValue(true);

    const { result } = renderHook(() => useChatFeatureEnabled("search"));

    expect(result.current).toBe(false);
  });

  it("calls onFeatureGateChange to subscribe", () => {
    renderHook(() => useChatFeatureEnabled("reactions"));

    expect(mockOnFeatureGateChange).toHaveBeenCalledTimes(1);
    expect(mockOnFeatureGateChange).toHaveBeenCalledWith(expect.any(Function));
  });

  it("returns unsubscribe function from onFeatureGateChange on unmount", () => {
    const { unmount } = renderHook(() =>
      useChatFeatureEnabled("file_sharing"),
    );

    unmount();

    expect(mockUnsubscribe).toHaveBeenCalledTimes(1);
  });

  it("checks the correct flag via isChatFeatureDisabled", () => {
    renderHook(() => useChatFeatureEnabled("reactions"));

    expect(mockIsChatFeatureDisabled).toHaveBeenCalledWith("reactions");
  });
});
