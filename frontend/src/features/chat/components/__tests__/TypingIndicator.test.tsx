import { render, screen } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";

import { useChatStore } from "@/stores/chat-store";
import { TypingIndicator } from "../TypingIndicator";

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

describe("TypingIndicator", () => {
  it("renders nothing when no one is typing", () => {
    useChatStore.setState({ typingUsers: {} });

    const { container } = render(
      <TypingIndicator conversationId="conv-1" />,
    );

    expect(container.innerHTML).toBe("");
    expect(screen.queryByTestId("typing-indicator")).not.toBeInTheDocument();
  });

  it('shows "Someone is typing..." when 1 user is typing', () => {
    useChatStore.setState({
      typingUsers: { "conv-1": ["user-2"] },
    });

    render(<TypingIndicator conversationId="conv-1" />);

    expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
    expect(screen.getByText("Someone is typing...")).toBeInTheDocument();
  });

  it('shows "2 people are typing..." when 2 users are typing', () => {
    useChatStore.setState({
      typingUsers: { "conv-1": ["user-2", "user-3"] },
    });

    render(<TypingIndicator conversationId="conv-1" />);

    expect(screen.getByText("2 people are typing...")).toBeInTheDocument();
  });

  it('shows "N people are typing..." when 3+ users are typing', () => {
    useChatStore.setState({
      typingUsers: { "conv-1": ["user-2", "user-3", "user-4"] },
    });

    render(<TypingIndicator conversationId="conv-1" />);

    expect(screen.getByText("3 people are typing...")).toBeInTheDocument();
  });

  it("renders nothing for a different conversation id", () => {
    useChatStore.setState({
      typingUsers: { "conv-2": ["user-2"] },
    });

    const { container } = render(
      <TypingIndicator conversationId="conv-1" />,
    );

    expect(container.innerHTML).toBe("");
  });
});
