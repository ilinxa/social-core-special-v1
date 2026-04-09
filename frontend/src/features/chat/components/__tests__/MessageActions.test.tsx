import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageActions } from "../MessageActions";
import type { ChatMessage } from "../../types";
import type { ConversationPermissions } from "../../types";

// Mock clipboard API — must use defineProperty because clipboard is a read-only getter in happy-dom
const mockWriteText = vi.fn().mockResolvedValue(undefined);
Object.defineProperty(navigator, "clipboard", {
  value: { writeText: mockWriteText },
  writable: true,
  configurable: true,
});

describe("MessageActions", () => {
  const mockOnEdit = vi.fn();
  const mockOnDelete = vi.fn();
  const mockOnReact = vi.fn();

  const baseMessage: ChatMessage = {
    id: "msg-1",
    conversation_id: "conv-1",
    sender_type: "user",
    sender_id: "user-1",
    sender_name: "John Doe",
    sender_avatar_url: null,
    content_type: "text",
    content: "Hello world",
    status: "active",
    sequence_number: 1,
    edited_at: null,
    created_at: new Date().toISOString(),
    attachments: [],
    reactions: { like: 0, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
    my_reactions: [],
  };

  const basePermissions: ConversationPermissions = {
    can_send_message: true,
    can_view_messages: true,
    can_leave: true,
    can_manage_group: false,
    can_add_participant: false,
    can_remove_participant: false,
    can_edit_group: false,
  };

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders message actions container", () => {
    render(
      <MessageActions
        message={baseMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    expect(screen.getByTestId("message-actions")).toBeInTheDocument();
  });

  it("shows react button when can_send_message is true", () => {
    render(
      <MessageActions
        message={baseMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    // React button (SmilePlus icon) + dropdown trigger = 2 buttons
    const container = screen.getByTestId("message-actions");
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(2);
  });

  it("hides react button when can_send_message is false", () => {
    const noSendPermissions = { ...basePermissions, can_send_message: false };

    render(
      <MessageActions
        message={baseMessage}
        isOwn={true}
        permissions={noSendPermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    // Only dropdown trigger remains (1 button)
    const container = screen.getByTestId("message-actions");
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(1);
  });

  it("shows dropdown trigger button", () => {
    render(
      <MessageActions
        message={baseMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    expect(screen.getByTestId("message-actions-trigger")).toBeInTheDocument();
  });

  it("shows Copy text for text messages", async () => {
    const user = userEvent.setup();

    render(
      <MessageActions
        message={baseMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    await user.click(screen.getByTestId("message-actions-trigger"));

    expect(screen.getByText("Copy text")).toBeInTheDocument();
  });

  it("hides Copy text for non-text messages", async () => {
    const user = userEvent.setup();
    const imageMessage = { ...baseMessage, content_type: "image" as const };

    render(
      <MessageActions
        message={imageMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    await user.click(screen.getByTestId("message-actions-trigger"));

    expect(screen.queryByText("Copy text")).not.toBeInTheDocument();
  });

  it("shows Edit for own recent text messages", async () => {
    const user = userEvent.setup();
    const recentMessage = {
      ...baseMessage,
      created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
    };

    render(
      <MessageActions
        message={recentMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    await user.click(screen.getByTestId("message-actions-trigger"));

    expect(screen.getByText("Edit")).toBeInTheDocument();
  });

  it("hides Edit for messages older than 15 minutes", async () => {
    const user = userEvent.setup();

    const oldMessage = {
      ...baseMessage,
      created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
    };

    render(
      <MessageActions
        message={oldMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    await user.click(screen.getByTestId("message-actions-trigger"));

    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
  });

  it("shows Delete for own messages", async () => {
    const user = userEvent.setup();

    render(
      <MessageActions
        message={baseMessage}
        isOwn={true}
        permissions={basePermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    await user.click(screen.getByTestId("message-actions-trigger"));

    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("shows Delete for admin (can_manage_group) on others' messages", async () => {
    const user = userEvent.setup();
    const adminPermissions = { ...basePermissions, can_manage_group: true };

    render(
      <MessageActions
        message={baseMessage}
        isOwn={false}
        permissions={adminPermissions}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onReact={mockOnReact}
      />
    );

    await user.click(screen.getByTestId("message-actions-trigger"));

    expect(screen.getByText("Delete")).toBeInTheDocument();
  });
});
