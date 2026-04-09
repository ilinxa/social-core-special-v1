import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { ChatRequestCard } from "../ChatRequestCard";
import type { ChatRequest } from "@/features/chat/types";

const mockAcceptMutate = vi.fn();
const mockIgnoreMutate = vi.fn();

const mockUseMutations = vi.fn(() => ({
  useAcceptChatRequest: () => ({
    mutate: mockAcceptMutate,
    isPending: false,
  }),
  useIgnoreChatRequest: () => ({
    mutate: mockIgnoreMutate,
    isPending: false,
  }),
}));

vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useAcceptChatRequest: () => mockUseMutations().useAcceptChatRequest(),
  useIgnoreChatRequest: () => mockUseMutations().useIgnoreChatRequest(),
}));

describe("ChatRequestCard", () => {
  const mockRequest: ChatRequest = {
    conversation_id: "conv-1",
    requester: {
      participant_type: "user",
      participant_id: "user-1",
      display_name: "John Doe",
      avatar_url: null,
    },
    preview_messages: [
      { content: "Hello!", created_at: "2026-03-26T10:00:00Z" },
    ],
    message_count: 3,
    created_at: "2026-03-26T09:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMutations.mockReturnValue({
      useAcceptChatRequest: () => ({
        mutate: mockAcceptMutate,
        isPending: false,
      }),
      useIgnoreChatRequest: () => ({
        mutate: mockIgnoreMutate,
        isPending: false,
      }),
    });
  });

  it("renders requester name", () => {
    renderWithProviders(<ChatRequestCard request={mockRequest} />);

    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("shows message count", () => {
    renderWithProviders(<ChatRequestCard request={mockRequest} />);

    expect(screen.getByText(/3/)).toBeInTheDocument();
  });

  it("shows preview messages", () => {
    renderWithProviders(<ChatRequestCard request={mockRequest} />);

    expect(screen.getByText("Hello!")).toBeInTheDocument();
  });

  it("accept button calls accept.mutate with conversation_id", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatRequestCard request={mockRequest} />);

    const acceptButton = screen.getByTestId("accept-request");
    await user.click(acceptButton);

    expect(mockAcceptMutate).toHaveBeenCalledWith("conv-1");
    expect(mockAcceptMutate).toHaveBeenCalledTimes(1);
  });

  it("ignore button calls ignore.mutate with conversation_id", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatRequestCard request={mockRequest} />);

    const ignoreButton = screen.getByTestId("ignore-request");
    await user.click(ignoreButton);

    expect(mockIgnoreMutate).toHaveBeenCalledWith("conv-1");
    expect(mockIgnoreMutate).toHaveBeenCalledTimes(1);
  });

  it("buttons are disabled when isPending", () => {
    mockUseMutations.mockReturnValue({
      useAcceptChatRequest: () => ({
        mutate: mockAcceptMutate,
        isPending: true,
      }),
      useIgnoreChatRequest: () => ({
        mutate: mockIgnoreMutate,
        isPending: true,
      }),
    });

    renderWithProviders(<ChatRequestCard request={mockRequest} />);

    const acceptButton = screen.getByTestId("accept-request");
    const ignoreButton = screen.getByTestId("ignore-request");

    expect(acceptButton).toBeDisabled();
    expect(ignoreButton).toBeDisabled();
  });
});
