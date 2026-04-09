import { render, screen } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";

import { useChatStore } from "@/stores/chat-store";
import { PresenceDot } from "../PresenceDot";

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

describe("PresenceDot", () => {
  it("shows green dot (online) when user is in onlineUsers set", () => {
    useChatStore.setState({ onlineUsers: new Set(["user-1"]) });

    render(<PresenceDot userId="user-1" />);

    const dot = screen.getByTestId("presence-dot");
    expect(dot).toHaveClass("bg-green-500");
    expect(dot).toHaveAttribute("data-online", "true");
  });

  it("shows gray dot (offline) when user is not in onlineUsers set", () => {
    useChatStore.setState({ onlineUsers: new Set() });

    render(<PresenceDot userId="user-1" />);

    const dot = screen.getByTestId("presence-dot");
    expect(dot).toHaveClass("bg-muted-foreground/40");
    expect(dot).toHaveAttribute("data-online", "false");
  });

  it("has correct aria-label for online state", () => {
    useChatStore.setState({ onlineUsers: new Set(["user-1"]) });

    render(<PresenceDot userId="user-1" />);

    expect(screen.getByLabelText("Online")).toBeInTheDocument();
  });

  it("has correct aria-label for offline state", () => {
    useChatStore.setState({ onlineUsers: new Set() });

    render(<PresenceDot userId="user-1" />);

    expect(screen.getByLabelText("Offline")).toBeInTheDocument();
  });

  it("accepts additional className prop", () => {
    useChatStore.setState({ onlineUsers: new Set(["user-1"]) });

    render(<PresenceDot userId="user-1" className="absolute bottom-0" />);

    const dot = screen.getByTestId("presence-dot");
    expect(dot).toHaveClass("absolute");
    expect(dot).toHaveClass("bottom-0");
  });
});
