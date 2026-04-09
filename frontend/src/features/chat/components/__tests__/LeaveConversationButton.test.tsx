import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LeaveConversationButton } from "../LeaveConversationButton";

const mockLeaveMutate = vi.fn();
vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useLeaveConversation: () => ({ mutate: mockLeaveMutate, isPending: false }),
}));

describe("LeaveConversationButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders leave button", () => {
    render(<LeaveConversationButton conversationId="conv-123" />);

    expect(
      screen.getByTestId("leave-conversation-button")
    ).toBeInTheDocument();
    expect(screen.getByText("Leave conversation")).toBeInTheDocument();
  });

  it("clicking shows confirmation dialog", async () => {
    const user = userEvent.setup();
    render(<LeaveConversationButton conversationId="conv-123" />);

    await user.click(screen.getByTestId("leave-conversation-button"));

    expect(screen.getByText("Leave conversation?")).toBeInTheDocument();
  });

  it("shows warning description text", async () => {
    const user = userEvent.setup();
    render(<LeaveConversationButton conversationId="conv-123" />);

    await user.click(screen.getByTestId("leave-conversation-button"));

    expect(
      screen.getByText(/You will no longer receive messages/i)
    ).toBeInTheDocument();
  });

  it("confirming calls leave.mutate with conversationId", async () => {
    const user = userEvent.setup();
    render(<LeaveConversationButton conversationId="conv-123" />);

    await user.click(screen.getByTestId("leave-conversation-button"));
    const confirmButton = screen.getByRole("button", { name: "Leave" });
    await user.click(confirmButton);

    expect(mockLeaveMutate).toHaveBeenCalledWith(
      "conv-123",
      expect.objectContaining({
        onSuccess: expect.any(Function),
      })
    );
  });

  it("cancel closes dialog", async () => {
    const user = userEvent.setup();
    render(<LeaveConversationButton conversationId="conv-123" />);

    await user.click(screen.getByTestId("leave-conversation-button"));
    expect(screen.getByText("Leave conversation?")).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    await user.click(cancelButton);

    expect(
      screen.queryByText("Leave conversation?")
    ).not.toBeInTheDocument();
  });
});
