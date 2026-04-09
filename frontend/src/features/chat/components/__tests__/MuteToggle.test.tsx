import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MuteToggle } from "../MuteToggle";

const mockMuteMutate = vi.fn();
const mockUnmuteMutate = vi.fn();
const mockIsPending = { mute: false, unmute: false };

vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useMuteConversation: () => ({
    mutate: mockMuteMutate,
    isPending: mockIsPending.mute,
  }),
  useUnmuteConversation: () => ({
    mutate: mockUnmuteMutate,
    isPending: mockIsPending.unmute,
  }),
}));

describe("MuteToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsPending.mute = false;
    mockIsPending.unmute = false;
  });

  it('shows "Mute" when not muted', () => {
    render(<MuteToggle conversationId="conv-123" isMuted={false} />);

    const button = screen.getByTestId("mute-toggle");
    expect(button).toBeInTheDocument();
    expect(screen.getByText("Mute")).toBeInTheDocument();
  });

  it('shows "Unmute" when muted', () => {
    render(<MuteToggle conversationId="conv-123" isMuted={true} />);

    const button = screen.getByTestId("mute-toggle");
    expect(button).toBeInTheDocument();
    expect(screen.getByText("Unmute")).toBeInTheDocument();
  });

  it("clicking Mute calls mute.mutate with conversationId", async () => {
    const user = userEvent.setup();
    render(<MuteToggle conversationId="conv-123" isMuted={false} />);

    const button = screen.getByTestId("mute-toggle");
    await user.click(button);

    expect(mockMuteMutate).toHaveBeenCalledWith("conv-123");
  });

  it("clicking Unmute calls unmute.mutate with conversationId", async () => {
    const user = userEvent.setup();
    render(<MuteToggle conversationId="conv-123" isMuted={true} />);

    const button = screen.getByTestId("mute-toggle");
    await user.click(button);

    expect(mockUnmuteMutate).toHaveBeenCalledWith("conv-123");
  });

  it("button is disabled when isPending", () => {
    mockIsPending.mute = true;

    render(<MuteToggle conversationId="conv-123" isMuted={false} />);

    const button = screen.getByTestId("mute-toggle");
    expect(button).toBeDisabled();
  });
});
