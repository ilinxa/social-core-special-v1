"use client";

/**
 * Notification Zustand Store
 * ==========================
 * App-wide ephemeral state for the notification system.
 *
 * Located in src/stores/ (NOT src/features/notifications/) because
 * Topbar bell badge needs unread counts outside the notifications feature tree.
 * Same pattern as chat-store.ts and auth-store.ts.
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";

// =============================================================================
// STATE & ACTIONS
// =============================================================================

interface NotificationState {
  /** Whether the notification system is enabled (false when SG returns 404) */
  isSystemEnabled: boolean;
  /** Notification counts per scope key ("user", "business:<uuid>", "platform:<uuid>") */
  scopeCounts: Record<string, number>;
  /** Whether the desktop notification dropdown is open */
  dropdownOpen: boolean;
}

interface NotificationActions {
  setSystemEnabled: (enabled: boolean) => void;
  setScopeCounts: (counts: Record<string, number>) => void;
  setDropdownOpen: (open: boolean) => void;
  reset: () => void;
}

type NotificationStore = NotificationState & NotificationActions;

const initialState: NotificationState = {
  isSystemEnabled: true,
  scopeCounts: {},
  dropdownOpen: false,
};

// =============================================================================
// STORE
// =============================================================================

export const useNotificationStore = create<NotificationStore>()(
  devtools(
    (set) => ({
      ...initialState,

      setSystemEnabled: (enabled) =>
        set({ isSystemEnabled: enabled }, false, "notifications/setSystemEnabled"),

      setScopeCounts: (counts) =>
        set({ scopeCounts: counts }, false, "notifications/setScopeCounts"),

      setDropdownOpen: (open) =>
        set({ dropdownOpen: open }, false, "notifications/setDropdownOpen"),

      reset: () => set(initialState, false, "notifications/reset"),
    }),
    { name: "notification-store" },
  ),
);

// =============================================================================
// SELECTOR HOOKS
// =============================================================================

export function useNotificationSystemEnabled(): boolean {
  return useNotificationStore((s) => s.isSystemEnabled);
}

export function useNotificationTotalUnread(): number {
  return useNotificationStore((s) =>
    Object.values(s.scopeCounts).reduce((sum, n) => sum + n, 0),
  );
}

export function useNotificationDropdownOpen(): boolean {
  return useNotificationStore((s) => s.dropdownOpen);
}

// =============================================================================
// NON-REACT ACCESS
// =============================================================================

export function getNotificationStore() {
  return useNotificationStore.getState();
}
