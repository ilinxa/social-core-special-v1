"use client";

import { memo, useState } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import type {
  ChatMessage,
  ConversationPermissions,
  ReactionType,
} from "@/features/chat/types";
import {
  useAddReaction,
  useDeleteMessage,
} from "@/features/chat/hooks/use-chat-mutations";
import { AttachmentGrid } from "./AttachmentGrid";
import { ImageLightbox } from "./ImageLightbox";
import { ReactionBar } from "./ReactionBar";
import { MessageActions } from "./MessageActions";
import { DeliveryStatus } from "./DeliveryStatus";

interface MessageBubbleProps {
  message: ChatMessage;
  isOwn: boolean;
  showSender: boolean;
  conversationId: string;
  permissions: ConversationPermissions;
  isDm: boolean;
  onEditMessage?: (messageId: string, content: string) => void;
}

/**
 * Renders a single message bubble with attachments, reactions, actions,
 * and delivery status.
 */
export const MessageBubble = memo(function MessageBubble({
  message,
  isOwn,
  showSender,
  conversationId,
  permissions,
  isDm,
  onEditMessage,
}: MessageBubbleProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const addReaction = useAddReaction(conversationId);
  const deleteMessage = useDeleteMessage(conversationId);

  if (message.status === "deleted") {
    return (
      <div className={cn("flex", isOwn ? "justify-end" : "justify-start")}>
        <div className="rounded-lg bg-muted/50 px-3 py-1.5">
          <span className="text-xs italic text-muted-foreground">
            This message was deleted
          </span>
        </div>
      </div>
    );
  }

  const handleReact = (reaction: ReactionType) => {
    addReaction.mutate({ messageId: message.id, reaction });
  };

  const handleEdit = () => {
    onEditMessage?.(message.id, message.content);
  };

  const handleDelete = () => {
    deleteMessage.mutate(message.id);
  };

  return (
    <div
      className={cn(
        "group flex gap-2",
        isOwn ? "flex-row-reverse" : "flex-row",
      )}
    >
      {/* Avatar (only for non-own messages, first in group) */}
      {!isOwn && showSender ? (
        <Avatar size="sm" className="mt-0.5">
          {message.sender_avatar_url && (
            <AvatarImage src={message.sender_avatar_url} />
          )}
          <AvatarFallback>
            {message.sender_name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
      ) : !isOwn ? (
        <div className="w-6 shrink-0" /> /* spacer for alignment */
      ) : null}

      {/* Bubble + reactions */}
      <div className="max-w-[75%] space-y-0.5">
        {/* Sender name (non-own, first in group) */}
        {!isOwn && showSender && (
          <p className="px-1 text-xs font-medium text-muted-foreground">
            {message.sender_name}
          </p>
        )}

        {/* Bubble content + actions */}
        <div className="flex items-start gap-1">
          {/* Actions (shown on hover, on left for own, right for others) */}
          {isOwn && (
            <MessageActions
              message={message}
              isOwn={isOwn}
              permissions={permissions}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onReact={handleReact}
            />
          )}

          <div
            className={cn(
              "rounded-2xl px-3 py-2",
              isOwn
                ? "bg-primary text-primary-foreground"
                : "bg-muted",
            )}
          >
            {/* Attachments */}
            {message.attachments.length > 0 && (
              <div className="mb-1">
                <AttachmentGrid
                  attachments={message.attachments}
                  onImageClick={setLightboxIndex}
                />
              </div>
            )}

            {/* Text content */}
            {message.content && (
              <p className="whitespace-pre-wrap break-words text-sm">
                {message.content}
              </p>
            )}
          </div>

          {!isOwn && (
            <MessageActions
              message={message}
              isOwn={isOwn}
              permissions={permissions}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onReact={handleReact}
            />
          )}
        </div>

        {/* Reactions */}
        <ReactionBar
          conversationId={conversationId}
          messageId={message.id}
          reactions={message.reactions}
          myReactions={message.my_reactions}
        />

        {/* Timestamp + edited badge + delivery status */}
        <div
          className={cn(
            "flex items-center gap-1 px-1",
            isOwn ? "justify-end" : "justify-start",
          )}
        >
          <span className="text-[10px] text-muted-foreground">
            {formatMessageTime(message.created_at)}
          </span>
          {message.status === "edited" && (
            <span className="text-[10px] text-muted-foreground">
              (edited)
            </span>
          )}
          <DeliveryStatus
            conversationId={conversationId}
            messageId={message.id}
            isOwn={isOwn}
            isDm={isDm}
          />
        </div>
      </div>

      {/* Image lightbox */}
      {lightboxIndex !== null && (
        <ImageLightbox
          attachments={message.attachments}
          initialIndex={lightboxIndex}
          open={lightboxIndex !== null}
          onOpenChange={(open) => {
            if (!open) setLightboxIndex(null);
          }}
        />
      )}
    </div>
  );
});

function formatMessageTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}
