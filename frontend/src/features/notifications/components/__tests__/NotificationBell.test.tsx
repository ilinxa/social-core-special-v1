import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { useNotificationStore } from "@/stores/notification-store";

// Mock the query hook
vi.mock("@/features/notifications/hooks/use-notification-queries", () => ({
  useNotificationScopes: vi.fn(() => ({ data: null, isLoading: false })),
}));

// Must import after mock
import { NotificationBell } from "@/features/notifications/components/NotificationBell";

describe("NotificationBell", () => {
  beforeEach(() => {
    act(() => {
      useNotificationStore.getState().reset();
    });
  });

  it("renders bell icon when system enabled", () => {
    renderWithProviders(<NotificationBell />);
    // Both desktop and mobile variants render
    expect(screen.getAllByLabelText("Notifications")).toHaveLength(2);
  });

  it("renders nothing when system disabled", () => {
    act(() => {
      useNotificationStore.getState().setSystemEnabled(false);
    });

    const { container } = renderWithProviders(<NotificationBell />);
    expect(container.innerHTML).toBe("");
  });

  it("shows badge with unread count", () => {
    act(() => {
      useNotificationStore.getState().setScopeCounts({
        user: 5,
        "business:abc": 3,
      });
    });

    renderWithProviders(<NotificationBell />);
    // Both desktop and mobile variants show badge
    expect(screen.getAllByText("8")).toHaveLength(2);
  });

  it("hides badge when count is 0", () => {
    renderWithProviders(<NotificationBell />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows 99+ for counts over 99", () => {
    act(() => {
      useNotificationStore.getState().setScopeCounts({ user: 150 });
    });

    renderWithProviders(<NotificationBell />);
    expect(screen.getAllByText("99+")).toHaveLength(2);
  });
});
