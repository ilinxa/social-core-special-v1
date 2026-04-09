import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { MessageSearchPanel } from "../MessageSearchPanel";

type MessageSearchResult = {
  id: string;
  conversation_id: string;
  sender_type: string;
  sender_id: string;
  sender_name: string;
  content: string;
  status: string;
  sequence_number: number;
  created_at: string;
  conversation_name: string;
};

const mockUseMessageSearch = vi.fn().mockReturnValue({
  data: undefined,
  isLoading: false,
  isFetchingNextPage: false,
  hasNextPage: false,
  fetchNextPage: vi.fn(),
});

vi.mock("@/features/chat/hooks/use-chat-queries", () => ({
  useMessageSearch: (...args: unknown[]) => mockUseMessageSearch(...args),
}));

vi.mock("react-intersection-observer", () => ({
  useInView: () => ({ ref: vi.fn(), inView: false }),
}));

describe("MessageSearchPanel", () => {
  const mockOnResultClick = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders search panel with input", () => {
    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByTestId("message-search-panel")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Search messages...")
    ).toBeInTheDocument();
  });

  it("shows 'Type to search messages' initially", () => {
    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText("Type to search messages")).toBeInTheDocument();
  });

  it("close button calls onClose", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    const panel = screen.getByTestId("message-search-panel");
    const buttons = within(panel).getAllByRole("button");
    await user.click(buttons[0]);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("shows loading skeleton when isLoading", () => {
    mockUseMessageSearch.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByTestId("message-search-panel")).toBeInTheDocument();
  });

  it("shows 'No messages found' when no results for query", async () => {
    mockUseMessageSearch.mockReturnValue({
      data: {
        pages: [{ results: [], count: 0, next: null, previous: null }],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    const user = userEvent.setup();
    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    const input = screen.getByPlaceholderText("Search messages...");
    await user.type(input, "hello");

    // Wait for the 300ms debounce to settle and component to re-render
    // The component renders: No messages found for \u201Chello\u201D (curly quotes from &ldquo;/&rdquo;)
    await waitFor(() => {
      expect(screen.getByText(/No messages found/)).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("renders search results", async () => {
    const mockResult: MessageSearchResult = {
      id: "msg-1",
      conversation_id: "conv-1",
      sender_type: "user",
      sender_id: "user-1",
      sender_name: "John Doe",
      content: "Hello world",
      status: "delivered",
      sequence_number: 1,
      created_at: "2026-03-26T10:00:00Z",
      conversation_name: "Test Conversation",
    };

    mockUseMessageSearch.mockReturnValue({
      data: {
        pages: [
          { results: [mockResult], count: 1, next: null, previous: null },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    const user = userEvent.setup();
    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    const input = screen.getByPlaceholderText("Search messages...");
    await user.type(input, "hello");

    // Wait for debounce to settle
    await waitFor(() => {
      expect(screen.getByTestId("search-result-msg-1")).toBeInTheDocument();
    }, { timeout: 2000 });
    expect(screen.getByText("Hello world")).toBeInTheDocument();
    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("clicking result calls onResultClick and onClose", async () => {
    const user = userEvent.setup();
    const mockResult: MessageSearchResult = {
      id: "msg-1",
      conversation_id: "conv-1",
      sender_type: "user",
      sender_id: "user-1",
      sender_name: "John Doe",
      content: "Hello world",
      status: "delivered",
      sequence_number: 1,
      created_at: "2026-03-26T10:00:00Z",
      conversation_name: "Test Conversation",
    };

    mockUseMessageSearch.mockReturnValue({
      data: {
        pages: [
          { results: [mockResult], count: 1, next: null, previous: null },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(
      <MessageSearchPanel
        onResultClick={mockOnResultClick}
        onClose={mockOnClose}
      />
    );

    const input = screen.getByPlaceholderText("Search messages...");
    await user.type(input, "hello");

    // Wait for debounce to settle and results to render
    await waitFor(() => {
      expect(screen.getByTestId("search-result-msg-1")).toBeInTheDocument();
    }, { timeout: 2000 });

    const resultElement = screen.getByTestId("search-result-msg-1");
    await user.click(resultElement);

    expect(mockOnResultClick).toHaveBeenCalledWith(mockResult);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });
});
