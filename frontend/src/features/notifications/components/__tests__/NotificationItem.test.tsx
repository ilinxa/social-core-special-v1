import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NotificationItem } from "@/features/notifications/components/NotificationItem";
import type { NotificationLogItem } from "@/features/notifications/types";

function makeNotification(
  overrides: Partial<NotificationLogItem> = {},
): NotificationLogItem {
  return {
    id: "notif-123",
    notification_type: "transaction_accepted",
    scope_type: "user",
    scope_id: null,
    channels: ["email"],
    context: {},
    status: "sent",
    channel_results: { email: { status: "sent" } },
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("NotificationItem", () => {
  it("renders title from display config", () => {
    render(<NotificationItem notification={makeNotification()} />);
    expect(screen.getByText("Your request was accepted")).toBeInTheDocument();
  });

  it("renders dynamic title from context when available", () => {
    render(
      <NotificationItem
        notification={makeNotification({
          notification_type: "chat_message_received",
          context: {
            conversation_id: "conv-1",
            sender_name: "Alice",
            preview: "Hello!",
          },
        })}
      />,
    );
    expect(screen.getByText("New message from Alice")).toBeInTheDocument();
  });

  it("renders relative timestamp", () => {
    render(<NotificationItem notification={makeNotification()} />);
    expect(screen.getByText("Just now")).toBeInTheDocument();
  });

  it("renders scope badge for business scope", () => {
    render(
      <NotificationItem
        notification={makeNotification({
          scope_type: "business",
          scope_id: "biz-123",
        })}
      />,
    );
    expect(screen.getByText("Business")).toBeInTheDocument();
  });

  it("does not render scope badge for user scope", () => {
    render(<NotificationItem notification={makeNotification()} />);
    expect(screen.queryByText("Business")).not.toBeInTheDocument();
    expect(screen.queryByText("Platform")).not.toBeInTheDocument();
  });

  it("renders compact variant", () => {
    render(<NotificationItem notification={makeNotification()} compact />);
    expect(screen.getByText("Your request was accepted")).toBeInTheDocument();
  });

  it("renders fallback for unknown notification type", () => {
    render(
      <NotificationItem
        notification={makeNotification({
          notification_type: "unknown_future_type",
        })}
      />,
    );
    expect(screen.getByText("Notification")).toBeInTheDocument();
  });
});
