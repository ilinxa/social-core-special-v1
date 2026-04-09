import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchConversationsApi,
  createConversationApi,
  fetchConversationApi,
  updateConversationApi,
  leaveConversationApi,
  muteConversationApi,
  unmuteConversationApi,
  fetchParticipantsApi,
  addParticipantApi,
  removeParticipantApi,
  promoteParticipantApi,
  demoteParticipantApi,
  fetchMessagesApi,
  sendMessageApi,
  editMessageApi,
  deleteMessageApi,
  markSeenApi,
  uploadAttachmentApi,
  fetchMediaGalleryApi,
  addReactionApi,
  removeReactionApi,
  fetchChatRequestsApi,
  acceptChatRequestApi,
  ignoreChatRequestApi,
  fetchBlocksApi,
  blockParticipantApi,
  unblockParticipantApi,
  fetchEntityInboxApi,
  searchMessagesApi,
  fetchUnreadCountsApi,
} from "../chat-api";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

beforeEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// CONVERSATIONS
// =============================================================================

describe("Conversations", () => {
  it("fetchConversationsApi gets /chat/conversations/ with params", async () => {
    const data = { count: 2, results: [{ id: "conv-1" }, { id: "conv-2" }] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchConversationsApi({ scope_type: "global" });

    expect(mockedGet).toHaveBeenCalledWith("/chat/conversations/", {
      params: { scope_type: "global" },
    });
    expect(response).toEqual(data);
  });

  it("fetchConversationsApi works without params", async () => {
    const data = { count: 0, results: [] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchConversationsApi();

    expect(mockedGet).toHaveBeenCalledWith("/chat/conversations/", {
      params: undefined,
    });
    expect(response).toEqual(data);
  });

  it("createConversationApi posts to /chat/conversations/", async () => {
    const result = {
      id: "conv-1",
      title: "Test Chat",
      _permissions: { can_edit: true },
    };
    mockedPost.mockResolvedValue({ data: result });

    const input = {
      conversation_type: "group",
      title: "Test Chat",
      participant_ids: ["user-1", "user-2"],
    };
    const response = await createConversationApi(input as never);

    expect(mockedPost).toHaveBeenCalledWith("/chat/conversations/", input);
    expect(response).toEqual(result);
  });

  it("fetchConversationApi gets /chat/conversations/{id}/", async () => {
    const result = {
      id: "conv-1",
      title: "My Chat",
      _permissions: { can_edit: true },
    };
    mockedGet.mockResolvedValue({ data: result });

    const response = await fetchConversationApi("conv-1");

    expect(mockedGet).toHaveBeenCalledWith("/chat/conversations/conv-1/");
    expect(response).toEqual(result);
  });

  it("updateConversationApi patches /chat/conversations/{id}/", async () => {
    const result = { id: "conv-1", title: "Renamed Chat" };
    mockedPatch.mockResolvedValue({ data: result });

    const input = { title: "Renamed Chat" };
    const response = await updateConversationApi("conv-1", input as never);

    expect(mockedPatch).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/",
      input,
    );
    expect(response).toEqual(result);
  });

  it("leaveConversationApi posts to /chat/conversations/{id}/leave/", async () => {
    mockedPost.mockResolvedValue({});

    await leaveConversationApi("conv-1");

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/leave/",
    );
  });

  it("muteConversationApi posts to /chat/conversations/{id}/mute/", async () => {
    mockedPost.mockResolvedValue({});

    await muteConversationApi("conv-1");

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/mute/",
    );
  });

  it("unmuteConversationApi posts to /chat/conversations/{id}/unmute/", async () => {
    mockedPost.mockResolvedValue({});

    await unmuteConversationApi("conv-1");

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/unmute/",
    );
  });
});

// =============================================================================
// PARTICIPANTS
// =============================================================================

describe("Participants", () => {
  it("fetchParticipantsApi gets /chat/conversations/{id}/participants/", async () => {
    const data = [
      { id: "p-1", display_name: "Alice" },
      { id: "p-2", display_name: "Bob" },
    ];
    mockedGet.mockResolvedValue({ data });

    const response = await fetchParticipantsApi("conv-1");

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/participants/",
    );
    expect(response).toEqual(data);
  });

  it("addParticipantApi posts to /chat/conversations/{id}/participants/", async () => {
    const result = { id: "p-3", display_name: "Charlie" };
    mockedPost.mockResolvedValue({ data: result });

    const input = { participant_id: "user-3", participant_type: "user" };
    const response = await addParticipantApi("conv-1", input as never);

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/participants/",
      input,
    );
    expect(response).toEqual(result);
  });

  it("removeParticipantApi deletes /chat/conversations/{id}/participants/{pid}/ with body", async () => {
    mockedDelete.mockResolvedValue({});

    await removeParticipantApi("conv-1", "p-2", "user");

    expect(mockedDelete).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/participants/p-2/",
      { data: { participant_type: "user" } },
    );
  });

  it("promoteParticipantApi posts to .../promote/", async () => {
    mockedPost.mockResolvedValue({});

    await promoteParticipantApi("conv-1", "p-1");

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/participants/p-1/promote/",
    );
  });

  it("demoteParticipantApi posts to .../demote/", async () => {
    mockedPost.mockResolvedValue({});

    await demoteParticipantApi("conv-1", "p-1");

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/participants/p-1/demote/",
    );
  });
});

