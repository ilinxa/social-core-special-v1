"use client";

import { Check, X } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  useAcceptChatRequest,
  useIgnoreChatRequest,
} from "@/features/chat/hooks/use-chat-mutations";
import type { ChatRequest } from "@/features/chat/types";

interface ChatRequestCardProps {
  request: ChatRequest;
}

/**
 * Card for a pending chat request.
 * Shows requester info, preview messages, and accept/ignore buttons.
 */
export function ChatRequestCard({ request }: ChatRequestCardProps) {
  const accept = useAcceptChatRequest();
  const ignore = useIgnoreChatRequest();

  const isPending = accept.isPending || ignore.isPending;

  return (
    <div
      className="rounded-lg border p-3"
      data-testid={`chat-request-${request.conversation_id}`}
    >
      {/* Requester info */}
      {request.requester && (
        <div className="flex items-center gap-2">
          <Avatar size="sm">
            {request.requester.avatar_url && (
              <AvatarImage src={request.requester.avatar_url} />
            )}
            <AvatarFallback>
              {request.requester.display_name.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {request.requester.display_name}
            </p>
            <p className="text-xs text-muted-foreground">
              {request.message_count}{" "}
              {request.message_count === 1 ? "message" : "messages"}
            </p>
          </div>
        </div>
      )}

      {/* Preview messages */}
      {request.preview_messages.length > 0 && (
        <div className="mt-2 space-y-1 rounded-md bg-muted/50 p-2">
          {request.preview_messages.map((msg, i) => (
            <p key={i} className="line-clamp-2 text-xs text-muted-foreground">
              {msg.content}
            </p>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-3 flex gap-2">
        <Button
          size="sm"
          className="flex-1"
          onClick={() => accept.mutate(request.conversation_id)}
          disabled={isPending}
          data-testid="accept-request"
        >
          <Check className="mr-1 h-3.5 w-3.5" />
          Accept
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          onClick={() => ignore.mutate(request.conversation_id)}
          disabled={isPending}
          data-testid="ignore-request"
        >
          <X className="mr-1 h-3.5 w-3.5" />
          Ignore
        </Button>
      </div>
    </div>
  );
}
