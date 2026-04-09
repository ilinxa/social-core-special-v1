import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import {
  EmptyConversationList,
  EmptyMessages,
  NoConversationSelected,
} from "../EmptyStates";

// =============================================================================
// TESTS: EmptyConversationList
// =============================================================================

describe("EmptyConversationList", () => {
  it('renders "No conversations yet"', () => {
    render(<EmptyConversationList />);

    expect(screen.getByText("No conversations yet")).toBeInTheDocument();
    expect(
      screen.getByText("Start a conversation to begin chatting"),
    ).toBeInTheDocument();
  });

  it("shows new conversation button when callback provided", () => {
    const onNewConversation = vi.fn();

    render(<EmptyConversationList onNewConversation={onNewConversation} />);

    const button = screen.getByRole("button", { name: /new conversation/i });
    expect(button).toBeInTheDocument();
  });

  it("calls onNewConversation when button clicked", () => {
    const onNewConversation = vi.fn();

    render(<EmptyConversationList onNewConversation={onNewConversation} />);

    const button = screen.getByRole("button", { name: /new conversation/i });
    fireEvent.click(button);

    expect(onNewConversation).toHaveBeenCalledTimes(1);
  });

  it("hides button when no callback", () => {
    render(<EmptyConversationList />);

    const button = screen.queryByRole("button", { name: /new conversation/i });
    expect(button).not.toBeInTheDocument();
  });
});

// =============================================================================
// TESTS: EmptyMessages
// =============================================================================

describe("EmptyMessages", () => {
  it('renders "Send a message to start the conversation"', () => {
    render(<EmptyMessages />);

    expect(
      screen.getByText("Send a message to start the conversation"),
    ).toBeInTheDocument();
  });

  it("renders MessageCircle icon", () => {
    const { container } = render(<EmptyMessages />);

    // Check that an SVG element is present (lucide icon)
    const icon = container.querySelector("svg");
    expect(icon).toBeInTheDocument();
  });
});

// =============================================================================
// TESTS: NoConversationSelected
// =============================================================================

describe("NoConversationSelected", () => {
  it('renders "Select a conversation"', () => {
    render(<NoConversationSelected />);

    expect(screen.getByText("Select a conversation")).toBeInTheDocument();
    expect(
      screen.getByText("Choose a conversation from the sidebar to start chatting"),
    ).toBeInTheDocument();
  });

  it("renders MessagesSquare icon", () => {
    const { container } = render(<NoConversationSelected />);

    // Check that an SVG element is present (lucide icon)
    const icon = container.querySelector("svg");
    expect(icon).toBeInTheDocument();
  });
});
