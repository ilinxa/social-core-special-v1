/**
 * Chat Mutation Hooks
 * ===================
 * TanStack Query mutation hooks for all chat write operations.
 *
 * Each mutation calls the API function and invalidates relevant queries on success.
 * Key mutations (send, edit, delete) will get optimistic updates in Phase 3.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
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
import type {
  AddParticipantInput,
  BlockInput,
  CreateConversationInput,
  EditMessageInput,
  ReactionType,
  SendMessageInput,
  UpdateConversationInput,
} from "@/features/chat/types";

// =============================================================================
// CONVERSATION MUTATIONS
// =============================================================================

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateConversationInput) => createConversationApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.all });
    },
  });
}

export function useUpdateConversation(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateConversationInput) =>
      updateConversationApi(conversationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
    },
  });
}

export function useLeaveConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => leaveConversationApi(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.all });
    },
  });
}

export function useMuteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => muteConversationApi(conversationId),
    onSuccess: (_data, conversationId) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
    },
  });
}

export function useUnmuteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => unmuteConversationApi(conversationId),
    onSuccess: (_data, conversationId) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
    },
  });
}

// =============================================================================
// PARTICIPANT MUTATIONS
// =============================================================================

export function useAddParticipant(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AddParticipantInput) =>
      addParticipantApi(conversationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.participants(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
    },
  });
}

export function useRemoveParticipant(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      participantId,
      participantType,
    }: {
      participantId: string;
      participantType: string;
    }) => removeParticipantApi(conversationId, participantId, participantType),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.participants(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
    },
  });
}

export function usePromoteParticipant(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (participantId: string) =>
      promoteParticipantApi(conversationId, participantId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.participants(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
    },
  });
}

export function useDemoteParticipant(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (participantId: string) =>
      demoteParticipantApi(conversationId, participantId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.participants(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversation(conversationId),
      });
    },
  });
}

// =============================================================================
// MESSAGE MUTATIONS
// =============================================================================

export function useSendMessage(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SendMessageInput) =>
      sendMessageApi(conversationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.messages(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
    },
  });
}

export function useEditMessage(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      messageId,
      data,
    }: {
      messageId: string;
      data: EditMessageInput;
    }) => editMessageApi(conversationId, messageId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.messages(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
    },
  });
}

export function useDeleteMessage(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: string) =>
      deleteMessageApi(conversationId, messageId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.messages(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
    },
  });
}

// =============================================================================
// WATERMARK MUTATIONS
// =============================================================================

export function useMarkSeen(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: string) =>
      markSeenApi(conversationId, { last_seen_message_id: messageId }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.unread(),
      });
    },
  });
}

// =============================================================================
// ATTACHMENT MUTATIONS
// =============================================================================

export function useUploadAttachment(conversationId: string) {
  return useMutation({
    mutationFn: (file: File) => uploadAttachmentApi(conversationId, file),
  });
}

// =============================================================================
// REACTION MUTATIONS
// =============================================================================

export function useAddReaction(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      messageId,
      reaction,
    }: {
      messageId: string;
      reaction: ReactionType;
    }) => addReactionApi(conversationId, messageId, reaction),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.messages(conversationId),
      });
    },
  });
}

export function useRemoveReaction(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      messageId,
      reaction,
    }: {
      messageId: string;
      reaction: ReactionType;
    }) => removeReactionApi(conversationId, messageId, reaction),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.messages(conversationId),
      });
    },
  });
}

// =============================================================================
// CHAT REQUEST MUTATIONS
// =============================================================================

export function useAcceptChatRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => acceptChatRequestApi(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.requests() });
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.conversations() });
    },
  });
}

export function useIgnoreChatRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => ignoreChatRequestApi(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.requests() });
    },
  });
}

// =============================================================================
// BLOCK MUTATIONS
// =============================================================================

export function useBlockParticipant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BlockInput) => blockParticipantApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.blocks() });
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.conversations() });
    },
  });
}

export function useUnblockParticipant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (blockId: string) => unblockParticipantApi(blockId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.blocks() });
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.conversations() });
    },
  });
}
