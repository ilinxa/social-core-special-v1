import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ParticipantList } from "../ParticipantList";
import type { ChatParticipant, ConversationPermissions } from "@/features/chat/types";

vi.mock("../ParticipantActions", () => ({
  ParticipantActions: () => <div data-testid="mock-participant-actions" />,
}));

vi.mock("../PresenceDot", () => ({
  PresenceDot: () => <div data-testid="mock-presence-dot" />,
}));

const mockPermissions: ConversationPermissions = {
  can_send_message: true,
  can_view_messages: true,
  can_leave: true,
  can_manage_group: false,
  can_add_participant: false,
  can_remove_participant: false,
  can_edit_group: false,
};

describe("ParticipantList", () => {
  it("renders participant list container", () => {
    const participants: ChatParticipant[] = [
      {
        id: "part-1",
        participant_type: "user",
        participant_id: "user-1",
        display_name: "John Doe",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    expect(screen.getByTestId("participant-list")).toBeInTheDocument();
  });

  it("shows active member count", () => {
    const participants: ChatParticipant[] = [
      {
        id: "part-1",
        participant_type: "user",
        participant_id: "user-1",
        display_name: "John Doe",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "part-2",
        participant_type: "user",
        participant_id: "user-2",
        display_name: "Jane Smith",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-3"
      />
    );

    expect(screen.getByText(/Members \(2\)/i)).toBeInTheDocument();
  });

  it("renders display names", () => {
    const participants: ChatParticipant[] = [
      {
        id: "part-1",
        participant_type: "user",
        participant_id: "user-1",
        display_name: "John Doe",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("shows (you) for current user", () => {
    const participants: ChatParticipant[] = [
      {
        id: "part-1",
        participant_type: "user",
        participant_id: "user-1",
        display_name: "John Doe",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-1"
      />
    );

    expect(screen.getByText("(you)")).toBeInTheDocument();
  });

  it("shows Admin badge for admin role", () => {
    const participants: ChatParticipant[] = [
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

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("shows inactive section for left participants", () => {
    const participants: ChatParticipant[] = [
      {
        id: "part-1",
        participant_type: "user",
        participant_id: "user-1",
        display_name: "Active User",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "part-2",
        participant_type: "user",
        participant_id: "user-2",
        display_name: "Left User",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: false,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-3"
      />
    );

    expect(screen.getByText(/Inactive/)).toBeInTheDocument();
  });

  it("shows Left text for inactive participants", () => {
    const participants: ChatParticipant[] = [
      {
        id: "part-1",
        participant_type: "user",
        participant_id: "user-1",
        display_name: "Left User",
        avatar_url: null,
        role: "member",
        request_status: "accepted",
        is_muted: false,
        is_active: false,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(
      <ParticipantList
        conversationId="conv-1"
        participants={participants}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    expect(screen.getByText("Left")).toBeInTheDocument();
  });
});
