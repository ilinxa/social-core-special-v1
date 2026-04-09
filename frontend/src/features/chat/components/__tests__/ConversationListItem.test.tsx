import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { ConversationListItem } from "../ConversationListItem";
import type { ConversationListItem as ConversationListItemType } from "@/features/chat/types";

// =============================================================================
// MOCK DATA
// =============================================================================

const createMockConversation = (
  overrides?: Partial<ConversationListItemType>,
): ConversationListItemType => ({
  id: "conv-1",
  scope_type: "global",
  scope_id: null,
  conversation_type: "direct",
  name: "John Doe",
  last_message: {
    id: "msg-1",
    sender_type: "user",
    sender_id: "user-1",
    sender_name: "John Doe",
    content_preview: "Hello there!",
    created_at: new Date().toISOString(),
  },
  unread_count: 0,
  is_muted: false,
  created_at: new Date().toISOString(),
  ...overrides,
});

// =============================================================================
// TESTS
// =============================================================================

describe("ConversationListItem", () => {
  it("renders conversation name", () => {
    const conversation = createMockConversation();
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("renders last message preview with sender name", () => {
    const conversation = createMockConversation();
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText(/John Doe: Hello there!/)).toBeInTheDocument();
  });

  it('shows "No messages yet" when last_message is null', () => {
    const conversation = createMockConversation({ last_message: null });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText("No messages yet")).toBeInTheDocument();
  });

  it("shows unread count badge when unread_count > 0", () => {
    const conversation = createMockConversation({ unread_count: 5 });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("does NOT show unread badge when unread_count is 0", () => {
    const conversation = createMockConversation({ unread_count: 0 });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    // Badge should not be present when unread is 0
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it('shows "99+" for unread > 99', () => {
    const conversation = createMockConversation({ unread_count: 150 });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText("99+")).toBeInTheDocument();
  });

  it("shows BellOff icon when muted", () => {
    const conversation = createMockConversation({ is_muted: true });
    const onClick = vi.fn();

    const { container } = render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    // BellOff icon should be present (lucide icons have data-lucide attribute)
    const bellOffIcon = container.querySelector("svg");
    expect(bellOffIcon).toBeInTheDocument();
  });

  it("applies active styles when isActive=true", () => {
    const conversation = createMockConversation();
    const onClick = vi.fn();

    const { container } = render(
      <ConversationListItem
        conversation={conversation}
        isActive={true}
        onClick={onClick}
      />,
    );

    const button = container.querySelector("button");
    expect(button).toHaveClass("bg-accent");
  });

  it("calls onClick with conversation id on click", () => {
    const conversation = createMockConversation({ id: "test-conv-123" });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    const button = screen.getByRole("option");
    fireEvent.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith("test-conv-123");
  });

  it("bold name when unread > 0", () => {
    const conversation = createMockConversation({
      name: "Jane Smith",
      unread_count: 3,
    });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    const nameElement = screen.getByText("Jane Smith");
    expect(nameElement).toHaveClass("font-semibold");
  });

  it("renders avatar with first letter of name", () => {
    const conversation = createMockConversation({ name: "Alice" });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it('renders "#" for group conversations', () => {
    const conversation = createMockConversation({
      conversation_type: "group",
      name: "Team Chat",
    });
    const onClick = vi.fn();

    render(
      <ConversationListItem
        conversation={conversation}
        isActive={false}
        onClick={onClick}
      />,
    );

    expect(screen.getByText("#")).toBeInTheDocument();
  });
});
