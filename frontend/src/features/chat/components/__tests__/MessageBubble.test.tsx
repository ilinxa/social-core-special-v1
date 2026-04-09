import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MessageBubble } from "../MessageBubble";
import type { ChatMessage, ConversationPermissions } from "@/features/chat/types";
import { renderWithProviders } from "@/test/utils";

const defaultPermissions: ConversationPermissions = {
  can_send_message: true,
  can_view_messages: true,
  can_edit_group: false,
  can_manage_group: false,
  can_add_participant: false,
  can_remove_participant: false,
  can_leave: true,
};

/**
 * Helper to create a ChatMessage with sensible defaults.
 */
function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "msg-123",
    conversation_id: "conv-456",
    sender_type: "user",
    sender_id: "user-789",
    sender_name: "Alice",
    sender_avatar_url: null,
    content_type: "text",
    content: "Hello, world!",
    status: "active",
    sequence_number: 1,
    edited_at: null,
    created_at: "2026-03-26T14:30:00Z",
    attachments: [],
    reactions: {
      like: 0,
      heart: 0,
      laugh: 0,
      wow: 0,
      sad: 0,
      angry: 0,
    },
    my_reactions: [],
    ...overrides,
  };
}

describe("MessageBubble", () => {
  it("renders message content text", () => {
    const message = makeMessage({ content: "Test message content" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={false}
        showSender={false}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    expect(screen.getByText("Test message content")).toBeInTheDocument();
  });

  it("shows sender name when showSender=true and isOwn=false", () => {
    const message = makeMessage({ sender_name: "Bob" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={false}
        showSender={true}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("hides sender name when isOwn=true", () => {
    const message = makeMessage({ sender_name: "Alice" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={true}
        showSender={true}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    expect(screen.queryByText("Alice")).not.toBeInTheDocument();
  });

  it("shows '(edited)' badge when status is 'edited'", () => {
    const message = makeMessage({
      status: "edited",
      edited_at: "2026-03-26T14:35:00Z",
    });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={false}
        showSender={false}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    expect(screen.getByText("(edited)")).toBeInTheDocument();
  });

  it("shows deleted message placeholder when status is 'deleted'", () => {
    const message = makeMessage({ status: "deleted" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={false}
        showSender={false}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    expect(screen.getByText("This message was deleted")).toBeInTheDocument();
    expect(screen.queryByText("Hello, world!")).not.toBeInTheDocument();
  });

  it("own messages have primary background", () => {
    const message = makeMessage({ content: "My message" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={true}
        showSender={false}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    const bubble = screen.getByText("My message").parentElement;
    expect(bubble).toHaveClass("bg-primary");
  });

  it("others' messages have muted background", () => {
    const message = makeMessage({ content: "Their message" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={false}
        showSender={false}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    const bubble = screen.getByText("Their message").parentElement;
    expect(bubble).toHaveClass("bg-muted");
  });

  it("hides sender name when showSender=false", () => {
    const message = makeMessage({ sender_name: "Charlie" });
    renderWithProviders(
      <MessageBubble
        message={message}
        isOwn={false}
        showSender={false}
        conversationId="conv-456"
        permissions={defaultPermissions}
        isDm={false}
      />,
    );

    expect(screen.queryByText("Charlie")).not.toBeInTheDocument();
  });
});
