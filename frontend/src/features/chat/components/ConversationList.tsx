"use client";

import { useEffect, useMemo, useState } from "react";
import { useInView } from "react-intersection-observer";
import { MessageSquarePlus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatScope } from "@/features/chat/contexts/chat-scope-context";
import {
  useConversations,
  useEntityInbox,
} from "@/features/chat/hooks/use-chat-queries";
import { ChatRequestList } from "./ChatRequestList";
import { ConversationListItem } from "./ConversationListItem";
import { ConversationListSkeleton } from "./ConversationListSkeleton";
import { EmptyConversationList } from "./EmptyStates";
import { ScopeTabBar, type ChatTab } from "./ScopeTabBar";

interface ConversationListProps {
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  showEntityInbox?: boolean;
}

export function ConversationList({
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  showEntityInbox = false,
}: ConversationListProps) {
  const { scopeType, scopeId, participantType, participantId } =
    useChatScope();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<ChatTab>("internal");

  // Internal conversations (scoped)
  const internalParams = useMemo(
    () =>
      scopeType === "global"
        ? {}
        : { scope_type: scopeType, scope_id: scopeId ?? undefined },
    [scopeType, scopeId],
  );
  const internalQuery = useConversations(internalParams);

  // Entity inbox (global scope, only when on inbox tab with entity info)
  const entityQuery = useEntityInbox(
    participantType ?? "",
    participantId ?? "",
  );
  const isEntityInboxActive =
    activeTab === "inbox" && showEntityInbox && !!participantType && !!participantId;

  // Pick the active data source
  const activeQuery = isEntityInboxActive ? entityQuery : internalQuery;
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    activeQuery;

  // Infinite scroll trigger
  const { ref, inView } = useInView({ threshold: 0 });
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Flatten pages and apply client-side search filter
  const allConversations = useMemo(() => {
    const items = data?.pages.flatMap((page) => page.results) ?? [];
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.last_message?.content_preview.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <h2 className="text-sm font-semibold">Chat</h2>
        <Button variant="ghost" size="icon-sm" onClick={onNewConversation}>
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>

      {/* Scope tabs (business/platform only) */}
      {showEntityInbox && (
        <div className="border-b px-3 py-2">
          <ScopeTabBar
            activeTab={activeTab}
            onTabChange={setActiveTab}
            showEntityInbox={showEntityInbox}
          />
        </div>
      )}

      {/* Search */}
      <div className="border-b px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>

      {/* Chat requests (global scope only, not on entity inbox) */}
      {scopeType === "global" && !isEntityInboxActive && (
        <ChatRequestList />
      )}

      {/* Conversation list */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <ConversationListSkeleton />
        ) : allConversations.length === 0 ? (
          <EmptyConversationList onNewConversation={onNewConversation} />
        ) : (
          <div
            className="space-y-0.5 p-1"
            role="listbox"
            aria-label="Conversations"
          >
            {allConversations.map((conversation) => (
              <ConversationListItem
                key={conversation.id}
                conversation={conversation}
                isActive={conversation.id === activeConversationId}
                onClick={onSelectConversation}
                entityType={isEntityInboxActive ? participantType : undefined}
              />
            ))}

            {/* Infinite scroll trigger */}
            {hasNextPage && (
              <div ref={ref} className="py-2">
                {isFetchingNextPage && <ConversationListSkeleton />}
              </div>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
