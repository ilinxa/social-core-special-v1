import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReactionBar } from "../ReactionBar";
import { renderWithProviders } from "@/test/utils";
import type { ReactionType } from "@/features/chat/types";

const mockAddMutate = vi.fn();
const mockRemoveMutate = vi.fn();

vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useAddReaction: () => ({ mutate: mockAddMutate, isPending: false }),
  useRemoveReaction: () => ({ mutate: mockRemoveMutate, isPending: false }),
}));

describe("ReactionBar", () => {
  const defaultProps = {
    conversationId: "conv-123",
    messageId: "msg-456",
    reactions: {
      like: 0,
      heart: 0,
      laugh: 0,
      wow: 0,
      sad: 0,
      angry: 0,
    } as Record<ReactionType, number>,
    myReactions: [] as ReactionType[],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when all reaction counts are zero", () => {
    const { container } = renderWithProviders(<ReactionBar {...defaultProps} />);

    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId("reaction-bar")).not.toBeInTheDocument();
  });

  it("renders reaction badges for non-zero counts", () => {
    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 3,
        heart: 1,
      },
    };

    renderWithProviders(<ReactionBar {...props} />);

    expect(screen.getByTestId("reaction-bar")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-badge-like")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-badge-heart")).toBeInTheDocument();
    expect(screen.queryByTestId("reaction-badge-laugh")).not.toBeInTheDocument();
  });

  it("shows emoji and count in badge", () => {
    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 5,
        wow: 2,
      },
    };

    renderWithProviders(<ReactionBar {...props} />);

    const likeBadge = screen.getByTestId("reaction-badge-like");
    const wowBadge = screen.getByTestId("reaction-badge-wow");

    expect(likeBadge).toHaveTextContent("👍");
    expect(likeBadge).toHaveTextContent("5");
    expect(wowBadge).toHaveTextContent("😮");
    expect(wowBadge).toHaveTextContent("2");
  });

  it("highlights user's own reactions", () => {
    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 3,
        heart: 2,
      },
      myReactions: ["like"] as ReactionType[],
    };

    renderWithProviders(<ReactionBar {...props} />);

    const likeBadge = screen.getByTestId("reaction-badge-like");
    const heartBadge = screen.getByTestId("reaction-badge-heart");

    // Own reaction should have border-primary class
    expect(likeBadge).toHaveClass("border-primary/50");
    // Non-own reaction should not have border-primary class
    expect(heartBadge).not.toHaveClass("border-primary/50");
  });

  it("clicking own reaction calls removeReaction.mutate", async () => {
    const user = userEvent.setup();

    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 1,
      },
      myReactions: ["like"] as ReactionType[],
    };

    renderWithProviders(<ReactionBar {...props} />);

    const likeBadge = screen.getByTestId("reaction-badge-like");
    await user.click(likeBadge);

    expect(mockRemoveMutate).toHaveBeenCalledWith({
      messageId: "msg-456",
      reaction: "like",
    });
    expect(mockRemoveMutate).toHaveBeenCalledTimes(1);
    expect(mockAddMutate).not.toHaveBeenCalled();
  });

  it("clicking non-own reaction calls addReaction.mutate", async () => {
    const user = userEvent.setup();

    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        heart: 2,
      },
      myReactions: [] as ReactionType[],
    };

    renderWithProviders(<ReactionBar {...props} />);

    const heartBadge = screen.getByTestId("reaction-badge-heart");
    await user.click(heartBadge);

    expect(mockAddMutate).toHaveBeenCalledWith({
      messageId: "msg-456",
      reaction: "heart",
    });
    expect(mockAddMutate).toHaveBeenCalledTimes(1);
    expect(mockRemoveMutate).not.toHaveBeenCalled();
  });

  it("shows add reaction button", () => {
    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 1,
      },
    };

    renderWithProviders(<ReactionBar {...props} />);

    expect(screen.getByTestId("reaction-add-button")).toBeInTheDocument();
  });

  it("renders ReactionPicker when add button clicked", async () => {
    const user = userEvent.setup();

    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 1,
      },
    };

    renderWithProviders(<ReactionBar {...props} />);

    const addButton = screen.getByTestId("reaction-add-button");
    await user.click(addButton);

    // ReactionPicker should be visible
    expect(screen.getByTestId("reaction-picker")).toBeInTheDocument();
  });

  it("adds reaction through picker and calls addReaction.mutate", async () => {
    const user = userEvent.setup();

    const props = {
      ...defaultProps,
      reactions: {
        ...defaultProps.reactions,
        like: 1,
      },
    };

    renderWithProviders(<ReactionBar {...props} />);

    const addButton = screen.getByTestId("reaction-add-button");
    await user.click(addButton);

    const laughButton = screen.getByTestId("reaction-laugh");
    await user.click(laughButton);

    expect(mockAddMutate).toHaveBeenCalledWith({
      messageId: "msg-456",
      reaction: "laugh",
    });
    expect(mockAddMutate).toHaveBeenCalledTimes(1);
  });

  it("handles multiple reactions correctly", () => {
    const props = {
      ...defaultProps,
      reactions: {
        like: 5,
        heart: 3,
        laugh: 2,
        wow: 1,
        sad: 0,
        angry: 0,
      },
      myReactions: ["like", "heart"] as ReactionType[],
    };

    renderWithProviders(<ReactionBar {...props} />);

    // All non-zero reactions should be visible
    expect(screen.getByTestId("reaction-badge-like")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-badge-heart")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-badge-laugh")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-badge-wow")).toBeInTheDocument();

    // Zero reactions should not be visible
    expect(screen.queryByTestId("reaction-badge-sad")).not.toBeInTheDocument();
    expect(screen.queryByTestId("reaction-badge-angry")).not.toBeInTheDocument();

    // Own reactions should be highlighted
    const likeBadge = screen.getByTestId("reaction-badge-like");
    const heartBadge = screen.getByTestId("reaction-badge-heart");
    const laughBadge = screen.getByTestId("reaction-badge-laugh");

    expect(likeBadge).toHaveClass("border-primary/50");
    expect(heartBadge).toHaveClass("border-primary/50");
    expect(laughBadge).not.toHaveClass("border-primary/50");
  });
});
