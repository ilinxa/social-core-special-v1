import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import {
  getNotificationStore,
  useNotificationDropdownOpen,
  useNotificationStore,
  useNotificationSystemEnabled,
  useNotificationTotalUnread,
} from "@/stores/notification-store";

describe("notification-store", () => {
  beforeEach(() => {
    act(() => {
      useNotificationStore.getState().reset();
    });
  });

  it("has correct initial state", () => {
    const state = getNotificationStore();
    expect(state.isSystemEnabled).toBe(true);
    expect(state.scopeCounts).toEqual({});
    expect(state.dropdownOpen).toBe(false);
  });

  it("setSystemEnabled toggles flag", () => {
    act(() => {
      getNotificationStore().setSystemEnabled(false);
    });
    expect(getNotificationStore().isSystemEnabled).toBe(false);

    act(() => {
      getNotificationStore().setSystemEnabled(true);
    });
    expect(getNotificationStore().isSystemEnabled).toBe(true);
  });

  it("setScopeCounts updates counts", () => {
    act(() => {
      getNotificationStore().setScopeCounts({
        user: 5,
        "business:abc": 3,
      });
    });
    expect(getNotificationStore().scopeCounts).toEqual({
      user: 5,
      "business:abc": 3,
    });
  });

  it("setDropdownOpen updates state", () => {
    act(() => {
      getNotificationStore().setDropdownOpen(true);
    });
    expect(getNotificationStore().dropdownOpen).toBe(true);
  });

  it("reset restores initial state", () => {
    act(() => {
      getNotificationStore().setSystemEnabled(false);
      getNotificationStore().setScopeCounts({ user: 10 });
      getNotificationStore().setDropdownOpen(true);
    });

    act(() => {
      getNotificationStore().reset();
    });

    const state = getNotificationStore();
    expect(state.isSystemEnabled).toBe(true);
    expect(state.scopeCounts).toEqual({});
    expect(state.dropdownOpen).toBe(false);
  });

  describe("selector hooks", () => {
    it("useNotificationSystemEnabled returns isSystemEnabled", () => {
      const { result } = renderHook(() => useNotificationSystemEnabled());
      expect(result.current).toBe(true);

      act(() => {
        getNotificationStore().setSystemEnabled(false);
      });
      expect(result.current).toBe(false);
    });

    it("useNotificationTotalUnread sums all scope counts", () => {
      const { result } = renderHook(() => useNotificationTotalUnread());
      expect(result.current).toBe(0);

      act(() => {
        getNotificationStore().setScopeCounts({
          user: 5,
          "business:abc": 3,
          "platform:xyz": 2,
        });
      });
      expect(result.current).toBe(10);
    });

    it("useNotificationDropdownOpen returns dropdownOpen", () => {
      const { result } = renderHook(() => useNotificationDropdownOpen());
      expect(result.current).toBe(false);

      act(() => {
        getNotificationStore().setDropdownOpen(true);
      });
      expect(result.current).toBe(true);
    });
  });

  describe("non-React access", () => {
    it("getNotificationStore returns current state", () => {
      act(() => {
        getNotificationStore().setScopeCounts({ user: 7 });
      });
      expect(getNotificationStore().scopeCounts.user).toBe(7);
    });
  });
});
