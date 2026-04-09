"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CHAT_MESSAGE_MAX_LENGTH } from "@/features/chat/constants/chat-constants";
import { useSendMessage } from "@/features/chat/hooks/use-chat-mutations";
import { useTypingIndicator } from "@/features/chat/hooks/use-typing-indicator";
import { useChatWsClient } from "@/features/chat/contexts/chat-ws-context";
import { useChatStore } from "@/stores/chat-store";
import { useChatScope } from "@/features/chat/contexts/chat-scope-context";
import { EntitySenderBadge } from "./EntitySenderBadge";

interface ComposeBarProps {
  conversationId: string;
  disabled?: boolean;
  disabledMessage?: string;
}

export function ComposeBar({
  conversationId,
  disabled = false,
  disabledMessage,
}: ComposeBarProps) {
  const { participantType } = useChatScope();
  const ws = useChatWsClient();
  const draft = useChatStore((s) => s.drafts[conversationId] ?? "");
  const setDraft = useChatStore((s) => s.setDraft);
  const clearDraft = useChatStore((s) => s.clearDraft);

  const [isSending, setIsSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sendMessage = useSendMessage(conversationId);
  const { onKeystroke, stopTyping } = useTypingIndicator(ws, conversationId);

  // Auto-focus compose input when conversation changes
  useEffect(() => {
    // Small delay to let the layout settle after conversation switch
    const timer = setTimeout(() => textareaRef.current?.focus(), 100);
    return () => clearTimeout(timer);
  }, [conversationId]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      if (value.length <= CHAT_MESSAGE_MAX_LENGTH) {
        setDraft(conversationId, value);
        onKeystroke();
      }
    },
    [conversationId, setDraft, onKeystroke],
  );

  const handleSend = useCallback(async () => {
    const text = draft.trim();
    if (!text || isSending) return;

    stopTyping();
    setIsSending(true);
    try {
      await sendMessage.mutateAsync({ content: text });
      clearDraft(conversationId);
      textareaRef.current?.focus();
    } finally {
      setIsSending(false);
    }
  }, [draft, isSending, sendMessage, clearDraft, conversationId, stopTyping]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  if (disabled) {
    return (
      <div className="border-t bg-muted/30 px-4 py-3">
        <p className="text-center text-sm text-muted-foreground">
          {disabledMessage ?? "You cannot send messages in this conversation"}
        </p>
      </div>
    );
  }

  const isEntitySender = participantType && participantType !== "user";

  return (
    <div className="border-t bg-background px-4 py-3">
      {isEntitySender && (
        <div className="mb-1.5 flex items-center gap-1.5" data-testid="entity-sender-indicator">
          <EntitySenderBadge participantType={participantType} size="sm" />
          <span className="text-xs text-muted-foreground">
            Sending as {participantType === "business" ? "business" : "platform"}
          </span>
        </div>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          placeholder="Type a message..."
          value={draft}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          className="min-h-[40px] max-h-[120px] resize-none text-sm"
          rows={1}
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!draft.trim() || isSending}
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      {draft.length > CHAT_MESSAGE_MAX_LENGTH * 0.9 && (
        <p className="mt-1 text-right text-xs text-muted-foreground">
          {draft.length}/{CHAT_MESSAGE_MAX_LENGTH}
        </p>
      )}
    </div>
  );
}
