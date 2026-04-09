"use client";

import { Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  useAcceptChatRequest,
  useIgnoreChatRequest,
} from "@/features/chat/hooks/use-chat-mutations";

interface RequestBannerProps {
  conversationId: string;
}

/**
 * Banner at the top of a conversation when viewing a pending chat request.
 * Shows "Accept to continue chatting" with accept/ignore buttons.
 */
export function RequestBanner({ conversationId }: RequestBannerProps) {
  const accept = useAcceptChatRequest();
  const ignore = useIgnoreChatRequest();
  const isPending = accept.isPending || ignore.isPending;

  return (
    <div
      className="flex items-center justify-between border-b bg-muted/30 px-4 py-2"
      data-testid="request-banner"
    >
      <p className="text-sm text-muted-foreground">
        Accept this request to continue chatting
      </p>
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => accept.mutate(conversationId)}
          disabled={isPending}
        >
          <Check className="mr-1 h-3.5 w-3.5" />
          Accept
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => ignore.mutate(conversationId)}
          disabled={isPending}
        >
          <X className="mr-1 h-3.5 w-3.5" />
          Ignore
        </Button>
      </div>
    </div>
  );
}
