"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatScope } from "@/features/chat/contexts/chat-scope-context";
import { useCreateConversation } from "@/features/chat/hooks/use-chat-mutations";
import type {
  ConversationType,
  ParticipantIdInput,
} from "@/features/chat/types";
import { searchUsersApi } from "@/features/explore/api/explore-api";

interface NewConversationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (conversationId: string) => void;
}

interface SearchResult {
  id: string;
  display_name: string;
  username: string;
  avatar_url?: string | null;
}

export function NewConversationDialog({
  open,
  onOpenChange,
  onCreated,
}: NewConversationDialogProps) {
  const { scopeType, scopeId } = useChatScope();
  const createConversation = useCreateConversation();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selected, setSelected] = useState<SearchResult[]>([]);
  const [groupName, setGroupName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isGroup = selected.length > 1;
  const conversationType: ConversationType = isGroup ? "group" : "direct";

  // Debounced search
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const response = await searchUsersApi({ q: query });
        setResults(
          response.results.map((u) => ({
            id: u.id,
            display_name: u.display_name,
            username: u.username,
            avatar_url: u.profile?.avatar_url,
          })),
        );
      } catch {
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Filter out already-selected users
  const filteredResults = useMemo(() => {
    const selectedIds = new Set(selected.map((s) => s.id));
    return results.filter((r) => !selectedIds.has(r.id));
  }, [results, selected]);

  const handleSelect = useCallback((user: SearchResult) => {
    setSelected((prev) => [...prev, user]);
    setQuery("");
    setResults([]);
  }, []);

  const handleRemove = useCallback((userId: string) => {
    setSelected((prev) => prev.filter((s) => s.id !== userId));
  }, []);

  const handleReset = useCallback(() => {
    setQuery("");
    setResults([]);
    setSelected([]);
    setGroupName("");
    setError(null);
  }, []);

  const handleCreate = useCallback(async () => {
    if (selected.length === 0) return;

    setError(null);
    const participantIds: ParticipantIdInput[] = selected.map((s) => ({
      participant_type: "user",
      participant_id: s.id,
    }));

    try {
      const conversation = await createConversation.mutateAsync({
        scope_type: scopeType,
        scope_id: scopeId,
        conversation_type: conversationType,
        participant_ids: participantIds,
        name: isGroup ? groupName.trim() || undefined : undefined,
      });
      onCreated(conversation.id);
      onOpenChange(false);
      handleReset();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create conversation",
      );
    }
  }, [
    selected,
    scopeType,
    scopeId,
    conversationType,
    isGroup,
    groupName,
    createConversation,
    onCreated,
    onOpenChange,
    handleReset,
  ]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) handleReset();
      onOpenChange(nextOpen);
    },
    [onOpenChange, handleReset],
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New conversation</DialogTitle>
          <DialogDescription>
            Search for users to start a conversation
          </DialogDescription>
        </DialogHeader>

        {/* Selected participants */}
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {selected.map((user) => (
              <Badge
                key={user.id}
                variant="secondary"
                className="gap-1 pr-1"
              >
                {user.display_name}
                <button
                  type="button"
                  onClick={() => handleRemove(user.id)}
                  className="rounded-full p-0.5 hover:bg-muted"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}

        {/* Group name (when >1 selected) */}
        {isGroup && (
          <div className="space-y-1.5">
            <Label htmlFor="group-name">Group name</Label>
            <Input
              id="group-name"
              placeholder="Enter group name..."
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
            />
          </div>
        )}

        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search users..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-8"
          />
        </div>

        {/* Search results */}
        <ScrollArea className="max-h-48">
          {isSearching ? (
            <div className="space-y-2 p-1">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex items-center gap-2 p-2">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="space-y-1">
                    <Skeleton className="h-3.5 w-24" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredResults.length > 0 ? (
            <div className="space-y-0.5 p-1">
              {filteredResults.map((user) => (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => handleSelect(user)}
                  className="flex w-full items-center gap-2 rounded-md p-2 text-left hover:bg-accent/50"
                >
                  <Avatar size="sm">
                    <AvatarFallback>
                      {user.display_name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {user.display_name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      @{user.username}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          ) : query.length >= 2 && !isSearching ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No users found
            </p>
          ) : null}
        </ScrollArea>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={
              selected.length === 0 || createConversation.isPending
            }
          >
            {createConversation.isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
