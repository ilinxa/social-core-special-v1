import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";
import {
  useCreateConversation,
  useUpdateConversation,
  useLeaveConversation,
  useMuteConversation,
  useUnmuteConversation,
  useAddParticipant,
  useRemoveParticipant,
  usePromoteParticipant,
  useDemoteParticipant,
  useSendMessage,
  useEditMessage,
  useDeleteMessage,
  useMarkSeen,
  useUploadAttachment,
  useAddReaction,
  useRemoveReaction,
  useAcceptChatRequest,
  useIgnoreChatRequest,
  useBlockParticipant,
  useUnblockParticipant,
} from "./use-chat-mutations";

vi.mock("@/features/chat/api/chat-api", () => ({
  createConversationApi: vi.fn().mockResolvedValue({ id: "conv-1" }),
  updateConversationApi: vi.fn().mockResolvedValue({ id: "conv-1" }),
  leaveConversationApi: vi.fn().mockResolvedValue(undefined),
  muteConversationApi: vi.fn().mockResolvedValue(undefined),
  unmuteConversationApi: vi.fn().mockResolvedValue(undefined),
  addParticipantApi: vi.fn().mockResolvedValue({ id: "p-1" }),
  removeParticipantApi: vi.fn().mockResolvedValue(undefined),
  promoteParticipantApi: vi.fn().mockResolvedValue(undefined),
  demoteParticipantApi: vi.fn().mockResolvedValue(undefined),
  sendMessageApi: vi.fn().mockResolvedValue({ id: "msg-1" }),
  editMessageApi: vi.fn().mockResolvedValue({ id: "msg-1" }),
  deleteMessageApi: vi.fn().mockResolvedValue(undefined),
  markSeenApi: vi.fn().mockResolvedValue(undefined),
  uploadAttachmentApi: vi.fn().mockResolvedValue({ id: "att-1" }),
  addReactionApi: vi.fn().mockResolvedValue(undefined),
  removeReactionApi: vi.fn().mockResolvedValue(undefined),
  acceptChatRequestApi: vi.fn().mockResolvedValue(undefined),
  ignoreChatRequestApi: vi.fn().mockResolvedValue(undefined),
  blockParticipantApi: vi.fn().mockResolvedValue({ id: "block-1" }),
  unblockParticipantApi: vi.fn().mockResolvedValue(undefined),
}));

import {
  createConversationApi,
  updateConversationApi,
  leaveConversationApi,
  muteConversationApi,
  unmuteConversationApi,
  addParticipantApi,
  removeParticipantApi,
  promoteParticipantApi,
  demoteParticipantApi,
  sendMessageApi,
  editMessageApi,
  deleteMessageApi,
  markSeenApi,
  uploadAttachmentApi,
  addReactionApi,
  removeReactionApi,
  acceptChatRequestApi,
  ignoreChatRequestApi,
  blockParticipantApi,
  unblockParticipantApi,
} from "@/features/chat/api/chat-api";

beforeEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// CONVERSATION MUTATIONS
// =============================================================================

describe("useCreateConversation", () => {
  it("calls createConversationApi", async () => {
    const { result } = renderHook(() => useCreateConversation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      scope_type: "global",
      conversation_type: "direct",
      participant_ids: [{ participant_type: "user", participant_id: "u-1" }],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createConversationApi).toHaveBeenCalledWith({
      scope_type: "global",
      conversation_type: "direct",
      participant_ids: [{ participant_type: "user", participant_id: "u-1" }],
    });
  });
});

describe("useUpdateConversation", () => {
  it("calls updateConversationApi with correct args", async () => {
    const { result } = renderHook(() => useUpdateConversation("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ name: "Updated" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateConversationApi).toHaveBeenCalledWith("conv-1", {
      name: "Updated",
    });
  });
});

