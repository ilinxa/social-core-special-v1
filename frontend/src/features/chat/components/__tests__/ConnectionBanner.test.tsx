import { render, screen } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";

import { useChatStore } from "@/stores/chat-store";
import { ConnectionBanner } from "../ConnectionBanner";

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

describe("ConnectionBanner", () => {
  it("renders nothing when connected", () => {
    useChatStore.setState({ wsState: "connected" });

    const { container } = render(<ConnectionBanner />);

    expect(container.innerHTML).toBe("");
    expect(screen.queryByTestId("connection-banner")).not.toBeInTheDocument();
  });

  it('shows "Connecting..." when connecting', () => {
    useChatStore.setState({ wsState: "connecting" });

    render(<ConnectionBanner />);

    const banner = screen.getByTestId("connection-banner");
    expect(banner).toBeInTheDocument();
    expect(screen.getByText("Connecting...")).toBeInTheDocument();
  });

  it('shows "Reconnecting..." when reconnecting', () => {
    useChatStore.setState({ wsState: "reconnecting" });

    render(<ConnectionBanner />);

    const banner = screen.getByTestId("connection-banner");
    expect(banner).toBeInTheDocument();
    expect(screen.getByText("Reconnecting...")).toBeInTheDocument();
  });

  it('shows "Offline -- messages may be delayed" when disconnected', () => {
    useChatStore.setState({ wsState: "disconnected" });

    render(<ConnectionBanner />);

    const banner = screen.getByTestId("connection-banner");
    expect(banner).toBeInTheDocument();
    expect(
      screen.getByText(/Offline.*messages may be delayed/),
    ).toBeInTheDocument();
  });

  it("has role=status for accessibility", () => {
    useChatStore.setState({ wsState: "connecting" });

    render(<ConnectionBanner />);

    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
