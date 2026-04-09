import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";

import {
  useChatStore,
  useChatActiveConversation,
  useChatWsState,
  useChatTypingUsers,
  useChatOnlineUsers,
  useIsUserOnline,
  useChatDraft,
  useChatPendingUploads,
  useChatUnreadCounts,
  useChatTotalUnread,
  useChatSeenWatermarks,
  useChatDeliveredWatermarks,
  getChatStore,
} from "./chat-store";

import type { UploadProgress } from "./chat-store";

const CONV_A = "conv-aaa-111";
const CONV_B = "conv-bbb-222";
const USER_1 = "user-111";
const USER_2 = "user-222";
const USER_3 = "user-333";
const MSG_1 = "msg-001";
const MSG_2 = "msg-002";

const mockUploads: UploadProgress[] = [
  { id: "up-1", filename: "photo.jpg", progress: 50, status: "uploading" },
  { id: "up-2", filename: "doc.pdf", progress: 100, status: "done", attachmentId: "att-1" },
];

describe("chat-store", () => {
  beforeEach(() => {
    useChatStore.setState({
      activeConversationId: null,
      wsState: "disconnected",
      typingUsers: {},
      onlineUsers: new Set<string>(),
      drafts: {},
      pendingUploads: {},
      unreadCounts: {},
      seenWatermarks: {},
      deliveredWatermarks: {},
    });
  });

  // ===========================================================================
  // INITIAL STATE
  // ===========================================================================

  describe("initial state", () => {
    it("has correct defaults", () => {
      const { result } = renderHook(() => useChatStore());
      expect(result.current.activeConversationId).toBeNull();
      expect(result.current.wsState).toBe("disconnected");
      expect(result.current.typingUsers).toEqual({});
      expect(result.current.onlineUsers).toEqual(new Set());
      expect(result.current.drafts).toEqual({});
      expect(result.current.pendingUploads).toEqual({});
      expect(result.current.unreadCounts).toEqual({});
      expect(result.current.seenWatermarks).toEqual({});
      expect(result.current.deliveredWatermarks).toEqual({});
    });
  });

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  describe("actions", () => {
    it("setActiveConversation sets the active conversation", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setActiveConversation(CONV_A);
      });

      expect(result.current.activeConversationId).toBe(CONV_A);
    });

    it("setActiveConversation clears when passed null", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setActiveConversation(CONV_A);
      });

      act(() => {
        result.current.setActiveConversation(null);
      });

      expect(result.current.activeConversationId).toBeNull();
    });

    it("setWsState updates the WebSocket state", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setWsState("connecting");
      });

      expect(result.current.wsState).toBe("connecting");

      act(() => {
        result.current.setWsState("connected");
      });

      expect(result.current.wsState).toBe("connected");
    });

    it("setTyping adds a user to the typing list", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setTyping(CONV_A, USER_1, true);
      });

      expect(result.current.typingUsers[CONV_A]).toEqual([USER_1]);
    });

    it("setTyping with isTyping=false removes user from typing list", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setTyping(CONV_A, USER_1, true);
        result.current.setTyping(CONV_A, USER_2, true);
      });

      act(() => {
        result.current.setTyping(CONV_A, USER_1, false);
      });

      expect(result.current.typingUsers[CONV_A]).toEqual([USER_2]);
    });

    it("setTyping does not duplicate a user already in the list", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setTyping(CONV_A, USER_1, true);
      });

      act(() => {
        result.current.setTyping(CONV_A, USER_1, true);
      });

      expect(result.current.typingUsers[CONV_A]).toEqual([USER_1]);
    });

    it("clearTyping removes the conversation entry", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setTyping(CONV_A, USER_1, true);
        result.current.setTyping(CONV_B, USER_2, true);
      });

      act(() => {
        result.current.clearTyping(CONV_A);
      });

      expect(result.current.typingUsers[CONV_A]).toBeUndefined();
      expect(result.current.typingUsers[CONV_B]).toEqual([USER_2]);
    });

    it("setOnline adds a user to the online set", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setOnline(USER_1, true);
      });

      expect(result.current.onlineUsers.has(USER_1)).toBe(true);
    });

    it("setOnline with isOnline=false removes user from the set", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setOnline(USER_1, true);
        result.current.setOnline(USER_2, true);
      });

      act(() => {
        result.current.setOnline(USER_1, false);
      });

      expect(result.current.onlineUsers.has(USER_1)).toBe(false);
      expect(result.current.onlineUsers.has(USER_2)).toBe(true);
    });

    it("setDraft sets draft text for a conversation", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setDraft(CONV_A, "Hello, world!");
      });

      expect(result.current.drafts[CONV_A]).toBe("Hello, world!");
    });

    it("clearDraft removes the conversation draft entry", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setDraft(CONV_A, "draft A");
        result.current.setDraft(CONV_B, "draft B");
      });

      act(() => {
        result.current.clearDraft(CONV_A);
      });

      expect(result.current.drafts[CONV_A]).toBeUndefined();
      expect(result.current.drafts[CONV_B]).toBe("draft B");
    });

    it("setPendingUploads sets uploads for a conversation", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setPendingUploads(CONV_A, mockUploads);
      });

      expect(result.current.pendingUploads[CONV_A]).toEqual(mockUploads);
    });

    it("clearPendingUploads removes the conversation uploads entry", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setPendingUploads(CONV_A, mockUploads);
        result.current.setPendingUploads(CONV_B, [mockUploads[0]]);
      });

      act(() => {
        result.current.clearPendingUploads(CONV_A);
      });

      expect(result.current.pendingUploads[CONV_A]).toBeUndefined();
      expect(result.current.pendingUploads[CONV_B]).toEqual([mockUploads[0]]);
    });

    it("setUnreadCounts replaces all counts", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setUnreadCounts({ global: 3, "biz-1": 5 });
      });

      expect(result.current.unreadCounts).toEqual({ global: 3, "biz-1": 5 });

      act(() => {
        result.current.setUnreadCounts({ global: 1 });
      });

      expect(result.current.unreadCounts).toEqual({ global: 1 });
    });

    it("incrementUnread increments an existing key", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setUnreadCounts({ global: 3 });
      });

      act(() => {
        result.current.incrementUnread("global");
      });

      expect(result.current.unreadCounts["global"]).toBe(4);
    });

    it("incrementUnread initializes a missing key to 1", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.incrementUnread("new-scope");
      });

      expect(result.current.unreadCounts["new-scope"]).toBe(1);
    });

    it("clearUnread removes the scope key", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setUnreadCounts({ global: 3, "biz-1": 5 });
      });

      act(() => {
        result.current.clearUnread("global");
      });

      expect(result.current.unreadCounts["global"]).toBeUndefined();
      expect(result.current.unreadCounts["biz-1"]).toBe(5);
    });

    it("setSeenWatermark sets a nested watermark", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setSeenWatermark(CONV_A, USER_1, MSG_1);
      });

      expect(result.current.seenWatermarks[CONV_A]).toEqual({ [USER_1]: MSG_1 });

      act(() => {
        result.current.setSeenWatermark(CONV_A, USER_2, MSG_2);
      });

      expect(result.current.seenWatermarks[CONV_A]).toEqual({
        [USER_1]: MSG_1,
        [USER_2]: MSG_2,
      });
    });

    it("setDeliveredWatermark sets a nested watermark", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setDeliveredWatermark(CONV_A, USER_1, MSG_1);
      });

      expect(result.current.deliveredWatermarks[CONV_A]).toEqual({ [USER_1]: MSG_1 });

      act(() => {
        result.current.setDeliveredWatermark(CONV_A, USER_2, MSG_2);
      });

      expect(result.current.deliveredWatermarks[CONV_A]).toEqual({
        [USER_1]: MSG_1,
        [USER_2]: MSG_2,
      });
    });

    it("reset returns to initial state", () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setActiveConversation(CONV_A);
        result.current.setWsState("connected");
        result.current.setTyping(CONV_A, USER_1, true);
        result.current.setOnline(USER_2, true);
        result.current.setDraft(CONV_A, "some draft");
        result.current.setPendingUploads(CONV_A, mockUploads);
        result.current.setUnreadCounts({ global: 5 });
        result.current.setSeenWatermark(CONV_A, USER_1, MSG_1);
        result.current.setDeliveredWatermark(CONV_A, USER_2, MSG_2);
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.activeConversationId).toBeNull();
      expect(result.current.wsState).toBe("disconnected");
      expect(result.current.typingUsers).toEqual({});
      expect(result.current.onlineUsers).toEqual(new Set());
      expect(result.current.drafts).toEqual({});
      expect(result.current.pendingUploads).toEqual({});
      expect(result.current.unreadCounts).toEqual({});
      expect(result.current.seenWatermarks).toEqual({});
      expect(result.current.deliveredWatermarks).toEqual({});
    });
  });

  // ===========================================================================
  // SELECTOR HOOKS
  // ===========================================================================

  describe("selector hooks", () => {
    it("useChatActiveConversation returns the active conversation id", () => {
      useChatStore.setState({ activeConversationId: CONV_A });
      const { result } = renderHook(() => useChatActiveConversation());
      expect(result.current).toBe(CONV_A);
    });

    it("useChatWsState returns the WebSocket state", () => {
      useChatStore.setState({ wsState: "reconnecting" });
      const { result } = renderHook(() => useChatWsState());
      expect(result.current).toBe("reconnecting");
    });

    it("useChatTypingUsers returns typing users for a conversation", () => {
      useChatStore.setState({ typingUsers: { [CONV_A]: [USER_1, USER_2] } });
      const { result } = renderHook(() => useChatTypingUsers(CONV_A));
      expect(result.current).toEqual([USER_1, USER_2]);
    });

    it("useChatTypingUsers returns empty array for unknown conversation", () => {
      const { result } = renderHook(() => useChatTypingUsers("unknown-conv"));
      expect(result.current).toEqual([]);
    });

    it("useChatOnlineUsers returns the online users set", () => {
      useChatStore.setState({ onlineUsers: new Set([USER_1, USER_3]) });
      const { result } = renderHook(() => useChatOnlineUsers());
      expect(result.current).toEqual(new Set([USER_1, USER_3]));
    });

    it("useIsUserOnline returns true for online user", () => {
      useChatStore.setState({ onlineUsers: new Set([USER_1]) });
      const { result } = renderHook(() => useIsUserOnline(USER_1));
      expect(result.current).toBe(true);
    });

    it("useIsUserOnline returns false for offline user", () => {
      useChatStore.setState({ onlineUsers: new Set([USER_1]) });
      const { result } = renderHook(() => useIsUserOnline(USER_2));
      expect(result.current).toBe(false);
    });

    it("useChatDraft returns the draft for a conversation", () => {
      useChatStore.setState({ drafts: { [CONV_A]: "Hello there" } });
      const { result } = renderHook(() => useChatDraft(CONV_A));
      expect(result.current).toBe("Hello there");
    });

    it("useChatDraft returns empty string for unknown conversation", () => {
      const { result } = renderHook(() => useChatDraft("unknown-conv"));
      expect(result.current).toBe("");
    });

    it("useChatPendingUploads returns uploads for a conversation", () => {
      useChatStore.setState({ pendingUploads: { [CONV_A]: mockUploads } });
      const { result } = renderHook(() => useChatPendingUploads(CONV_A));
      expect(result.current).toEqual(mockUploads);
    });

    it("useChatPendingUploads returns empty array for unknown conversation", () => {
      const { result } = renderHook(() => useChatPendingUploads("unknown-conv"));
      expect(result.current).toEqual([]);
    });

    it("useChatUnreadCounts returns all unread counts", () => {
      useChatStore.setState({ unreadCounts: { global: 2, "biz-1": 7 } });
      const { result } = renderHook(() => useChatUnreadCounts());
      expect(result.current).toEqual({ global: 2, "biz-1": 7 });
    });

    it("useChatTotalUnread returns sum of all unread counts", () => {
      useChatStore.setState({ unreadCounts: { global: 2, "biz-1": 7, "biz-2": 1 } });
      const { result } = renderHook(() => useChatTotalUnread());
      expect(result.current).toBe(10);
    });

    it("useChatTotalUnread returns 0 when no unread counts", () => {
      const { result } = renderHook(() => useChatTotalUnread());
      expect(result.current).toBe(0);
    });

    it("useChatSeenWatermarks returns seen watermarks for a conversation", () => {
      useChatStore.setState({
        seenWatermarks: { [CONV_A]: { [USER_1]: MSG_1, [USER_2]: MSG_2 } },
      });
      const { result } = renderHook(() => useChatSeenWatermarks(CONV_A));
      expect(result.current).toEqual({ [USER_1]: MSG_1, [USER_2]: MSG_2 });
    });

    it("useChatSeenWatermarks returns empty object for unknown conversation", () => {
      const { result } = renderHook(() => useChatSeenWatermarks("unknown-conv"));
      expect(result.current).toEqual({});
    });

    it("useChatDeliveredWatermarks returns delivered watermarks for a conversation", () => {
      useChatStore.setState({
        deliveredWatermarks: { [CONV_A]: { [USER_1]: MSG_1 } },
      });
      const { result } = renderHook(() => useChatDeliveredWatermarks(CONV_A));
      expect(result.current).toEqual({ [USER_1]: MSG_1 });
    });

    it("useChatDeliveredWatermarks returns empty object for unknown conversation", () => {
      const { result } = renderHook(() => useChatDeliveredWatermarks("unknown-conv"));
      expect(result.current).toEqual({});
    });
  });

  // ===========================================================================
  // NON-REACT ACCESS
  // ===========================================================================

  describe("getChatStore", () => {
    it("returns the current state", () => {
      useChatStore.setState({
        activeConversationId: CONV_B,
        wsState: "connected",
        unreadCounts: { global: 4 },
      });

      const state = getChatStore();

      expect(state.activeConversationId).toBe(CONV_B);
      expect(state.wsState).toBe("connected");
      expect(state.unreadCounts).toEqual({ global: 4 });
      expect(state.typingUsers).toEqual({});
      expect(state.onlineUsers).toEqual(new Set());
      expect(state.drafts).toEqual({});
      expect(state.pendingUploads).toEqual({});
      expect(state.seenWatermarks).toEqual({});
      expect(state.deliveredWatermarks).toEqual({});
    });
  });
});
