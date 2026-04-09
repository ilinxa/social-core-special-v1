import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { createWrapper } from "@/test/utils";
import { useChatStore } from "@/stores/chat-store";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Track registered event handlers and state-change handlers so tests can
// invoke them to simulate server->client events.
let mockEventHandlers: Map<string, (payload: unknown) => void>;
let mockStateHandler: ((state: string) => void) | null;

const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockSend = vi.fn();

// Track constructor calls for lifecycle tests
const mockConstructorArgs: unknown[] = [];

vi.mock("@/lib/ws-client", () => {
  class MockWsClient {
    connect = mockConnect;
    disconnect = mockDisconnect;
    send = mockSend;

    constructor(opts: unknown) {
      mockConstructorArgs.push(opts);
      mockEventHandlers = new Map();
      mockStateHandler = null;
    }

    on(event: string, handler: (payload: unknown) => void): () => void {
      mockEventHandlers.set(event, handler);
      return vi.fn();
    }

    onStateChange(handler: (state: string) => void): () => void {
      mockStateHandler = handler;
      return vi.fn();
    }

    get state() {
      return "connected" as const;
    }
  }

  return { WsClient: MockWsClient };
});

vi.mock("@/lib/api-client", () => ({
  getAccessToken: vi.fn(() => "test-token"),
}));