// =============================================================================
// MESSAGES
// =============================================================================

describe("Messages", () => {
  it("fetchMessagesApi gets /chat/conversations/{id}/messages/ with params", async () => {
    const data = [{ id: "msg-1", body: "Hello" }];
    mockedGet.mockResolvedValue({ data });

    const response = await fetchMessagesApi("conv-1", {
      cursor: "2026-03-20T00:00:00Z",
      page_size: 25,
    } as never);

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/",
      { params: { cursor: "2026-03-20T00:00:00Z", page_size: 25 } },
    );
    expect(response).toEqual(data);
  });

  it("fetchMessagesApi works without params", async () => {
    const data = [{ id: "msg-1" }];
    mockedGet.mockResolvedValue({ data });

    const response = await fetchMessagesApi("conv-1");

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/",
      { params: undefined },
    );
    expect(response).toEqual(data);
  });

  it("sendMessageApi posts to /chat/conversations/{id}/messages/", async () => {
    const result = { id: "msg-2", body: "Hi there" };
    mockedPost.mockResolvedValue({ data: result });

    const input = { body: "Hi there" };
    const response = await sendMessageApi("conv-1", input as never);

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/",
      input,
    );
    expect(response).toEqual(result);
  });

  it("editMessageApi patches /chat/conversations/{id}/messages/{mid}/", async () => {
    const result = { id: "msg-1", body: "Edited text" };
    mockedPatch.mockResolvedValue({ data: result });

    const input = { body: "Edited text" };
    const response = await editMessageApi("conv-1", "msg-1", input as never);

    expect(mockedPatch).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/msg-1/",
      input,
    );
    expect(response).toEqual(result);
  });

  it("deleteMessageApi deletes /chat/conversations/{id}/messages/{mid}/", async () => {
    mockedDelete.mockResolvedValue({});

    await deleteMessageApi("conv-1", "msg-1");

    expect(mockedDelete).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/msg-1/",
    );
  });
});

// =============================================================================
// WATERMARKS
// =============================================================================

describe("Watermarks", () => {
  it("markSeenApi posts to /chat/conversations/{id}/seen/", async () => {
    mockedPost.mockResolvedValue({});

    await markSeenApi("conv-1", { last_seen_message_id: "msg-5" });

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/seen/",
      { last_seen_message_id: "msg-5" },
    );
  });
});

// =============================================================================
// ATTACHMENTS
// =============================================================================

describe("Attachments", () => {
  it("uploadAttachmentApi posts FormData to /chat/conversations/{id}/upload/", async () => {
    const result = { id: "att-1", file_name: "photo.png", url: "/media/photo.png" };
    mockedPost.mockResolvedValue({ data: result });

    const file = new File(["binary-data"], "photo.png", {
      type: "image/png",
    });
    const response = await uploadAttachmentApi("conv-1", file);

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/upload/",
      expect.any(FormData),
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    expect(response).toEqual(result);
  });
});

// =============================================================================
// MEDIA GALLERY
// =============================================================================

describe("Media Gallery", () => {
  it("fetchMediaGalleryApi gets /chat/conversations/{id}/media/ with params", async () => {
    const data = { results: [{ id: "att-1" }], next_cursor: "cursor-abc" };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchMediaGalleryApi("conv-1", {
      cursor: "cursor-prev",
      page_size: 20,
    } as never);

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/media/",
      { params: { cursor: "cursor-prev", page_size: 20 } },
    );
    expect(response).toEqual(data);
  });

  it("fetchMediaGalleryApi works without params", async () => {
    const data = { results: [], next_cursor: null };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchMediaGalleryApi("conv-1");

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/media/",
      { params: undefined },
    );
    expect(response).toEqual(data);
  });
});

// =============================================================================
// REACTIONS
// =============================================================================

describe("Reactions", () => {
  it("addReactionApi posts to .../reactions/ with reaction body", async () => {
    mockedPost.mockResolvedValue({});

    await addReactionApi("conv-1", "msg-1", "thumbs_up" as never);

    expect(mockedPost).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/msg-1/reactions/",
      { reaction: "thumbs_up" },
    );
  });

  it("removeReactionApi deletes .../reactions/ with reaction in body", async () => {
    mockedDelete.mockResolvedValue({});

    await removeReactionApi("conv-1", "msg-1", "heart" as never);

    expect(mockedDelete).toHaveBeenCalledWith(
      "/chat/conversations/conv-1/messages/msg-1/reactions/",
      { data: { reaction: "heart" } },
    );
  });
});

