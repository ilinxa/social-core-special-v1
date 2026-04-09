import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { RequestBanner } from "../RequestBanner";

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

describe("RequestBanner", () => {
  const conversationId = "conv-1";

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

  it("renders banner text", () => {
    renderWithProviders(<RequestBanner conversationId={conversationId} />);

    expect(
      screen.getByText("Accept this request to continue chatting")
    ).toBeInTheDocument();
    expect(screen.getByTestId("request-banner")).toBeInTheDocument();
  });

  it("accept button calls accept.mutate with conversationId", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RequestBanner conversationId={conversationId} />);

    const acceptButton = screen.getByRole("button", { name: /accept/i });
    await user.click(acceptButton);

    expect(mockAcceptMutate).toHaveBeenCalledWith("conv-1");
    expect(mockAcceptMutate).toHaveBeenCalledTimes(1);
  });

  it("ignore button calls ignore.mutate with conversationId", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RequestBanner conversationId={conversationId} />);

    const ignoreButton = screen.getByRole("button", { name: /ignore/i });
    await user.click(ignoreButton);

    expect(mockIgnoreMutate).toHaveBeenCalledWith("conv-1");
    expect(mockIgnoreMutate).toHaveBeenCalledTimes(1);
  });

  it("buttons disabled when isPending", () => {
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

    renderWithProviders(<RequestBanner conversationId={conversationId} />);

    const acceptButton = screen.getByRole("button", { name: /accept/i });
    const ignoreButton = screen.getByRole("button", { name: /ignore/i });

    expect(acceptButton).toBeDisabled();
    expect(ignoreButton).toBeDisabled();
  });

  it("renders both accept and ignore buttons", () => {
    renderWithProviders(<RequestBanner conversationId={conversationId} />);

    expect(screen.getByRole("button", { name: /accept/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ignore/i })).toBeInTheDocument();
  });
});
