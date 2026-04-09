import { describe, it, expect } from "vitest";
import { groupMessages } from "../message-grouping";
import type { ChatMessage } from "@/features/chat/types";

/**
 * Helper to create a minimal ChatMessage with defaults.
 */
function makeMessage(
  overrides: Partial<ChatMessage> & Pick<ChatMessage, "id" | "created_at">,
): ChatMessage {
  return {
    id: overrides.id,
    conversation_id: overrides.conversation_id ?? "conv-1",
    sender_type: overrides.sender_type ?? "user",
    sender_id: overrides.sender_id ?? "user-1",
    sender_name: overrides.sender_name ?? "Alice",
    sender_avatar_url: overrides.sender_avatar_url ?? null,
    content_type: overrides.content_type ?? "text",
    content: overrides.content ?? "Hello",
    status: overrides.status ?? "active",
    sequence_number: overrides.sequence_number ?? 1,
    edited_at: overrides.edited_at ?? null,
    created_at: overrides.created_at,
    attachments: overrides.attachments ?? [],
    reactions: overrides.reactions ?? {
      like: 0,
      heart: 0,
      laugh: 0,
      wow: 0,
      sad: 0,
      angry: 0,
    },
    my_reactions: overrides.my_reactions ?? [],
  };
}

describe("groupMessages", () => {
  it("returns empty array for empty input", () => {
    const result = groupMessages([]);
    expect(result).toEqual([]);
  });

  it("single message returns date separator + one group with 1 message", () => {
    const msg = makeMessage({
      id: "msg-1",
      created_at: "2024-03-20T10:00:00Z",
    });

    const result = groupMessages([msg]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg],
    });
  });

  it("two messages from same sender within 5 min → one group", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      created_at: "2024-03-20T10:04:59Z", // 4m 59s later
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1, msg2],
    });
  });

  it("two messages from same sender but >5 min apart → two groups", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      created_at: "2024-03-20T10:05:01Z", // 5m 1s later
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg2],
    });
  });

  it("two messages from different sender_id → two groups", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      sender_name: "Alice",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-2",
      sender_name: "Bob",
      created_at: "2024-03-20T10:01:00Z",
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "user-2",
      senderType: "user",
      messages: [msg2],
    });
  });

  it("messages spanning two days → date separator between them", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      created_at: "2024-03-21T10:00:00Z",
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "date",
      date: "2024-03-21T10:00:00Z",
    });
    expect(result[3]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg2],
    });
  });

  it("system message breaks a group", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      content_type: "text",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      content_type: "system",
      content: "Alice joined the conversation",
      created_at: "2024-03-20T10:01:00Z",
    });
    const msg3 = makeMessage({
      id: "msg-3",
      sender_id: "user-1",
      content_type: "text",
      created_at: "2024-03-20T10:02:00Z",
    });

    const result = groupMessages([msg1, msg2, msg3]);

    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg2],
    });
    expect(result[3]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg3],
    });
  });

  it("system message is in its own group", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      content_type: "system",
      content: "Conversation created",
      created_at: "2024-03-20T10:00:00Z",
    });

    const result = groupMessages([msg1]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
  });

  it("different sender_type (user vs business) creates separate groups even if same sender_id", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_type: "user",
      sender_id: "entity-1",
      sender_name: "Alice",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_type: "business",
      sender_id: "entity-1",
      sender_name: "Acme Corp",
      created_at: "2024-03-20T10:01:00Z",
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "entity-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "entity-1",
      senderType: "business",
      messages: [msg2],
    });
  });

  it("mixed scenario: multiple senders, dates, and system messages", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      sender_name: "Alice",
      content: "Hello",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      sender_name: "Alice",
      content: "How are you?",
      created_at: "2024-03-20T10:01:00Z",
    });
    const msg3 = makeMessage({
      id: "msg-3",
      sender_id: "user-2",
      sender_name: "Bob",
      content: "I'm good!",
      created_at: "2024-03-20T10:02:00Z",
    });
    const msg4 = makeMessage({
      id: "msg-4",
      sender_id: "user-1",
      sender_name: "Alice",
      content_type: "system",
      content: "Alice renamed the group",
      created_at: "2024-03-20T10:10:00Z",
    });
    const msg5 = makeMessage({
      id: "msg-5",
      sender_id: "user-1",
      sender_name: "Alice",
      content: "Check out the new name",
      created_at: "2024-03-21T10:00:00Z", // Next day
    });
    const msg6 = makeMessage({
      id: "msg-6",
      sender_id: "user-2",
      sender_name: "Bob",
      content: "Nice!",
      created_at: "2024-03-21T10:02:00Z",
    });

    const result = groupMessages([msg1, msg2, msg3, msg4, msg5, msg6]);

    expect(result).toHaveLength(7);

    // Day 1 separator
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });

    // Alice's first two messages grouped
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1, msg2],
    });

    // Bob's message
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "user-2",
      senderType: "user",
      messages: [msg3],
    });

    // System message (breaks group despite being Alice)
    expect(result[3]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg4],
    });

    // Day 2 separator
    expect(result[4]).toEqual({
      type: "date",
      date: "2024-03-21T10:00:00Z",
    });

    // Alice's message
    expect(result[5]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg5],
    });

    // Bob's message
    expect(result[6]).toEqual({
      type: "messages",
      senderId: "user-2",
      senderType: "user",
      messages: [msg6],
    });
  });

  it("messages exactly 5 minutes apart are within gap threshold", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      created_at: "2024-03-20T10:05:00Z", // Exactly 5 minutes
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1, msg2],
    });
  });

  it("three messages from same sender all grouped if within 5 min window", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      created_at: "2024-03-20T10:02:00Z",
    });
    const msg3 = makeMessage({
      id: "msg-3",
      sender_id: "user-1",
      created_at: "2024-03-20T10:04:00Z",
    });

    const result = groupMessages([msg1, msg2, msg3]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1, msg2, msg3],
    });
  });

  it("alternating senders create separate groups", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-2",
      created_at: "2024-03-20T10:01:00Z",
    });
    const msg3 = makeMessage({
      id: "msg-3",
      sender_id: "user-1",
      created_at: "2024-03-20T10:02:00Z",
    });
    const msg4 = makeMessage({
      id: "msg-4",
      sender_id: "user-2",
      created_at: "2024-03-20T10:03:00Z",
    });

    const result = groupMessages([msg1, msg2, msg3, msg4]);

    expect(result).toHaveLength(5);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "user-2",
      senderType: "user",
      messages: [msg2],
    });
    expect(result[3]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg3],
    });
    expect(result[4]).toEqual({
      type: "messages",
      senderId: "user-2",
      senderType: "user",
      messages: [msg4],
    });
  });

  it("system message between two regular messages from same sender creates three groups", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      content_type: "text",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-2",
      content_type: "system",
      created_at: "2024-03-20T10:01:00Z",
    });
    const msg3 = makeMessage({
      id: "msg-3",
      sender_id: "user-1",
      content_type: "text",
      created_at: "2024-03-20T10:02:00Z",
    });

    const result = groupMessages([msg1, msg2, msg3]);

    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1],
    });
    expect(result[2]).toEqual({
      type: "messages",
      senderId: "user-2",
      senderType: "user",
      messages: [msg2],
    });
    expect(result[3]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg3],
    });
  });

  it("multiple date changes create multiple date separators", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      created_at: "2024-03-21T10:00:00Z",
    });
    const msg3 = makeMessage({
      id: "msg-3",
      created_at: "2024-03-22T10:00:00Z",
    });

    const result = groupMessages([msg1, msg2, msg3]);

    expect(result).toHaveLength(6);
    expect(result[0].type).toBe("date");
    expect(result[1].type).toBe("messages");
    expect(result[2].type).toBe("date");
    expect(result[3].type).toBe("messages");
    expect(result[4].type).toBe("date");
    expect(result[5].type).toBe("messages");
  });

  it("image messages are grouped like text messages", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_id: "user-1",
      content_type: "image",
      content: "",
      attachments: [
        {
          id: "att-1",
          file_type: "image",
          original_filename: "photo.jpg",
          mime_type: "image/jpeg",
          file_size: 1024,
          width: 800,
          height: 600,
          url: "https://example.com/photo.jpg",
        },
      ],
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_id: "user-1",
      content_type: "text",
      content: "Check this out",
      created_at: "2024-03-20T10:01:00Z",
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "user-1",
      senderType: "user",
      messages: [msg1, msg2],
    });
  });

  it("platform sender type is handled correctly", () => {
    const msg1 = makeMessage({
      id: "msg-1",
      sender_type: "platform",
      sender_id: "platform-1",
      sender_name: "Admin",
      created_at: "2024-03-20T10:00:00Z",
    });
    const msg2 = makeMessage({
      id: "msg-2",
      sender_type: "platform",
      sender_id: "platform-1",
      sender_name: "Admin",
      created_at: "2024-03-20T10:01:00Z",
    });

    const result = groupMessages([msg1, msg2]);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      type: "date",
      date: "2024-03-20T10:00:00Z",
    });
    expect(result[1]).toEqual({
      type: "messages",
      senderId: "platform-1",
      senderType: "platform",
      messages: [msg1, msg2],
    });
  });
});
