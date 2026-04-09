import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BlockList } from "../BlockList";
import { renderWithProviders } from "@/test/utils";

const mockUseChatBlocks = vi.fn().mockReturnValue({
  data: undefined,
  isLoading: false,
  isFetchingNextPage: false,
  hasNextPage: false,
  fetchNextPage: vi.fn(),
});
const mockUnblockMutate = vi.fn();

vi.mock("@/features/chat/hooks/use-chat-queries", () => ({
  useChatBlocks: (...args: unknown[]) => mockUseChatBlocks(...args),
}));
vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useUnblockParticipant: () => ({ mutate: mockUnblockMutate, isPending: false }),
}));
vi.mock("react-intersection-observer", () => ({
  useInView: () => ({ ref: vi.fn(), inView: false }),
}));

describe("BlockList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows "No blocked users" when empty', () => {
    mockUseChatBlocks.mockReturnValue({
      data: { pages: [{ results: [], count: 0 }] },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<BlockList />);

    expect(screen.getByText("No blocked users")).toBeInTheDocument();
  });

  it("shows loading skeletons when isLoading", () => {
    mockUseChatBlocks.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    const { container } = renderWithProviders(<BlockList />);

    const skeletons = container.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders blocked user names", () => {
    mockUseChatBlocks.mockReturnValue({
      data: {
        pages: [
          {
            results: [
              {
                id: "block-1",
                blocked_type: "user",
                blocked_id: "user-123",
                blocked_name: "John Doe",
                created_at: "2026-03-20T10:00:00Z",
              },
              {
                id: "block-2",
                blocked_type: "user",
                blocked_id: "user-456",
                blocked_name: "Jane Smith",
                created_at: "2026-03-21T15:30:00Z",
              },
            ],
            count: 2,
          },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<BlockList />);

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
  });

  it("shows formatted block date", () => {
    mockUseChatBlocks.mockReturnValue({
      data: {
        pages: [
          {
            results: [
              {
                id: "block-1",
                blocked_type: "user",
                blocked_id: "user-123",
                blocked_name: "John Doe",
                created_at: "2026-03-20T10:00:00Z",
              },
            ],
            count: 1,
          },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<BlockList />);

    expect(screen.getByText(/Blocked/)).toBeInTheDocument();
  });

  it("unblock button calls unblock.mutate with block id", async () => {
    const user = userEvent.setup();
    mockUseChatBlocks.mockReturnValue({
      data: {
        pages: [
          {
            results: [
              {
                id: "block-1",
                blocked_type: "user",
                blocked_id: "user-123",
                blocked_name: "John Doe",
                created_at: "2026-03-20T10:00:00Z",
              },
            ],
            count: 1,
          },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<BlockList />);

    const unblockButton = screen.getByTestId("unblock-block-1");
    await user.click(unblockButton);

    expect(mockUnblockMutate).toHaveBeenCalledWith("block-1");
  });

  it("renders block-list container", () => {
    mockUseChatBlocks.mockReturnValue({
      data: {
        pages: [
          {
            results: [
              {
                id: "block-1",
                blocked_type: "user",
                blocked_id: "user-123",
                blocked_name: "John Doe",
                created_at: "2026-03-20T10:00:00Z",
              },
            ],
            count: 1,
          },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<BlockList />);

    expect(screen.getByTestId("block-list")).toBeInTheDocument();
  });
});
