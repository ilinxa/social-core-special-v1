import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";
import { ChatRequestList } from "../ChatRequestList";

type ChatRequest = {
  conversation_id: string;
  requester: {
    participant_type: string;
    participant_id: string;
    display_name: string;
    avatar_url: string | null;
  } | null;
  preview_messages: Array<{ content: string; created_at: string }>;
  message_count: number;
  created_at: string;
};

const mockUseChatRequests = vi.fn().mockReturnValue({
  data: undefined,
  isLoading: false,
  isFetchingNextPage: false,
  hasNextPage: false,
  fetchNextPage: vi.fn(),
});

vi.mock("@/features/chat/hooks/use-chat-queries", () => ({
  useChatRequests: (...args: unknown[]) => mockUseChatRequests(...args),
}));

vi.mock("react-intersection-observer", () => ({
  useInView: () => ({ ref: vi.fn(), inView: false }),
}));

vi.mock("../ChatRequestCard", () => ({
  ChatRequestCard: ({ request }: { request: { conversation_id: string } }) => (
    <div data-testid={`mock-request-card-${request.conversation_id}`} />
  ),
}));

describe("ChatRequestList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when no requests and not loading", () => {
    mockUseChatRequests.mockReturnValue({
      data: {
        pages: [{ results: [], count: 0, next: null, previous: null }],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    const { container } = renderWithProviders(<ChatRequestList />);

    expect(container.firstChild).toBeNull();
  });

  it("shows loading skeletons when isLoading", () => {
    mockUseChatRequests.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    const { container } = renderWithProviders(<ChatRequestList />);

    const skeletons = container.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders request cards for each request", () => {
    const mockRequests: ChatRequest[] = [
      {
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
      },
      {
        conversation_id: "conv-2",
        requester: {
          participant_type: "user",
          participant_id: "user-2",
          display_name: "Jane Smith",
          avatar_url: null,
        },
        preview_messages: [
          { content: "Hi there!", created_at: "2026-03-26T11:00:00Z" },
        ],
        message_count: 1,
        created_at: "2026-03-26T10:30:00Z",
      },
    ];

    mockUseChatRequests.mockReturnValue({
      data: {
        pages: [
          { results: mockRequests, count: 2, next: null, previous: null },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<ChatRequestList />);

    expect(screen.getByTestId("mock-request-card-conv-1")).toBeInTheDocument();
    expect(screen.getByTestId("mock-request-card-conv-2")).toBeInTheDocument();
  });

  it("shows request count in heading", () => {
    const mockRequests: ChatRequest[] = [
      {
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
      },
    ];

    mockUseChatRequests.mockReturnValue({
      data: {
        pages: [
          { results: mockRequests, count: 1, next: null, previous: null },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<ChatRequestList />);

    expect(screen.getByText(/Message Requests/)).toBeInTheDocument();
    expect(screen.getByText(/1/)).toBeInTheDocument();
  });

  it("renders chat-request-list container", () => {
    const mockRequests: ChatRequest[] = [
      {
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
      },
    ];

    mockUseChatRequests.mockReturnValue({
      data: {
        pages: [
          { results: mockRequests, count: 1, next: null, previous: null },
        ],
      },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    });

    renderWithProviders(<ChatRequestList />);

    expect(screen.getByTestId("chat-request-list")).toBeInTheDocument();
  });
});
