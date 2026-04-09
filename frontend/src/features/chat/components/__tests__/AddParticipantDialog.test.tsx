import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddParticipantDialog } from "../AddParticipantDialog";
import type { ChatParticipant } from "@/features/chat/types";
import { toast } from "sonner";

const mockAddMutate = vi.fn();

vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useAddParticipant: () => ({ mutate: mockAddMutate, isPending: false }),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const mockOnOpenChange = vi.fn();

const existingParticipants: ChatParticipant[] = [
  {
    id: "part-1",
    participant_type: "user",
    participant_id: "user-1",
    display_name: "Existing User",
    avatar_url: null,
    role: "member",
    request_status: "accepted",
    is_muted: false,
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
  },
];

describe("AddParticipantDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dialog title when open", () => {
    render(
      <AddParticipantDialog
        conversationId="conv-1"
        existingParticipants={existingParticipants}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByText("Add participant")).toBeInTheDocument();
  });

  it("shows input with placeholder", () => {
    render(
      <AddParticipantDialog
        conversationId="conv-1"
        existingParticipants={existingParticipants}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByPlaceholderText("Enter user ID...")
    ).toBeInTheDocument();
  });

  it("submit button disabled when input empty", () => {
    render(
      <AddParticipantDialog
        conversationId="conv-1"
        existingParticipants={existingParticipants}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const submitButton = screen.getByTestId("add-participant-submit");
    expect(submitButton).toBeDisabled();
  });

  it("shows toast error for existing participant", async () => {
    const user = userEvent.setup();
    render(
      <AddParticipantDialog
        conversationId="conv-1"
        existingParticipants={existingParticipants}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const input = screen.getByPlaceholderText("Enter user ID...");
    await user.type(input, "user-1");
    await user.click(screen.getByTestId("add-participant-submit"));

    expect(toast.error).toHaveBeenCalledWith(
      "This user is already a participant"
    );
    expect(mockAddMutate).not.toHaveBeenCalled();
  });

  it("calls addParticipant.mutate with correct data", async () => {
    const user = userEvent.setup();
    render(
      <AddParticipantDialog
        conversationId="conv-1"
        existingParticipants={existingParticipants}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const input = screen.getByPlaceholderText("Enter user ID...");
    await user.type(input, "user-2");
    await user.click(screen.getByTestId("add-participant-submit"));

    expect(mockAddMutate).toHaveBeenCalledWith(
      { participant_type: "user", participant_id: "user-2" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("submit button has correct text", () => {
    render(
      <AddParticipantDialog
        conversationId="conv-1"
        existingParticipants={existingParticipants}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByRole("button", { name: /add to conversation/i })
    ).toBeInTheDocument();
  });
});