// =============================================================================
// CHAT REQUESTS
// =============================================================================

describe("Chat Requests", () => {
  it("fetchChatRequestsApi gets /chat/requests/ with params", async () => {
    const data = {
      count: 1,
      results: [{ id: "conv-5", requester: "user-9" }],
    };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchChatRequestsApi({ page: 1, page_size: 10 });

    expect(mockedGet).toHaveBeenCalledWith("/chat/requests/", {
      params: { page: 1, page_size: 10 },
    });
    expect(response).toEqual(data);
  });

  it("fetchChatRequestsApi works without params", async () => {
    const data = { count: 0, results: [] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchChatRequestsApi();

    expect(mockedGet).toHaveBeenCalledWith("/chat/requests/", {
      params: undefined,
    });
    expect(response).toEqual(data);
  });

  it("acceptChatRequestApi posts to /chat/requests/{id}/accept/", async () => {
    mockedPost.mockResolvedValue({});

    await acceptChatRequestApi("conv-5");

    expect(mockedPost).toHaveBeenCalledWith("/chat/requests/conv-5/accept/");
  });

  it("ignoreChatRequestApi posts to /chat/requests/{id}/ignore/", async () => {
    mockedPost.mockResolvedValue({});

    await ignoreChatRequestApi("conv-5");

    expect(mockedPost).toHaveBeenCalledWith("/chat/requests/conv-5/ignore/");
  });
});

// =============================================================================
// BLOCKS
// =============================================================================

describe("Blocks", () => {
  it("fetchBlocksApi gets /chat/blocks/ with params", async () => {
    const data = {
      count: 1,
      results: [{ id: "block-1", blocked_id: "user-7" }],
    };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchBlocksApi({ page: 1 });

    expect(mockedGet).toHaveBeenCalledWith("/chat/blocks/", {
      params: { page: 1 },
    });
    expect(response).toEqual(data);
  });

  it("fetchBlocksApi works without params", async () => {
    const data = { count: 0, results: [] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchBlocksApi();

    expect(mockedGet).toHaveBeenCalledWith("/chat/blocks/", {
      params: undefined,
    });
    expect(response).toEqual(data);
  });

  it("blockParticipantApi posts to /chat/blocks/", async () => {
    const result = { id: "block-2", blocked_id: "user-8" };
    mockedPost.mockResolvedValue({ data: result });

    const input = { blocked_id: "user-8", blocked_type: "user" };
    const response = await blockParticipantApi(input as never);

    expect(mockedPost).toHaveBeenCalledWith("/chat/blocks/", input);
    expect(response).toEqual(result);
  });

  it("unblockParticipantApi deletes /chat/blocks/{id}/", async () => {
    mockedDelete.mockResolvedValue({});

    await unblockParticipantApi("block-1");

    expect(mockedDelete).toHaveBeenCalledWith("/chat/blocks/block-1/");
  });
});

// =============================================================================
// ENTITY INBOX
// =============================================================================

describe("Entity Inbox", () => {
  it("fetchEntityInboxApi gets /chat/entity/{type}/{id}/inbox/ with params", async () => {
    const data = {
      count: 3,
      results: [{ id: "conv-10" }, { id: "conv-11" }, { id: "conv-12" }],
    };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchEntityInboxApi("business", "biz-1", {
      page: 2,
    });

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/entity/business/biz-1/inbox/",
      { params: { page: 2 } },
    );
    expect(response).toEqual(data);
  });

  it("fetchEntityInboxApi works without params", async () => {
    const data = { count: 0, results: [] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchEntityInboxApi("platform", "plat-1");

    expect(mockedGet).toHaveBeenCalledWith(
      "/chat/entity/platform/plat-1/inbox/",
      { params: undefined },
    );
    expect(response).toEqual(data);
  });
});

// =============================================================================
// SEARCH
// =============================================================================

describe("Search", () => {
  it("searchMessagesApi gets /chat/messages/search/ with params", async () => {
    const data = {
      count: 1,
      results: [{ id: "msg-99", body: "search hit", conversation_id: "conv-1" }],
    };
    mockedGet.mockResolvedValue({ data });

    const params = { q: "hello", conversation_id: "conv-1" };
    const response = await searchMessagesApi(params as never);

    expect(mockedGet).toHaveBeenCalledWith("/chat/messages/search/", {
      params,
    });
    expect(response).toEqual(data);
  });
});

// =============================================================================
// UNREAD COUNTS
// =============================================================================

describe("Unread Counts", () => {
  it("fetchUnreadCountsApi gets /chat/unread/", async () => {
    const data = { global: 5, business_abc: 2 };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchUnreadCountsApi();

    expect(mockedGet).toHaveBeenCalledWith("/chat/unread/");
    expect(response).toEqual(data);
  });
});
