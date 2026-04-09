/**
 * Chat helper — common chat operations for tests.
 *
 * Provides API-based conversation and message setup.
 */

import type { ApiClient } from '../lib/api-client';

/** Create a DM conversation via API. */
export async function createConversationViaApi(
  api: ApiClient,
  participantIds: string[],
  options?: {
    name?: string;
    scope_type?: string;
    scope_id?: string;
    participant_type?: string;
    conversation_type?: string;
  },
): Promise<{ id: string; name: string; conversation_type: string }> {
  const pType = options?.participant_type ?? 'user';
  const body: Record<string, unknown> = {
    scope_type: options?.scope_type ?? 'global',
    scope_id: options?.scope_id ?? null,
    conversation_type: options?.conversation_type ?? 'direct',
    participant_ids: participantIds.map((id) => ({
      participant_type: pType,
      participant_id: id,
    })),
  };
  if (options?.name) body.name = options.name;
  const res = await api.post('chat/conversations/', body);
  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`createConversationViaApi failed (${res.status}): ${errBody}`);
  }
  return (await res.json()) as { id: string; name: string; conversation_type: string };
}

/** Send a message in a conversation via API. */
export async function sendMessageViaApi(
  api: ApiClient,
  conversationId: string,
  content: string,
): Promise<{ id: string; content: string }> {
  const res = await api.post(`chat/conversations/${conversationId}/messages/`, {
    content,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`sendMessageViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; content: string };
}

/** Get conversations list via API. */
export async function getConversationsViaApi(
  api: ApiClient,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get('chat/conversations/');
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getConversationsViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Get messages in a conversation via API. */
export async function getMessagesViaApi(
  api: ApiClient,
  conversationId: string,
): Promise<Record<string, unknown>[]> {
  const res = await api.get(`chat/conversations/${conversationId}/messages/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getMessagesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>[];
}

/** Add a reaction to a message via API. */
export async function addReactionViaApi(
  api: ApiClient,
  conversationId: string,
  messageId: string,
  reaction: string,
): Promise<void> {
  const res = await api.post(
    `chat/conversations/${conversationId}/messages/${messageId}/reactions/`,
    { reaction },
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`addReactionViaApi failed (${res.status}): ${body}`);
  }
}

/** Block a user in chat via API. */
export async function blockUserViaApi(
  api: ApiClient,
  userId: string,
): Promise<void> {
  const res = await api.post('chat/blocks/', { blocked_type: 'user', blocked_id: userId });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`blockUserViaApi failed (${res.status}): ${body}`);
  }
}

/** Accept a chat request via API. */
export async function acceptChatRequestViaApi(
  api: ApiClient,
  conversationId: string,
): Promise<void> {
  const res = await api.post(`chat/requests/${conversationId}/accept/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`acceptChatRequestViaApi failed (${res.status}): ${body}`);
  }
}

/** Edit a message via API. */
export async function editMessageViaApi(
  api: ApiClient,
  conversationId: string,
  messageId: string,
  content: string,
): Promise<void> {
  const res = await api.patch(
    `chat/conversations/${conversationId}/messages/${messageId}/`,
    { content },
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`editMessageViaApi failed (${res.status}): ${body}`);
  }
}

/** Delete a message via API. */
export async function deleteMessageViaApi(
  api: ApiClient,
  conversationId: string,
  messageId: string,
): Promise<void> {
  const res = await api.delete(
    `chat/conversations/${conversationId}/messages/${messageId}/`,
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`deleteMessageViaApi failed (${res.status}): ${body}`);
  }
}

/** Create a group conversation via API. */
export async function createGroupConversationViaApi(
  api: ApiClient,
  participantIds: string[],
  name: string,
): Promise<{ id: string; name: string; conversation_type: string }> {
  const res = await api.post('chat/conversations/', {
    scope_type: 'global',
    scope_id: null,
    conversation_type: 'group',
    participant_ids: participantIds.map((id) => ({
      participant_type: 'user',
      participant_id: id,
    })),
    name,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createGroupConversationViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; name: string; conversation_type: string };
}