vi.mock("@/stores/auth-store", () => ({
  useUser: vi.fn(() => ({ id: "user-1" })),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

vi.mock("@/features/chat/utils/optimistic-updates", () => ({
  insertMessageInCache: vi.fn(),
  updateMessageInCache: vi.fn(),
  updateReactionInCache: vi.fn(),
  moveConversationToTop: vi.fn(),
  incrementConversationUnread: vi.fn(),
}));

// Import AFTER mocks are declared
import { useUser } from "@/stores/auth-store";
import { toast } from "sonner";
import {
  insertMessageInCache,
  updateMessageInCache,
  moveConversationToTop,
  incrementConversationUnread,
  updateReactionInCache,
} from "@/features/chat/utils/optimistic-updates";
import { useChatWs } from "../use-chat-ws";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Simulate a server event arriving on the WS. */
function emitServerEvent(type: string, payload: unknown) {
  const handler = mockEventHandlers.get(type);
  if (!handler) throw new Error(`No handler registered for "${type}"`);
  handler(payload);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useChatWs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConstructorArgs.length = 0;
    useChatStore.setState({
      activeConversationId: null,
      wsState: "disconnected",
      typingUsers: {},
      onlineUsers: new Set<string>(),
      seenWatermarks: {},
      deliveredWatermarks: {},
      unreadCounts: {},
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // CONNECTION LIFECYCLE
  // =========================================================================

  it("creates WsClient and connects when user is authenticated", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    expect(mockConstructorArgs).toHaveLength(1);
    expect(mockConstructorArgs[0]).toEqual(
      expect.objectContaining({
        url: expect.stringContaining("/ws/chat/"),
        reconnect: true,
      }),
    );
    expect(mockConnect).toHaveBeenCalledTimes(1);
  });

  it("disconnects on unmount", () => {
    const { unmount } = renderHook(() => useChatWs(), {
      wrapper: createWrapper(),
    });

    unmount();

    expect(mockDisconnect).toHaveBeenCalledTimes(1);
  });

  it("does NOT connect when no user (currentUserId is empty)", () => {
    vi.mocked(useUser).mockReturnValue(null);

    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    expect(mockConstructorArgs).toHaveLength(0);
    expect(mockConnect).not.toHaveBeenCalled();
  });

  // =========================================================================
  // EVENT SUBSCRIPTIONS
  // =========================================================================

  it("subscribes to all 10 server event types", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    const expectedEvents = [
      "message.new",
      "message.edited",
      "message.deleted",
      "typing",
      "seen.update",
      "delivered.update",
      "presence",
      "reaction.update",
      "conversation.new",
      "error",
    ];

    // The event handlers map is populated by the mock's `on()` method
    for (const event of expectedEvents) {
      expect(mockEventHandlers.has(event)).toBe(true);
    }
  });

  it("calls setWsState on state changes", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    // onStateChange should have been called — mockStateHandler will be set
    expect(mockStateHandler).not.toBeNull();

    // Simulate a state change
    act(() => {
      if (mockStateHandler) mockStateHandler("connected");
    });

    expect(useChatStore.getState().wsState).toBe("connected");
  });

  // =========================================================================
  // EVENT HANDLERS
  // =========================================================================

  it("handles message.new — inserts message and moves conversation to top", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("message.new", {
        id: "msg-1",
        conversation_id: "conv-1",
        sender_type: "user",
        sender_id: "user-2",
        sender_name: "Alice",
        sender_avatar_url: null,
        content_type: "text",
        content: "Hello!",
        status: "sent",
        sequence_number: 1,
        edited_at: null,
        created_at: "2026-03-20T12:00:00Z",
        attachments: [],
      });
    });

    expect(insertMessageInCache).toHaveBeenCalledTimes(1);
    expect(insertMessageInCache).toHaveBeenCalledWith(
      expect.anything(), // queryClient
      "conv-1",
      expect.objectContaining({
        id: "msg-1",
        content: "Hello!",
        reactions: { like: 0, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
        my_reactions: [],
      }),
    );
    expect(moveConversationToTop).toHaveBeenCalledWith(
      expect.anything(),
      "conv-1",
      expect.objectContaining({
        id: "msg-1",
        sender_name: "Alice",
        content_preview: "Hello!",
      }),
    );
  });

  it("handles message.new — increments unread for non-active conversation", () => {
    useChatStore.setState({ activeConversationId: "conv-other" });

    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("message.new", {
        id: "msg-2",
        conversation_id: "conv-1",
        sender_type: "user",
        sender_id: "user-2",
        sender_name: "Bob",
        sender_avatar_url: null,
        content_type: "text",
        content: "Hey",
        status: "sent",
        sequence_number: 2,
        edited_at: null,
        created_at: "2026-03-20T12:01:00Z",
        attachments: [],
      });
    });

    expect(incrementConversationUnread).toHaveBeenCalledWith(
      expect.anything(),
      "conv-1",
    );
  });

  it("handles message.edited — updates message in cache", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("message.edited", {
        conversation_id: "conv-1",
        message_id: "msg-1",
        content: "Edited content",
        edited_at: "2026-03-20T12:05:00Z",
      });
    });

    expect(updateMessageInCache).toHaveBeenCalledWith(
      expect.anything(),
      "conv-1",
      "msg-1",
      {
        content: "Edited content",
        edited_at: "2026-03-20T12:05:00Z",
        status: "edited",
      },
    );
  });

  it("handles message.deleted — marks message deleted in cache", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("message.deleted", {
        conversation_id: "conv-1",
        message_id: "msg-1",
      });
    });

    expect(updateMessageInCache).toHaveBeenCalledWith(
      expect.anything(),
      "conv-1",
      "msg-1",
      { status: "deleted" },
    );
  });

  it("handles typing — updates Zustand typing state (ignores own events)", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    // Typing from another user — should update store
    act(() => {
      emitServerEvent("typing", {
        conversation_id: "conv-1",
        user_id: "user-2",
        is_typing: true,
      });
    });

    expect(useChatStore.getState().typingUsers["conv-1"]).toContain("user-2");

    // Typing from self (user-1) — should be ignored
    act(() => {
      emitServerEvent("typing", {
        conversation_id: "conv-1",
        user_id: "user-1",
        is_typing: true,
      });
    });

    // user-1 should NOT appear in typing users
    expect(useChatStore.getState().typingUsers["conv-1"]).not.toContain(
      "user-1",
    );
  });

  it("handles presence — updates online users in Zustand", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("presence", {
        user_id: "user-3",
        is_online: true,
      });
    });

    expect(useChatStore.getState().onlineUsers.has("user-3")).toBe(true);

    act(() => {
      emitServerEvent("presence", {
        user_id: "user-3",
        is_online: false,
      });
    });

    expect(useChatStore.getState().onlineUsers.has("user-3")).toBe(false);
  });

  it("handles seen.update — updates Zustand watermarks", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("seen.update", {
        conversation_id: "conv-1",
        participant_id: "part-1",
        last_seen_message_id: "msg-10",
      });
    });

    expect(useChatStore.getState().seenWatermarks["conv-1"]).toEqual({
      "part-1": "msg-10",
    });
  });

  it("handles reaction.update — calls updateReactionInCache", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("reaction.update", {
        conversation_id: "conv-1",
        message_id: "msg-1",
        user_id: "user-2",
        reaction: "heart",
        action: "added",
      });
    });

    expect(updateReactionInCache).toHaveBeenCalledWith(
      expect.anything(),
      "conv-1",
      "msg-1",
      "heart",
      "added",
      "user-2",
      "user-1", // current user
    );
  });

  it("handles error — shows toast notification", () => {
    renderHook(() => useChatWs(), { wrapper: createWrapper() });

    act(() => {
      emitServerEvent("error", {
        message: "Something went wrong",
        code: "ERR_GENERIC",
      });
    });

    expect(toast.error).toHaveBeenCalledWith("Something went wrong");
  });
});
