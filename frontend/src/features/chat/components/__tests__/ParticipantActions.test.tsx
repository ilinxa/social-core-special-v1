import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ParticipantActions } from "../ParticipantActions";
import type { ChatParticipant, ConversationPermissions } from "@/features/chat/types";

const mockPromoteMutate = vi.fn();
const mockDemoteMutate = vi.fn();
const mockRemoveMutate = vi.fn();

vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  usePromoteParticipant: () => ({
    mutate: mockPromoteMutate,
    isPending: false,
  }),
  useDemoteParticipant: () => ({
    mutate: mockDemoteMutate,
    isPending: false,
  }),
  useRemoveParticipant: () => ({ mutate: mockRemoveMutate, isPending: false }),
}));

const mockPermissions: ConversationPermissions = {
  can_send_message: true,
  can_view_messages: true,
  can_leave: true,
  can_manage_group: true,
  can_add_participant: false,
  can_remove_participant: true,
  can_edit_group: false,
};

const mockParticipant: ChatParticipant = {
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
};

describe("ParticipantActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null for self", () => {
    const { container } = render(
      <ParticipantActions
        conversationId="conv-1"
        participant={mockParticipant}
        permissions={mockPermissions}
        currentUserId="user-1"
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it("returns null for inactive participant", () => {
    const inactiveParticipant = { ...mockParticipant, is_active: false };
    const { container } = render(
      <ParticipantActions
        conversationId="conv-1"
        participant={inactiveParticipant}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it("returns null when no manage or remove permissions", () => {
    const noPermissions = {
      ...mockPermissions,
      can_manage_group: false,
      can_remove_participant: false,
    };
    const { container } = render(
      <ParticipantActions
        conversationId="conv-1"
        participant={mockParticipant}
        permissions={noPermissions}
        currentUserId="user-2"
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it("shows Make admin for non-admin with can_manage_group", async () => {
    const user = userEvent.setup();
    render(
      <ParticipantActions
        conversationId="conv-1"
        participant={mockParticipant}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    await user.click(
      screen.getByTestId("participant-actions-user-1")
    );

    expect(screen.getByText("Make admin")).toBeInTheDocument();
  });

  it("shows Remove admin for admin with can_manage_group", async () => {
    const user = userEvent.setup();
    const adminParticipant = { ...mockParticipant, role: "admin" as const };
    render(
      <ParticipantActions
        conversationId="conv-1"
        participant={adminParticipant}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    await user.click(
      screen.getByTestId("participant-actions-user-1")
    );

    expect(screen.getByText("Remove admin")).toBeInTheDocument();
  });

  it("promote calls promote.mutate with participant_id", async () => {
    const user = userEvent.setup();
    render(
      <ParticipantActions
        conversationId="conv-1"
        participant={mockParticipant}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    await user.click(
      screen.getByTestId("participant-actions-user-1")
    );
    await user.click(screen.getByText("Make admin"));

    expect(mockPromoteMutate).toHaveBeenCalledWith("user-1");
  });

  it("shows Remove from group with can_remove_participant", async () => {
    const user = userEvent.setup();
    render(
      <ParticipantActions
        conversationId="conv-1"
        participant={mockParticipant}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    await user.click(
      screen.getByTestId("participant-actions-user-1")
    );

    expect(screen.getByText("Remove from group")).toBeInTheDocument();
  });

  it("remove calls remove.mutate with correct params", async () => {
    const user = userEvent.setup();
    render(
      <ParticipantActions
        conversationId="conv-1"
        participant={mockParticipant}
        permissions={mockPermissions}
        currentUserId="user-2"
      />
    );

    await user.click(
      screen.getByTestId("participant-actions-user-1")
    );
    await user.click(screen.getByText("Remove from group"));

    expect(mockRemoveMutate).toHaveBeenCalledWith({
      participantId: "user-1",
      participantType: "user",
    });
  });
});