describe("useLeaveConversation", () => {
  it("calls leaveConversationApi", async () => {
    const { result } = renderHook(() => useLeaveConversation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(leaveConversationApi).toHaveBeenCalledWith("conv-1");
  });
});

describe("useMuteConversation", () => {
  it("calls muteConversationApi", async () => {
    const { result } = renderHook(() => useMuteConversation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(muteConversationApi).toHaveBeenCalledWith("conv-1");
  });
});

describe("useUnmuteConversation", () => {
  it("calls unmuteConversationApi", async () => {
    const { result } = renderHook(() => useUnmuteConversation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(unmuteConversationApi).toHaveBeenCalledWith("conv-1");
  });
});

// =============================================================================
// PARTICIPANT MUTATIONS
// =============================================================================

describe("useAddParticipant", () => {
  it("calls addParticipantApi with correct args", async () => {
    const { result } = renderHook(() => useAddParticipant("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      participant_type: "user",
      participant_id: "u-2",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addParticipantApi).toHaveBeenCalledWith("conv-1", {
      participant_type: "user",
      participant_id: "u-2",
    });
  });
});

describe("useRemoveParticipant", () => {
  it("calls removeParticipantApi with correct args", async () => {
    const { result } = renderHook(() => useRemoveParticipant("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      participantId: "u-2",
      participantType: "user",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removeParticipantApi).toHaveBeenCalledWith("conv-1", "u-2", "user");
  });
});

describe("usePromoteParticipant", () => {
  it("calls promoteParticipantApi", async () => {
    const { result } = renderHook(() => usePromoteParticipant("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("u-2");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(promoteParticipantApi).toHaveBeenCalledWith("conv-1", "u-2");
  });
});

describe("useDemoteParticipant", () => {
  it("calls demoteParticipantApi", async () => {
    const { result } = renderHook(() => useDemoteParticipant("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("u-2");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(demoteParticipantApi).toHaveBeenCalledWith("conv-1", "u-2");
  });
});

// =============================================================================
// MESSAGE MUTATIONS
// =============================================================================

describe("useSendMessage", () => {
  it("calls sendMessageApi with correct args", async () => {
    const { result } = renderHook(() => useSendMessage("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ content: "Hello!" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(sendMessageApi).toHaveBeenCalledWith("conv-1", {
      content: "Hello!",
    });
  });
});

describe("useEditMessage", () => {
  it("calls editMessageApi with correct args", async () => {
    const { result } = renderHook(() => useEditMessage("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      messageId: "msg-1",
      data: { content: "Updated text" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(editMessageApi).toHaveBeenCalledWith("conv-1", "msg-1", {
      content: "Updated text",
    });
  });
});

describe("useDeleteMessage", () => {
  it("calls deleteMessageApi", async () => {
    const { result } = renderHook(() => useDeleteMessage("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("msg-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteMessageApi).toHaveBeenCalledWith("conv-1", "msg-1");
  });
});

// =============================================================================
// WATERMARK MUTATIONS
// =============================================================================

describe("useMarkSeen", () => {
  it("calls markSeenApi with last_seen_message_id", async () => {
    const { result } = renderHook(() => useMarkSeen("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("msg-5");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(markSeenApi).toHaveBeenCalledWith("conv-1", {
      last_seen_message_id: "msg-5",
    });
  });
});

// =============================================================================
// ATTACHMENT MUTATIONS
// =============================================================================

describe("useUploadAttachment", () => {
  it("calls uploadAttachmentApi with file", async () => {
    const { result } = renderHook(() => useUploadAttachment("conv-1"), {
      wrapper: createWrapper(),
    });

    const file = new File(["test"], "test.png", { type: "image/png" });
    result.current.mutate(file);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(uploadAttachmentApi).toHaveBeenCalledWith("conv-1", file);
  });
});

// =============================================================================
// REACTION MUTATIONS
// =============================================================================

describe("useAddReaction", () => {
  it("calls addReactionApi with correct args", async () => {
    const { result } = renderHook(() => useAddReaction("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ messageId: "msg-1", reaction: "like" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addReactionApi).toHaveBeenCalledWith("conv-1", "msg-1", "like");
  });
});

describe("useRemoveReaction", () => {
  it("calls removeReactionApi with correct args", async () => {
    const { result } = renderHook(() => useRemoveReaction("conv-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ messageId: "msg-1", reaction: "heart" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removeReactionApi).toHaveBeenCalledWith("conv-1", "msg-1", "heart");
  });
});

// =============================================================================
// CHAT REQUEST MUTATIONS
// =============================================================================

describe("useAcceptChatRequest", () => {
  it("calls acceptChatRequestApi", async () => {
    const { result } = renderHook(() => useAcceptChatRequest(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(acceptChatRequestApi).toHaveBeenCalledWith("conv-1");
  });
});

describe("useIgnoreChatRequest", () => {
  it("calls ignoreChatRequestApi", async () => {
    const { result } = renderHook(() => useIgnoreChatRequest(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(ignoreChatRequestApi).toHaveBeenCalledWith("conv-1");
  });
});

// =============================================================================
// BLOCK MUTATIONS
// =============================================================================

describe("useBlockParticipant", () => {
  it("calls blockParticipantApi", async () => {
    const { result } = renderHook(() => useBlockParticipant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      blocked_type: "user",
      blocked_id: "u-3",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(blockParticipantApi).toHaveBeenCalledWith({
      blocked_type: "user",
      blocked_id: "u-3",
    });
  });
});

describe("useUnblockParticipant", () => {
  it("calls unblockParticipantApi", async () => {
    const { result } = renderHook(() => useUnblockParticipant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("block-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(unblockParticipantApi).toHaveBeenCalledWith("block-1");
  });
});
