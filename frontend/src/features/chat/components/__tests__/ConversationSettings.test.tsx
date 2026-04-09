import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConversationSettings } from "../ConversationSettings";
import type {
  ConversationDetail,
  ConversationPermissions,
  ChatParticipant,
} from "@/features/chat/types";
import type { WithPermissions } from "@/types/api";

vi.mock("../GroupInfoSection", () => ({
  GroupInfoSection: () => <div data-testid="mock-group-info" />,
}));

vi.mock("../ParticipantList", () => ({
  ParticipantList: () => <div data-testid="mock-participant-list" />,
}));

vi.mock("../AddParticipantDialog", () => ({
  AddParticipantDialog: () => <div data-testid="mock-add-participant" />,
}));

vi.mock("../MuteToggle", () => ({
  MuteToggle: () => <div data-testid="mock-mute-toggle" />,
}));

vi.mock("../LeaveConversationButton", () => ({
  LeaveConversationButton: () => <div data-testid="mock-leave-button" />,
}));

vi.mock("../BlockList", () => ({
  BlockList: () => <div data-testid="mock-block-list" />,
}));

const mockOnOpenChange = vi.fn();
const mockOnLeft = vi.fn();

const mockParticipants: ChatParticipant[] = [
  {
    id: "part-1",
    participant_type: "user",
    participant_id: "user-1",
    display_name: "John Doe",
    avatar_url: null,
    role: "admin",
    request_status: "accepted",
    is_muted: false,
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
  },
];

const mockPermissions: ConversationPermissions = {
  can_send_message: true,
  can_view_messages: true,
  can_leave: true,
  can_manage_group: true,
  can_add_participant: true,
  can_remove_participant: true,
  can_edit_group: true,
};

const baseConversation: ConversationDetail = {
  id: "conv-1",
  scope_type: "global",
  scope_id: null,
  conversation_type: "group",
  name: "Engineering Team",
  description: "Team chat",
  participants: mockParticipants,
  last_message: null,
  is_active: true,
  created_at: "2024-01-01T00:00:00Z",
};

describe("ConversationSettings", () => {
  it("renders Group settings title for group conversations", () => {
    const conversation: ConversationDetail &
  WithPermissions<
    ConversationPermissions
    > = {
      ...baseConversation,
      _permissions: mockPermissions,
    };

    render(
      <ConversationSettings
        conversation={conversation}
        currentUserId="user-1"
        open={true}
        onOpenChange={mockOnOpenChange}
        onLeft={mockOnLeft}
      />
    );

    expect(screen.getByText("Group settings")).toBeInTheDocument();
  });

  it("renders Conversation settings title for DM", () => {
    const dmConversation: ConversationDetail &
  WithPermissions<
    ConversationPermissions
    > = {
      ...baseConversation,
      conversation_type: "direct",
      _permissions: mockPermissions,
    };

    render(
      <ConversationSettings
        conversation={dmConversation}
        currentUserId="user-1"
        open={true}
        onOpenChange={mockOnOpenChange}
        onLeft={mockOnLeft}
      />
    );

    expect(screen.getByText("Conversation settings")).toBeInTheDocument();
  });

  it("shows group info section for groups", () => {
    const conversation: ConversationDetail &
  WithPermissions<
    ConversationPermissions
    > = {
      ...baseConversation,
      _permissions: mockPermissions,
    };

    render(
      <ConversationSettings
        conversation={conversation}
        currentUserId="user-1"
        open={true}
        onOpenChange={mockOnOpenChange}
        onLeft={mockOnLeft}
      />
    );

    expect(screen.getByTestId("mock-group-info")).toBeInTheDocument();
  });

  it("hides group info section for DMs", () => {
    const dmConversation: ConversationDetail &
  WithPermissions<
    ConversationPermissions
    > = {
      ...baseConversation,
      conversation_type: "direct",
      _permissions: mockPermissions,
    };

    render(
      <ConversationSettings
        conversation={dmConversation}
        currentUserId="user-1"
        open={true}
        onOpenChange={mockOnOpenChange}
        onLeft={mockOnLeft}
      />
    );

    expect(screen.queryByTestId("mock-group-info")).not.toBeInTheDocument();
  });

  it("shows add participant button when can_add_participant is true", () => {
    const conversation: ConversationDetail &
  WithPermissions<
    ConversationPermissions
    > = {
      ...baseConversation,
      _permissions: mockPermissions,
    };

    render(
      <ConversationSettings
        conversation={conversation}
        currentUserId="user-1"
        open={true}
        onOpenChange={mockOnOpenChange}
        onLeft={mockOnLeft}
      />
    );

    expect(screen.getByTestId("add-participant-button")).toBeInTheDocument();
  });

  it("hides add participant button when can_add_participant is false", () => {
    const conversation: ConversationDetail &
  WithPermissions<
    ConversationPermissions
    > = {
      ...baseConversation,
      _permissions: {
        ...mockPermissions,
        can_add_participant: false,
      },
    };

    render(
      <ConversationSettings
        conversation={conversation}
        currentUserId="user-1"
        open={true}
        onOpenChange={mockOnOpenChange}
        onLeft={mockOnLeft}
      />
    );

    expect(
      screen.queryByTestId("add-participant-button")
    ).not.toBeInTheDocument();
  });
});
