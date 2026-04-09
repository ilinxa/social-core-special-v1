import { render, screen } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";

import { useChatStore } from "@/stores/chat-store";
import { DeliveryStatus } from "../DeliveryStatus";

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

describe("DeliveryStatus", () => {
  it("renders nothing for non-own messages", () => {
    const { container } = render(
      <DeliveryStatus
        conversationId="conv-1"
        messageId="msg-1"
        isOwn={false}
        isDm={true}
      />,
    );

    expect(container.innerHTML).toBe("");
  });

  describe("DM mode", () => {
    it("shows single check (Sent) when no watermarks exist", () => {
      useChatStore.setState({
        seenWatermarks: {},
        deliveredWatermarks: {},
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={true}
        />,
      );

      expect(screen.getByTestId("delivery-sent")).toBeInTheDocument();
      expect(screen.getByLabelText("Sent")).toBeInTheDocument();
      expect(screen.queryByTestId("delivery-delivered")).not.toBeInTheDocument();
      expect(screen.queryByTestId("delivery-seen")).not.toBeInTheDocument();
    });

    it("shows double check (Delivered) when deliveredWatermarks match", () => {
      useChatStore.setState({
        seenWatermarks: {},
        deliveredWatermarks: {
          "conv-1": { "user-2": "msg-1" },
        },
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={true}
        />,
      );

      expect(screen.getByTestId("delivery-delivered")).toBeInTheDocument();
      expect(screen.getByLabelText("Delivered")).toBeInTheDocument();
      expect(screen.queryByTestId("delivery-seen")).not.toBeInTheDocument();
    });

    it("shows blue double check (Seen) when seenWatermarks match", () => {
      useChatStore.setState({
        seenWatermarks: {
          "conv-1": { "user-2": "msg-1" },
        },
        deliveredWatermarks: {
          "conv-1": { "user-2": "msg-1" },
        },
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={true}
        />,
      );

      expect(screen.getByTestId("delivery-seen")).toBeInTheDocument();
      expect(screen.getByLabelText("Seen")).toBeInTheDocument();
      expect(
        screen.queryByTestId("delivery-delivered"),
      ).not.toBeInTheDocument();
    });

    it("shows Seen when seenWatermark is ahead of messageId", () => {
      useChatStore.setState({
        seenWatermarks: {
          "conv-1": { "user-2": "msg-5" },
        },
        deliveredWatermarks: {},
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={true}
        />,
      );

      // "msg-5" > "msg-1" so message is considered seen
      expect(screen.getByTestId("delivery-seen")).toBeInTheDocument();
    });
  });

  describe("Group mode", () => {
    it("shows Sent check when no seen watermarks", () => {
      useChatStore.setState({
        seenWatermarks: {},
        deliveredWatermarks: {},
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={false}
        />,
      );

      expect(screen.getByTestId("delivery-sent")).toBeInTheDocument();
      expect(screen.getByLabelText("Sent")).toBeInTheDocument();
    });

    it('shows "Seen by 2" when 2 participants have seen', () => {
      useChatStore.setState({
        seenWatermarks: {
          "conv-1": {
            "user-2": "msg-1",
            "user-3": "msg-1",
          },
        },
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={false}
        />,
      );

      expect(screen.getByTestId("delivery-seen-count")).toBeInTheDocument();
      expect(screen.getByText("Seen by 2")).toBeInTheDocument();
    });

    it('shows "Seen by 1" when only 1 participant has seen', () => {
      useChatStore.setState({
        seenWatermarks: {
          "conv-1": {
            "user-2": "msg-1",
            "user-3": "msg-0", // older than current message, not counted
          },
        },
      });

      render(
        <DeliveryStatus
          conversationId="conv-1"
          messageId="msg-1"
          isOwn={true}
          isDm={false}
        />,
      );

      expect(screen.getByText("Seen by 1")).toBeInTheDocument();
    });
  });
});
